"""Tạo ảnh chú giải Q6 từ nguyên văn mã nguồn đã checkout; không chạy truy vấn.

Chạy từ tpch: ../venv/bin/python render_q6_assets.py --source-root ../../source-inspection
Pillow dùng môi trường hiện có. Mã nguồn upstream nằm ngoài kho benchmark.
"""

# Đọc tham số dòng lệnh và báo thiếu tham số rõ ràng.
import argparse
# Tính SHA-256 để đối chiếu đoạn mã trích với nguồn.
import hashlib
# Đọc hoặc ghi JSON nguồn và kết quả có cấu trúc.
import json
# Đọc đường dẫn bằng Path thay vì ghép chuỗi phụ thuộc máy.
from pathlib import Path
# Gọi chương trình ngoài bằng danh sách tham số và kiểm tra trạng thái.
import subprocess

# Đọc, vẽ và lưu ảnh bằng Pillow.
from PIL import Image, ImageDraw, ImageFont


# Lưu thư mục chứa chính mô-đun, không phụ thuộc thư mục Terminal.
HERE = Path(__file__).resolve().parent
# Lưu thư mục lưu ảnh notebook.
OUT = HERE / "q6-assets"
# Lưu thư mục font có sẵn trên macOS.
FONTS = Path("/System/Library/Fonts/Supplemental")
# Bảng màu chữ, chú thích và hai loại luồng trong hình.
INK, MUTED, GREEN, ORANGE = "#172e37", "#51636b", "#17654e", "#9b4d15"
# Lưu danh sách nguồn và checksum các đoạn mã trích.
MANIFEST = []


# Chọn font macOS cho chữ thường, đậm hoặc mã nguồn.
def font(size, bold=False, mono=False):
    # Tên tệp font macOS theo kiểu chữ cần vẽ.
    name = "Courier New.ttf" if mono else "Arial Bold.ttf" if bold else "Arial.ttf"
    # Trả giá trị vừa xác định cho hàm gọi.
    return ImageFont.truetype(str(FONTS / name), size)


# Vẽ dòng chữ ở tọa độ ảnh, thay ký hiệu số để font hiển thị đúng.
def write(d, x, y, text, size=27, color=INK, bold=False, mono=False):
    # Duyệt từng mục theo thứ tự để thu dữ liệu hoặc ghép phần trình bày tương ứng.
    for number, symbol in enumerate("①②③④⑤⑥⑦⑧", start=1):
        # Giá trị trung gian `text` được dùng ngay ở bước bên dưới.
        text = text.replace(symbol, f"({number})")
    # Vẽ thành phần tại tọa độ đã tính, không thay đổi dữ liệu truy vấn.
    d.text((x, y), text, font=font(size, bold, mono), fill=color)


# Ngắt dòng theo độ rộng pixel, trả vị trí để nội dung kế tiếp không đè nhau.
def paragraph(d, x, y, text, width, size=27, color=INK):
    # Duyệt từng mục theo thứ tự để thu dữ liệu hoặc ghép phần trình bày tương ứng.
    for original in text.split("\n"):
        # Dòng chữ đang ghép trước khi xuống dòng hoặc nội dung nguồn đang xét.
        line = ""
        # Duyệt từng mục theo thứ tự để thu dữ liệu hoặc ghép phần trình bày tương ứng.
        for word in original.split():
            # Dòng chữ dự kiến sau khi thêm một từ, dùng để đo độ rộng.
            test = (line + " " + word).strip()
            # Chọn nhánh phù hợp với dữ liệu hoặc trạng thái vừa đọc.
            if line and d.textlength(test, font=font(size)) > width:
                # Vẽ thành phần tại tọa độ đã tính, không thay đổi dữ liệu truy vấn.
                write(d, x, y, line, size, color)
                # Nối thêm nội dung hiện tại, giữ thứ tự các mục đã tạo trước đó.
                y += size + 13
                # Dòng chữ đang ghép trước khi xuống dòng hoặc nội dung nguồn đang xét.
                line = word
            else:
                # Dòng chữ đang ghép trước khi xuống dòng hoặc nội dung nguồn đang xét.
                line = test
        # Vẽ thành phần tại tọa độ đã tính, không thay đổi dữ liệu truy vấn.
        write(d, x, y, line, size, color)
        # Nối thêm nội dung hiện tại, giữ thứ tự các mục đã tạo trước đó.
        y += size + 13
    # Trả giá trị vừa xác định cho hàm gọi.
    return y


