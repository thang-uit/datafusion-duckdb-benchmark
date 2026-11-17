//! Standalone DataFusion 32 runner; the original SQL is read, never rewritten.

// Mô-đun triển khai điểm mở rộng tối ưu kế hoạch vật lý.
mod q17_rule;
// Mô-đun suy luận giới hạn dòng và chi phí dựng theo mô hình.
mod statistics;
#[cfg(test)]
// Chỉ biên dịch kiểm thử khi chạy cargo test.
mod tests;

// Đường dẫn hệ điều hành dùng để tìm kho và tệp SQL.
use std::path::PathBuf;
// Bộ đếm nguyên tử ghi số lần quy tắc thực sự đổi kế hoạch.
use std::sync::atomic::Ordering;
// Chia sẻ toán tử/kế hoạch bằng tham chiếu đếm, không sao chép dữ liệu.
use std::sync::Arc;
// Đồng hồ đơn điệu dùng để tách thời gian chuẩn bị, lập kế hoạch và chạy.
use std::time::Instant;

use datafusion::arrow::array::{Array, Float64Array};
// Kiểu kết quả và lỗi thống nhất với DataFusion.
use datafusion::common::{DataFusionError, Result};
use datafusion::execution::context::SessionState;
use datafusion::execution::runtime_env::RuntimeEnv;
// Thực thi kế hoạch và xuất cây toán tử để đối chiếu.
use datafusion::physical_plan::{collect, displayable};
use datafusion::prelude::{SessionConfig, SessionContext};
// Chuyển kết quả và bằng chứng thành JSON cho notebook.
use serde::Serialize;

use q17_rule::{JoinDecision, StatisticsBuildSideRule};

#[derive(Serialize)]
// Cấu trúc JSON trả cho notebook, tách số liệu trước và sau thực thi.
struct RunResult {
    // Phiên bản bộ máy Rust, kiểm tra với yêu cầu 32.0.0 của notebook.
    datafusion_version: &'static str,
    // Lượt chạy có đăng ký quy tắc riêng hay chỉ dùng quy tắc chuẩn.
    rule_enabled: bool,
    // Tên quy tắc để kiểm tra binary đúng phiên bản demo.
    rule_name: &'static str,
    // Số phép nối được quy tắc thay đổi trước khi thực thi.
    rule_applications: usize,
    // Xác nhận hai phương án cùng bật thống kê nguồn.
    collect_statistics: bool,
    // False ở plan-only, không dùng bản đó để so thời gian thực thi.
    execution_performed: bool,
    // Nhật ký căn cứ và quyết định được chốt trước collect.
    decisions: Vec<JoinDecision>,
    // Nguyên văn SQL Q17 của kho benchmark.
    sql: String,
    // Thời gian đăng ký bảng và thu metadata, tách khỏi lập kế hoạch.
    preparation_seconds: f64,
    // Thời gian tạo và tối ưu kế hoạch vật lý.
    planning_seconds: f64,
    // Tổng gồm chuẩn bị, lập kế hoạch và collect, không gồm in JSON.
    preparation_planning_execution_seconds: f64,
    // Thời gian collect trên kế hoạch đã chọn.
    execution_seconds: f64,
    // Tổng lập kế hoạch và collect, không gồm khởi động tiến trình.
    total_seconds: f64,
    // Một giá trị Q17, None nếu chỉ lập kế hoạch.
    value: Option<f64>,
    // Số dòng kết quả đã thu sau thực thi.
    output_rows: usize,
    // Cây vật lý được chọn để đối chiếu các đầu vào.
    physical_plan: String,
    // Cùng cây vật lý sau thực thi, kèm các bộ đếm thực tế.
    physical_plan_with_metrics: String,
}

// Tạo lỗi lập kế hoạch có thông báo rõ cho người gọi.
fn invalid(message: &str) -> DataFusionError {
    DataFusionError::Plan(message.to_owned())
}

