"""Thu hồ sơ Q6 và trình bày số liệu thật trong notebook; không tự chạy khi import."""

# Escape dữ liệu trước khi đưa vào HTML notebook.
from html import escape
# Đọc hoặc ghi JSON nguồn và kết quả có cấu trúc.
import json
# Đọc đường dẫn bằng Path thay vì ghép chuỗi phụ thuộc máy.
from pathlib import Path
# Tìm mẫu tên toán tử, biểu thức hoặc đường dẫn trong văn bản.
import re
# Tạo thư mục tạm và dọn tự động sau khi đọc hồ sơ.
from tempfile import TemporaryDirectory
# Lấy mốc đo thời gian đơn điệu.
from time import perf_counter

# Nạp tiện ích phục vụ phần minh họa, chưa chạy truy vấn khi import.
from IPython.display import HTML

# Dùng chung màu chữ và nền của bảng notebook.
from notebook_theme import REPORT_CSS


# Lưu kiểu trình bày số liệu Q6.
STYLE = """<style>
.q6-view {font:15px/1.6 system-ui,sans-serif;color:var(--tpch-report-fg,#202b33)}
.q6-view table {border-collapse:collapse;width:100%;margin:12px 0}
.q6-view td,.q6-view th {border:1px solid #8886;padding:10px;text-align:left;vertical-align:top}
.q6-view th {background:#8882}.q6-view pre {white-space:pre-wrap;overflow-wrap:anywhere;
font:13px/1.6 monospace;padding:14px;background:#8881;border:1px solid #8886}
.q6-view summary {cursor:pointer;font-weight:600}.q6-view details {margin:12px 0}
.q6-view .bar {height:12px;background:#aa601e;border-radius:3px;margin:5px 0 12px}
.q6-view .row {margin:14px 0}.q6-view strong {font-weight:700}
</style>""" + REPORT_CSS


# Escape dấu nháy đơn để giá trị trở thành một chuỗi SQL hợp lệ.
def _quote(value):
    # Trả giá trị vừa xác định cho hàm gọi.
    return "'" + str(value).replace("'", "''") + "'"


# Đọc cấu hình đang có trên chính kết nối DuckDB.
def _setting(con, name):
    # Trả giá trị vừa xác định cho hàm gọi.
    return con.execute("SELECT current_setting(" + _quote(name) + ")").fetchone()[0]


