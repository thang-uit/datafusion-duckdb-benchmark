// Bộ đếm nguyên tử ghi số lần quy tắc thực sự đổi kế hoạch.
use std::sync::atomic::Ordering;
// Chia sẻ toán tử/kế hoạch bằng tham chiếu đếm, không sao chép dữ liệu.
use std::sync::Arc;

use datafusion::arrow::array::{Array, Float64Array, Int64Array, StringArray};
use datafusion::arrow::datatypes::{DataType, Field, Schema};
use datafusion::arrow::record_batch::RecordBatch;
use datafusion::common::Result;
use datafusion::execution::context::SessionState;
use datafusion::execution::runtime_env::RuntimeEnv;
use datafusion::parquet::arrow::ArrowWriter;
use datafusion::physical_plan::collect;
use datafusion::prelude::{SessionConfig, SessionContext};

use super::q17_rule::StatisticsBuildSideRule;

const SQL: &str = "SELECT SUM(l_extendedprice) / 7.0 AS avg_yearly
FROM lineitem, part
WHERE p_partkey = l_partkey AND p_brand = 'Brand#23' AND p_container = 'MED BOX'
AND l_quantity < (SELECT 0.2 * AVG(l_quantity) FROM lineitem WHERE l_partkey = p_partkey)";

// Tạo Parquet nhỏ có dòng trùng và mặt hàng ngoài bộ lọc để kiểm chứng kết quả.
fn fixture() -> tempfile::TempDir {
    let dir = tempfile::tempdir().unwrap();
    let line_schema = Arc::new(Schema::new(vec![
        Field::new("l_partkey", DataType::Int64, false),
        Field::new("l_quantity", DataType::Float64, false),
        Field::new("l_extendedprice", DataType::Float64, false),
    ]));
    let part_schema = Arc::new(Schema::new(vec![
        Field::new("p_partkey", DataType::Int64, false),
        Field::new("p_brand", DataType::Utf8, false),
        Field::new("p_container", DataType::Utf8, false),
    ]));
    let lines = RecordBatch::try_new(
        line_schema,
        vec![
            Arc::new(Int64Array::from(vec![1, 1, 1, 2, 2, 2, 3])),
            Arc::new(Float64Array::from(vec![1., 9., 20., 1., 1., 20., 1.])),
            Arc::new(Float64Array::from(vec![
                70., 630., 1400., 14., 21., 140., 9999.,
            ])),
        ],
    )
    .unwrap();
    let parts = RecordBatch::try_new(
        part_schema,
        vec![
            Arc::new(Int64Array::from(vec![1, 2, 3])),
            Arc::new(StringArray::from(vec!["Brand#23", "Brand#23", "Other"])),
            Arc::new(StringArray::from(vec!["MED BOX", "MED BOX", "MED BOX"])),
        ],
    )
    .unwrap();
    for (name, batch) in [("lineitem", lines), ("part", parts)] {
        let folder = dir.path().join(name);
        std::fs::create_dir(&folder).unwrap();
        let file = std::fs::File::create(folder.join("part-0.parquet")).unwrap();
        let mut writer = ArrowWriter::try_new(file, batch.schema(), None).unwrap();
        writer.write(&batch).unwrap();
        writer.close().unwrap();
    }
    dir
}

