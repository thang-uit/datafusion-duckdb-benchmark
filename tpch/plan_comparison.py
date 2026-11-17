"""Hiển thị đối chiếu EXPLAIN trong notebook, không thực thi để lấy kết quả SQL."""

# Đếm số lần tên toán tử xuất hiện trong EXPLAIN.
from collections import Counter
# Escape dữ liệu trước khi đưa vào HTML notebook.
from html import escape
# Tìm mẫu tên toán tử, biểu thức hoặc đường dẫn trong văn bản.
import re

# Nạp tiện ích phục vụ phần minh họa, chưa chạy truy vấn khi import.
from IPython.display import HTML

# Chú giải tên trạng thái do DataFusion trả về bằng tiếng Việt.
from plan_notes import stage_label, stage_note
# Ghép vùng kiến trúc tương ứng với kế hoạch đang đọc.
from plan_architecture import architecture_panel, architecture_overview, architecture_location, REPORT_CSS


# Mỗi hàng gom các toán tử có vai trò liên quan; không khẳng định chúng giống thuật toán.
STAGES = (
    ("Đọc nguồn", ("ParquetExec", "DataSourceExec"), ("READ_PARQUET", "PARQUET_SCAN"),
     "Cột và bộ lọc nằm trong chi tiết kế hoạch; tên nguồn không cho biết đã bỏ bao nhiêu nhóm hàng."),
    ("Lọc", ("FilterExec",), ("FILTER",),
     "Bộ lọc có thể nằm trong bước đọc. Không thấy FILTER riêng không có nghĩa là không lọc."),
    ("Gom lô", ("CoalesceBatchesExec",), (),
     "DataFusion có thể gom các lô nhỏ. DuckDB không nhất thiết hiển thị công việc tương ứng thành ô riêng."),
    ("Biểu thức / chọn cột", ("ProjectionExec",), ("PROJECTION",),
     "Projection có thể chọn, đổi tên hoặc tính biểu thức. Vị trí phép nhân Q6 xem trong kế hoạch thật."),
    ("Nối", ("HashJoinExec", "NestedLoopJoinExec", "SortMergeJoinExec"),
     ("HASH_JOIN", "NESTED_LOOP_JOIN", "PIECEWISE_MERGE_JOIN", "CROSS_PRODUCT", "DELIM_JOIN"),
     "DataFusion 32 hash join dựng bảng băm phía trái; DuckDB 0.9.1 dựng phía phải. Đối chiếu tên nguồn ở nhánh con."),
    ("Tổng hợp", ("AggregateExec",),
     ("UNGROUPED_AGGREGATE", "HASH_GROUP_BY", "PERFECT_HASH_GROUP_BY"),
     "Phân biệt tổng hợp toàn bảng với gom nhóm; xem SUM/AVG và khóa nhóm ở chi tiết."),
    ("Sắp xếp", ("SortExec", "SortPreservingMergeExec"), ("ORDER_BY", "TOP_N"),
     "Q6 và Q17 gốc không có ORDER BY; không tự thêm một bước sắp xếp vào hình minh họa."),
)


# Lưu vị trí riêng của một số vai trò toán tử trên hình.
OPERATOR_LOCATIONS = {
    "Đọc nguồn": "2 — Parquet trong Catalog/Data Sources",
    "Gom lô": "7–8 — toán tử và luồng lô",
}
# Lưu vị trí thực thi dùng khi vai trò không có ánh xạ riêng.
DEFAULT_OPERATOR_LOCATION = "7 — Execution Engine"


# Lấy các trạng thái từ DataFusion EXPLAIN VERBOSE, không chạy SELECT gốc.
def _datafusion_plans(ctx, sql):
    # VERBOSE trả các trạng thái trước/sau quy tắc; collect ở đây thu mô tả EXPLAIN.
    rows = []
    # Duyệt từng mục theo thứ tự để thu dữ liệu hoặc ghép phần trình bày tương ứng.
    for batch in ctx.sql("EXPLAIN VERBOSE " + sql).collect():
        # Thêm mục hiện tại vào tập dữ liệu theo đúng thứ tự.
        rows.extend(batch.to_pylist())
    # Trả giá trị vừa xác định cho hàm gọi.
    return [(str(row["plan_type"]), str(row["plan"])) for row in rows]