# Đo đúng một lượt SELECT, thu JSON profiling và trả cấu hình về trước đó.
def profile_duckdb_q6(con, sql):
    """Chạy SELECT một lần, thu kết quả, thời gian ngoài API và JSON toán tử.

    EXPLAIN không thực thi SELECT. Tệp hồ sơ dùng thư mục tạm, được đọc rồi xóa.
    Khôi phục cấu hình profiling/explain; giữ nguyên disabled_optimizers của người gọi.
    """
    # Lưu đường dẫn profiling trước lượt đo để trả lại sau đó.
    previous_output = _setting(con, "profiling_output")
    # Lưu chế độ profiling trước lượt đo.
    previous_profiling = _setting(con, "enable_profiling")
    # Lưu chế độ EXPLAIN trước lượt đo.
    previous_explain = str(_setting(con, "explain_output")).lower()
    # Lưu danh sách quy tắc bị tắt khi SELECT thực sự chạy.
    disabled = str(_setting(con, "disabled_optimizers"))
    # Kiểm tra trường hợp thiếu dữ liệu hoặc chưa có giá trị trước khi dùng tiếp.
    if previous_explain not in {"all", "physical_only", "optimized_only"}:
        # Dừng với thông báo rõ ràng thay vì tiếp tục bằng dữ liệu hoặc cấu hình không hợp lệ.
        raise ValueError("Không nhận diện cấu hình explain_output hiện tại.")
    # Kiểm tra trường hợp thiếu dữ liệu hoặc chưa có giá trị trước khi dùng tiếp.
    if previous_profiling not in {None, "json", "query_tree", "query_tree_optimizer"}:
        # Dừng với thông báo rõ ràng thay vì tiếp tục bằng dữ liệu hoặc cấu hình không hợp lệ.
        raise ValueError("Không nhận diện cấu hình enable_profiling hiện tại.")
    # Chuyển lỗi ra thông báo dễ đọc, bảo đảm chạy phần dọn dẹp nếu có.
    try:
        # Áp cấu hình hoặc câu lệnh DuckDB tại đúng bước được mô tả ở trên.
        con.execute("PRAGMA disable_profiling")
        # Áp cấu hình hoặc câu lệnh DuckDB tại đúng bước được mô tả ở trên.
        con.execute("SET explain_output='physical_only'")
        # Lưu mô tả kế hoạch thật do bộ máy trả về.
        plan = "\n\n".join(str(row[1]) for row in con.execute("EXPLAIN " + sql).fetchall())
        # Mở tài nguyên trong khối có quản lý để đóng hoặc dọn tự động khi kết thúc.
        with TemporaryDirectory(prefix="tpch-q6-") as folder:
            # Giá trị trung gian `output` được dùng ngay ở bước bên dưới.
            output = Path(folder) / "profile.json"
            # Áp cấu hình hoặc câu lệnh DuckDB tại đúng bước được mô tả ở trên.
            con.execute("PRAGMA profiling_output=" + _quote(output))
            # Áp cấu hình hoặc câu lệnh DuckDB tại đúng bước được mô tả ở trên.
            con.execute("PRAGMA enable_profiling='json'")
            # Chuyển lỗi ra thông báo dễ đọc, bảo đảm chạy phần dọn dẹp nếu có.
            try:
                # Giá trị trung gian `start` được dùng ngay ở bước bên dưới.
                start = perf_counter()
                # Lưu các dòng kết quả hoặc HTML đang được ghép.
                rows = con.execute(sql).fetchall()
                # Lưu số giây đo quanh execute và fetchall.
                seconds = perf_counter() - start
            finally:
                # Áp cấu hình hoặc câu lệnh DuckDB tại đúng bước được mô tả ở trên.
                con.execute("PRAGMA disable_profiling")
            # Lưu cây JSON profiling của đúng lượt SELECT.
            profile = json.loads(output.read_text())
        # Trả giá trị vừa xác định cho hàm gọi.
        return {"rows": rows, "seconds": seconds, "profile": profile,
                "plan": plan, "disabled_optimizers": disabled}
    finally:
        # Áp cấu hình hoặc câu lệnh DuckDB tại đúng bước được mô tả ở trên.
        con.execute("PRAGMA disable_profiling")
        # Áp cấu hình hoặc câu lệnh DuckDB tại đúng bước được mô tả ở trên.
        con.execute("SET explain_output=" + _quote(previous_explain))
        # Áp cấu hình hoặc câu lệnh DuckDB tại đúng bước được mô tả ở trên.
        con.execute("PRAGMA profiling_output=" + _quote(previous_output))
        # Kiểm tra trường hợp thiếu dữ liệu hoặc chưa có giá trị trước khi dùng tiếp.
        if previous_profiling is not None:
            # Áp cấu hình hoặc câu lệnh DuckDB tại đúng bước được mô tả ở trên.
            con.execute("PRAGMA enable_profiling=" + _quote(previous_profiling))


# Duyệt hồ sơ từ các nút con lên cha để đọc nguồn trước đầu ra.
def _nodes(profile):
    # Lưu kết quả có cấu trúc của lần chạy hoặc giá trị trả về.
    result = []
    # Duyệt từng mục theo thứ tự để thu dữ liệu hoặc ghép phần trình bày tương ứng.
    for child in profile.get("children", []):
        # Thêm mục hiện tại vào tập dữ liệu theo đúng thứ tự.
        result.extend(_nodes(child))
    # Chọn nhánh phù hợp với dữ liệu hoặc trạng thái vừa đọc.
    if str(profile.get("name", "")).strip().lower() != "query":
        # Thêm mục hiện tại vào tập dữ liệu theo đúng thứ tự.
        result.append(profile)
    # Trả giá trị vừa xác định cho hàm gọi.
    return result


