#!/usr/bin/env python3

# sys đọc DDL mà shell chuyển qua stdin.
import sys
# Tạo danh mục view bằng DuckDB 0.9.1.
import duckdb
# Đo thời gian chuẩn bị view riêng với thời gian benchmark.
import timeit


if __name__ == "__main__":
    # Mở cùng cơ sở dữ liệu tạm mà runner truy vấn sẽ dùng.
    con = duckdb.connect(database="my-db.duckdb", read_only=False)

    # Toàn bộ DDL có thể gồm nhiều câu CREATE VIEW.
    query = sys.stdin.read()

    # Thông báo đang đăng ký bảng thay vì đo SELECT.
    print("Set up a view over the Parquet files")
    # Bắt đầu đồng hồ chuẩn bị.
    start = timeit.default_timer()
    # View đọc Parquet trực tiếp, không nạp bảng vào bộ lưu trữ DuckDB.
    con.execute(query)
    # Kết thúc khoảng tạo view.
    end = timeit.default_timer()
    # In thời gian chuẩn bị theo giây.
    print(end - start)
