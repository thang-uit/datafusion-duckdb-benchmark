#!/usr/bin/env python3
"""Cập nhật tên ảnh Docker trong DataFusion 31, không sửa bộ máy truy vấn."""

# argparse đọc đường dẫn checkout được setup.sh truyền vào.
import argparse
# Path đọc và ghi tập lệnh của checkout bên ngoài Git của benchmark.
from pathlib import Path

# Tên cũ trong mã tác giả và tên hiện tại của cùng dự án sinh dữ liệu TPC-H.
OLD_IMAGE = "ghcr.io/databloom-ai/tpch-docker:main"
NEW_IMAGE = "ghcr.io/scalytics/tpch-docker:main"


def prepare(checkout):
    """Thay đúng hai lời gọi Docker, hoặc giữ nguyên nếu đã cập nhật trước đó."""
    # Hai lời gọi lần lượt sinh dữ liệu .tbl và sao chép đáp án tham khảo.
    script = Path(checkout) / "benchmarks" / "bench.sh"
    # Đọc nguyên văn để các thay đổi khác trong checkout được giữ nguyên.
    original = script.read_text()
    # Chỉ chấp nhận cấu trúc phiên bản đã được kiểm tra, tránh vá nhầm mã khác.
    if original.count(OLD_IMAGE) + original.count(NEW_IMAGE) != 2:
        raise ValueError("Không tìm thấy đúng hai ảnh Docker TPC-H trong benchmarks/bench.sh.")
    # replace không đổi tệp nếu cả hai chỗ đã dùng tên mới.
    updated = original.replace(OLD_IMAGE, NEW_IMAGE)
    # Ghi khi cần để không đổi thời gian sửa tệp ở mỗi lần chuẩn bị.
    if updated != original:
        script.write_text(updated)
    # In tên ảnh để người chạy biết nguồn Docker đang được sử dụng.
    print(f"TPC-H Docker image: {NEW_IMAGE}")


if __name__ == "__main__":
    # Tạo giao diện dòng lệnh chỉ nhận một thư mục checkout.
    parser = argparse.ArgumentParser(description=__doc__)
    # setup.sh truyền checkout arrow-datafusion tại thư mục gốc benchmark.
    parser.add_argument("checkout", type=Path)
    # Kiểm tra tham số rồi áp dụng bản vá nhỏ, có thể chạy lại an toàn.
    prepare(parser.parse_args().checkout)
