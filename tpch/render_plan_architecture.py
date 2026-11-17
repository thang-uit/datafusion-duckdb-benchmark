"""Khoanh vùng trên Hình 2 hiện có; không sửa hình gốc hoặc chạy SQL."""
# Đọc đường dẫn bằng Path thay vì ghép chuỗi phụ thuộc máy.
from pathlib import Path
# Đọc, vẽ và lưu ảnh bằng Pillow.
from PIL import Image, ImageDraw
# Nạp tiện ích phục vụ phần minh họa, chưa chạy truy vấn khi import.
from render_q6_assets import font

# Lưu thư mục chứa chính mô-đun, không phụ thuộc thư mục Terminal.
HERE = Path(__file__).resolve().parent
# Lưu thư mục lưu ảnh notebook.
OUT = HERE / "plan-assets"
# Màu đỏ dùng thống nhất cho vùng cần chú ý.
RED = "#b52b24"
# Lưu tọa độ số chú giải trên hình nguồn.
POINTS = {1:(525,860),2:(525,290),3:(1210,470),4:(1205,690),
          5:(1990,470),6:(1995,690),7:(2085,176),8:(2460,1064),9:(1990,966)}
# Ellipses follow the original geometry and avoid changing component colors.
REGIONS = {
    "logical":(721,363,1140,467),
    "logical_loop":(748,506,1108,729),
    "physical":(1391,363,1920,478),
    "physical_loop":(1481,506,1836,729),
    "rewrite":(1444,886,1918,1040),
    "parquet":(47,234,484,352),
    "expression":(2147,73,2737,224),
    "aggregate":(2147,231,2737,381),
    "join":(2147,390,2737,540),
    "streams":(2354,955,2557,1019),
}
# Lưu các hình chú giải cần xuất cho từng giai đoạn.
VIEWS = {
    "overview":([],[],"Các số 1–8 khớp chú giải đầu notebook; số 9 đánh dấu điểm mở rộng kế hoạch vật lý."),
    "logical-initial":([3],["logical"],"Kế hoạch logic ban đầu: initial_logical_plan → vùng LogicalPlan (3)."),
    "logical-optimized":([3,4],["logical","logical_loop"],"Logic sau tối ưu: logical_plan; các quy tắc biến đổi nằm ở vòng logic (4)."),
    "physical-final":([5,6],["physical","physical_loop"],"Kế hoạch vật lý cuối: physical_plan (5), sau các quy tắc vật lý ở vòng (6)."),
    "logical-rewrite":([4],["logical_loop"],"logical_plan after ...: trạng thái kế hoạch sau quy tắc ở vòng logic (4)."),
    "physical-initial":([5],["physical"],"initial_physical_plan: cây ExecutionPlan (5), trước tối ưu vật lý."),
    "physical-rewrite":([6],["physical_loop"],"physical_plan after ...: trạng thái kế hoạch sau quy tắc ở vòng vật lý (6)."),
    "execution-q6":([2,7,8],["parquet","expression","streams"],"Q6: nguồn Parquet (2), toán tử thực thi (7), luồng lô Arrow (8); không có GROUP BY hay Sort."),
    "execution-join":([2,7,8],["parquet","expression","aggregate","join","streams"],"Q17: Parquet (2), nối và tổng hợp theo khóa (7), truyền lô Arrow qua Streams (8)."),
    "extension-rewrite":([5,6,9],["physical","physical_loop","rewrite"],"Quy tắc bổ sung: Extension ExecutionPlan Rewrite (9) tham gia vòng vật lý (6), đổi cây (5)."),
}


# Chỉ chạy quy trình tạo ảnh khi được gọi trực tiếp.
def main():
    # Thực hiện bước chuẩn bị hoặc trình bày với các giá trị đã xác định.
    OUT.mkdir(exist_ok=True)
    # Duyệt từng mục theo thứ tự để thu dữ liệu hoặc ghép phần trình bày tương ứng.
    for name,(numbers,regions,caption) in VIEWS.items():
        # Chuẩn bị ảnh hoặc bề mặt vẽ, giữ nguyên kích thước nguồn.
        im=Image.open(HERE/"Architecture-DataFusion-Numbered.png").convert("RGB")
        # Chuẩn bị ảnh hoặc bề mặt vẽ, giữ nguyên kích thước nguồn.
        d=ImageDraw.Draw(im)
        # Add only a callout for the extension; preserve all original content.
        d.line((1904,966,1954,966),fill=RED,width=4)
        # Vẽ thành phần tại tọa độ đã tính, không thay đổi dữ liệu truy vấn.
        d.ellipse((1962,938,2018,994),fill="white",outline=RED,width=4)
        # Vẽ thành phần tại tọa độ đã tính, không thay đổi dữ liệu truy vấn.
        d.text((1990,966),"9",anchor="mm",font=font(32,True),fill=RED)
        # Duyệt từng mục theo thứ tự để thu dữ liệu hoặc ghép phần trình bày tương ứng.
        for region in regions:
            # Vẽ thành phần tại tọa độ đã tính, không thay đổi dữ liệu truy vấn.
            d.ellipse(REGIONS[region],outline=RED,width=6)
        # Duyệt từng mục theo thứ tự để thu dữ liệu hoặc ghép phần trình bày tương ứng.
        for number in numbers:
            # Tọa độ tâm số chú giải trong ảnh nguồn.
            x,y=POINTS[number]
            # Vẽ thành phần tại tọa độ đã tính, không thay đổi dữ liệu truy vấn.
            d.ellipse((x-36,y-36,x+36,y+36),outline=RED,width=6)
        # Preserve the paper caption, and clearly separate the added explanation.
        extended=Image.new("RGB",(im.width,im.height+105),"white")
        # Thêm mục hiện tại vào tập dữ liệu theo đúng thứ tự.
        extended.paste(im,(0,0));ed=ImageDraw.Draw(extended)
        # Vẽ thành phần tại tọa độ đã tính, không thay đổi dữ liệu truy vấn.
        ed.line((24,im.height+10,im.width-24,im.height+10),fill="#a8a8a8",width=2)
        # Vẽ thành phần tại tọa độ đã tính, không thay đổi dữ liệu truy vấn.
        ed.text((32,im.height+28),caption,font=font(32),fill="#172e37")
        # Keep the original resolution so the figure remains readable when enlarged.
        extended.quantize(colors=128).save(OUT/(name+".png"),optimize=True)
    # In trạng thái hoặc kết quả đã thu, không chạy lại SQL để in.
    print(f"Generated {len(VIEWS)} annotated architecture views in {OUT}")


# Chỉ thực hiện quy trình khi chạy tệp trực tiếp, không tự chạy lúc import.
if __name__=="__main__":main()
