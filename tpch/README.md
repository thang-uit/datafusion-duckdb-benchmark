# Notebook TPC-H · Q6 và Q17

Quy trình clone, Docker, môi trường Mac và benchmark nằm ở [README gốc của kho](../README.md). Trang này hướng dẫn đọc notebook và tạo lại hình.

## Chạy notebook

Mở `TPC_H_Q6_Q17.ipynb` trong VS Code. Chọn kernel **Python (TPC-H DataFusion 32)** hoặc `venv/bin/python` của kho, rồi chạy các ô từ trên xuống. Output cũ đã được bỏ để kết quả thuộc đúng lần chạy hiện tại.

| Mục | Việc cần làm |
|---|---|
| Chuẩn bị | Xác nhận DataFusion 32.0.0/DuckDB 0.9.1, xem metadata 8 bảng và dòng hàng mẫu, đăng ký cùng Parquet |
| 1.1–1.6 | Q6: chạy hai bộ máy, định vị trên kiến trúc, xem EXPLAIN và hồ sơ thời gian |
| 1.7 | Đổi `disabled_optimizers=''` thành `'filter_pushdown'`, chạy ô cấu hình rồi ô đối chứng. Ô sau tự trả về mặc định |
| 1.8 | Đối chiếu kế hoạch, kết quả và thời gian vừa đo. Không mặc định phương án mới luôn nhanh hơn |
| 2.1–2.2 | Q17 gốc: chạy hai bộ máy và xem phía dựng bảng băm |
| 2.3 | Đổi FROM để kiểm chứng ảnh hưởng thứ tự đầu vào, đây là thay SQL |
| 2.4–2.5 | Giữ SQL gốc, xem quy tắc thống kê và mã Rust hiện tại |
| 2.6 | Build release bằng Cargo sau mỗi lần sửa Rust |
| 2.7 | `--plan-only`: chỉ lập kế hoạch và đọc căn cứ trước thực thi |
| 2.8–2.9 | Chạy cùng binary Rust khi tắt/bật quy tắc, so kết quả, kế hoạch và bộ đếm |
| 2.10 | Giới hạn kết luận và số đo của lần chạy |

Benchmark Terminal chạy 5 lượt/câu và ghi 3 lượt cuối. Notebook chạy **một lượt/cấu hình**, riêng DataFusion Q6 có một lượt `EXPLAIN ANALYZE VERBOSE` bổ sung. DuckDB thu JSON profiling trong chính lượt SELECT ban đầu. Các ô EXPLAIN và hiển thị hình không tự chạy lại truy vấn thật.

Phần Rust có timeout 120 giây/lần chạy, 15 phút/lần build khi gọi từ notebook. Các lượt Rust đều bật `collect_statistics=true`, chỉ khác đăng ký quy tắc. Dùng cặp này để đánh giá quy tắc, không dùng chênh lệch giữa wheel Python và binary Rust để quy lợi ích cho phần mở rộng.

## Các tiện ích

- `plan_comparison.py`: `compare_plans` là hàm bổ sung, không phải API có sẵn của DataFusion. Hàm gọi `EXPLAIN VERBOSE` và DuckDB `EXPLAIN`, giữ thứ tự trạng thái và giải thích bằng `plan_notes.py`.
- `plan_architecture.py`, `plan-assets/`: nhúng hình kiến trúc, chỉ rõ vùng logic, vật lý, thực thi và điểm mở rộng.
- `q6_walkthrough.py`: thu hồ sơ Q6, đọc bộ đếm và tạo bảng đối chứng.
- `q17_extension.py`: gọi chương trình Rust, kiểm tra phiên bản/SQL/kết quả rồi tạo bảng so sánh.
- `notebook_theme.py`: thống nhất màu chữ và nền để bảng dễ đọc trong theme sáng/tối.
- `q17-physical-rule/`: [mã, chính sách chọn phía dựng và kiểm thử](q17-physical-rule/README.md).

Khi sửa tiện ích Python, restart kernel rồi chạy lại các ô chuẩn bị để tránh dùng mô-đun cũ. `queries.sql` giữ mỗi truy vấn trên một dòng để các runner lấy đúng số câu. Hai tệp `create-single-*.sql` chứa đường dẫn tương đối từ `tpch/` đến cùng bộ dữ liệu.

## Tạo lại hình

Các hình cần chạy notebook đã có sẵn trong Git. Từ thư mục `tpch/`, sau khi kích hoạt `venv`:

```bash
# Tạo các vùng đánh dấu trên Hình 2 đã đánh số.
python render_plan_architecture.py

# Vẽ luồng quy tắc thống kê Q17, không chạy SQL.
python render_q17_statistics.py
```

Để tạo lại ảnh trích mã Q6, cần các checkout dùng riêng cho tra cứu nguồn nằm **ngoài kho benchmark**:

```bash
# Chạy tại thư mục gốc kho benchmark. ../source-inspection là thư mục anh em.
mkdir -p ../source-inspection
git clone --branch 32.0.0 --depth 1 https://github.com/apache/datafusion.git \
  ../source-inspection/datafusion-32.0.0
git clone --branch v0.9.1 --depth 1 https://github.com/duckdb/duckdb.git \
  ../source-inspection/duckdb-0.9.1

cd tpch
python render_q6_assets.py --source-root ../../source-inspection
```

Trình vẽ dùng font Arial/Courier có sẵn trên macOS. JSON `q6-assets/sources.json` và `q17-assets/source-snippets.json` lưu mã nguyên văn, số dòng, commit, URL và SHA-256. Không clone DuckDB hoặc DataFusion bổ sung nếu chỉ chạy notebook với ảnh có sẵn.

Hình 2 lấy từ [bài báo DataFusion](https://doi.org/10.1145/3626246.3653368). Số đánh dấu và chú giải do nhóm bổ sung. Sơ đồ và ảnh mã nguồn giải thích cơ chế, không tự chứng minh thời gian. Kết luận hiệu năng cần kết quả và hồ sơ thực thi của lượt đo tương ứng.
