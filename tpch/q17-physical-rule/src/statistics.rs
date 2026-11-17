//! Statistics-only evidence: never executes input plans or matches table names.

use datafusion::arrow::datatypes::{DataType, Schema};
// Nguồn Parquet cung cấp thống kê metadata trước thực thi.
use datafusion::datasource::physical_plan::ParquetExec;
// Gom nhiều lô nhỏ mà không đổi tổng số dòng.
use datafusion::physical_plan::coalesce_batches::CoalesceBatchesExec;
// Toán tử lọc chỉ giữ hoặc bỏ dòng, không sinh dòng mới.
use datafusion::physical_plan::filter::FilterExec;
// Nguồn dữ liệu trong bộ nhớ phục vụ kiểm tra quy tắc tổng quát.
use datafusion::physical_plan::memory::MemoryExec;
// Toán tử chọn và sắp lại cột, không thay giá trị dòng.
use datafusion::physical_plan::projection::ProjectionExec;
// Giao diện chung của các toán tử trong cây vật lý.
use datafusion::physical_plan::ExecutionPlan;
// Chuyển kết quả và bằng chứng thành JSON cho notebook.
use serde::Serialize;
// Chia sẻ toán tử/kế hoạch bằng tham chiếu đếm, không sao chép dữ liệu.
use std::sync::Arc;

// Approximate per-row hash/index/link overhead, a model parameter, not measured RAM.
pub const HASH_OVERHEAD_BYTES_PER_ROW: usize = 32;

#[derive(Clone, Debug, Serialize)]
// Phân biệt giới hạn dưới, giới hạn trên và số dòng ước lượng.
pub struct RowEvidence {
    // Cận dưới có căn cứ của số dòng đầu ra.
    pub lower_rows: usize,
    // Cận trên có căn cứ, None nghĩa chưa biết.
    pub upper_rows: Option<usize>,
    // Ước lượng nếu toán tử cung cấp, khác với hai cận chắc chắn.
    pub estimated_rows: Option<usize>,
    // Giải thích nguồn thống kê và cách truyền giới hạn qua toán tử.
    pub explanation: String,
}

impl RowEvidence {
    // Không đủ thông tin thì trả cận dưới 0, cận trên và ước lượng chưa biết.
    fn unknown(reason: &str) -> Self {
        Self {
            lower_rows: 0,
            upper_rows: None,
            estimated_rows: None,
            explanation: reason.to_owned(),
        }
    }
}

// Suy luận từ metadata và tính chất toán tử, tuyệt đối không thực thi đầu vào.
pub fn row_evidence(plan: &Arc<dyn ExecutionPlan>) -> RowEvidence {
    // Projection thay cột nhưng giữ số dòng nên truyền căn cứ từ đầu vào.
    if let Some(projection) = plan.as_any().downcast_ref::<ProjectionExec>() {
        let mut e = row_evidence(projection.input());
        e.explanation = format!("Projection preserves rows -> {}", e.explanation);
        return e;
    }
    // CoalesceBatches chỉ gom lô nên giữ giới hạn dòng.
    if let Some(coalesce) = plan.as_any().downcast_ref::<CoalesceBatchesExec>() {
        let mut e = row_evidence(coalesce.input());
        e.explanation = format!("Coalesce preserves rows -> {}", e.explanation);
        return e;
    }
    // Bộ lọc có thể loại mọi dòng, không tự giả định tỷ lệ lọc.
    if let Some(filter) = plan.as_any().downcast_ref::<FilterExec>() {
        let mut e = row_evidence(filter.input());
        // Filter có thể trả 0 dòng dù đầu vào có nhiều dòng.
        e.lower_rows = 0;
        // Nếu DataFusion có số ước lượng thì giữ riêng, không thay giới hạn bằng nó.
        e.estimated_rows = filter.statistics().num_rows;
        e.explanation = format!(
            "Filter cannot add rows; output estimate may be absent -> {}",
            e.explanation
        );
        return e;
    }
    // Đọc thống kê Parquet đã thu lúc đăng ký nguồn.
    if let Some(scan) = plan.as_any().downcast_ref::<ParquetExec>() {
        // Thống kê nguồn chứa số dòng và cờ chính xác.
        let stats = scan.base_config().statistics.clone();
        // Chỉ dùng số dòng nguồn làm cận chắc chắn khi metadata chính xác.
        if stats.is_exact {
            // Cần có cả số dòng lẫn cờ exact trước khi tạo giới hạn.
            if let Some(n) = stats.num_rows {
                // LIMIT nếu có làm giảm số dòng tối đa có thể trả.
                let upper = scan.base_config().limit.map_or(n, |limit| n.min(limit));
                // Scan có predicate thì số dòng nguồn chỉ còn là cận trên đầu ra.
                let has_predicate = scan.predicate().is_some();
                // Trả căn cứ từ nguồn, chưa có số dòng quan sát sau chạy.
                return RowEvidence {
                    lower_rows: if has_predicate { 0 } else { upper },
                    upper_rows: Some(upper),
                    estimated_rows: if has_predicate { None } else { Some(upper) },
                    explanation: if has_predicate {
                        "Exact Parquet metadata row count; scan predicate makes it an upper bound"
                    } else {
                        "Exact Parquet metadata row count"
                    }
                    .to_owned(),
                };
            }
        }
        // Không đủ metadata thì không tự gán kích thước cho nguồn.
        return RowEvidence::unknown("Parquet metadata statistics absent or inexact");
    }
    // MemoryExec exposes exact source cardinality, useful for generic verification.
    if plan.as_any().is::<MemoryExec>() {
        // Lấy thống kê do toán tử cung cấp, không đọc dữ liệu qua collect.
        let stats = plan.statistics();
        // Cần có cả số dòng lẫn cờ exact trước khi tạo giới hạn.
        if let Some(n) = stats.num_rows.filter(|_| stats.is_exact) {
            // Trả căn cứ từ nguồn, chưa có số dòng quan sát sau chạy.
            return RowEvidence {
                lower_rows: n,
                upper_rows: Some(n),
                estimated_rows: Some(n),
                explanation: "Exact in-memory source row count".to_owned(),
            };
        }
    }
    // Toán tử chưa hỗ trợ không được suy ra giới hạn không có căn cứ.
    RowEvidence::unknown("Unsupported operator: do not infer a row bound")
}