// Dùng cùng SQL và cấu hình, chỉ khác việc đăng ký quy tắc vật lý.
async fn run(dir: &tempfile::TempDir, enabled: bool, sql: &str) -> Result<(f64, usize)> {
    // Hai phương án cùng bật thống kê và một phân vùng để đối chứng công bằng.
    let config = SessionConfig::new()
        // Giữ cùng cấu hình một phân vùng của demo.
        .with_target_partitions(1)
        // Cho nguồn Parquet cung cấp thống kê metadata trước khi chạy.
        .with_collect_statistics(true);
    // Tạo quy tắc và bộ đếm mới cho đúng lượt chạy này.
    let rule = Arc::new(StatisticsBuildSideRule::default());
    // Khởi tạo trạng thái với các bộ tối ưu chuẩn của DataFusion.
    let mut state = SessionState::new_with_config_rt(config, Arc::new(RuntimeEnv::default()));
    // Chỉ thêm quy tắc riêng ở phương án bật, giữ nguyên cấu hình khác.
    if enabled {
        // Điểm mở rộng xanh dương: đăng ký quy tắc vào vòng tối ưu vật lý.
        state = state.add_physical_optimizer_rule(rule.clone());
    }
    // Tạo phiên từ trạng thái đã chọn, không cần máy chủ CSDL.
    let ctx = SessionContext::new_with_state(state);
    for name in ["lineitem", "part"] {
        // Giải đường dẫn từ tpch/ và xác nhận tệp tồn tại.
        let path = dir.path().join(name).join("part-0.parquet");
        ctx.sql(&format!(
            "CREATE EXTERNAL TABLE {name} STORED AS PARQUET LOCATION '{}'",
            path.display()
        ))
        .await?
        .collect()
        .await?;
    }
    // Tạo cây vật lý, các quy tắc được áp dụng ở bước này.
    let plan = ctx.sql(sql).await?.create_physical_plan().await?;
    let schema = plan.schema();
    // DataFusion chạy toán tử và thu các RecordBatch kết quả.
    let batches = collect(plan, ctx.task_ctx()).await?;
    assert_eq!(schema.field(0).name(), "avg_yearly");
    let result = batches[0]
        .column(0)
        .as_any()
        .downcast_ref::<Float64Array>()
        .unwrap()
        .value(0);
    Ok((result, rule.applications.load(Ordering::Relaxed)))
}

#[tokio::test]
// Quy tắc phải giữ kết quả 15.0 và không làm mất dòng bán hàng trùng.
async fn rewrite_preserves_q17_result_and_duplicate_sales_rows() -> Result<()> {
    let dir = fixture();
    let (before, count_before) = run(&dir, false, SQL).await?;
    let (after, count_after) = run(&dir, true, SQL).await?;
    assert_eq!(count_before, 0);
    assert_eq!(count_after, 1);
    assert_eq!(before, 15.0);
    assert_eq!(before, after);
    Ok(())
}

#[tokio::test]
// Kế hoạch đã có phía dựng phù hợp không được đảo ngược lại.
async fn already_swapped_query_is_not_swapped_back() -> Result<()> {
    let dir = fixture();
    let (value, count) = run(
        &dir,
        true,
        &SQL.replace("FROM lineitem, part", "FROM part, lineitem"),
    )
    .await?;
    assert_eq!(count, 0);
    assert_eq!(value, 15.0);
    Ok(())
}

#[tokio::test]
// Đổi literal bộ lọc vẫn hoạt động, chứng minh không nhận diện sẵn riêng Q17.
async fn changed_filter_is_supported_without_literal_matching() -> Result<()> {
    let dir = fixture();
    // Q17 nằm ở dòng 17, chỉ số Rust bắt đầu từ 0 nên dùng nth(16).
    let sql = SQL.replace("p_brand = 'Brand#23'", "p_brand IN ('Brand#23', 'Unused')");
    let (before, _) = run(&dir, false, &sql).await?;
    let (after, count) = run(&dir, true, &sql).await?;
    assert_eq!(count, 1);
    assert_eq!(before, 15.0);
    assert_eq!(before, after);
    Ok(())
}

use super::statistics::{build_cost, row_evidence};
use datafusion::common::ScalarValue;
use datafusion::config::ConfigOptions;
use datafusion::logical_expr::{JoinType, Operator};
use datafusion::physical_expr::expressions::{BinaryExpr, Column, Literal};
// Giao diện đăng ký quy tắc biến đổi kế hoạch vật lý của DataFusion.
use datafusion::physical_optimizer::PhysicalOptimizerRule;
// Toán tử lọc chỉ giữ hoặc bỏ dòng, không sinh dòng mới.
use datafusion::physical_plan::filter::FilterExec;
use datafusion::physical_plan::joins::{HashJoinExec, PartitionMode};
// Nguồn dữ liệu trong bộ nhớ phục vụ kiểm tra quy tắc tổng quát.
use datafusion::physical_plan::memory::MemoryExec;
// Toán tử chọn và sắp lại cột, không thay giá trị dòng.
use datafusion::physical_plan::projection::ProjectionExec;
// Giao diện chung của các toán tử trong cây vật lý.
use datafusion::physical_plan::ExecutionPlan;

