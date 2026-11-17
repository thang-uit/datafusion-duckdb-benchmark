"""Chú giải tiếng Việt cho các nhãn EXPLAIN; không thay đổi cây kế hoạch."""

# Lưu chú giải các loại kế hoạch DataFusion.
PLAN_NOTES = {
    "initial_logical_plan": ("Kế hoạch logic ban đầu", "Biểu diễn yêu cầu từ SQL trước các bước phân tích và tối ưu được liệt kê tiếp theo."),
    "analyzed_logical_plan": ("Kế hoạch logic sau phân tích", "Kế hoạch sau các quy tắc phân tích, bao gồm điều chỉnh kiểu dữ liệu."),
    "logical_plan": ("Kế hoạch logic sau tối ưu", "Các phép xử lý còn lại sau những lượt tối ưu logic."),
    "initial_physical_plan": ("Kế hoạch vật lý ban đầu", "Cây toán tử thực thi được tạo từ kế hoạch logic, trước tối ưu vật lý."),
    "physical_plan": ("Kế hoạch vật lý cuối", "Cây toán tử sẽ xử lý dữ liệu khi truy vấn được thực thi."),
}

# Lưu chú giải tên quy tắc tối ưu.
RULE_NOTES = {
    "inline_table_scan": ("Mở rộng kế hoạch nguồn bảng", "Đưa kế hoạch lồng trong nguồn bảng vào cây khi quy tắc áp dụng được."),
    "type_coercion": ("Điều chỉnh kiểu dữ liệu", "Làm các kiểu đầu vào tương thích với biểu thức và hàm."),
    "count_wildcard_rule": ("Chuẩn hóa COUNT(*)", "Chuẩn hóa biểu thức đếm; không thêm phép đếm vào truy vấn không yêu cầu đếm."),
    "simplify_expressions": ("Đơn giản hóa biểu thức", "Ví dụ: tính trước biểu thức hằng khi phù hợp."),
    "unwrap_cast_in_comparison": ("Rút gọn chuyển kiểu trong so sánh", "Bỏ hoặc chuyển vị trí phép chuyển kiểu khi bảo toàn ý nghĩa so sánh."),
    "replace_distinct_aggregate": ("Biến đổi tổng hợp có DISTINCT", "Viết lại dạng tổng hợp DISTINCT mà quy tắc hỗ trợ."),
    "eliminate_join": ("Loại phép nối không cần thiết", "Chỉ loại phép nối khi đủ điều kiện giữ nguyên kết quả."),
    "decorrelate_predicate_subquery": ("Biến đổi truy vấn con trong điều kiện", "Chuyển cấu trúc truy vấn con tương quan sang dạng nối khi áp dụng được."),
    "scalar_subquery_to_join": ("Chuyển truy vấn con một giá trị thành nối", "Viết lại truy vấn con vô hướng thành cấu trúc nối tương đương."),
    "extract_equijoin_predicate": ("Tách điều kiện nối bằng", "Nhận diện các cặp khóa có điều kiện bằng nhau để phục vụ phép nối."),
    "merge_projection": ("Gộp bước chọn cột", "Kết hợp các Projection liên tiếp khi phù hợp."),
    "rewrite_disjunctive_predicate": ("Biến đổi điều kiện có OR", "Tổ chức lại điều kiện để hỗ trợ các phép tối ưu tiếp theo."),
    "eliminate_duplicated_expr": ("Loại biểu thức lặp", "Loại những biểu thức trùng trong phạm vi quy tắc hỗ trợ."),
    "eliminate_filter": ("Rút gọn bộ lọc", "Loại hoặc biến đổi bộ lọc khi biết điều kiện luôn đúng hoặc luôn sai."),
    "eliminate_cross_join": ("Biến đổi tích Descartes", "Tận dụng điều kiện nối để thay tích Descartes khi phù hợp."),
    "common_sub_expression_eliminate": ("Dùng lại biểu thức chung", "Tránh tính lặp một biểu thức khi phép biến đổi hợp lệ."),
    "eliminate_limit": ("Rút gọn giới hạn dòng", "Loại hoặc đơn giản hóa Limit khi đủ điều kiện."),
    "propagate_empty_relation": ("Lan truyền quan hệ rỗng", "Đơn giản hóa cây khi một nhánh đã được xác định không có dòng."),
    "filter_null_join_keys": ("Lọc khóa nối NULL", "Loại các khóa NULL khi ngữ nghĩa của phép nối cho phép."),
    "eliminate_outer_join": ("Rút gọn phép nối ngoài", "Chuyển loại nối khi điều kiện cho phép mà không đổi kết quả."),
    "push_down_limit": ("Đưa giới hạn dòng về gần nguồn", "Di chuyển Limit khi không làm mất các dòng cần thiết."),
    "push_down_filter": ("Đưa điều kiện lọc về gần nguồn", "Giảm dữ liệu ở những phần kế hoạch phía trên khi phép biến đổi hợp lệ."),
    "single_distinct_aggregation_to_group_by": ("Biến đổi tổng hợp DISTINCT thành gom nhóm", "Áp dụng cho dạng tổng hợp DISTINCT mà quy tắc hỗ trợ."),
    "push_down_projection": ("Chỉ yêu cầu các cột cần thiết", "Giới hạn các cột cần truyền qua những phần của kế hoạch."),
    "eliminate_projection": ("Loại bước chọn cột không cần thiết", "Bỏ Projection khi nó không còn cần cho kết quả."),
    "OutputRequirements": ("Quản lý yêu cầu đầu ra", "Thêm hoặc tháo nút hỗ trợ để bảo toàn yêu cầu đầu ra trong tối ưu vật lý."),
    "aggregate_statistics": ("Tận dụng thống kê cho tổng hợp", "Thay cách tính bằng thống kê khi có đủ thông tin hợp lệ."),
    "join_selection": ("Lựa chọn cách thực hiện phép nối", "Xem xét phương án nối và phía đầu vào dựa trên thông tin sẵn có."),
    "EnforceDistribution": ("Bảo đảm phân phối dữ liệu", "Bổ sung hoặc điều chỉnh phân vùng để đáp ứng yêu cầu toán tử."),
    "CombinePartialFinalAggregate": ("Kết hợp các giai đoạn tổng hợp", "Gộp tổng hợp cục bộ và tổng hợp cuối khi đủ điều kiện."),
    "EnforceSorting": ("Bảo đảm thứ tự dữ liệu", "Điều chỉnh việc sắp xếp theo yêu cầu của các toán tử."),
    "coalesce_batches": ("Gom các lô dữ liệu nhỏ", "Bổ sung CoalesceBatchesExec khi phù hợp."),
    "PipelineChecker": ("Kiểm tra khả năng thực thi", "Kiểm tra các yêu cầu của kế hoạch, bao gồm giới hạn dữ liệu khi có liên quan."),
    "LimitAggregation": ("Tận dụng giới hạn trong tổng hợp", "Xem xét giới hạn lượng công việc tổng hợp khi ngữ nghĩa cho phép."),
}