# Lấy ba loại kế hoạch DuckDB rồi khôi phục cấu hình cũ.
def _duckdb_plans(con, sql):
    # Lưu thiết lập để sau khi xem kế hoạch kết nối vẫn giữ cấu hình cũ.
    previous = str(con.execute("SELECT current_setting('explain_output')").fetchone()[0]).lower()
    # Các giá trị cấu hình được phép nội suy lại vào lệnh SET.
    allowed = {"all", "physical_only", "optimized_only"}
    # Kiểm tra trường hợp thiếu dữ liệu hoặc chưa có giá trị trước khi dùng tiếp.
    if previous not in allowed:
        # Dừng với thông báo rõ ràng thay vì tiếp tục bằng dữ liệu hoặc cấu hình không hợp lệ.
        raise ValueError(f"Thiết lập explain_output không được nhận diện: {previous}")
    # Chuyển lỗi ra thông báo dễ đọc, bảo đảm chạy phần dọn dẹp nếu có.
    try:
        # all hiển thị logical_plan, logical_opt và physical_plan trong bản DuckDB này.
        con.execute("SET explain_output='all'")
        # Trả giá trị vừa xác định cho hàm gọi.
        return [(str(kind), str(plan)) for kind, plan in con.execute("EXPLAIN " + sql).fetchall()]
    finally:
        # Chỉ nội suy giá trị đã được kiểm tra theo danh sách cố định ở trên.
        con.execute(f"SET explain_output='{previous}'")


# Tìm đúng loại kế hoạch, báo rõ khi đầu ra không có loại đó.
def _find(plans, name):
    # Trả giá trị vừa xác định cho hàm gọi.
    return next((plan for kind, plan in reversed(plans) if kind == name), "Không có mục này trong đầu ra.")


# Đếm tên toán tử xuất hiện trong cây vật lý của từng bộ máy.
def _operator_counts(df_plan, duck_plan):
    # DataFusion in một toán tử Exec ở đầu mỗi dòng thụt vào.
    df_counts = Counter(re.findall(r"^\s*([A-Za-z][A-Za-z0-9_]*Exec)\s*:", df_plan, re.MULTILINE))
    # DuckDB in tên toán tử trong các khung; chỉ đếm tên toán tử đã nhận diện.
    known = {name for _, _, names, _ in STAGES for name in names}
    # Đếm đúng các tên toán tử DuckDB đã nhận diện trong khung EXPLAIN.
    duck_counts = Counter(
        name for name in re.findall(r"[│|]\s*([A-Z][A-Z_0-9]+)\s*[│|]", duck_plan) if name in known
    )
    # Trả giá trị vừa xác định cho hàm gọi.
    return df_counts, duck_counts


# Trình bày tên và số lượng toán tử, không suy diễn tốc độ từ số lượng.
def _operator_cell(names, counts):
    # Các mục khớp từ đầu ra thật, không tự khôi phục chi tiết bộ máy đã lược bớt.
    found = [(name, counts[name]) for name in names if counts[name]]
    # Kiểm tra trường hợp thiếu dữ liệu hoặc chưa có giá trị trước khi dùng tiếp.
    if not found:
        # Trả giá trị vừa xác định cho hàm gọi.
        return '<span class="pc-muted">Không thấy toán tử riêng tương ứng</span>'
    # Trả giá trị vừa xác định cho hàm gọi.
    return "<br>".join(f"<code>{escape(name)}</code> × {count}" for name, count in found)


