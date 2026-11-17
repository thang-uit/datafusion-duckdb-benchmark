# Apache Arrow DataFusion · TPC-H Demo

Chạy lại benchmark DataFusion/DuckDB từ mã tác giả, sau đó dùng Q6 và Q17 để đọc kế hoạch thực thi và minh họa điểm mở rộng của DataFusion.

> **Môi trường hướng dẫn:** máy Mac, macOS, Apple Silicon ARM64, Python 3.11. DataFusion Python **32.0.0**, DuckDB **0.9.1**. Đây là thực nghiệm cục bộ, không phải một kết quả TPC-H được chứng nhận.

[Mã tác giả](https://github.com/JayjeetAtGithub/datafusion-duckdb-benchmark) · [Kho fork](https://github.com/thang-uit/datafusion-duckdb-benchmark) · [Bài báo](https://doi.org/10.1145/3626246.3653368) · [Hướng dẫn notebook](tpch/README.md)

## 1. Nội dung và phiên bản

**Apache DataFusion** là bộ máy truy vấn phân tích viết bằng Rust, dùng Apache Arrow trong bộ nhớ, có thể nhúng vào ứng dụng và mở rộng các tầng xử lý truy vấn. Trong demo, Python gọi bộ máy có sẵn. Phần Rust Q17 bổ sung quy tắc tối ưu vật lý mà không viết lại thuật toán hash join.

**TPC-H** mô phỏng dữ liệu đặt hàng và cung ứng với 8 bảng, 22 truy vấn phân tích. Benchmark dùng cùng SQL và cùng tệp Parquet để đối chiếu hai bộ máy. **SF=10** là quy mô danh nghĩa khoảng 10 GB của dữ liệu nguồn, không phải số bảng hay kích thước Parquet sau nén.

| Thành phần | Phiên bản | Vai trò |
|---|---|---|
| Python | 3.11 | Chạy benchmark và notebook trong `venv/` riêng |
| DataFusion Python | 32.0.0 | Chạy SQL trong benchmark và notebook |
| DuckDB Python | 0.9.1 | Hệ thống đối chứng |
| DataFusion Rust trong `arrow-datafusion/` | tag 31.0.0 | Sinh/chuyển dữ liệu theo `setup.sh` của mã tác giả |
| DataFusion Rust trong `q17-physical-rule/` | 32.0.0 | Chạy Q17 với quy tắc mở rộng của demo |
| NumPy / PyArrow | 1.26.4 / 14.0.2 | Tương thích các gói native Python đời này |

Kho gốc còn có ClickBench và H2O. Quy trình dưới chỉ chạy **TPC-H**, không cần chạy hai bộ còn lại.

## 2. Cài công cụ trên Mac

Cần Git, Homebrew, Docker Desktop đang chạy và Rust/Cargo. **Docker chỉ dùng để sinh dữ liệu TPC-H**. Benchmark Python và notebook chạy trực tiếp trên Mac, không cần Docker sau khi đã có Parquet.

```bash
# Cài Python, Git và Rust/Cargo bằng Homebrew.
brew install python@3.11 git rust

# Nếu chưa có Docker Desktop.
brew install --cask docker

# Mở Docker và chờ ứng dụng báo đã sẵn sàng.
open -a Docker

# Xác nhận Docker, Cargo và trình biên dịch Rust hoạt động.
docker info
cargo --version
rustc --version
```

## 3. Clone và tạo môi trường Python riêng

Chạy tại thư mục muốn lưu dự án:

```bash
# Clone fork của mã tác giả.
git clone https://github.com/thang-uit/datafusion-duckdb-benchmark.git
cd datafusion-duckdb-benchmark

# Checkout này chỉ phục vụ sinh dữ liệu, không được đưa vào Git của benchmark.
git clone --branch 31.0.0 --depth 1 \
  https://github.com/apache/datafusion.git arrow-datafusion

# Dùng đúng Python 3.11 thay vì Python mặc định của macOS.
"$(brew --prefix python@3.11)/bin/python3.11" -m venv venv
source venv/bin/activate

# Cài các phiên bản Python được dùng trong demo.
python -m pip install -r requirements.txt

# Kiểm tra đúng bộ máy trước khi chạy.
python -c "import sys, datafusion, duckdb; print(sys.version.split()[0]); print('DataFusion:', datafusion.__version__); print('DuckDB:', duckdb.__version__)"
```

Kết quả cần có Python **3.11.x**, DataFusion **32.0.0**, DuckDB **0.9.1**. Mỗi lần mở Terminal mới, chạy lại `source venv/bin/activate` từ thư mục gốc kho. Các dự án khác dùng môi trường riêng.

## 4. Sinh dữ liệu SF=10

```bash
cd tpch
bash setup.sh
```

`setup.sh` thực hiện lần lượt:

1. Kiểm tra checkout, công cụ và Docker đang chạy.
2. Chọn tag DataFusion Rust `31.0.0` dùng để chuyển dữ liệu.
3. Gọi `common/prepare-tpch-source.py` để đổi hai tham chiếu ảnh Docker cũ `ghcr.io/databloom-ai/tpch-docker:main` sang `ghcr.io/scalytics/tpch-docker:main`. Các phần khác của `bench.sh` được giữ nguyên.
4. Trên Mac ARM64, đặt `DOCKER_DEFAULT_PLATFORM=linux/amd64` nếu chưa có cấu hình. Không cần tự thêm biến này vào lệnh.
5. Docker chạy `dbgen` tạo `.tbl`. Chương trình Rust của DataFusion chuyển dữ liệu sang Parquet.
6. Đưa kết quả về `arrow-datafusion/benchmarks/data/tpch_dataset/`.

> **Chạy lại setup sẽ xóa bộ đích `tpch_dataset/` trước khi sinh lại.** Không chạy lại bước này nếu chỉ muốn đo lại trên dữ liệu đã có. Lần đầu Cargo cần tải và biên dịch phụ thuộc. Thời gian phụ thuộc máy và cache. Tên ảnh Docker `:main` không khóa nội dung theo digest, nên không bảo đảm tái tạo byte giống hệt mọi thời điểm.

Kiểm tra metadata và kích thước dữ liệu, từ thư mục `tpch/`:

```bash
python - <<'PY'
from pathlib import Path
import pyarrow.parquet as pq

root = Path('../arrow-datafusion/benchmarks/data/tpch_dataset')
for path in sorted(root.glob('*/part-0.parquet')):
    metadata = pq.read_metadata(path)
    print(f'{path.parent.name:10} {metadata.num_rows:>12,} dòng '
          f'{metadata.num_row_groups:>3} nhóm hàng '
          f'{path.stat().st_size / 1_000_000_000:.3f} GB')
PY
```

Bộ SF=10 của demo có **59.986.052 dòng `lineitem`** và **2.000.000 dòng `part`**. `lineitem` là dòng hàng trong đơn đặt hàng, `part` là danh mục mặt hàng. Số dòng kiểm tra ở trên lấy từ metadata, không giải mã toàn bộ dữ liệu.

## 5. Chạy benchmark và xuất biểu đồ

Tiếp tục tại `tpch/`, với `venv` đã kích hoạt:

```bash
# Chạy DataFusion rồi DuckDB, cấu hình single.
bash benchmark.sh

# Vẽ từ CSV đã ghi, không chạy lại truy vấn.
python plot.py

# Mở biểu đồ vừa đo trên Mac.
open ../results/latest/comparison.tpch.pdf
```

| Kết quả | Nội dung |
|---|---|
| `results/latest/tpch_datafusion.csv` | Các lượt đo DataFusion |
| `results/latest/tpch_duckdb.csv` | Các lượt đo DuckDB |
| `results/latest/comparison.tpch.pdf` | Thời gian trung bình và độ lệch chuẩn của mẫu đã lưu |

Mỗi truy vấn chạy **5 lượt**. Hai lượt đầu không ghi CSV, ba lượt cuối được lưu theo thứ tự `query, cores, iteration, duration`. `single` dùng một phân vùng DataFusion và một luồng DuckDB. Trên Mac, tập lệnh bỏ qua thao tác `/proc/sys/vm/drop_caches` chỉ có trên Linux. Không diễn giải đây là phép đo cùng trạng thái cache với máy tác giả.

**Giữ giới hạn Q15 của mã gốc:** nhánh nhiều câu SQL trong `common/run-query-datafusion.py` so tên CSV đầy đủ với chuỗi `tpch_datafusion.csv`, trong khi script truyền đường dẫn có thư mục. Vì vậy lần chạy có thể thiếu mẫu DataFusion Q15. Kiểm tra CSV trước khi kết luận biểu đồ có đủ kết quả hai phía cho cả 22 câu. Fork này giữ điều kiện đó để đối chiếu mã gốc, không âm thầm sửa kết quả.

`benchmark.sh` ghi đè hai CSV trong `results/latest/`. Kết quả lịch sử tác giả nằm ở các thư mục ngày tháng khác trong `results/` và không bị thay. Thời gian trên Mac có thể khác bài báo do phần cứng, hệ điều hành, bộ nhớ đệm và bản build.

## 6. Chạy notebook Q6 và Q17 trong VS Code

Sau bước 5, Terminal đang ở `tpch/`. Quay về thư mục gốc rồi đăng ký kernel:

```bash
# Về gốc kho từ tpch/.
cd ..
source venv/bin/activate

# Đăng ký kernel dùng riêng môi trường của kho này.
python -m ipykernel install --user \
  --name tpch-datafusion32 --display-name "Python (TPC-H DataFusion 32)"
```

Mở thư mục kho trong VS Code, cài hai extension **Python** và **Jupyter** được đề xuất, rồi mở [`tpch/TPC_H_Q6_Q17.ipynb`](tpch/TPC_H_Q6_Q17.ipynb). Chọn kernel **Python (TPC-H DataFusion 32)** hoặc interpreter `venv/bin/python`, chạy từ trên xuống theo từng ô.

| Phần | Việc thực hiện |
|---|---|
| Chuẩn bị | Kiểm tra phiên bản, quy mô 8 bảng, dòng hàng mẫu và đăng ký nguồn Parquet |
| Q6 | Chạy một lượt trên từng bộ máy, đọc EXPLAIN, thu hồ sơ thực thi và xác định khác biệt vị trí lọc |
| Q6 đối chứng | Tự đổi `disabled_optimizers=''` thành `'filter_pushdown'`, chạy lại hai ô đối chứng. Notebook trả cấu hình về mặc định sau đó |
| Q17 gốc | Chạy một lượt mỗi bộ máy, xem nhánh dựng bảng băm |
| Q17 đổi FROM | Đổi thứ tự hai bảng để kiểm chứng tác động của phía dựng, chưa phải quy tắc mở rộng |
| Q17 mở rộng | Build Rust, xem `--plan-only`, chạy cùng SQL khi tắt/bật quy tắc rồi so kết quả, thời gian và bộ đếm |

Notebook được lưu **không có output cũ**. Các số mới do chính máy đang chạy tạo ra. Hình và tiện ích Python cần thiết đã có trong kho, không cần clone DuckDB để chạy notebook. Sau khi sửa tệp Python hỗ trợ, restart kernel rồi chạy lại các ô chuẩn bị. Nếu ngắt một truy vấn native mà kernel chưa dừng, dùng **Restart Kernel** trước khi tiếp tục.

## 7. Quy tắc vật lý Q17

Từ thư mục gốc kho, có thể build và gọi trực tiếp thay vì dùng các ô notebook:

```bash
cargo build --release --locked -j 3 \
  --manifest-path tpch/q17-physical-rule/Cargo.toml

# Chỉ đọc metadata và lập kế hoạch, chưa thực thi Q17.
tpch/q17-physical-rule/target/release/q17-physical-rule "$PWD" on --plan-only

# Cùng SQL và cùng binary, chỉ khác việc đăng ký quy tắc.
tpch/q17-physical-rule/target/release/q17-physical-rule "$PWD" off
tpch/q17-physical-rule/target/release/q17-physical-rule "$PWD" on
```

Quy tắc dùng metadata và giới hạn số dòng để so chi phí dựng bảng băm theo mô hình. Khi đủ căn cứ, nó đổi hai đầu vào phép nối, đổi khóa và dùng Projection phục hồi cột đầu ra. Quy tắc không biết trước số dòng sau khi chạy và vẫn dùng HashJoinExec của DataFusion. Cả hai lượt Rust bật thu thống kê. So hiệu quả bằng cặp Rust tắt/bật, không gộp với thời gian wheel Python.

Đọc chi tiết tại [`tpch/q17-physical-rule/README.md`](tpch/q17-physical-rule/README.md). Một lượt nhanh hơn không bảo đảm mọi lần đều nhanh hơn.

## 8. Các tệp và thư mục

| Tệp hoặc thư mục | Vai trò |
|---|---|
| `tests/test_demo.py` | Kiểm thử bản vá Docker, EXPLAIN và kết quả/cấu hình Q6 trên Parquet nhỏ |
| `requirements.txt` | Phiên bản thư viện Python của demo |
| `.vscode/` | Gợi ý interpreter của kho và extension cần cài, không chứa đường dẫn cá nhân |
| `common/prepare-tpch-source.py` | Cập nhật tên ảnh Docker của bộ sinh TPC-H |
| `common/run-datafusion.sh`, `run-duckdb.sh` | Duyệt tệp truy vấn và gọi tiến trình Python |
| `common/run-query-datafusion.py`, `run-query-duckdb.py` | Chạy 5 lượt và lưu 3 lượt cuối vào CSV |
| `common/create-view-duckdb.py` | Tạo view trong `my-db.duckdb`, tham chiếu các tệp Parquet |
| `tpch/setup.sh` | Chuẩn bị nguồn và sinh/chuyển dữ liệu SF=10 |
| `tpch/benchmark.sh` | Chạy bộ truy vấn cho hai bộ máy |
| `tpch/queries.sql` | 22 truy vấn của benchmark, mỗi câu một dòng. Giữ nguyên để bảo toàn cách đọc của mã gốc |
| `tpch/create-single-*.sql` | Đăng ký 8 bảng hoặc view đọc cùng Parquet |
| `tpch/plot.py` | Tạo biểu đồ từ CSV |
| `tpch/TPC_H_Q6_Q17.ipynb` | Quy trình minh họa tương tác, comment giải thích mã và SQL |
| `tpch/notebook_theme.py` | Màu chữ và nền các bảng notebook |
| `tpch/plan_notes.py` | Chú giải tiếng Việt cho tên kế hoạch và quy tắc |
| `tpch/plan_comparison.py` | Hàm tự viết `compare_plans`, lấy EXPLAIN thật rồi bố trí hai bên |
| `tpch/plan_architecture.py` | Ánh xạ kế hoạch với vùng trên hình kiến trúc |
| `tpch/q6_walkthrough.py` | Thu JSON profiling DuckDB, đọc bộ đếm DataFusion và so Q6 trước/sau |
| `tpch/q17_extension.py` | Gọi binary Rust có timeout và kiểm tra, trình bày JSON đối chứng |
| `tpch/q17-physical-rule/` | Mã Rust mở rộng, kiểm thử, Cargo.lock và thông tin nguồn/bản quyền |
| `tpch/plan-assets/`, `q6-assets/`, `q17-assets/` | Hình cần để chạy notebook. JSON bên cạnh ảnh ghi nguồn trích mã |
| `tpch/Architecture-DataFusion*.png` | Hình kiến trúc gốc và bản thêm số chú giải |
| `tpch/DataFusion-Environtment.png` | Trích đoạn bài báo về phiên bản thực nghiệm |
| `tpch/render_*.py` | Tạo lại hình kiến trúc, Q6 và luồng thống kê Q17. Không tự chạy khi import |
| `arrow-datafusion/`, `venv/`, `**/target/` | Checkout, thư viện và kết quả build cục bộ, Git bỏ qua |
| `results/latest/`, `tpch/plan-evidence/` | Kết quả chạy và khảo sát cục bộ, Git bỏ qua |
| `clickbench/`, `h2o/`, `benchmark-single-core.sh` | Bộ đo khác của kho gốc, không thuộc các bước TPC-H phía trên |
| `results/` | Kết quả lịch sử đã có từ kho tác giả |

Nguồn tác giả được giữ riêng với tiện ích minh họa. Fork bổ sung hỗ trợ Mac, notebook, ảnh chú giải và quy tắc Rust. Không đưa checkout DataFusion/DuckDB, dữ liệu lớn, cache, cơ sở dữ liệu tạm hoặc binary lên Git.

## 9. Kiểm tra nhanh

```bash
# Từ thư mục gốc, môi trường Python đã kích hoạt.
python -m compileall -q common tpch -x '/target/'

# Kiểm tra các script thuộc quy trình TPC-H.
for script in common/run-datafusion.sh common/run-duckdb.sh tpch/setup.sh tpch/benchmark.sh; do
  bash -n "$script"
done

# Kiểm thử tích hợp Python trên Parquet nhỏ, không dùng dữ liệu SF=10.
python -m unittest discover -s tests -v

# Chỉ dùng dữ liệu nhỏ/tạm cho kiểm thử Rust, không chạy lại SF=10.
cargo fmt --manifest-path tpch/q17-physical-rule/Cargo.toml --all -- --check
cargo test --release --locked -j 3 \
  --manifest-path tpch/q17-physical-rule/Cargo.toml
```

Tạo lại các hình hiện có và cách đọc từng phần notebook được mô tả tại [`tpch/README.md`](tpch/README.md). Kết thúc môi trường Python bằng `deactivate`.

## Nguồn và ghi nhận

- A. Lamb và cộng sự, “Apache Arrow DataFusion: A Fast, Embeddable, Modular Analytic Query Engine,” *SIGMOD Companion*, 2024, tr. 5–17, [DOI 10.1145/3626246.3653368](https://doi.org/10.1145/3626246.3653368).
- [Kho benchmark tác giả](https://github.com/JayjeetAtGithub/datafusion-duckdb-benchmark) và [alamb/datafusion-duckdb-benchmark](https://github.com/alamb/datafusion-duckdb-benchmark).
- [TPC-H](https://www.tpc.org/tpch/default5.asp), [Apache DataFusion](https://github.com/apache/datafusion), [scalytics/TPCH-Docker](https://github.com/scalytics/TPCH-Docker).
- Các script gốc cũng ghi nhận [ClickBench/DuckDB](https://github.com/ClickHouse/ClickBench/tree/main/duckdb) và [ClickBench/DataFusion](https://github.com/ClickHouse/ClickBench/tree/main/datafusion).