#[derive(Clone, Debug, Serialize)]
// Khoảng chi phí theo mô hình byte, khác chi phí RAM hoặc CPU đo thực tế.
pub struct BuildCost {
    // Tổng độ rộng các cột cố định, không tự đoán kích thước chuỗi.
    pub projected_fixed_width_bytes: usize,
    // Tham số chi phí băm cho mỗi dòng của mô hình.
    pub hash_overhead_bytes_per_row: usize,
    // Cận dưới theo mô hình byte, None nếu phép nhân tràn số.
    pub lower_bytes: Option<usize>,
    // Cận trên theo mô hình byte, không phải RAM thực tế.
    pub upper_bytes: Option<usize>,
}

// Chỉ tính kiểu có độ rộng cố định, không đoán kích thước chuỗi và kiểu lồng.
fn fixed_width(schema: &Schema) -> Option<usize> {
    // Cộng độ rộng từng cột, trả None ngay khi thiếu mô hình hoặc tràn số.
    schema.fields().iter().try_fold(0usize, |sum, field| {
        // Đổi kiểu cột sang số byte mô hình cho một dòng.
        let width = match field.data_type() {
            DataType::Int8 | DataType::UInt8 => 1,
            DataType::Int16 | DataType::UInt16 | DataType::Float16 => 2,
            DataType::Int32 | DataType::UInt32 | DataType::Float32 | DataType::Date32 => 4,
            DataType::Int64
            | DataType::UInt64
            | DataType::Float64
            | DataType::Date64
            | DataType::Timestamp(_, _)
            | DataType::Duration(_) => 8,
            DataType::Decimal128(_, _) => 16,
            DataType::Decimal256(_, _) => 32,
            // Unknown string/nested widths: do not fabricate a byte cost.
            _ => return None,
        };
        // Tránh tràn số khi cộng độ rộng nhiều cột.
        sum.checked_add(width)
    })
}

// Tính cận chi phí bằng số dòng nhân độ rộng và chi phí băm mô hình.
pub fn build_cost(evidence: &RowEvidence, schema: &Schema) -> Option<BuildCost> {
    // Nếu không biết độ rộng cột thì không so chi phí hai phía.
    let width = fixed_width(schema)?;
    // Thêm chi phí băm cố định và kiểm tra tràn số.
    let per_row = width.checked_add(HASH_OVERHEAD_BYTES_PER_ROW)?;
    Some(BuildCost {
        projected_fixed_width_bytes: width,
        hash_overhead_bytes_per_row: HASH_OVERHEAD_BYTES_PER_ROW,
        // Nhân cận dưới với chi phí mỗi dòng, để None nếu tràn số.
        lower_bytes: evidence.lower_rows.checked_mul(per_row),
        // Chỉ tính cận trên khi số dòng tối đa có căn cứ.
        upper_bytes: evidence.upper_rows.and_then(|n| n.checked_mul(per_row)),
    })
}
