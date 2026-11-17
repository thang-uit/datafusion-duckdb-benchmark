"""Gọi chương trình Rust và trình bày kết quả Q17; không tối ưu kế hoạch bằng Python."""

# Escape dữ liệu trước khi đưa vào HTML notebook.
from html import escape
# Đọc hoặc ghi JSON nguồn và kết quả có cấu trúc.
import json
# So sánh kết quả số thực với sai số nhỏ.
import math
# Đọc đường dẫn bằng Path thay vì ghép chuỗi phụ thuộc máy.
from pathlib import Path
# Tìm mẫu tên toán tử, biểu thức hoặc đường dẫn trong văn bản.
import re
# Gọi chương trình ngoài bằng danh sách tham số và kiểm tra trạng thái.
import subprocess

# Nạp tiện ích phục vụ phần minh họa, chưa chạy truy vấn khi import.
from IPython.display import HTML

# Ghép vùng kiến trúc tương ứng với kế hoạch đang đọc.
from plan_architecture import architecture_panel, REPORT_CSS


# Gọi binary Rust có timeout rồi kiểm tra JSON đúng phiên bản và chế độ.
def run_q17_rule(benchmark_root, enabled, plan_only=False):
    """Chạy một lượt Q17 gốc trong Rust; timeout dừng tiến trình nếu quá 120 giây."""
    # Lưu đường dẫn chuẩn hóa tới kho benchmark.
    root = Path(benchmark_root).resolve()
    # Lưu binary release của chương trình Rust Q17.
    binary = root / "tpch/q17-physical-rule/target/release/q17-physical-rule"
    # Kiểm tra trường hợp thiếu dữ liệu hoặc chưa có giá trị trước khi dùng tiếp.
    if not binary.is_file():
        # Dừng với thông báo rõ ràng thay vì tiếp tục bằng dữ liệu hoặc cấu hình không hợp lệ.
        raise FileNotFoundError("Chưa build chương trình Rust. Chạy ô cargo build trước.")
    # Lưu chế độ on/off quyết định có đăng ký quy tắc riêng.
    mode = "on" if enabled else "off"
    # Lưu danh sách tham số truyền trực tiếp cho subprocess, không qua shell.
    command = [str(binary), str(root), mode]
    # Chọn nhánh phù hợp với dữ liệu hoặc trạng thái vừa đọc.
    if plan_only:
        # Thêm mục hiện tại vào tập dữ liệu theo đúng thứ tự.
        command.append("--plan-only")
    # Chuyển lỗi ra thông báo dễ đọc, bảo đảm chạy phần dọn dẹp nếu có.
    try:
        # Kết quả subprocess gồm stdout, stderr và mã kết thúc, có giới hạn thời gian.
        process = subprocess.run(
            command,
            capture_output=True, text=True, timeout=120, check=True,
        )
    except subprocess.TimeoutExpired as error:
        # Dừng với thông báo rõ ràng thay vì tiếp tục bằng dữ liệu hoặc cấu hình không hợp lệ.
        raise RuntimeError("Q17 vượt quá 120 giây; tiến trình Rust đã bị dừng.") from error
    except subprocess.CalledProcessError as error:
        # Dừng với thông báo rõ ràng thay vì tiếp tục bằng dữ liệu hoặc cấu hình không hợp lệ.
        raise RuntimeError(f"Chương trình Rust không hoàn tất:\n{error.stderr}") from error
    # Lưu kết quả có cấu trúc của lần chạy hoặc giá trị trả về.
    result = json.loads(process.stdout)
    # Lưu SQL Q17 gốc hoặc nội dung nguồn để đối chiếu.
    original = (root / "tpch/queries.sql").read_text().splitlines()[16]
    # Chọn nhánh phù hợp với dữ liệu hoặc trạng thái vừa đọc.
    if result["sql"] != original:
        # Dừng với thông báo rõ ràng thay vì tiếp tục bằng dữ liệu hoặc cấu hình không hợp lệ.
        raise ValueError("Chương trình Rust không sử dụng đúng SQL Q17 gốc.")
    # Chọn nhánh phù hợp với dữ liệu hoặc trạng thái vừa đọc.
    if result["datafusion_version"] != "32.0.0":
        # Dừng với thông báo rõ ràng thay vì tiếp tục bằng dữ liệu hoặc cấu hình không hợp lệ.
        raise ValueError("Phiên bản DataFusion Rust không đúng 32.0.0.")
    # Kiểm tra trường hợp thiếu dữ liệu hoặc chưa có giá trị trước khi dùng tiếp.
    if result.get("rule_name") != "statistics_build_side" or not result.get("collect_statistics"):
        # Dừng với thông báo rõ ràng thay vì tiếp tục bằng dữ liệu hoặc cấu hình không hợp lệ.
        raise ValueError("Binary cũ hoặc chưa bật cùng thống kê; chạy lại ô cargo build.")
    # Kiểm tra trường hợp thiếu dữ liệu hoặc chưa có giá trị trước khi dùng tiếp.
    if result.get("execution_performed") != (not plan_only):
        # Dừng với thông báo rõ ràng thay vì tiếp tục bằng dữ liệu hoặc cấu hình không hợp lệ.
        raise ValueError("Chế độ lập kế hoạch/thực thi không đúng yêu cầu.")
    # Lưu nhật ký quyết định được Rust chốt trước khi thực thi.
    decisions = result.get("decisions", [])
    # Chọn nhánh phù hợp với dữ liệu hoặc trạng thái vừa đọc.
    if result["rule_applications"] != sum(d["swapped"] for d in decisions):
        # Dừng với thông báo rõ ràng thay vì tiếp tục bằng dữ liệu hoặc cấu hình không hợp lệ.
        raise ValueError("Số lần biến đổi không khớp nhật ký quyết định.")
    # Kiểm tra trường hợp thiếu dữ liệu hoặc chưa có giá trị trước khi dùng tiếp.
    if not enabled and result["rule_applications"]:
        # Dừng với thông báo rõ ràng thay vì tiếp tục bằng dữ liệu hoặc cấu hình không hợp lệ.
        raise ValueError("Phương án tắt đã biến đổi kế hoạch.")
    # Trả giá trị vừa xác định cho hàm gọi.
    return result