# Vẽ số chú giải tại vị trí thành phần trong ảnh.
def circle(d, x, y, number, color):
    # Vẽ thành phần tại tọa độ đã tính, không thay đổi dữ liệu truy vấn.
    d.ellipse((x - 25, y - 25, x + 25, y + 25), fill="white", outline=color, width=4)
    # Vẽ thành phần tại tọa độ đã tính, không thay đổi dữ liệu truy vấn.
    d.text((x, y), str(number), anchor="mm", font=font(27, True), fill=color)


# Lưu ảnh vào thư mục hình của notebook.
def save(im, name):
    # Ghi kết quả tạo hình hoặc metadata ra tệp đích.
    im.save(OUT / name)


# Kết xuất đúng đoạn mã upstream cùng số dòng, commit, URL và SHA-256.
def source_figure(source_root, name, title, sections, notes):
    """Giữ từng dòng nguồn, số dòng gốc và URL cố định theo commit."""
    # Chuẩn bị ảnh hoặc bề mặt vẽ, giữ nguyên kích thước nguồn.
    im = Image.new("RGB", (2000, 2600), "white")
    # Chuẩn bị ảnh hoặc bề mặt vẽ, giữ nguyên kích thước nguồn.
    d = ImageDraw.Draw(im)
    # Vẽ thành phần tại tọa độ đã tính, không thay đổi dữ liệu truy vấn.
    write(d, 65, 36, title, 43, bold=True)
    # Vẽ thành phần tại tọa độ đã tính, không thay đổi dữ liệu truy vấn.
    write(d, 65, 102, "Ảnh kết xuất nguyên văn mã nguồn • số dòng gốc • vùng liên quan được tô nền", 26, MUTED)
    # Vị trí dọc của nội dung kế tiếp trong ảnh, tránh chồng lên đoạn trước.
    y = 163
    # Lưu thông tin truy nguyên từng đoạn mã trong một hình.
    entries = []
    # Duyệt từng mục theo thứ tự để thu dữ liệu hoặc ghép phần trình bày tương ứng.
    for repo, relative, first, last, highlighted in sections:
        # Lưu đường dẫn checkout ứng với đoạn mã cần trích.
        checkout = source_root / repo
        # Lưu mã commit thật của checkout để khóa liên kết nguồn.
        commit = subprocess.check_output(["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True).strip()
        # Chọn đúng kho GitHub cho DataFusion hoặc DuckDB.
        owner = "duckdb/duckdb" if repo.startswith("duckdb") else "apache/datafusion"
        # Liên kết GitHub khóa theo commit và khoảng số dòng trích mã.
        url = f"https://github.com/{owner}/blob/{commit}/{relative}#L{first}-L{last}"
        # Đọc nội dung tệp hiện tại để trình bày hoặc kiểm tra, không lấy từ output cũ.
        lines = (checkout / relative).read_text().splitlines()
        # Lưu các dòng mã nguồn được trích theo khoảng số dòng.
        selected = lines[first - 1:last]
        # Chọn nhánh phù hợp với dữ liệu hoặc trạng thái vừa đọc.
        if len(selected) != last - first + 1:
            # Dừng với thông báo rõ ràng thay vì tiếp tục bằng dữ liệu hoặc cấu hình không hợp lệ.
            raise ValueError(f"Khoảng dòng không tồn tại: {relative}:{first}-{last}")
        # Lưu đoạn mã nguyên văn, giữ newline để tính checksum.
        code = "\n".join(selected) + "\n"
        # Thêm mục hiện tại vào tập dữ liệu theo đúng thứ tự.
        entries.append({"repository": repo, "commit": commit, "file": relative,
                        "lines": [first, last], "url": url, "source": code,
                        "sha256": hashlib.sha256(code.encode()).hexdigest()})
        # Vẽ thành phần tại tọa độ đã tính, không thay đổi dữ liệu truy vấn.
        write(d, 65, y, repo + "  •  " + relative, 25, GREEN, True)
        # Nối thêm nội dung hiện tại, giữ thứ tự các mục đã tạo trước đó.
        y += 45
        # Cỡ chữ ban đầu, chỉ giảm khi mã vượt chiều rộng cho phép.
        size = 26
        # Điều chỉnh từng bước cho tới khi nội dung vừa giới hạn hiển thị.
        while max(d.textlength(line.expandtabs(4), font=font(size, mono=True)) for line in selected) > 1780:
            # Nối thêm nội dung hiện tại, giữ thứ tự các mục đã tạo trước đó.
            size -= 1
        # Lưu chiều cao mỗi dòng để giữ bố cục mã nguồn.
        line_height = size + 15
        # Vẽ thành phần tại tọa độ đã tính, không thay đổi dữ liệu truy vấn.
        d.rounded_rectangle((65, y - 7, 1935, y + len(selected) * line_height + 9), radius=10,
                            fill="#f4f6f7", outline="#cfd8dc", width=2)
        # Duyệt từng mục theo thứ tự để thu dữ liệu hoặc ghép phần trình bày tương ứng.
        for number, line in enumerate(selected, start=first):
            # Chọn nhánh phù hợp với dữ liệu hoặc trạng thái vừa đọc.
            if number in highlighted:
                # Vẽ thành phần tại tọa độ đã tính, không thay đổi dữ liệu truy vấn.
                d.rectangle((67, y - 2, 1933, y + line_height - 2), fill="#fff0ce")
                # Vẽ thành phần tại tọa độ đã tính, không thay đổi dữ liệu truy vấn.
                d.rectangle((67, y - 2, 75, y + line_height - 2), fill=ORANGE)
            # Vẽ thành phần tại tọa độ đã tính, không thay đổi dữ liệu truy vấn.
            write(d, 84, y, str(number), size, MUTED, mono=True)
            # Vẽ thành phần tại tọa độ đã tính, không thay đổi dữ liệu truy vấn.
            write(d, 160, y, line.expandtabs(4), size, mono=True)
            # Nối thêm nội dung hiện tại, giữ thứ tự các mục đã tạo trước đó.
            y += line_height
        # Nối thêm nội dung hiện tại, giữ thứ tự các mục đã tạo trước đó.
        y += 45
    # Vị trí dọc của nội dung kế tiếp trong ảnh, tránh chồng lên đoạn trước.
    y = paragraph(d, 65, y, notes, 1865, 29)
    # Vị trí dọc của nội dung kế tiếp trong ảnh, tránh chồng lên đoạn trước.
    y = paragraph(d, 65, y + 15, "Nguồn được ghi đầy đủ bằng liên kết và mã commit dưới ảnh trong notebook. Ảnh giải thích cơ chế; số đo thời gian nằm ở ô thực thi.", 1865, 25, MUTED)
    # Thực hiện bước chuẩn bị hoặc trình bày với các giá trị đã xác định.
    save(im.crop((0, 0, 2000, y + 45)), name)
    # Thêm mục hiện tại vào tập dữ liệu theo đúng thứ tự.
    MANIFEST.append({"image": name, "title": title, "snippets": entries})


# Tạo chú giải Q6 trên hình kiến trúc đã đánh số.
def architecture():
    # Chuẩn bị ảnh hoặc bề mặt vẽ, giữ nguyên kích thước nguồn.
    im = Image.new("RGB", (2000, 1660), "white")
    # Chuẩn bị ảnh hoặc bề mặt vẽ, giữ nguyên kích thước nguồn.
    d = ImageDraw.Draw(im)
    # Vẽ thành phần tại tọa độ đã tính, không thay đổi dữ liệu truy vấn.
    write(d, 65, 38, "Q6 nằm ở đâu trong kiến trúc DataFusion?", 44, bold=True)
    # Vẽ thành phần tại tọa độ đã tính, không thay đổi dữ liệu truy vấn.
    write(d, 65, 108, "Lập kế hoạch chọn cách thực hiện; dữ liệu chỉ đi qua các toán tử khi gọi collect().", 27, MUTED)
    # Chuẩn bị ảnh hoặc bề mặt vẽ, giữ nguyên kích thước nguồn.
    source = Image.open(HERE / "Architecture-DataFusion-Numbered.png").convert("RGB")
    # Giá trị trung gian `height` được dùng ngay ở bước bên dưới.
    height = round(1860 * source.height / source.width)
    # Thực hiện bước chuẩn bị hoặc trình bày với các giá trị đã xác định.
    im.paste(source.resize((1860, height), Image.Resampling.LANCZOS), (65, 165))
    # Giá trị trung gian `sx, sy` được dùng ngay ở bước bên dưới.
    sx, sy = 1860 / source.width, height / source.height
    # Duyệt từng mục theo thứ tự để thu dữ liệu hoặc ghép phần trình bày tương ứng.
    for rect, color in [((48, 236, 480, 348), ORANGE), ((2150, 78, 2730, 220), GREEN)]:
        # Giá trị trung gian `x1, y1, x2, y2` được dùng ngay ở bước bên dưới.
        x1, y1, x2, y2 = rect
        # Vẽ thành phần tại tọa độ đã tính, không thay đổi dữ liệu truy vấn.
        d.rounded_rectangle((65+x1*sx,165+y1*sy,65+x2*sx,165+y2*sy), radius=9, outline=color, width=7)
    # Vị trí dọc của nội dung kế tiếp trong ảnh, tránh chồng lên đoạn trước.
    y = 165 + height + 30
    # Duyệt từng mục theo thứ tự để thu dữ liệu hoặc ghép phần trình bày tương ứng.
    for number, color, title, note in [
        (2, ORANGE, "Nguồn Parquet / ParquetExec", "Đọc, giải nén và giải mã cột; hồ sơ thực thi cho biết chi phí của đường nguồn."),
        (7, GREEN, "Biểu thức và toán tử thực thi", "FilterExec đánh giá điều kiện trên lô Arrow; AggregateExec tính tích và tổng Q6."),
        (4, MUTED, "Tối ưu logic → kế hoạch vật lý ở 5–6", "Quyết định vị trí bộ lọc. Vòng biến đổi kế hoạch không phải quá trình quét dữ liệu."),
    ]:
        # Vẽ thành phần tại tọa độ đã tính, không thay đổi dữ liệu truy vấn.
        circle(d, 93, y+25, number, color)
        # Vẽ thành phần tại tọa độ đã tính, không thay đổi dữ liệu truy vấn.
        write(d, 140, y+3, title, 29, color, True)
        # Vị trí dọc của nội dung kế tiếp trong ảnh, tránh chồng lên đoạn trước.
        y = paragraph(d, 140, y+48, note, 1770, 27) + 22
    # Vị trí dọc của nội dung kế tiếp trong ảnh, tránh chồng lên đoạn trước.
    y = paragraph(d, 65, y, "Nguồn: Lamb và cộng sự, Hình 2, mục 5, DOI 10.1145/3626246.3653368. Chú giải do nhóm bổ sung. Đây là kiến trúc DataFusion; DuckDB chỉ được đối chiếu theo chức năng tương ứng.", 1860, 25, MUTED)
    # Thực hiện bước chuẩn bị hoặc trình bày với các giá trị đã xác định.
    save(im.crop((0,0,2000,y+40)), "01-q6-kien-truc.png")


# Vẽ luồng đọc/lọc trước và sau, không tự điền số đo thời gian.
def flow():
    # Chuẩn bị ảnh hoặc bề mặt vẽ, giữ nguyên kích thước nguồn.
    im = Image.new("RGB", (2000, 1510), "white")
    # Chuẩn bị ảnh hoặc bề mặt vẽ, giữ nguyên kích thước nguồn.
    d = ImageDraw.Draw(im)
    # Vẽ thành phần tại tọa độ đã tính, không thay đổi dữ liệu truy vấn.
    write(d, 65, 36, "Cùng Q6, thay vị trí thực hiện bộ lọc", 46, bold=True)
    # Vẽ thành phần tại tọa độ đã tính, không thay đổi dữ liệu truy vấn.
    write(d, 65, 109, "Sơ đồ chức năng, đọc từ trái sang phải; không biểu diễn tỷ lệ thời gian.", 27, MUTED)
    # Lưu các dòng kết quả hoặc HTML đang được ghép.
    rows = [
        ("DataFusion 32.0.0 — mặc định", "datafusion.execution.parquet.pushdown_filters = false", GREEN,
         [("② ParquetExec", "Đọc, giải mã\n4 cột cần thiết"), ("⑦ FilterExec", "Arrow: đánh giá\nđiều kiện, giữ dòng"),
          ("Projection / SUM", "Chọn cột, nhân\nvà cộng tổng"), ("⑧ Kết quả", "1 giá trị revenue")]),
        ("DuckDB 0.9.1 — mặc định", "disabled_optimizers = '' → quy tắc filter_pushdown được phép chạy", ORANGE,
         [("READ_PARQUET", "Đọc + giải mã\n+ ApplyFilter"), ("Trong bộ đọc", "Lọc từng lô;\nchọn dòng đầu ra"),
          ("PROJECTION / SUM", "Nhân rồi\ncộng tổng"), ("Kết quả", "Cùng revenue")]),
        ("DuckDB 0.9.1 — đối chứng", "SET disabled_optimizers='filter_pushdown'", GREEN,
         [("READ_PARQUET", "Đọc, giải mã\n4 cột cần thiết"), ("FILTER riêng", "SelectExpression\n→ chọn dòng"),
          ("PROJECTION / SUM", "Nhân rồi\ncộng tổng"), ("Kết quả", "Kiểm tra bằng\nlượt mặc định")]),
    ]
    # Duyệt từng mục theo thứ tự để thu dữ liệu hoặc ghép phần trình bày tương ứng.
    for index, (title, setting, color, boxes) in enumerate(rows):
        # Vị trí dọc của nội dung kế tiếp trong ảnh, tránh chồng lên đoạn trước.
        y = 185 + index * 355
        # Vẽ thành phần tại tọa độ đã tính, không thay đổi dữ liệu truy vấn.
        write(d, 65, y, title, 34, color, True)
        # Vẽ thành phần tại tọa độ đã tính, không thay đổi dữ liệu truy vấn.
        write(d, 65, y+53, setting, 25, MUTED)
        # Duyệt từng mục theo thứ tự để thu dữ liệu hoặc ghép phần trình bày tương ứng.
        for i, (label, detail) in enumerate(boxes):
            # Vị trí ngang tính theo số thứ tự ô trên sơ đồ.
            x = 65 + i * 480
            # Khung bao của một công việc trong sơ đồ.
            rect = (x, y+110, x+425, y+278)
            # Vẽ thành phần tại tọa độ đã tính, không thay đổi dữ liệu truy vấn.
            d.rounded_rectangle(rect, radius=12, fill="#edf5f1" if color == GREEN else "#fff3e5", outline=color, width=2)
            # Vẽ thành phần tại tọa độ đã tính, không thay đổi dữ liệu truy vấn.
            write(d, x+20, y+128, label, 27, color, True)
            # Vẽ thành phần tại tọa độ đã tính, không thay đổi dữ liệu truy vấn.
            paragraph(d, x+20, y+177, detail, 385, 26)
            # Chọn nhánh phù hợp với dữ liệu hoặc trạng thái vừa đọc.
            if i < 3:
                # Tọa độ đường nối giữa hai bước kế tiếp.
                mid = y+198
                # Vẽ thành phần tại tọa độ đã tính, không thay đổi dữ liệu truy vấn.
                d.line((x+430,mid,x+469,mid), fill=MUTED, width=4)
                # Vẽ thành phần tại tọa độ đã tính, không thay đổi dữ liệu truy vấn.
                d.polygon([(x+470,mid),(x+458,mid-9),(x+458,mid+9)], fill=MUTED)
        # Chọn nhánh phù hợp với dữ liệu hoặc trạng thái vừa đọc.
        if index == 1:
            # Hai ô đầu chỉ phóng to hai công việc bên trong cùng READ_PARQUET.
            d.rounded_rectangle((57,y+102,981,y+286),radius=16,outline=ORANGE,width=4)
            # Vẽ thành phần tại tọa độ đã tính, không thay đổi dữ liệu truy vấn.
            write(d, 72, y+293, "Hai ô đầu thuộc cùng một toán tử READ_PARQUET, không phải hai lần đọc tệp.", 23, ORANGE)
    # Vị trí dọc của nội dung kế tiếp trong ảnh, tránh chồng lên đoạn trước.
    y = paragraph(d, 65, 1280, "Cấu hình DuckDB tắt một quy tắc tối ưu của phiên, không sửa cờ C++ của thư viện. DataFusion có cấu hình bộ đọc khác tên và khác phạm vi; hai thiết lập không phải cùng một biến.", 1865, 29)
    # Vị trí dọc của nội dung kế tiếp trong ảnh, tránh chồng lên đoạn trước.
    y = paragraph(d, 65, y+15, "Q6 không có nối bảng, GROUP BY hoặc ORDER BY. Kế hoạch đầy đủ có thể thêm toán tử gom lô/chọn cột; hình tập trung vào khác biệt đọc và lọc. Việc nhanh hơn phải kiểm tra bằng số đo thật.", 1865, 26, MUTED)
    # Thực hiện bước chuẩn bị hoặc trình bày với các giá trị đã xác định.
    save(im.crop((0,0,2000,y+40)), "07-q6-luong-truoc-sau.png")


# Chỉ chạy quy trình tạo ảnh khi được gọi trực tiếp.
def main():
    # Giao diện tham số dòng lệnh, báo lỗi rõ khi thiếu đường dẫn nguồn.
    parser = argparse.ArgumentParser(description=__doc__)
    # Thực hiện bước chuẩn bị hoặc trình bày với các giá trị đã xác định.
    parser.add_argument("--source-root", type=Path, required=True)
    # Lưu checkout upstream dùng riêng để trích mã.
    source_root = parser.parse_args().source_root.resolve()
    # Thực hiện bước chuẩn bị hoặc trình bày với các giá trị đã xác định.
    OUT.mkdir(exist_ok=True)
    # Thực hiện bước chuẩn bị hoặc trình bày với các giá trị đã xác định.
    source_figure(source_root, "02-datafusion-cau-hinh.png", "DataFusion 32: lọc trong giải mã mặc định tắt", [
        ("datafusion-32.0.0", "datafusion/common/src/config.rs", 284, 286, {286}),
        ("datafusion-32.0.0", "datafusion/core/src/datasource/physical_plan/parquet.rs", 211, 215, {213,214}),
        ("datafusion-32.0.0", "datafusion/core/src/datasource/physical_plan/parquet.rs", 462, 475, {463,475}),
    ], "① pushdown_filters=false là mặc định. ② Bộ đọc lấy tùy chọn từ cấu hình phiên nếu không có ghi đè. ③ Chỉ khi bật và dựng được bộ lọc thì builder.with_row_filter(...) mới gắn lọc vào bộ giải mã. Tắt lựa chọn này vẫn có FilterExec bên ngoài và vẫn có thể bỏ nhóm hàng bằng thống kê.")
    # Thực hiện bước chuẩn bị hoặc trình bày với các giá trị đã xác định.
    source_figure(source_root, "03-datafusion-filterexec.png", "DataFusion 32: FilterExec xử lý lô Arrow", [
        ("datafusion-32.0.0", "datafusion/physical-plan/src/filter.rs", 303, 315, {308,309,313}),
    ], "① evaluate(batch): kiểm tra biểu thức điều kiện trên lô. ② into_array: biểu diễn kết quả thành mảng. ③ filter_record_batch: chọn các dòng có kết quả đúng. Đây là cơ chế lọc riêng sau bộ đọc; đoạn mã tự nó chưa chứng minh nhanh hơn DuckDB.")
    # Thực hiện bước chuẩn bị hoặc trình bày với các giá trị đã xác định.
    source_figure(source_root, "04-duckdb-cau-hinh.png", "DuckDB 0.9.1: cho phép đưa điều kiện vào bộ đọc", [
        ("duckdb-0.9.1", "extension/parquet/parquet_extension.cpp", 175, 180, {177}),
        ("duckdb-0.9.1", "src/optimizer/pushdown/pushdown_get.cpp", 52, 56, {56}),
    ], "① table_function.filter_pushdown=true khai báo bộ đọc hỗ trợ lọc đẩy xuống. ② Bộ tối ưu chuyển các điều kiện phù hợp thành table_filters của phép quét. Lệnh SET disabled_optimizers='filter_pushdown' tắt quy tắc tối ưu trong phiên; không sửa dòng C++ này.")
    # Thực hiện bước chuẩn bị hoặc trình bày với các giá trị đã xác định.
    source_figure(source_root, "05-duckdb-doc-va-loc.png", "DuckDB 0.9.1: đọc cột điều kiện rồi ApplyFilter", [
        ("duckdb-0.9.1", "extension/parquet/parquet_reader.cpp", 945, 955, {951,954}),
        ("duckdb-0.9.1", "extension/parquet/parquet_reader.cpp", 688, 703, {699,700,701}),
    ], "① Read giải mã dữ liệu cột cần kiểm tra. ② ApplyFilter cập nhật lựa chọn dòng của lô. ③ Nhánh vector phẳng không có giá trị thiếu lặp qua các vị trí; OP::Operation so sánh với hằng số, && có thể bỏ so sánh khi dòng đã bị loại. Đường thực thi gồm đọc, giải mã và lọc. Đoạn mã này chưa đo riêng chi phí dòng 700.")
    # Thực hiện bước chuẩn bị hoặc trình bày với các giá trị đã xác định.
    source_figure(source_root, "06-duckdb-filter-rieng.png", "DuckDB 0.9.1: FILTER riêng sau khi tắt quy tắc", [
        ("duckdb-0.9.1", "src/execution/operator/filter/physical_filter.cpp", 42, 53, {45,48,50}),
    ], "① SelectExpression kiểm tra điều kiện và tạo danh sách vị trí được giữ. ② Nếu giữ mọi dòng, Reference dùng lại đầu vào. ③ Nếu chỉ giữ một phần, Slice chọn các vị trí đó. Đối chứng thay cả đường thực thi đọc/lọc; không chỉ bỏ một vòng lặp và cũng không bỏ việc lọc Q6.")
    # Thực hiện bước chuẩn bị hoặc trình bày với các giá trị đã xác định.
    architecture()
    # Thực hiện bước chuẩn bị hoặc trình bày với các giá trị đã xác định.
    flow()
    # Ghi kết quả tạo hình hoặc metadata ra tệp đích.
    (OUT / "sources.json").write_text(json.dumps(MANIFEST, ensure_ascii=False, indent=2) + "\n")
    # In trạng thái hoặc kết quả đã thu, không chạy lại SQL để in.
    print("Đã tạo 7 ảnh và sources.json; không chạy truy vấn.")


# Chỉ thực hiện quy trình khi chạy tệp trực tiếp, không tự chạy lúc import.
if __name__ == "__main__":
    # Thực hiện bước chuẩn bị hoặc trình bày với các giá trị đã xác định.
    main()