# Dịch nhãn trạng thái kế hoạch sang tiếng Việt.
def stage_label(kind):
    """Giữ nguyên tên kỹ thuật để đối chiếu với đầu ra gốc."""
    # Chọn chú giải theo tên trạng thái thật trong EXPLAIN.
    if kind in PLAN_NOTES:
        # Trả nội dung hiển thị, không chạy thêm SELECT trong bước ghép kết quả.
        return f"{PLAN_NOTES[kind][0]} — {kind}"
    # Giá trị trung gian `rule` được dùng ngay ở bước bên dưới.
    rule = kind.partition(" after ")[2]
    # Chọn nhánh phù hợp với dữ liệu hoặc trạng thái vừa đọc.
    if rule in RULE_NOTES:
        # Trả nội dung hiển thị, không chạy thêm SELECT trong bước ghép kết quả.
        return f"{RULE_NOTES[rule][0]} — {kind}"
    # Trả giá trị vừa xác định cho hàm gọi.
    return f"Trạng thái sau quy tắc — {kind}" if rule else kind


# Giải thích ý nghĩa của trạng thái hoặc quy tắc được DataFusion in ra.
def stage_note(kind):
    # Chọn chú giải theo tên trạng thái thật trong EXPLAIN.
    if kind in PLAN_NOTES:
        # Trả giá trị vừa xác định cho hàm gọi.
        return PLAN_NOTES[kind][1]
    # Giá trị trung gian `rule` được dùng ngay ở bước bên dưới.
    rule = kind.partition(" after ")[2]
    # Đoạn chú giải đã escape để không bị hiểu thành mã HTML.
    note = RULE_NOTES.get(rule, (None, "Trạng thái sau quy tắc được DataFusion ghi lại."))[1]
    # Trả giá trị vừa xác định cho hàm gọi.
    return note + " Sự xuất hiện của quy tắc không có nghĩa cây đã thay đổi."
