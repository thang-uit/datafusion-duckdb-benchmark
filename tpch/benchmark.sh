#!/bin/bash
# Dừng khi một lệnh cấp cao thất bại, giữ chính sách xử lý pipeline của mã tác giả.
set -e
# Về thư mục tpch/ để đường dẫn SQL và Parquet tương đối luôn đúng.
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
# single là một phân vùng DataFusion và một luồng DuckDB, multi quét nhiều mức.
sweep_cores="${1:-single}"
# Kết quả mới được giữ riêng, không ghi đè kết quả lịch sử của tác giả.
mkdir -p ../results/latest
# Mỗi lần benchmark bắt đầu với hai CSV thời gian mới.
rm -f ../results/latest/tpch_datafusion.csv ../results/latest/tpch_duckdb.csv
# Chạy DataFusion trước, mỗi dòng trong queries.sql là một truy vấn.
bash ../common/run-datafusion.sh create-single-datafusion.sql queries.sql "$sweep_cores" ../results/latest/tpch_datafusion.csv
# Chạy DuckDB trên cùng SQL và dữ liệu Parquet sau khi DataFusion hoàn tất.
bash ../common/run-duckdb.sh create-single-duckdb.sql queries.sql "$sweep_cores" ../results/latest/tpch_duckdb.csv