# Hiển thị kế hoạch dưới dạng HTML đã escape ký tự.
def _plan_block(label, plan, data_dir, explanation=None):
    # Chỉ rút gọn tiền tố đường dẫn trong hình; bản SQL và kế hoạch gốc không bị thay đổi.
    visual = plan
    # Kiểm tra trường hợp thiếu dữ liệu hoặc chưa có giá trị trước khi dùng tiếp.
    if data_dir is not None:
        # Lưu tiền tố đường dẫn dữ liệu cần ẩn trong bảng trình bày.
        prefix = str(data_dir).rstrip("/")
        # Lưu bản hiển thị đã rút gọn đường dẫn, không sửa kế hoạch để thực thi.
        visual = visual.replace(prefix + "/", "[DỮ LIỆU]/")
        # Lưu bản hiển thị đã rút gọn đường dẫn, không sửa kế hoạch để thực thi.
        visual = visual.replace(prefix.lstrip("/") + "/", "[DỮ LIỆU]/")
    # Escape mọi nội dung SQL/kế hoạch trước khi đưa vào HTML.
    note = f"<p>{escape(explanation)}</p>" if explanation else ""
    # Trả nội dung hiển thị, không chạy thêm SELECT trong bước ghép kết quả.
    return f"<section><h4>{escape(label)}</h4>{note}<pre>{escape(visual)}</pre></section>"