# Hiển thị bằng chứng được thu trước collect, không dùng số dòng chạy xong để chọn.
def show_estimation_decisions(run):
    """Hiển thị bằng chứng thu trước collect, tách giới hạn khỏi số dự đoán."""
    # Phân biệt giá trị chưa biết với con số có trong JSON.
    def number(value):
        # Trả giá trị vừa xác định cho hàm gọi.
        return "Chưa biết" if value is None else f"{value:,}"

    # Lưu các dòng kết quả hoặc HTML đang được ghép.
    rows = ""
    # Duyệt từng mục theo thứ tự để thu dữ liệu hoặc ghép phần trình bày tương ứng.
    for decision in run["decisions"]:
        # Ghép tên hai cột khóa nối để người đọc nhận diện đúng phép nối.
        key = ", ".join(f"{left} = {right}" for left, right in decision["join_keys"])
        # Duyệt từng mục theo thứ tự để thu dữ liệu hoặc ghép phần trình bày tương ứng.
        for side, label in [("left", "Trái: dựng ban đầu"), ("right", "Phải: dò ban đầu")]:
            # Lấy căn cứ số dòng và mô hình chi phí của đúng phía đang xét.
            e, cost = decision[side], decision[side + "_cost"]
            # Nối thêm nội dung hiện tại, giữ thứ tự các mục đã tạo trước đó.
            rows += (
                f"<tr><td>{escape(key)}</td><td>{label}</td>"
                f"<td>{number(e['estimated_rows'])}</td>"
                f"<td>{number(e['lower_rows'])} – {number(e['upper_rows'])}</td>"
                f"<td>{number(cost['projected_fixed_width_bytes']) if cost else 'Chưa biết'}</td>"
                f"<td>{number(cost['lower_bytes']) if cost else 'Chưa biết'} – "
                f"{number(cost['upper_bytes']) if cost else 'Chưa biết'}</td></tr>"
            )
        # Lưu nhận xét phản ánh cả trường hợp nhanh hơn, chậm hơn hoặc khác kết quả.
        conclusion = ("Đổi phía: chi phí mô hình tối đa bên phải nhỏ hơn tối thiểu bên trái."
                      if decision["swapped"] else "Giữ thứ tự: thiếu căn cứ hoặc khoảng chi phí chồng lấp.")
        # Nối thêm nội dung hiện tại, giữ thứ tự các mục đã tạo trước đó.
        rows += f"<tr><td colspan='6'><strong>{conclusion}</strong></td></tr>"
    # Kiểm tra trường hợp thiếu dữ liệu hoặc chưa có giá trị trước khi dùng tiếp.
    if not rows:
        # Lưu các dòng kết quả hoặc HTML đang được ghép.
        rows = "<tr><td colspan='6'>Không có quyết định đổi cho phép nối được hỗ trợ.</td></tr>"
    # Nhãn phân biệt chỉ lập kế hoạch với lượt đã thực thi.
    execution = "Chưa thực thi Q17." if not run["execution_performed"] else "Nhật ký được chốt trước lần collect đã chạy."
    # Trả nội dung hiển thị, không chạy thêm SELECT trong bước ghép kết quả.
    return HTML(f"""<div class="q17-estimation" style="font:14px/1.6 system-ui">{REPORT_CSS}
<h3>Quyết định từ thống kê trước thực thi</h3>
{architecture_panel("extension-rewrite")}<p><strong>{execution}</strong>
Cả hai phương án Rust bật collect_statistics=true; không biết trước số dòng sau lọc.</p>
<table style="width:100%;border-collapse:collapse" border="1" cellpadding="8">
<thead><tr><th>Khóa nối</th><th>Phía trước biến đổi</th><th>Số dòng dự đoán</th>
<th>Khoảng số dòng có căn cứ</th><th>Độ rộng cột (byte/dòng)</th><th>Khoảng chi phí mô hình (byte)</th></tr></thead>
<tbody>{rows}</tbody></table>
<p>Công thức: số dòng × (độ rộng các cột cố định + 32 byte chi phí băm mô hình mỗi dòng).
32 là tham số chung, không phải số đo RAM hay bảo đảm chi phí thực tế. Giới hạn trên không phải số dòng dự đoán.
Cột chuỗi/kiểu chưa hỗ trợ không được tự gán độ rộng. Không chạy COUNT, lấy mẫu hay đọc kết quả Q17 để quyết định.</p>
<p>Chuẩn bị/đăng ký bảng: {run['preparation_seconds']:.6f}s; lập kế hoạch: {run['planning_seconds']:.6f}s.
Không dùng số dòng thực tế trong EXPLAIN ANALYZE để chọn phía dựng.</p></div>""")