# Vẽ bảng số dòng và timing từ hồ sơ DuckDB vừa thu.
def _duck_table(profile):
    # Danh sách toán tử trong hồ sơ DuckDB, nguồn trước đầu ra sau.
    nodes = _nodes(profile)
    # Lưu timing lớn nhất để tỷ lệ thanh trực quan không vượt khung.
    maximum = max((float(n["timing"]) for n in nodes), default=0) or 1
    # Lưu các dòng kết quả hoặc HTML đang được ghép.
    rows = ""
    # Duyệt từng mục theo thứ tự để thu dữ liệu hoặc ghép phần trình bày tương ứng.
    for node in nodes:
        # Lưu số giây đo quanh execute và fetchall.
        seconds = float(node["timing"])
        # Nối thêm nội dung hiện tại, giữ thứ tự các mục đã tạo trước đó.
        rows += (f"<tr><td><code>{escape(str(node['name']).strip())}</code></td>"
                 f"<td>{int(node['cardinality']):,}</td><td>{seconds:.6f} giây"
                 f"<div class='bar' style='width:{100 * seconds / maximum:.2f}%'></div></td></tr>")
    # Trả nội dung hiển thị, không chạy thêm SELECT trong bước ghép kết quả.
    return ("<table><thead><tr><th>Toán tử — nguồn trước, đầu ra sau</th>"
            "<th>Dòng đầu ra thực tế</th><th>DuckDB operator timing</th></tr></thead>"
            f"<tbody>{rows}</tbody></table>")


# Lấy một bộ đếm trên đúng dòng toán tử DataFusion.
def _df_metric(plan, operator, key):
    # Dòng chữ đang ghép trước khi xuống dòng hoặc nội dung nguồn đang xét.
    line = next((line for line in plan.splitlines() if line.lstrip().startswith(operator + ":")), "")
    # Tìm bộ đếm trong đúng dòng kế hoạch, không tự tạo số liệu nếu thiếu.
    found = re.search(r"(?:\[|, )" + re.escape(key) + r"=([^,\]]+)", line)
    # Trả giá trị vừa xác định cho hàm gọi.
    return found.group(1) if found else "Không có bộ đếm"