type Rows = Vec<Vec<Option<i64>>>;

// Tạo nguồn bộ nhớ với tên cột tùy ý và giá trị NULL cho kiểm thử tổng quát.
fn memory(name: &str, values: Vec<Option<i64>>) -> Arc<dyn ExecutionPlan> {
    let schema = Arc::new(Schema::new(vec![Field::new(name, DataType::Int64, true)]));
    let batch =
        RecordBatch::try_new(schema.clone(), vec![Arc::new(Int64Array::from(values))]).unwrap();
    Arc::new(MemoryExec::try_new(&[vec![batch]], schema, None).unwrap())
}

// Tạo hash join nhỏ để kiểm tra giới hạn và tính đúng của phép đảo.
fn join(
    left: Arc<dyn ExecutionPlan>,
    right: Arc<dyn ExecutionPlan>,
    nulls: bool,
    kind: JoinType,
) -> Arc<dyn ExecutionPlan> {
    let keys = vec![(
        Column::new(left.schema().field(0).name(), 0),
        Column::new(right.schema().field(0).name(), 0),
    )];
    Arc::new(
        HashJoinExec::try_new(
            left,
            right,
            keys,
            None,
            &kind,
            PartitionMode::CollectLeft,
            nulls,
        )
        .unwrap(),
    )
}

// Thu và sắp kết quả để so tính tương đương không phụ thuộc thứ tự dòng.
async fn sorted_rows(plan: Arc<dyn ExecutionPlan>) -> Result<Rows> {
    // Tạo phiên từ trạng thái đã chọn, không cần máy chủ CSDL.
    let ctx = SessionContext::new();
    // DataFusion chạy toán tử và thu các RecordBatch kết quả.
    let batches = collect(plan, ctx.task_ctx()).await?;
    let mut rows = Vec::new();
    for batch in batches {
        for i in 0..batch.num_rows() {
            let mut row = Vec::new();
            for col in batch.columns() {
                let a = col.as_any().downcast_ref::<Int64Array>().unwrap();
                row.push(if a.is_null(i) { None } else { Some(a.value(i)) });
            }
            rows.push(row);
        }
    }
    rows.sort();
    Ok(rows)
}

#[tokio::test]
// Kiểm tra đổi tên cột, NULL, dòng trùng và áp quy tắc nhiều lần không đổi sai.
async fn generic_names_duplicates_nulls_and_idempotence() -> Result<()> {
    for nulls in [false, true] {
        let left = memory(
            "invoice_key",
            (0..100)
                .map(|n| if n % 10 == 0 { None } else { Some(n % 3) })
                .collect(),
        );
        let right = memory("catalogue_key", vec![Some(1), Some(1), None]);
        // Tạo cây vật lý, các quy tắc được áp dụng ở bước này.
        let plan = join(left, right, nulls, JoinType::Inner);
        let original = sorted_rows(plan.clone()).await?;
        // Tạo quy tắc và bộ đếm mới cho đúng lượt chạy này.
        let rule = StatisticsBuildSideRule::default();
        // Tạo phép nối với đầu vào đảo lại và phục hồi cột cho toán tử cha.
        let rewritten = rule.optimize(plan.clone(), &ConfigOptions::default())?;
        assert_eq!(rewritten.schema(), plan.schema());
        assert_eq!(rule.applications.load(Ordering::Relaxed), 1);
        assert_eq!(original, sorted_rows(rewritten.clone()).await?);
        rule.optimize(rewritten, &ConfigOptions::default())?;
        assert_eq!(rule.applications.load(Ordering::Relaxed), 1);
    }
    Ok(())
}