# Kiểm tra kết quả tương đương rồi trình bày hai lượt Rust đối chứng.
def show_rule_comparison(baseline, rewritten, reference_value, data_dir=None):
    """Bảng thời gian và kế hoạch lấy từ đúng hai lượt Rust đã chạy."""
    # Kiểm tra trường hợp thiếu dữ liệu hoặc chưa có giá trị trước khi dùng tiếp.
    if not all(r.get("execution_performed") for r in (baseline, rewritten)):
        # Dừng với thông báo rõ ràng thay vì tiếp tục bằng dữ liệu hoặc cấu hình không hợp lệ.
        raise ValueError("Cần hai lượt thực thi, không dùng bản plan-only để so thời gian.")
    # Lưu xác nhận SQL của hai lượt Rust không đổi.
    same_sql = baseline["sql"] == rewritten["sql"]
    # Lưu so kết quả số thực với sai số đã quy định.
    same_result = math.isclose(baseline["value"], rewritten["value"], rel_tol=1e-12, abs_tol=1e-6)
    # Lưu đối chiếu kết quả Rust với mốc Python.
    same_reference = math.isclose(rewritten["value"], reference_value, rel_tol=1e-12, abs_tol=1e-6)
    # Kiểm tra trường hợp thiếu dữ liệu hoặc chưa có giá trị trước khi dùng tiếp.
    if not (same_sql and same_result and same_reference):
        # Dừng với thông báo rõ ràng thay vì tiếp tục bằng dữ liệu hoặc cấu hình không hợp lệ.
        raise ValueError("SQL hoặc kết quả không tương đương; chưa chấp nhận thay đổi kế hoạch.")
    # Lưu chênh lệch thời gian trước trừ sau, giá trị âm nghĩa là chậm hơn.
    delta = baseline["total_seconds"] - rewritten["total_seconds"]
    # Chọn nhánh phù hợp với dữ liệu hoặc trạng thái vừa đọc.
    if delta > 0:
        # Lưu nhận xét dựa trên số liệu vừa thu.
        finding = f"Lượt bật quy tắc giảm {delta:.3f} giây ({100 * delta / baseline['total_seconds']:.1f}%)."
    else:
        # Lưu nhận xét dựa trên số liệu vừa thu.
        finding = f"Lượt bật quy tắc chưa cải thiện, tăng {-delta:.3f} giây."
    # Lưu các dòng kết quả hoặc HTML đang được ghép.
    rows = ""
    # Khởi tạo phần chứa hai kế hoạch có bộ đếm sau thực thi.
    plans = ""
    # Khởi tạo các hàng so bộ đếm của phép nối mục tiêu.
    target_rows = ""
    # Duyệt từng mục theo thứ tự để thu dữ liệu hoặc ghép phần trình bày tương ứng.
    for label, run in [("Tắt quy tắc", baseline), ("Bật quy tắc", rewritten)]:
        # Nối thêm nội dung hiện tại, giữ thứ tự các mục đã tạo trước đó.
        rows += (f"<tr><th>{label}</th><td>{run['rule_applications']}</td>"
                 f"<td>{run['preparation_seconds']:.6f}</td><td>{run['planning_seconds']:.6f}</td><td>{run['execution_seconds']:.6f}</td>"
                 f"<td>{run['total_seconds']:.6f}</td><td>{run['preparation_planning_execution_seconds']:.6f}</td><td>{run['value']}</td></tr>")
        # Lưu bản hiển thị đã rút gọn đường dẫn, không sửa kế hoạch để thực thi.
        visual = run["physical_plan_with_metrics"]
        # Lưu dòng của phép nối mục tiêu cần lấy bộ đếm.
        target = next((line for line in visual.splitlines() if "HashJoinExec:" in line
                       and any(keys in line for keys in ["on=[(l_partkey@0, p_partkey@0)]", "on=[(p_partkey@0, l_partkey@0)]"])
                       and "filter=" not in line), None)
        # Kiểm tra trường hợp thiếu dữ liệu hoặc chưa có giá trị trước khi dùng tiếp.
        if target is None:
            # Dừng với thông báo rõ ràng thay vì tiếp tục bằng dữ liệu hoặc cấu hình không hợp lệ.
            raise ValueError("Không nhận diện được bộ đếm của phép nối mục tiêu.")
        # Tập giá trị bộ đếm thực tế cần đưa vào bảng.
        values = []
        # Duyệt từng mục theo thứ tự để thu dữ liệu hoặc ghép phần trình bày tương ứng.
        for key in ["build_input_rows", "build_mem_used", "build_time", "join_time"]:
            # Tìm bộ đếm trong đúng dòng kế hoạch, không tự tạo số liệu nếu thiếu.
            value = re.search(r"(?:\[|, )" + key + r"=([^,\]]+)", target)
            # Kiểm tra trường hợp thiếu dữ liệu hoặc chưa có giá trị trước khi dùng tiếp.
            if value is None:
                # Dừng với thông báo rõ ràng thay vì tiếp tục bằng dữ liệu hoặc cấu hình không hợp lệ.
                raise ValueError(f"Thiếu bộ đếm {key} tại phép nối mục tiêu.")
            # Thêm mục hiện tại vào tập dữ liệu theo đúng thứ tự.
            values.append(value.group(1))
        # Nối thêm nội dung hiện tại, giữ thứ tự các mục đã tạo trước đó.
        target_rows += f"<tr><th>{label}</th>" + "".join(f"<td>{escape(v)}</td>" for v in values) + "</tr>"
        # Kiểm tra trường hợp thiếu dữ liệu hoặc chưa có giá trị trước khi dùng tiếp.
        if data_dir is not None:
            # Lưu tiền tố đường dẫn dữ liệu cần ẩn trong bảng trình bày.
            prefix = str(data_dir).rstrip("/")
            # Lưu bản hiển thị đã rút gọn đường dẫn, không sửa kế hoạch để thực thi.
            visual = visual.replace(prefix + "/", "[DỮ LIỆU]/").replace(prefix.lstrip("/") + "/", "[DỮ LIỆU]/")
        # Nối thêm nội dung hiện tại, giữ thứ tự các mục đã tạo trước đó.
        plans += f"<details open><summary>{label} — kế hoạch đã thực thi và bộ đếm</summary><pre>{escape(visual)}</pre></details>"
    # Trả nội dung hiển thị, không chạy thêm SELECT trong bước ghép kết quả.
    return HTML(f"""<div class='q17-extension'><style>
.q17-extension {{color:var(--tpch-report-fg,#202b33);font:14px/1.6 system-ui,sans-serif}}
.q17-extension table {{width:100%;border-collapse:collapse}}
.q17-extension td,.q17-extension th {{padding:10px;border:1px solid #8886;text-align:left}}
.q17-extension pre {{white-space:pre-wrap;overflow-wrap:anywhere;padding:12px;background:#8881;font:12px/1.6 monospace}}
.q17-extension summary {{font-weight:700;cursor:pointer}}.q17-extension details {{margin:18px 0}}
</style>{REPORT_CSS}<h3>Q17 — cùng SQL gốc, cùng chương trình Rust/DataFusion 32</h3>
<table><thead><tr><th>Phương án</th><th>Số lần đổi kế hoạch</th><th>Chuẩn bị (s)</th><th>Lập kế hoạch (s)</th>
<th>Thực thi (s)</th><th>Kế hoạch + chạy (s)</th><th>Chuẩn bị + kế hoạch + chạy (s)</th><th>Kết quả</th></tr></thead><tbody>{rows}</tbody></table>
<p><strong>{escape(finding)}</strong> SQL giữ nguyên; cả hai bật thống kê nguồn; kết quả hai lượt và kết quả Python gần bằng nhau.</p>
<h4>Phép nối mục tiêu — số liệu từ cùng lần collect</h4>
<table><thead><tr><th>Phương án</th><th>Dòng phía dựng</th><th>build_mem_used (byte)</th>
<th>build_time</th><th>join_time</th></tr></thead><tbody>{target_rows}</tbody></table>
<p>Tổng gồm lập kế hoạch và collect trong chương trình Rust; không gồm khởi động tiến trình, đăng ký bảng,
build hay in kế hoạch. Cột tổng có chuẩn bị cộng thêm thời gian đăng ký bảng và thu metadata; không gồm khởi động tiến trình. Mỗi phương án một lượt; không xóa cache. So sánh hiệu quả quy tắc bằng hai lượt Rust;
thời gian Python và DuckDB là mốc tham khảo riêng.</p>
{show_estimation_decisions(rewritten).data}{plans}<p>Tại phép nối mục tiêu, đối chiếu <code>build_input_rows</code>, <code>build_mem_used</code>,
<code>build_time</code> và nguồn của nhánh trái. build_time có cả đọc đầu vào;
không cộng bộ đếm thời gian của toán tử cha và con. Bộ đếm output_rows của HashJoin bản 32 ở nhánh thông thường
ghi số dòng lô phía dò; dùng Projection/Coalesce kế tiếp để xem số dòng ghép.</p></div>""")