# Đặt số liệu hai hồ sơ cạnh nhau, giữ đúng phạm vi bộ đếm từng bên.
def q6_diagnostics(df_rows, duck_run):
    """Khoanh vùng bằng profile mới; không quy thời gian cho một dòng mã C++."""
    # Lưu mô tả kế hoạch thật do bộ máy trả về.
    plan = next((row["plan"] for row in df_rows if row["plan_type"] == "Plan with Metrics"), "")
    # Kiểm tra trường hợp thiếu dữ liệu hoặc chưa có giá trị trước khi dùng tiếp.
    if not plan:
        # Dừng với thông báo rõ ràng thay vì tiếp tục bằng dữ liệu hoặc cấu hình không hợp lệ.
        raise ValueError("EXPLAIN ANALYZE không trả Plan with Metrics; cần kiểm tra phiên bản.")
    # Các bộ đếm DataFusion cần giải thích và phạm vi đo của từng bộ đếm.
    counters = [
        ("ParquetExec", "time_elapsed_processing", "Thời gian xử lý luồng đọc/giải mã, không phải riêng CPU"),
        ("ParquetExec", "output_rows", "Dòng bộ đọc chuyển cho toán tử phía trên"),
        ("ParquetExec", "row_groups_pruned", "Nhóm hàng bỏ qua bằng thống kê"),
        ("ParquetExec", "pushdown_rows_filtered", "Dòng loại bởi bộ lọc trong giải mã"),
        ("FilterExec", "output_rows", "Dòng còn lại sau FilterExec"),
        ("FilterExec", "elapsed_compute", "Chi phí tính toán được FilterExec ghi nhận"),
        ("AggregateExec", "elapsed_compute", "Chi phí tổng hợp, gồm biểu thức nhân Q6"),
    ]
    # Lưu các dòng kết quả hoặc HTML đang được ghép.
    rows = "".join(f"<tr><td><code>{op}.{key}</code></td>"
                   f"<td>{escape(_df_metric(plan, op, key))}</td><td>{escape(note)}</td></tr>"
                   for op, key, note in counters)
    # Danh sách toán tử trong hồ sơ DuckDB, nguồn trước đầu ra sau.
    nodes = _nodes(duck_run["profile"])
    # Toán tử có timing lớn nhất trong đúng hồ sơ vừa thu.
    hot = max(nodes, key=lambda n: float(n["timing"])) if nodes else None
    # Lưu nhận xét dựa trên số liệu vừa thu.
    finding = (f"Trong hồ sơ DuckDB vừa chạy, toán tử có timing lớn nhất là "
               f"<strong>{escape(str(hot['name']).strip())}</strong> "
               f"({float(hot['timing']):.6f} giây)." if hot else "Không có hồ sơ toán tử.")
    # Trả nội dung hiển thị, không chạy thêm SELECT trong bước ghép kết quả.
    return HTML(STYLE + f"""<div class='q6-view'>
<h3>Q6 — phát hiện nơi tốn thời gian từ lần chạy này</h3>
<p><strong>DataFusion:</strong> lần chẩn đoán EXPLAIN ANALYZE riêng, chạy thêm một lần Q6.</p>
<table><thead><tr><th>Bộ đếm</th><th>Giá trị vừa thu</th><th>Cách đọc</th></tr></thead><tbody>{rows}</tbody></table>
<p><strong>DuckDB:</strong> hồ sơ của đúng lần SELECT Q6 mặc định ở ô phía trên, không chạy lại tại đây.</p>
{_duck_table(duck_run['profile'])}<p>{finding}</p>
<p>Nếu READ_PARQUET chiếm phần lớn thời gian, cần khảo sát đường đọc, giải nén, giải mã và lọc trong bộ đọc;
không thể quy toàn bộ thời gian đó cho ApplyFilter. Mã nguồn phía dưới giải thích cách đường này hoạt động.</p>
<p>Hai bộ máy có bộ đếm khác phạm vi. Không cộng/trừ các bộ đếm DataFusion và DuckDB để tính mức nhanh hơn.
EXPLAIN không có ANALYZE chỉ cho biết kế hoạch, không có số đo trên.</p>
<details><summary>Kế hoạch DataFusion kèm bộ đếm nguyên bản</summary><pre>{escape(plan)}</pre></details>
<details><summary>JSON DuckDB nguyên bản của lượt mặc định</summary><pre>{escape(json.dumps(duck_run['profile'], ensure_ascii=False, indent=2))}</pre></details>
</div>""")