#[test]
// Filter/Projection truyền giới hạn metadata, không lấy số dòng đã lọc để quyết định.
fn filter_projection_propagate_bounds_not_observed_matches() -> Result<()> {
    // Deliberately no matches: the estimate must NOT execute/count the filter.
    let source = memory("unrelated_key", (0..100).map(Some).collect());
    let predicate = Arc::new(BinaryExpr::new(
        Arc::new(Column::new("unrelated_key", 0)),
        Operator::Eq,
        Arc::new(Literal::new(ScalarValue::Int64(Some(-999)))),
    ));
    let filtered: Arc<dyn ExecutionPlan> = Arc::new(FilterExec::try_new(predicate, source)?);
    let projected: Arc<dyn ExecutionPlan> = Arc::new(ProjectionExec::try_new(
        vec![(
            Arc::new(Column::new("unrelated_key", 0)),
            "renamed".to_owned(),
        )],
        filtered,
    )?);
    let evidence = row_evidence(&projected);
    assert_eq!(evidence.lower_rows, 0);
    assert_eq!(evidence.upper_rows, Some(100));
    Ok(())
}

#[test]
// Phía phải lớn hơn hoặc khoảng chồng lấp phải giữ kế hoạch ban đầu.
fn larger_right_and_overlapping_filter_bounds_keep_order() -> Result<()> {
    let left = memory("x", vec![Some(1); 3]);
    let right = memory("y", vec![Some(1); 100]);
    // Tạo quy tắc và bộ đếm mới cho đúng lượt chạy này.
    let rule = StatisticsBuildSideRule::default();
    rule.optimize(
        join(left, right, false, JoinType::Inner),
        &ConfigOptions::default(),
    )?;
    assert_eq!(rule.applications.load(Ordering::Relaxed), 0);
    let make_filtered = |name: &str, n| -> Result<Arc<dyn ExecutionPlan>> {
        let source = memory(name, vec![Some(1); n]);
        let predicate = Arc::new(BinaryExpr::new(
            Arc::new(Column::new(name, 0)),
            Operator::Gt,
            Arc::new(Literal::new(ScalarValue::Int64(Some(0)))),
        ));
        Ok(Arc::new(FilterExec::try_new(predicate, source)?))
    };
    rule.optimize(
        join(
            make_filtered("a", 100)?,
            make_filtered("b", 3)?,
            false,
            JoinType::Inner,
        ),
        &ConfigOptions::default(),
    )?;
    assert_eq!(rule.applications.load(Ordering::Relaxed), 0);
    Ok(())
}

#[tokio::test]
// Không áp phép đảo INNER cho OUTER join vì có thể đổi ý nghĩa kết quả.
async fn outer_join_is_preserved() -> Result<()> {
    // Tạo cây vật lý, các quy tắc được áp dụng ở bước này.
    let plan = join(
        memory("x", vec![Some(1); 100]),
        memory("y", vec![Some(2)]),
        false,
        JoinType::Left,
    );
    // Tạo quy tắc và bộ đếm mới cho đúng lượt chạy này.
    let rule = StatisticsBuildSideRule::default();
    // Tạo phép nối với đầu vào đảo lại và phục hồi cột cho toán tử cha.
    let rewritten = rule.optimize(plan.clone(), &ConfigOptions::default())?;
    assert_eq!(rule.applications.load(Ordering::Relaxed), 0);
    assert_eq!(sorted_rows(plan).await?, sorted_rows(rewritten).await?);
    Ok(())
}

#[test]
// Toán tử lạ, cột chuỗi và tràn số phải để chưa biết thay vì đoán chi phí.
fn unknown_operators_variable_width_and_overflow_are_not_invented() {
    use datafusion::physical_plan::empty::EmptyExec;
    let unknown: Arc<dyn ExecutionPlan> =
        Arc::new(EmptyExec::new(false, Arc::new(Schema::empty())));
    let e = row_evidence(&unknown);
    assert_eq!(e.upper_rows, None);
    assert!(build_cost(
        &e,
        &Schema::new(vec![Field::new("s", DataType::Utf8, true)])
    )
    .is_none());
    let exact = super::statistics::RowEvidence {
        lower_rows: usize::MAX,
        upper_rows: Some(usize::MAX),
        estimated_rows: None,
        explanation: "overflow test".to_owned(),
    };
    let c = build_cost(
        &exact,
        &Schema::new(vec![Field::new("n", DataType::Int64, false)]),
    )
    .unwrap();
    assert_eq!(c.upper_bytes, None);
    assert_eq!(c.lower_bytes, None);
}
