#!/usr/bin/env python3
"""Chạy SQL bằng DataFusion, giữ cơ chế năm lượt của mã tác giả."""

# Đọc SQL từ stdin và các tham số dòng lệnh.
import sys
# Đồng hồ đơn điệu dùng để đo thời gian đã trôi qua.
import timeit
# Các lớp tạo phiên truy vấn nhúng, cấu hình và tài nguyên thực thi.
from datafusion import SessionContext, SessionConfig, RuntimeConfig


if __name__ == "__main__":
    # SQL được shell truyền nguyên văn, mỗi tiến trình nhận một truy vấn.
    query = sys.stdin.read()
    # In câu đang đo để đối chiếu log.
    print(query)
    # Tham số đầu là tệp đăng ký các bảng Parquet.
    create_query_file = sys.argv[1]
    # Số thứ tự câu trong queries.sql.
    query_num = sys.argv[2]
    # single dùng một mức số phân vùng, multi thử dãy mức bên dưới.
    sweep_cores = sys.argv[3]
    # Đường dẫn CSV lưu thời gian của ba lượt cuối.
    result_file = sys.argv[4]
    # Chọn danh sách số phân vùng theo chế độ chạy.
    if sweep_cores == "multi":
        # Dãy cấu hình mở rộng của kho tác giả.
        cores = [1, 2, 4, 8, 16, 32, 64, 128, 192]
    else:
        # Thực nghiệm single dùng một phân vùng thực thi.
        cores = [1]
    # Tạo phiên độc lập cho mỗi mức số phân vùng.
    for c in cores:
        # Số phân vùng không phải giới hạn cứng mọi luồng của tiến trình.
        config = SessionConfig().with_target_partitions(c)
        # Phiên giữ danh mục nguồn và cấu hình tài nguyên.
        ctx = SessionContext(config, RuntimeConfig())
        # Đọc DDL đăng ký nguồn từ tệp của tác giả.
        with open(create_query_file, "r") as stream:
            # Mỗi dòng là một câu tạo bảng đọc Parquet.
            create_queries = stream.readlines()
            # Đo riêng bước chuẩn bị, không cộng vào SELECT.
            setup_start = timeit.default_timer()
            # Đăng ký lần lượt các bảng vào phiên hiện tại.
            for create_query in create_queries:
                # DDL nhận đường dẫn dữ liệu nhưng chưa chạy Q6/Q17.
                ctx.sql(create_query)
            # Tính số giây đăng ký bảng.
            setup_seconds = timeit.default_timer() - setup_start
        # In thời gian chuẩn bị để phân biệt với thời gian truy vấn.
        print("Setup table: {}".format(setup_seconds))
        # Tác giả đo năm lượt trong cùng phiên.
        for try_num in range(1, 6):
            # Bắt đầu trước lời gọi lập kế hoạch và thực thi.
            start = timeit.default_timer()
            # Giữ nguyên điều kiện Q15 của tác giả, kể cả giới hạn đường dẫn CSV trong README.
            if query_num == "15" and result_file == "tpch_datafusion.csv":
                # Q15 có nhiều lệnh tạo view, SELECT và xóa view.
                query_parts = query.split(";")[:-1]
                # Thực hiện các lệnh theo thứ tự trong cùng phiên.
                for query_part in query_parts:
                    # collect buộc thực thi từng lệnh trước khi sang lệnh sau.
                    result = ctx.sql(f"{query_part.strip()};").collect()
            else:
                # Thu toàn bộ lô Arrow để không chỉ đo lúc tạo đối tượng truy vấn.
                result = ctx.sql(query).collect()
            # Dừng khi đã thu kết quả.
            end = timeit.default_timer()
            # In thời gian kể cả hai lượt đầu không được lưu.
            print(end - start)
            # Bỏ hai lượt khởi động, chỉ lưu lượt 3, 4 và 5.
            if try_num > 2:
                # Nối thêm thay vì ghi đè kết quả các câu trước.
                with open(result_file, "a") as stream:
                    # Bốn cột là query, cores, iteration, duration bằng giây.
                    stream.write("{},{},{},{}\n".format(query_num, c, try_num, end - start))
