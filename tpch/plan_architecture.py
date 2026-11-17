"""Đối chiếu đầu ra thật với Hình 2 DataFusion; chỉ tạo HTML, không chạy SQL."""
# Nhúng ảnh vào HTML để không phụ thuộc máy chủ bên ngoài.
from base64 import b64encode
# Giữ cache ảnh đã đọc để không mã hóa lại nhiều lần.
from functools import lru_cache
# Escape dữ liệu trước khi đưa vào HTML notebook.
from html import escape
# Đọc đường dẫn bằng Path thay vì ghép chuỗi phụ thuộc máy.
from pathlib import Path

# Dùng chung màu chữ và nền của bảng notebook.
from notebook_theme import REPORT_CSS

# Lưu thư mục chứa chính mô-đun, không phụ thuộc thư mục Terminal.
HERE = Path(__file__).resolve().parent
# Lưu liên kết bài báo dùng làm nguồn chú thích.
SOURCE = "https://doi.org/10.1145/3626246.3653368"

# Lưu ánh xạ các giai đoạn với thành phần và chú giải kiến trúc.
STAGES = {
    "overview": ("Vị trí của các mục trong hình kiến trúc", "1–9",
        "Hình 2 mô tả DataFusion. Các số khoanh được nhóm bổ sung để nối hình với mã và đầu ra EXPLAIN.",
        "ctx.sql(\"EXPLAIN VERBOSE \" + sql).collect()",
        "collect ở câu lệnh này thu mô tả kế hoạch, chưa thực thi Q6/Q17 để lấy doanh thu."),
    "logical-initial": ("Kế hoạch logic ban đầu", "3",
        "Vùng LogicalPlan: biểu diễn yêu cầu đọc, lọc, nối và tổng hợp trước tối ưu logic.",
        'plan_type == "initial_logical_plan"',
        "Đây đã là LogicalPlan, không phải cây cú pháp SQL (AST)."),
    "logical-optimized": ("Kế hoạch logic sau tối ưu", "3–4",
        "Cây LogicalPlan (3) sau vòng Optimizations / Transformations bên trái (4).",
        'plan_type == "logical_plan"',
        "Các trạng thái logical_plan after ... ở mục 5 cho biết cây sau từng quy tắc."),
    "logical-rewrite": ("Các quy tắc biến đổi logic", "4",
        "Vòng dưới LogicalPlan: phân tích kiểu và tối ưu biến đổi cây logic.",
        'plan_type.startswith("logical_plan after ")',
        "SAME TEXT AS ABOVE nghĩa cây không đổi ở trạng thái đó; không phải một lượt chạy trên dữ liệu."),
    "physical-initial": ("Kế hoạch vật lý trước tối ưu", "5",
        "Vùng ExecutionPlan: cây toán tử vật lý vừa được tạo trước các quy tắc vật lý.",
        'plan_type == "initial_physical_plan"',
        "ExecutionPlan là giao diện biểu diễn toán tử/kế hoạch vật lý trong DataFusion."),
    "physical-final": ("Kế hoạch vật lý cuối", "5–6",
        "Cây ExecutionPlan (5) sau vòng Optimizations / Transformations bên phải (6).",
        'plan_type == "physical_plan"',
        "Tên Exec là các thành phần được chọn để thực hiện khi chạy; EXPLAIN chưa đo chúng."),
    "physical-rewrite": ("Các quy tắc biến đổi vật lý", "6",
        "Vòng dưới ExecutionPlan: các quy tắc như join_selection và coalesce_batches.",
        'plan_type.startswith("physical_plan after ")',
        "Đây là quá trình chuẩn bị kế hoạch, không phải dữ liệu đang chạy qua các toán tử."),
    "execution-q6": ("Toán tử Q6 trong bộ máy thực thi", "2, 7–8",
        "ParquetExec đọc nguồn Parquet (2); Filter/Projection/Aggregate thực thi trong engine (7), truyền lô Arrow qua Streams (8).",
        "ctx.sql(q6_sql).collect()",
        "Q6 tổng hợp không GROUP BY; không được suy ra có bảng băm nhiều nhóm từ ô HashAggregate trên hình. Không có ORDER BY."),
    "execution-join": ("Toán tử Q17 trong bộ máy thực thi", "2, 7–8",
        "ParquetExec đọc nguồn (2); HashJoinExec tương ứng Join, AggregateExec AVG theo khóa tương ứng HashAggregate ở engine (7).",
        "ctx.sql(q17_sql).collect()",
        "Bước thu kết quả truyền RecordBatch qua Streams (8). Hình không hiển thị riêng mọi toán tử hoặc thứ tự nhánh của Q17."),
    "extension-rewrite": ("Nơi quy tắc thống kê sửa kế hoạch Q17", "5–6, 9",
        "Số 9 trỏ đúng ô xanh dương Extension ExecutionPlan Rewrite, tham gia vòng vật lý (6) để thay cây ExecutionPlan (5).",
        "state.add_physical_optimizer_rule(rule.clone())\nStatisticsBuildSideRule.optimize(plan, config)",
        "Quy tắc đổi đầu vào HashJoinExec và phục hồi cột. Không tạo Extension Node mới, không viết HashJoinExec hay Extension Stream mới."),
}