# Ghép EXPLAIN hai bộ máy thành bảng có chú giải, không chạy ANALYZE.
def compare_plans(ctx, con, sql, title, data_dir=None):
    """Trả HTML đối chiếu từ EXPLAIN thật; không gọi EXPLAIN ANALYZE."""
    # Lưu các trạng thái EXPLAIN VERBOSE DataFusion trả về.
    df_plans = _datafusion_plans(ctx, sql)
    # Lưu các kế hoạch EXPLAIN DuckDB trả về.
    duck_plans = _duckdb_plans(con, sql)
    # Lưu cây vật lý cuối của DataFusion.
    df_physical = _find(df_plans, "physical_plan")
    # Lưu cây vật lý cuối của DuckDB.
    duck_physical = _find(duck_plans, "physical_plan")
    # Đếm toán tử riêng cho từng bộ máy, không coi số lượng là bằng chứng tốc độ.
    df_counts, duck_counts = _operator_counts(df_physical, duck_physical)

    # Bảng đối chiếu theo vai trò không thay thế thứ tự đầu vào, đầu ra của cây.
    rows = "".join(
        f"<tr><th scope='row'>{escape(stage)}</th>"
        f"<td>{_operator_cell(df_names, df_counts)}</td>"
        f"<td>{_operator_cell(duck_names, duck_counts)}</td>"
        f"<td>{escape(note)}<br><strong>Trên hình DataFusion: "
        f"{escape(OPERATOR_LOCATIONS.get(stage, DEFAULT_OPERATOR_LOCATION))}</strong></td></tr>"
        for stage, df_names, duck_names, note in STAGES
    )
    # Chú giải cách đọc cây vật lý từ nguồn lên phía trên.
    physical_note = "Đọc từ nguồn ở dưới lên: bộ máy chọn các toán tử nào và đầu vào của chúng là gì. Đây là kế hoạch, chưa phải thời gian thực thi."
    # Chú giải cách so cây logic sau tối ưu với cây ban đầu.
    logical_note = "Đọc từ dưới lên và so với bản ban đầu: cột, bộ lọc và cấu trúc nối đã được biến đổi như thế nào."
    # Chú giải cây logic trước tối ưu và các phép cần thực hiện.
    initial_note = "Đọc từ dưới lên: nguồn dữ liệu → điều kiện lọc → tổng hợp → cột đầu ra. Với Q17 còn có truy vấn con và phép nối."
    # Ghép phần kế hoạch vật lý hai bên để hiển thị cạnh nhau.
    physical = _plan_block("DataFusion — kế hoạch vật lý cuối (physical_plan)", df_physical, data_dir, physical_note)
    # Nối thêm nội dung hiện tại, giữ thứ tự các mục đã tạo trước đó.
    physical += _plan_block("DuckDB — kế hoạch vật lý cuối (physical_plan)", duck_physical, data_dir, physical_note)
    # Ghép phần kế hoạch logic sau tối ưu hai bên.
    logical = _plan_block("DataFusion — logic sau tối ưu (logical_plan)", _find(df_plans, "logical_plan"), data_dir, logical_note)
    # Nối thêm nội dung hiện tại, giữ thứ tự các mục đã tạo trước đó.
    logical += _plan_block("DuckDB — logic sau tối ưu (logical_opt)", _find(duck_plans, "logical_opt"), data_dir, logical_note)
    # Lưu SQL Q17 gốc hoặc nội dung nguồn để đối chiếu.
    original = _plan_block("DataFusion — logic ban đầu (initial_logical_plan)", _find(df_plans, "initial_logical_plan"), data_dir, initial_note)
    # Nối thêm nội dung hiện tại, giữ thứ tự các mục đã tạo trước đó.
    original += _plan_block("DuckDB — logic ban đầu (logical_plan)", _find(duck_plans, "logical_plan"), data_dir, initial_note)
    # Giữ nguyên thứ tự, kể cả quy tắc xuất hiện nhiều lần trong các lượt tối ưu.
    passes = "".join(
        f"<details><summary>{index}. {escape(stage_label(kind))}</summary>"
        f"<p><strong>{escape(architecture_location(kind))}</strong></p>"
        f"<p>{escape(stage_note(kind))}</p>{_plan_block(kind, plan, data_dir)}</details>"
        for index, (kind, plan) in enumerate(df_plans, start=1)
    )
    # Bản thô không rút gọn đường dẫn, giúp đối chiếu với đầu ra nguyên bản.
    raw_df = "\n\n".join(f"{kind}\n{plan}" for kind, plan in df_plans)
    # Lưu đầu ra nguyên bản các loại kế hoạch DuckDB.
    raw_duck = "\n\n".join(f"{kind}\n{plan}" for kind, plan in duck_plans)

    # Trả nội dung hiển thị, không chạy thêm SELECT trong bước ghép kết quả.
    return HTML(f"""
<div class="pc-comparison">
<style>
.pc-comparison {{ color:var(--tpch-report-fg,#202b33); font:14px/1.6 system-ui,sans-serif; }}
.pc-comparison table {{ width:100%; border-collapse:collapse; table-layout:fixed; margin:12px 0; }}
.pc-comparison th,.pc-comparison td {{ border:1px solid #8888; padding:10px; vertical-align:top; text-align:left; overflow-wrap:anywhere; }}
.pc-comparison thead {{ background:#8882; }}
.pc-comparison .pc-muted {{ color:#485763; opacity:1; }}
.pc-comparison code {{ font:13px/1.5 monospace; }}
.pc-comparison .pc-grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:16px; }}
.pc-comparison .pc-grid section {{ min-width:0; }}
.pc-comparison pre {{ white-space:pre-wrap; overflow-wrap:anywhere; font:12px/1.55 monospace; padding:12px; background:#8881; border:1px solid #8886; }}
.pc-comparison details {{ border:1px solid #8886; padding:10px; margin:10px 0; }}
.pc-comparison summary {{ cursor:pointer; font-weight:600; }}
.pc-comparison summary:focus-visible {{ outline:2px solid currentColor; outline-offset:3px; }}
@media(max-width:800px) {{ .pc-comparison .pc-grid {{ grid-template-columns:1fr; }} }}
</style>
{REPORT_CSS}
<h3>{escape(title)} — đối chiếu kế hoạch thật</h3>
<p>Chỉ lập kế hoạch bằng EXPLAIN. Số × là số toán tử nhìn thấy, không phải số lần đọc đĩa hay số dòng thực tế.</p>
<p>Mục 0 định vị các kế hoạch trên hình kiến trúc. Trong mỗi mục tiếp theo, hình khoanh vùng nằm trước đầu ra tương ứng.</p>
<p>Đọc các mục 1–4 trước: kế hoạch ban đầu → logic sau tối ưu → vật lý cuối → đối chiếu toán tử. Mục 5 ghi chi tiết quá trình biến đổi; mục 6 giữ nguyên đầu ra.</p>
<details open><summary>0. Đối chiếu với hình kiến trúc DataFusion</summary>{architecture_overview()}</details>
<details><summary>1. Kế hoạch logic ban đầu — hai bộ máy cạnh nhau</summary>{architecture_panel("logical-initial")}<div class="pc-grid">{original}</div></details>
<details><summary>2. Kế hoạch logic sau tối ưu — hai bộ máy cạnh nhau</summary>{architecture_panel("logical-optimized")}<div class="pc-grid">{logical}</div></details>
<details><summary>3. Kế hoạch vật lý cuối — hai bộ máy cạnh nhau</summary>{architecture_panel("physical-final")}<div class="pc-grid">{physical}</div></details>
<details><summary>4. Đối chiếu toán tử theo vai trò</summary>
{architecture_panel("execution-join" if df_counts["HashJoinExec"] else "execution-q6")}
<table><thead><tr><th style="width:13%">Công việc</th><th style="width:23%">DataFusion 32.0.0</th><th style="width:23%">DuckDB 0.9.1</th><th style="width:41%">Cách hiểu</th></tr></thead>
<tbody>{rows}</tbody></table>
<p>Đọc cây từ nhánh nguồn ở dưới lên; các hàng trên không mô tả thứ tự. Ít toán tử hơn không tự chứng minh nhanh hơn.</p></details>
<details><summary>5. Chi tiết các giai đoạn DataFusion — tra cứu khi cần</summary>
<details><summary>Vòng tối ưu logic (4)</summary>{architecture_panel("logical-rewrite")}</details>
<details><summary>Cây vật lý ban đầu (5)</summary>{architecture_panel("physical-initial")}</details>
<details><summary>Vòng tối ưu vật lý (6)</summary>{architecture_panel("physical-rewrite")}</details>
<p><code>ctx.sql("EXPLAIN VERBOSE " + sql).collect()</code> trả bảng mô tả có hai cột <code>plan_type</code> và <code>plan</code>. <code>to_pylist()</code> chuyển các lô Arrow thành dòng Python để hiển thị. Đây là đầu ra DataFusion, không phải các bước do tiện ích tự tạo.</p>
<p>Các mục dưới giữ nguyên thứ tự trả về, kèm chú giải tiếng Việt. Một quy tắc có thể xuất hiện nhiều lần. <code>SAME TEXT AS ABOVE</code> nghĩa là nội dung kế hoạch giống trạng thái trước đó được in; tên quy tắc không chứng minh nó đã thay đổi truy vấn. Đây không phải các lần chạy truy vấn trên dữ liệu.</p>
{passes}</details>
<details><summary>6. Đầu ra nguyên bản, giữ đầy đủ đường dẫn</summary><div class="pc-grid">
{_plan_block("DataFusion", raw_df, None)}{_plan_block("DuckDB", raw_duck, None)}</div></details>
<p><strong>Giới hạn:</strong> EC của DuckDB là số dòng ước lượng. DuckDB 0.9.1 có thể tự in “...” trong biểu thức; phần đó không được tự khôi phục. HTML giữ nội dung mà EXPLAIN trả về, không đảm bảo hiển thị mọi chi tiết nội bộ. Giai đoạn DataFusion không thay đổi kế hoạch có thể chỉ ghi SAME TEXT AS ABOVE.</p>
<p>EXPLAIN không cung cấp thời gian từng toán tử, số dòng thực tế hay bộ nhớ đã dùng. Muốn thu các số liệu đó cần EXPLAIN ANALYZE, tức là chạy truy vấn thêm; bảng này không làm bước đó.</p>
</div>""")
