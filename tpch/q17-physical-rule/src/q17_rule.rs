//! Generic, conservative build-side selection from pre-execution row bounds.
//! Swap/projection mechanics follow DataFusion 32's swap_hash_join.

use crate::statistics::{build_cost, row_evidence, BuildCost, RowEvidence};
use datafusion::common::tree_node::{Transformed, TreeNode};
use datafusion::common::{DataFusionError, JoinType, Result};
use datafusion::config::ConfigOptions;
// Biểu thức cột dùng để khôi phục vị trí cột sau đổi hai đầu vào.
use datafusion::physical_expr::expressions::Column;
// Kiểu chung của biểu thức vật lý trong Projection.
use datafusion::physical_expr::PhysicalExpr;
// Giao diện đăng ký quy tắc biến đổi kế hoạch vật lý của DataFusion.
use datafusion::physical_optimizer::PhysicalOptimizerRule;
use datafusion::physical_plan::joins::{HashJoinExec, PartitionMode};
// Toán tử chọn và sắp lại cột, không thay giá trị dòng.
use datafusion::physical_plan::projection::ProjectionExec;
// Giao diện chung của các toán tử trong cây vật lý.
use datafusion::physical_plan::ExecutionPlan;
// Chuyển kết quả và bằng chứng thành JSON cho notebook.
use serde::Serialize;
// Bộ đếm nguyên tử ghi số lần quy tắc thực sự đổi kế hoạch.
use std::sync::atomic::{AtomicUsize, Ordering};
// Arc chia sẻ quy tắc, Mutex bảo vệ nhật ký quyết định.
use std::sync::{Arc, Mutex};

#[derive(Clone, Debug, Serialize)]
// Một quyết định có cả căn cứ hai phía và lý do đổi hoặc giữ.
pub struct JoinDecision {
    // Tên các khóa hai phía để nhận diện phép nối trong nhật ký.
    pub join_keys: Vec<(String, String)>,
    // Căn cứ số dòng của phía trái trước biến đổi.
    pub left: RowEvidence,
    // Căn cứ số dòng của phía phải trước biến đổi.
    pub right: RowEvidence,
    // Khoảng chi phí mô hình cho phía dựng ban đầu.
    pub left_cost: Option<BuildCost>,
    // Khoảng chi phí mô hình nếu đổi sang phía phải.
    pub right_cost: Option<BuildCost>,
    // True chỉ khi quy tắc quyết định tạo phép nối đảo đầu vào.
    pub swapped: bool,
    // Lý do giữ hoặc đổi để người đọc kiểm tra được lựa chọn.
    pub reason: String,
}

#[derive(Debug, Default)]
// Quy tắc được dùng lại trên cây, giữ bộ đếm và nhật ký riêng.
pub struct StatisticsBuildSideRule {
    // Bộ đếm số lần biến đổi thành công, không phải số dòng kết quả.
    pub applications: AtomicUsize,
    // Nhật ký căn cứ và quyết định được chốt trước collect.
    decisions: Mutex<Vec<JoinDecision>>,
}

impl StatisticsBuildSideRule {
    // Lấy bản sao nhật ký đã khóa để không thay đổi bằng chứng gốc.
    pub fn decisions(&self) -> Result<Vec<JoinDecision>> {
        // Ghi bằng chứng trước thực thi vào nhật ký được bảo vệ.
        self.decisions
            .lock()
            .map(|v| v.clone())
            .map_err(|_| DataFusionError::Internal("Join decision log lock poisoned".to_owned()))
    }
}

