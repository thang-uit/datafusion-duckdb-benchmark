#!/bin/bash
# Nhận tệp tạo view, tệp truy vấn, cấu hình single/multi và CSV đích.
CREATE=$1
QUERIES=$2
SWEEP_CORES=$3
RESULT_FILE=$4
# Tệp truy vấn bắt đầu từ câu số 1.
QUERY_NUM=1
# In các tham số để biết kết quả được ghi ở đâu.
echo "Using ${CREATE}, appending results to ${RESULT_FILE}"
# Chỉ xóa cơ sở dữ liệu tạm của benchmark, giữ các tệp DuckDB khác trong thư mục.
rm -f my-db.duckdb my-db.duckdb.wal
# Tạo các view đọc trực tiếp cùng tệp Parquet được DataFusion sử dụng.
../common/create-view-duckdb.py < "$CREATE"
# Đọc nguyên từng dòng SQL, không giải nghĩa ký tự gạch chéo.
while IFS= read -r query || [[ -n "$query" ]]; do
    # macOS bỏ qua thao tác cache chỉ tồn tại trên Linux.
    if [[ "$(uname -s)" == "Linux" ]]; then
        # Hoàn tất dữ liệu đang chờ ghi.
        sync
        # Yêu cầu Linux xóa bộ nhớ đệm trước mỗi truy vấn, không phải trước mỗi lượt Python.
        echo 3 | sudo tee /proc/sys/vm/drop_caches >/dev/null
        # Chờ thao tác ghi hoàn tất trước khi đo.
        sync
    fi
    # In số câu hiện tại.
    echo "qnum: $QUERY_NUM"
    # Chạy năm lượt bằng Python, ghi ba lượt cuối và log tiến trình gần nhất.
    ../common/run-query-duckdb.py "$QUERY_NUM" "$SWEEP_CORES" "$RESULT_FILE" <<< "$query" | tee /tmp/duckdb.log
    # Chuyển sang số câu tiếp theo.
    QUERY_NUM=$((QUERY_NUM + 1))
done < "$QUERIES"