# So SQL đang chạy, kết quả và thời gian trước/sau thay cấu hình Q6.
def q6_control_result(baseline, trial, df_value):
    """Đối chiếu hai lần SELECT thật và thông báo đúng cả khi không cải thiện."""
    # Lưu trạng thái tương đương kết quả của hai phương án.
    same = baseline["rows"] == trial["rows"] and trial["rows"][0][0] == df_value
    # Lưu chênh lệch thời gian trước trừ sau, giá trị âm nghĩa là chậm hơn.
    delta = baseline["seconds"] - trial["seconds"]
    # Lưu phần trăm chênh lệch theo thời gian mốc.
    percent = 100 * delta / baseline["seconds"] if baseline["seconds"] else 0
    # Lưu xác nhận lượt đối chứng thực sự tắt filter_pushdown.
    changed = trial["disabled_optimizers"] == "filter_pushdown"
    # Kiểm tra trường hợp thiếu dữ liệu hoặc chưa có giá trị trước khi dùng tiếp.
    if not same:
        # Lưu nhận xét phản ánh cả trường hợp nhanh hơn, chậm hơn hoặc khác kết quả.
        conclusion = "Kết quả khác nhau. Không chấp nhận thay đổi này như một tối ưu tương đương."
    # Kiểm tra trường hợp thiếu dữ liệu hoặc chưa có giá trị trước khi dùng tiếp.
    elif not changed:
        # Lưu nhận xét phản ánh cả trường hợp nhanh hơn, chậm hơn hoặc khác kết quả.
        conclusion = "Chưa tắt filter_pushdown: đây là một lượt chạy mặc định nữa, chưa phải đối chứng chuyển đường lọc."
    # Chọn nhánh phù hợp với dữ liệu hoặc trạng thái vừa đọc.
    elif delta > 0:
        # Lưu nhận xét phản ánh cả trường hợp nhanh hơn, chậm hơn hoặc khác kết quả.
        conclusion = f"Lượt tắt filter_pushdown giảm {delta:.3f} giây ({percent:.1f}%) so với lượt mặc định ở trên; kết quả giữ nguyên."
    else:
        # Lưu nhận xét phản ánh cả trường hợp nhanh hơn, chậm hơn hoặc khác kết quả.
        conclusion = f"Lượt này chưa cải thiện: chậm thêm {-delta:.3f} giây; kết quả giữ nguyên. Không kết luận nhanh hơn."
    # Lưu các dòng kết quả hoặc HTML đang được ghép.
    rows = ""
    # Duyệt từng mục theo thứ tự để thu dữ liệu hoặc ghép phần trình bày tương ứng.
    for label, run in [("Mặc định", baseline), ("Lượt đối chứng", trial)]:
        # Nối thêm nội dung hiện tại, giữ thứ tự các mục đã tạo trước đó.
        rows += (f"<tr><th>{label}</th><td><code>{escape(run['disabled_optimizers'] or '(rỗng)')}</code></td>"
                 f"<td>{run['seconds']:.6f} giây</td><td>{escape(str(run['rows'][0][0]))}</td></tr>")
    # Trả nội dung hiển thị, không chạy thêm SELECT trong bước ghép kết quả.
    return HTML(STYLE + f"""<div class='q6-view'><h3>Q6 — kết quả đối chứng trên máy hiện tại</h3>
<table><thead><tr><th>Lượt chạy</th><th>disabled_optimizers lúc chạy</th><th>Thời gian ngoài API</th><th>revenue</th></tr></thead><tbody>{rows}</tbody></table>
<p><strong>{escape(conclusion)}</strong></p>
<p>Cả hai lượt DuckDB đều bật JSON profiling và đo execute + fetchall; EXPLAIN nằm ngoài khoảng đo.
Mỗi cấu hình một lượt, mặc định chạy trước, không xóa cache. Chênh lệch quan sát còn chịu ảnh hưởng bộ nhớ đệm và tải máy.</p>
<h4>Toán tử sau khi áp dụng cấu hình trong ô vừa chạy</h4>{_duck_table(trial['profile'])}
<details open><summary>Kế hoạch vật lý mặc định</summary><pre>{escape(baseline['plan'])}</pre></details>
<details open><summary>Kế hoạch vật lý của lượt đối chứng</summary><pre>{escape(trial['plan'])}</pre></details>
<p>Khi tắt thành công, kế hoạch Q6 có FILTER riêng giữa READ_PARQUET và PROJECTION. Thay đổi này lựa chọn lại đường thực thi;
không sửa SQL nghiệp vụ, không sửa mã C++ và không biến DuckDB thành DataFusion.</p></div>""")
