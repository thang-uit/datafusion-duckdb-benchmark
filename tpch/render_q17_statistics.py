"""Vẽ luồng chọn phía dựng từ thống kê; không chạy SQL hoặc điền số đo."""
# Đọc đường dẫn bằng Path thay vì ghép chuỗi phụ thuộc máy.
from pathlib import Path
# Đọc, vẽ và lưu ảnh bằng Pillow.
from PIL import Image, ImageDraw
# Nạp tiện ích phục vụ phần minh họa, chưa chạy truy vấn khi import.
from render_q6_assets import write, paragraph, MUTED, GREEN, ORANGE


# Chỉ chạy quy trình tạo ảnh khi được gọi trực tiếp.
def main():
    # Chuẩn bị ảnh hoặc bề mặt vẽ, giữ nguyên kích thước nguồn.
    image = Image.new("RGB", (2000, 1270), "white")
    # Chuẩn bị ảnh hoặc bề mặt vẽ, giữ nguyên kích thước nguồn.
    draw = ImageDraw.Draw(image)
    # Vẽ thành phần tại tọa độ đã tính, không thay đổi dữ liệu truy vấn.
    write(draw, 65, 40, "Chọn phía dựng từ thống kê trước thực thi", 46, bold=True)
    # Vẽ thành phần tại tọa độ đã tính, không thay đổi dữ liệu truy vấn.
    paragraph(draw, 65, 115,
              "Quy tắc bổ sung qua PhysicalOptimizerRule — không nhận diện tên bảng, nhãn hiệu hoặc kết quả đã chạy.",
              1860, 29, MUTED)
    # Khai báo các bước của sơ đồ cùng tọa độ và nội dung từng ô.
    boxes = [
        (65, 215, 870, 245, "1. Thu thống kê nguồn", "collect_statistics = true\nParquet metadata: số dòng nguồn và kiểu cột.\nChưa chạy truy vấn để đếm kết quả.", GREEN),
        (1065, 215, 870, 245, "2. Truyền giới hạn số dòng", "Filter: 0 ≤ đầu ra ≤ đầu vào.\nProjection và Coalesce: giữ số dòng.\nKhông biết tỷ lệ lọc thì không tự điền con số.", GREEN),
        (65, 570, 870, 265, "3. So chi phí dựng theo mô hình", "Số dòng × (độ rộng cột cố định + 32 byte).\nChỉ đổi khi chi phí tối đa bên phải\nnhỏ hơn chi phí tối thiểu bên trái.\nThiếu thông tin hoặc chồng lấp: giữ kế hoạch.", ORANGE),
        (1065, 570, 870, 265, "4. Đổi ExecutionPlan", "INNER / CollectLeft, một phân vùng.\nĐổi hai đầu vào và khóa nối.\nProjection phục hồi thứ tự cột.\nDùng lại HashJoinExec của DataFusion 32.", ORANGE),
    ]
    # Duyệt từng mục theo thứ tự để thu dữ liệu hoặc ghép phần trình bày tương ứng.
    for x,y,w,h,title,detail,color in boxes:
        # Vẽ thành phần tại tọa độ đã tính, không thay đổi dữ liệu truy vấn.
        draw.rounded_rectangle((x,y,x+w,y+h), radius=12, outline=color, width=3, fill="#f4f7f6")
        # Vẽ thành phần tại tọa độ đã tính, không thay đổi dữ liệu truy vấn.
        write(draw,x+24,y+20,title,33,color,True)
        # Vị trí đáy đoạn chữ, dùng để kiểm tra không tràn khung.
        end=paragraph(draw,x+24,y+82,detail,w-48,28)
        assert end<y+h-10
    # Duyệt từng mục theo thứ tự để thu dữ liệu hoặc ghép phần trình bày tương ứng.
    for x1,y1,x2,y2 in [(950,335,1040,335),(1000,475,1000,545),(950,700,1040,700)]:
        # Vẽ thành phần tại tọa độ đã tính, không thay đổi dữ liệu truy vấn.
        draw.line((x1,y1,x2,y2),fill=MUTED,width=4)
        # Chọn nhánh phù hợp với dữ liệu hoặc trạng thái vừa đọc.
        if y1==y2: draw.polygon([(x2,y2),(x2-14,y2-9),(x2-14,y2+9)],fill=MUTED)
        # Vẽ thành phần tại tọa độ đã tính, không thay đổi dữ liệu truy vấn.
        else: draw.polygon([(x2,y2),(x2-9,y2-14),(x2+9,y2-14)],fill=MUTED)
    # Vẽ thành phần tại tọa độ đã tính, không thay đổi dữ liệu truy vấn.
    paragraph(draw,65,920,"Luồng kiến trúc: Catalog/Data Sources → thống kê tại vòng tối ưu vật lý → Extension ExecutionPlan Rewrite (xanh dương) → Execution Engine.",1860,32)
    # Vẽ thành phần tại tọa độ đã tính, không thay đổi dữ liệu truy vấn.
    paragraph(draw,65,1035,"Giới hạn số dòng không phải số dòng dự đoán. Chi phí mô hình không phải RAM đo được. Số dòng thực tế chỉ xuất hiện sau collect và không được dùng ngược lại để quyết định kế hoạch.",1860,29,MUTED)
    # Đường dẫn tới ảnh hoặc tệp đầu ra đang được xử lý.
    path=Path(__file__).resolve().parent/'q17-assets/08-q17-thong-ke-truoc-chay.png'
    # Ghi kết quả tạo hình hoặc metadata ra tệp đích.
    image.save(path)
    # In trạng thái hoặc kết quả đã thu, không chạy lại SQL để in.
    print(path)


# Chỉ thực hiện quy trình khi chạy tệp trực tiếp, không tự chạy lúc import.
if __name__ == '__main__':
    # Thực hiện bước chuẩn bị hoặc trình bày với các giá trị đã xác định.
    main()
