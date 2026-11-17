# Hình đối chiếu kế hoạch với kiến trúc DataFusion

Nguồn hình nền: `../Architecture-DataFusion-Numbered.png`, dựa trên Hình 2,
A. Lamb và cộng sự, “Apache Arrow DataFusion: A Fast, Embeddable, Modular Analytic
Query Engine,” SIGMOD Companion 2024, tr. 8,
[DOI 10.1145/3626246.3653368](https://doi.org/10.1145/3626246.3653368).

Số 1–8 giữ như chú giải đầu notebook. Số 9 do nhóm bổ sung trỏ vào ô xanh dương
Extension ExecutionPlan Rewrite. Ellipse đỏ chỉ vùng đang giải thích; không thay
màu hoặc nội dung kiến trúc gốc. Chú thích dưới ảnh tách khỏi chú thích bài báo.
Hình mô tả DataFusion, không phải kiến trúc DuckDB hoặc bằng chứng tốc độ.

- `overview`: hình tổng quan 1–9.
- `logical-initial`: LogicalPlan ban đầu (3).
- `logical-optimized`: LogicalPlan sau tối ưu và vòng logic (3–4).
- `logical-rewrite`: vòng quy tắc logic (4).
- `physical-initial`: ExecutionPlan trước tối ưu vật lý (5).
- `physical-final`: ExecutionPlan sau vòng vật lý (5–6).
- `physical-rewrite`: vòng quy tắc vật lý (6).
- `execution-q6`: nguồn Parquet, biểu thức và Streams (2, 7–8); tổng hợp Q6
  không có GROUP BY nên không khoanh HashAggregate như bằng chứng dựng bảng băm.
- `execution-join`: thêm Join và HashAggregate để giải thích Q17 (2, 7–8).
- `extension-rewrite`: quy tắc Rust bổ sung tại ExecutionPlan Rewrite (5–6, 9).

Tạo lại từ thư mục tpch, dùng Pillow hiện có:

```bash
../venv/bin/python render_plan_architecture.py
```

`plan_architecture.py` nhúng PNG vào HTML để hình đi cùng output notebook,
không phụ thuộc máy chủ ảnh hoặc JavaScript. Khi chạy lại cần cả tệp Python
và thư mục ảnh. `plan_comparison.py` vẫn lấy kế hoạch thật bằng EXPLAIN;
không chạy SELECT hoặc ANALYZE chỉ để vẽ/chú giải hình.
