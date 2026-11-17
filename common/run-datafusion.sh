#!/bin/bash
# Nhận tệp đăng ký bảng, tệp truy vấn, cấu hình single/multi và CSV đích.
CREATE=$1
QUERIES=$2
SWEEP_CORES=$3
RESULT_FILE=$4
# Các truy vấn trong tệp được đánh số từ 1, mỗi truy vấn nằm trên một dòng.
QUERY_NUM=1
# In cấu hình đầu vào để đối chiếu nhật ký với lần chạy.
echo "Using ${CREATE}, appending results to ${RESULT_FILE}"
# IFS/read -r giữ nguyên khoảng trắng và dấu gạch chéo trong chuỗi SQL.
while IFS= read -r query || [[ -n "$query" ]]; do
    # Chỉ Linux có giao diện xóa cache này, macOS giữ cơ chế cache của hệ điều hành.
    if [[ "$(uname -s)" == "Linux" ]]; then
        # Đẩy dữ liệu đang chờ ghi xuống đĩa trước khi yêu cầu xóa cache.
        sync
        # Ghi 3 yêu cầu kernel Linux giải phóng page cache, dentry và inode.
        echo 3 | sudo tee /proc/sys/vm/drop_caches >/dev/null
        # Hoàn tất ghi trước khi bắt đầu truy vấn kế tiếp.
        sync
    fi
    # Số câu giúp đối chiếu thời gian với dòng tương ứng trong queries.sql.
    echo "qnum: $QUERY_NUM"
    # Tiến trình Python chạy năm lượt và chỉ ghi ba lượt cuối, tee giữ log mới nhất.
    ../common/run-query-datafusion.py "$CREATE" "$QUERY_NUM" "$SWEEP_CORES" "$RESULT_FILE" <<< "$query" | tee /tmp/datafusion.log
    # Tăng số câu sau khi tiến trình con kết thúc.
    QUERY_NUM=$((QUERY_NUM + 1))
done < "$QUERIES"