#[tokio::main(flavor = "current_thread")]
// Đọc cấu hình, lập kế hoạch rồi chỉ thực thi khi không có --plan-only.
async fn main() -> Result<()> {
    // Bỏ tên chương trình để đọc thư mục benchmark và chế độ on/off.
    let mut args = std::env::args().skip(1);
    // Chuẩn hóa đường dẫn kho được truyền vào, không hardcode đường dẫn máy.
    let benchmark = PathBuf::from(
        args.next()
            .ok_or_else(|| invalid("Missing benchmark root"))?,
    )
    .canonicalize()?;
    // Chỉ chấp nhận on hoặc off để hai phương án có ý nghĩa rõ ràng.
    let enabled = match args.next().as_deref() {
        Some("on") => true,
        Some("off") => false,
        _ => return Err(invalid("Rule mode must be on or off")),
    };
    // Cờ plan-only chỉ đọc metadata và lập kế hoạch, chưa collect Q17.
    let plan_only = match args.next().as_deref() {
        None => false,
        Some("--plan-only") => true,
        _ => return Err(invalid("Unexpected argument; use --plan-only")),
    };
    // Từ chối tham số dư để tránh hiểu sai chế độ chạy.
    if args.next().is_some() {
        return Err(invalid("Unexpected arguments"));
    }
    // Thư mục giữ SQL và DDL của benchmark.
    let tpch = benchmark.join("tpch");
    // Đọc đúng tệp truy vấn của tác giả.
    let query_file = std::fs::read_to_string(tpch.join("queries.sql"))?;
    // Q17 nằm ở dòng 17, chỉ số Rust bắt đầu từ 0 nên dùng nth(16).
    let sql = query_file
        .lines()
        .nth(16)
        .ok_or_else(|| invalid("queries.sql has no Q17"))?
        .to_owned();
    // Bắt đầu đo đăng ký bảng và thu metadata riêng với SELECT.
    let prepare_start = Instant::now();
    // Both controls collect the same metadata; only the extension differs.
    let config = SessionConfig::new()
        // Giữ cùng cấu hình một phân vùng của demo.
        .with_target_partitions(1)
        // Cho nguồn Parquet cung cấp thống kê metadata trước khi chạy.
        .with_collect_statistics(true);
    // Tạo tài nguyên thực thi mặc định cho phiên nhúng.
    let runtime = Arc::new(RuntimeEnv::default());
    // Tạo quy tắc và bộ đếm mới cho đúng lượt chạy này.
    let rule = Arc::new(StatisticsBuildSideRule::default());
    // Khởi tạo trạng thái với các bộ tối ưu chuẩn của DataFusion.
    let mut state = SessionState::new_with_config_rt(config, runtime);
    // Chỉ thêm quy tắc riêng ở phương án bật, giữ nguyên cấu hình khác.
    if enabled {
        // This registration is the ExecutionPlan Rewrite extension point.
        state = state.add_physical_optimizer_rule(rule.clone());
    }
    // Tạo phiên từ trạng thái đã chọn, không cần máy chủ CSDL.
    let ctx = SessionContext::new_with_state(state);
    // Đọc các câu đăng ký cùng nguồn Parquet như benchmark Python.
    let ddl_file = std::fs::read_to_string(tpch.join("create-single-datafusion.sql"))?;
    // Đăng ký từng bảng, bỏ dòng trống trong DDL.
    for line in ddl_file.lines().filter(|l| !l.trim().is_empty()) {
        // Tìm dấu nháy mở bao quanh đường dẫn tệp trong DDL.
        let first = line
            .find('\'')
            .ok_or_else(|| invalid("Missing path in external-table DDL"))?;
        // Tìm dấu nháy đóng của đường dẫn đó.
        let last = line
            .rfind('\'')
            .ok_or_else(|| invalid("Missing path in external-table DDL"))?;
        // Từ chối DDL lỗi trước khi cắt chuỗi đường dẫn.
        if last <= first {
            return Err(invalid("Invalid external-table DDL path"));
        }
        // Giải đường dẫn từ tpch/ và xác nhận tệp tồn tại.
        let path = tpch.join(&line[first + 1..last]).canonicalize()?;
        // Chỉ thay đường dẫn nguồn bằng bản tuyệt đối, giữ tên bảng và định dạng.
        let ddl = format!(
            "{}'{}'{}",
            &line[..first],
            path.to_string_lossy().replace('\'', "''"),
            &line[last + 1..]
        );
        // Thực thi DDL đăng ký nguồn, chưa chạy truy vấn Q17.
        ctx.sql(&ddl).await?.collect().await?;
    }

    // Kết thúc thời gian đăng ký nguồn và metadata.
    let preparation_seconds = prepare_start.elapsed().as_secs_f64();
    // Bắt đầu khoảng đo lập kế hoạch.
    let start = Instant::now();
    // Đọc và phân tích nguyên văn Q17.
    let query = ctx.sql(&sql).await?;
    // Tạo cây vật lý, các quy tắc được áp dụng ở bước này.
    let plan = query.create_physical_plan().await?;
    // Tách riêng thời gian lập kế hoạch trước collect.
    let planning_seconds = start.elapsed().as_secs_f64();
    // Đọc số lần rewrite trước khi có dòng kết quả thực thi.
    let applications = rule.applications.load(Ordering::Relaxed);
    // Snapshot evidence BEFORE collect: decisions cannot depend on observed row counts.
    let decisions = rule.decisions()?;
    // Plan-only trả chưa có kết quả, chế độ thường mới đi vào collect.
    let (execution_seconds, output_rows, value) = if plan_only {
        // Chưa chạy nên không báo một giá trị Q17 giả tạo.
        (0.0, 0, None)
    } else {
        // Bắt đầu đồng hồ thực thi kế hoạch đã chọn.
        let execute_start = Instant::now();
        // DataFusion chạy toán tử và thu các RecordBatch kết quả.
        let batches = collect(plan.clone(), ctx.task_ctx()).await?;
        // Kết thúc đồng hồ sau khi collect hoàn tất.
        let elapsed = execute_start.elapsed().as_secs_f64();
        // Đếm dòng của kết quả đã thu, không dùng để chọn kế hoạch trước đó.
        let output_rows: usize = batches.iter().map(|b| b.num_rows()).sum();
        // Lấy cột kết quả kiểu Float64 mà Q17 trả về.
        let values = batches
            .first()
            .and_then(|b| b.column(0).as_any().downcast_ref::<Float64Array>())
            .ok_or_else(|| invalid("Q17 did not return a Float64 result"))?;
        // Q17 phải trả một giá trị khác NULL trước khi chấp nhận đối chứng.
        if output_rows != 1 || values.is_null(0) {
            return Err(invalid("Q17 did not return one non-null value"));
        }
        // Đưa số đo thực thi và giá trị thật vào bản ghi.
        (elapsed, output_rows, Some(values.value(0)))
    };
    // Ghép phiên bản, SQL, bằng chứng và thời gian thành một JSON.
    let record = RunResult {
        datafusion_version: "32.0.0",
        rule_enabled: enabled,
        rule_name: "statistics_build_side",
        rule_applications: applications,
        collect_statistics: true,
        execution_performed: !plan_only,
        decisions,
        sql,
        preparation_seconds,
        planning_seconds,
        preparation_planning_execution_seconds: preparation_seconds
            + planning_seconds
            + execution_seconds,
        execution_seconds,
        total_seconds: planning_seconds + execution_seconds,
        value,
        output_rows,
        physical_plan: displayable(plan.as_ref()).indent(true).to_string(),
        physical_plan_with_metrics:
            datafusion::physical_plan::display::DisplayableExecutionPlan::with_metrics(
                plan.as_ref(),
            )
            .indent(true)
            .to_string(),
    };
    // In JSON sau khoảng đo để notebook đọc, không tính thời gian in vào SELECT.
    println!(
        "{}",
        serde_json::to_string(&record).map_err(|e| invalid(&e.to_string()))?
    );
    Ok(())
}
