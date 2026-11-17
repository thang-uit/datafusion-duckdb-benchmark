#!/usr/bin/env python3

# DuckDB chạy ngay trong tiến trình Python, không kết nối máy chủ ngoài.
import duckdb
# Đồng hồ đo khoảng execute và fetchall.
import timeit
# Đọc chuỗi SQL và cấu hình do shell truyền vào.
import sys


if __name__ == "__main__":
    # Lấy nguyên câu SQL từ stdin.
    query = sys.stdin.read()
    # In SQL để theo dõi truy vấn đang chạy.
    print(query)

    # Mở cơ sở dữ liệu tạm chứa view đã tạo, dữ liệu vẫn ở Parquet.
    con = duckdb.connect(database="my-db.duckdb", read_only=False)

    # Số thứ tự truy vấn trong CSV.
    query_num = sys.argv[1]
    # Chọn cấu hình single hoặc các mức đa luồng.
    sweep_cores = sys.argv[2]
    # Đường dẫn CSV thời gian cần nối thêm.
    result_file = sys.argv[3]

    # Chọn danh sách số luồng.
    if sweep_cores == "multi":
        # Các mức dùng cho thí nghiệm mở rộng của mã tác giả.
        cores = [1, 2, 4, 8, 16, 32, 64, 128, 192]
    else:
        # single dùng đúng một luồng xử lý truy vấn.
        cores = [1]

    # Chạy các lượt đo cho từng mức số luồng.
    for c in cores:
        # Có năm lượt đo tại mỗi mức.
        for try_num in range(1, 6):
            # Áp số luồng trước khi bắt đầu đồng hồ.
            con.execute("PRAGMA threads={}".format(c))
            # Bắt đầu đo sau bước cấu hình.
            start = timeit.default_timer()
            # execute lập/chạy kế hoạch, fetchall lấy toàn bộ kết quả để truy vấn hoàn tất.
            result = con.execute(query).fetchall()
            # Dừng đồng hồ khi đã thu kết quả.
            end = timeit.default_timer()
            # In cả năm thời gian để kiểm tra tiến trình.
            print(end-start)

            # Chỉ đưa ba lượt cuối vào CSV.
            if try_num > 2:
                # Nối thêm kết quả hiện tại vào tệp.
                with open(result_file, "a") as myfile:
                    # Đổi chênh lệch đồng hồ thành số giây.
                    time = (end - start)
                    # Ghi query, threads, iteration, duration không có dòng tiêu đề.
                    myfile.write("{},{},{},{}\n".format(query_num, c, try_num, time))