impl PhysicalOptimizerRule for StatisticsBuildSideRule {
    // DataFusion gọi hàm này trong vòng tối ưu kế hoạch vật lý.
    fn optimize(
        &self,
        plan: Arc<dyn ExecutionPlan>,
        _config: &ConfigOptions,
    ) -> Result<Arc<dyn ExecutionPlan>> {
        // Duyệt từ toán tử con lên cha, bảo toàn cấu trúc các nhánh chưa đổi.
        plan.transform_up(&|node| {
            // Chỉ xét HashJoinExec, các loại toán tử khác đi qua nguyên trạng.
            let Some(join) = node.as_any().downcast_ref::<HashJoinExec>() else {
                // Không đủ điều kiện hoặc không có lợi thế, giữ nguyên toán tử.
                return Ok(Transformed::No(node));
            };
            // Appended after standard rules: exchanging distributed children here
            // could invalidate enforced distributions. Restrict to one partition.
            if *join.join_type() != JoinType::Inner
                || *join.partition_mode() != PartitionMode::CollectLeft
                || join.filter().is_some()
                || join.left().output_partitioning().partition_count() != 1
                || join.right().output_partitioning().partition_count() != 1
            {
                // Không đủ điều kiện hoặc không có lợi thế, giữ nguyên toán tử.
                return Ok(Transformed::No(node));
            }
            // Lấy số dòng hoặc giới hạn của phía đang dựng bảng băm.
            let left = row_evidence(join.left());
            // Lấy căn cứ tương tự của phía đang dò.
            let right = row_evidence(join.right());
            // Ước chi phí phía trái bằng số dòng và độ rộng cột đã biết.
            let left_cost = build_cost(&left, join.left().schema().as_ref());
            // Dùng cùng mô hình cho phía phải để so sánh.
            let right_cost = build_cost(&right, join.right().schema().as_ref());
            // The intervals bound the COST MODEL, not actual allocator usage.
            let swapped = matches!((&left_cost, &right_cost), (Some(l), Some(r))
                if matches!((r.upper_bytes, l.lower_bytes), (Some(ru), Some(ll)) if ru < ll));
            // Ghi rõ lý do lựa chọn để notebook có thể giải thích quyết định.
            let reason = if swapped {
                "right_upper_model_cost < left_lower_model_cost"
            } else {
                "insufficient_or_overlapping_cost_bounds_keep_order"
            };
            // Ghi bằng chứng trước thực thi vào nhật ký được bảo vệ.
            self.decisions
                .lock()
                .map_err(|_| {
                    DataFusionError::Internal("Join decision log lock poisoned".to_owned())
                })?
                // Lưu cả giới hạn và ước lượng, không nhập nhằng hai loại thông tin.
                .push(JoinDecision {
                    join_keys: join
                        .on()
                        .iter()
                        .map(|(l, r)| (l.name().to_owned(), r.name().to_owned()))
                        .collect(),
                    left,
                    right,
                    left_cost,
                    right_cost,
                    swapped,
                    reason: reason.to_owned(),
                });
            // Khoảng chồng lấp hoặc thiếu căn cứ không được ép đổi kế hoạch.
            if !swapped {
                // Không đủ điều kiện hoặc không có lợi thế, giữ nguyên toán tử.
                return Ok(Transformed::No(node));
            }
            // Tạo phép nối với đầu vào đảo lại và phục hồi cột cho toán tử cha.
            let rewritten = swap_inner_join_preserving_schema(join)?;
            // Chỉ tăng số lần rewrite khi đã tạo kế hoạch thay thế thành công.
            self.applications.fetch_add(1, Ordering::Relaxed);
            // Báo bộ tối ưu rằng toán tử đã được biến đổi.
            Ok(Transformed::Yes(rewritten))
        })
    }
    // Tên quy tắc được đưa vào đầu ra EXPLAIN và JSON.
    fn name(&self) -> &str {
        "statistics_build_side"
    }
    // Yêu cầu DataFusion kiểm tra lược đồ đầu ra sau rewrite.
    fn schema_check(&self) -> bool {
        true
    }
}

/// Swap only the supported INNER join and restore its original output schema.
fn swap_inner_join_preserving_schema(join: &HashJoinExec) -> Result<Arc<dyn ExecutionPlan>> {
    // Lưu thứ tự và tên cột của đầu vào trái ban đầu.
    let left_schema = join.left().schema();
    // Lưu lược đồ đầu vào phải ban đầu.
    let right_schema = join.right().schema();
    // Dùng lại HashJoinExec của DataFusion, không cài hash join mới.
    let swapped: Arc<dyn ExecutionPlan> = Arc::new(HashJoinExec::try_new(
        // Phía phải cũ trở thành phía dựng mới trong CollectLeft.
        Arc::clone(join.right()),
        // Phía trái cũ chuyển sang phía dò.
        Arc::clone(join.left()),
        join.on()
            .iter()
            // Đảo khóa nối cùng đầu vào để vẫn ghép đúng giá trị.
            .map(|(l, r)| (r.clone(), l.clone()))
            .collect(),
        None, // The rule rejects joins with an additional join filter.
        &JoinType::Inner,
        PartitionMode::CollectLeft,
        // Giữ nguyên quy tắc so khớp NULL của phép nối gốc.
        join.null_equals_null(),
    )?);

    // The swap emits [old right, old left]. Restore [old left, old right]
    // because upstream Q17 expressions still refer to the original column indices.
    let mut expressions: Vec<(Arc<dyn PhysicalExpr>, String)> = Vec::new();
    // Các cột trái cũ hiện nằm sau toàn bộ cột phải cũ.
    for (index, field) in left_schema.fields().iter().enumerate() {
        expressions.push((
            Arc::new(Column::new(
                field.name(),
                // Dịch chỉ số qua số cột bên phải để trỏ đúng cột trái cũ.
                right_schema.fields().len() + index,
            )),
            field.name().clone(),
        ));
    }
    // Sau nhóm trái cũ, thêm các cột phải cũ ở vị trí đầu của join mới.
    for (index, field) in right_schema.fields().iter().enumerate() {
        expressions.push((
            Arc::new(Column::new(field.name(), index)),
            field.name().clone(),
        ));
    }
    // Projection chỉ phục hồi cột, không thay điều kiện hay giá trị kết quả.
    let result: Arc<dyn ExecutionPlan> = Arc::new(ProjectionExec::try_new(expressions, swapped)?);
    // Từ chối kế hoạch nếu thứ tự, kiểu hoặc tên cột bị thay đổi.
    if result.schema() != join.schema() {
        return Err(DataFusionError::Plan(
            "Q17 rewrite changed the output schema".to_owned(),
        ));
    }
    Ok(result)
}
