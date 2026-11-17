#!/bin/bash
# Dừng ngay nếu một bước sinh dữ liệu hoặc pipeline thất bại.
set -euo pipefail

# Tìm tpch/ từ vị trí script để không phụ thuộc thư mục Terminal đang đứng.
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# Kho DataFusion bên ngoài được đặt tại arrow-datafusion/ của benchmark.
source_dir="${script_dir}/../arrow-datafusion"
# Dừng trước khi tác động dữ liệu nếu chưa có đúng checkout.
if [[ ! -f "${source_dir}/benchmarks/bench.sh" ]]; then
    echo "Thiếu arrow-datafusion/. Clone Apache DataFusion theo README trước." >&2
    exit 1
fi
# Kiểm tra công cụ được dùng trực tiếp hoặc bởi bench.sh của tác giả.
for program in python3 docker cargo git; do
    command -v "$program" >/dev/null || { echo "Thiếu công cụ: $program" >&2; exit 1; }
done
# Docker Desktop phải đang chạy trước khi bắt đầu sinh dữ liệu.
docker info >/dev/null
# Chọn tag Rust 31.0.0 dùng để chuyển dữ liệu, khác Python DataFusion 32.0.0 để đo.
git -C "$source_dir" checkout 31.0.0
# Đổi tên ảnh Docker cũ sang scalytics, giữ nguyên phần còn lại của bench.sh.
python3 "${script_dir}/../common/prepare-tpch-source.py" "$source_dir"
# Ảnh sinh dữ liệu có kiến trúc amd64, chọn rõ nền tảng trên máy Mac ARM64.
if [[ "$(uname -s)" == "Darwin" && "$(uname -m)" == "arm64" ]]; then
    export DOCKER_DEFAULT_PLATFORM="${DOCKER_DEFAULT_PLATFORM:-linux/amd64}"
fi
# Hệ số quy mô TPC-H, không phải số lượng bảng.
scale_factor=10
# Chạy bench.sh tại thư mục mà mã tác giả sử dụng.
cd "$source_dir"
# Bước setup chủ động sinh lại bộ đích, cần sao lưu trước nếu muốn giữ dữ liệu cũ.
rm -rf ./benchmarks/data/tpch_dataset
# SF=1 và SF=10 dùng hai tên benchmark khác nhau trong DataFusion 31.
if [[ "$scale_factor" == 1 ]]; then
    # Sinh .tbl rồi chuyển sang Parquet.
    ./benchmarks/bench.sh data tpch
    # Đặt tên thư mục chung để các tệp SQL luôn tìm đúng dữ liệu.
    mv ./benchmarks/data/tpch_sf1 ./benchmarks/data/tpch_dataset
elif [[ "$scale_factor" == 10 ]]; then
    # Docker sinh dữ liệu, Cargo biên dịch và chạy bộ chuyển đổi của DataFusion.
    ./benchmarks/bench.sh data tpch10
    # Dùng cùng đường dẫn cho DataFusion Python và DuckDB.
    mv ./benchmarks/data/tpch_sf10 ./benchmarks/data/tpch_dataset
else
    # Không tiếp tục với hệ số chưa có nhánh xử lý.
    echo "Invalid scale factor: $scale_factor" >&2
    exit 1
fi