# Lưu kiểu trình bày vùng kiến trúc trong notebook.
CSS = """<style>
.plan-architecture {font:14px/1.65 system-ui,sans-serif;color:var(--tpch-report-fg,#202b33);margin:12px 0 20px}
.plan-architecture figure {margin:12px 0}
.plan-architecture img {display:block;width:100%;height:auto;background:white}
.plan-architecture figcaption {font-size:12px;margin-top:8px}
.plan-architecture .location {font-weight:650}
.plan-architecture pre {white-space:pre-wrap;overflow-wrap:anywhere;font:13px/1.6 monospace;padding:10px;background:#8881}
.plan-architecture table {border-collapse:collapse;width:100%;table-layout:auto}
.plan-architecture th,.plan-architecture td {border:1px solid #8886;padding:8px;text-align:left;vertical-align:top;overflow-wrap:anywhere}
.plan-architecture summary {cursor:pointer;font-weight:600}
.plan-architecture summary:focus-visible {outline:2px solid currentColor;outline-offset:3px}
.plan-architecture .pa-image {display:block;max-width:1250px;margin:auto}
</style>"""


# Đọc và mã hóa ảnh theo giai đoạn, dùng cache để tránh đọc lặp.
@lru_cache(maxsize=10)
def _image_data(stage):
    # Đường dẫn tới ảnh hoặc tệp đầu ra đang được xử lý.
    path = HERE / "plan-assets" / f"{stage}.png"
    # Trả giá trị vừa xác định cho hàm gọi.
    return "data:image/png;base64," + b64encode(path.read_bytes()).decode("ascii")


# Ánh xạ tên trạng thái EXPLAIN sang vùng kiến trúc tương ứng.
def stage_location(kind):
    # Chọn chú giải theo tên trạng thái thật trong EXPLAIN.
    if kind == "initial_logical_plan":
        # Trả giá trị vừa xác định cho hàm gọi.
        return "logical-initial"
    # Chọn chú giải theo tên trạng thái thật trong EXPLAIN.
    if kind == "logical_plan":
        # Trả giá trị vừa xác định cho hàm gọi.
        return "logical-optimized"
    # Chọn chú giải theo tên trạng thái thật trong EXPLAIN.
    if kind == "analyzed_logical_plan" or kind.startswith("logical_plan after "):
        # Trả giá trị vừa xác định cho hàm gọi.
        return "logical-rewrite"
    # Chọn chú giải theo tên trạng thái thật trong EXPLAIN.
    if kind == "initial_physical_plan":
        # Trả giá trị vừa xác định cho hàm gọi.
        return "physical-initial"
    # Chọn chú giải theo tên trạng thái thật trong EXPLAIN.
    if kind.startswith("physical_plan after "):
        # Trả giá trị vừa xác định cho hàm gọi.
        return "physical-rewrite"
    # Chọn chú giải theo tên trạng thái thật trong EXPLAIN.
    if kind in {"physical_plan", "physical_plan_with_statistics"}:
        # Trả giá trị vừa xác định cho hàm gọi.
        return "physical-final"
    # Chưa nhận diện được trường hợp này, không tự suy ra giá trị.
    return None


# Tạo chú giải vị trí trên Hình 2 từ trạng thái thật.
def architecture_location(kind):
    # Vùng kiến trúc ứng với tên trạng thái kế hoạch.
    stage = stage_location(kind)
    # Kiểm tra trường hợp thiếu dữ liệu hoặc chưa có giá trị trước khi dùng tiếp.
    if stage is None:
        # Trả giá trị vừa xác định cho hàm gọi.
        return "Đầu ra bổ sung; không tự gán vào một giai đoạn khi chưa nhận diện được."
    # Lấy tiêu đề và số chú giải của vùng đã nhận diện.
    title, numbers, *_ = STAGES[stage]
    # Trả nội dung hiển thị, không chạy thêm SELECT trong bước ghép kết quả.
    return f"Trên Hình 2: số {numbers} — {title}."


# Ghép hình, nguồn và chú giải của một vùng kiến trúc.
def architecture_panel(stage):
    # Tách thông tin hình, mã đối chiếu và ghi chú của cùng một vùng.
    title, numbers, description, code, note = STAGES[stage]
    # Mã hóa ảnh thành data URI để output HTML tự chứa hình.
    uri = _image_data(stage)
    # Trả nội dung hiển thị, không chạy thêm SELECT trong bước ghép kết quả.
    return f"""{CSS}{REPORT_CSS}<section class="plan-architecture" aria-label="{escape(title, quote=True)}">
<p class="location">Hình kiến trúc — số {escape(numbers)}: {escape(title)}</p>
<p>{escape(description)}</p>
<figure><div class="pa-image">
<img src="{uri}" alt="Hình 2 DataFusion: đánh dấu số {escape(numbers, quote=True)}. {escape(description, quote=True)}"></div>
<figcaption>Nguồn: <a href="{SOURCE}" target="_blank" rel="noopener">Lamb và cộng sự, 2024, Hình 2, tr. 8</a>.
Số khoanh và đường đánh dấu do nhóm bổ sung; nội dung hình gốc được giữ. Đây là kiến trúc DataFusion, không gán cho DuckDB.</figcaption></figure>
<pre>{escape(code)}</pre><p>{escape(note)}</p></section>"""


# Tạo bảng nối các mục kế hoạch với số trên Hình 2.
def architecture_overview():
    # Lưu các dòng kết quả hoặc HTML đang được ghép.
    rows = [
        ("1. Logic ban đầu", "3 — LogicalPlan", "initial_logical_plan"),
        ("2. Logic sau tối ưu", "3–4 — LogicalPlan và vòng bên trái", "logical_plan"),
        ("3. Vật lý cuối", "5–6 — ExecutionPlan và vòng bên phải", "physical_plan"),
        ("4. Toán tử", "2, 7–8 — nguồn, Execution Engine và Streams", "ParquetExec / FilterExec / HashJoinExec / AggregateExec"),
        ("5. Biến đổi chi tiết", "4 hoặc 6 — vòng tối ưu tương ứng", "logical_plan after ... / physical_plan after ..."),
        ("Quy tắc thống kê Q17", "9 — Extension ExecutionPlan Rewrite", "add_physical_optimizer_rule / optimize"),
    ]
    # Ghép các hàng đối chiếu nhãn, vùng kiến trúc và đầu ra thực tế.
    body = "".join(f"<tr><th scope='row'>{escape(label)}</th><td>{escape(area)}</td><td><code>{escape(output)}</code></td></tr>"
                   for label, area, output in rows)
    # Trả giá trị vừa xác định cho hàm gọi.
    return architecture_panel("overview") + f"""<div class='plan-architecture'><table>
<thead><tr><th>Mục đang xem</th><th>Vị trí trên hình DataFusion</th><th>Đầu ra / mã đối chiếu</th></tr></thead>
<tbody>{body}</tbody></table><p><strong>Lập kế hoạch:</strong> SQL (1) + thông tin nguồn (2) → LogicalPlan (3–4) → ExecutionPlan (5–6).
<strong>Thực thi:</strong> khi collect truy vấn thật, các toán tử (7) đọc nguồn (2), truyền lô qua (8).
Dữ liệu không đi xuyên qua cây logic như các mũi tên lập kế hoạch. Các số khoanh là chú giải, không phải thứ tự chạy tất cả các khối trên hình.</p></div>"""
