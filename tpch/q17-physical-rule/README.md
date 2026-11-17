# Q17: chọn phía dựng từ thống kê trước thực thi

Chương trình dùng **DataFusion Rust 32.0.0**, đọc nguyên văn dòng 17 của
`../queries.sql`. Không đổi FROM, điều kiện lọc hoặc công thức SQL.

## Chính sách lựa chọn

`StatisticsBuildSideRule` triển khai `PhysicalOptimizerRule` tại điểm mở rộng
**Extension — ExecutionPlan Rewrite** của Hình 2 trong bài báo. Quy tắc không
nhận diện tên bảng, tên cột, đường dẫn tệp cụ thể, nhãn hiệu hoặc bao bì.
Không dùng số dòng đã quan sát sau chạy để chọn kế hoạch.

Cả hai phương án Rust đều dùng:

```rust
SessionConfig::new()
    .with_target_partitions(1)
    .with_collect_statistics(true)
```

Đây là cấu hình đối chứng có thu thống kê, khác cấu hình Python benchmark gốc.
Chỉ phương án `on` đăng ký thêm `state.add_physical_optimizer_rule(rule.clone())`.
Các quy tắc chuẩn vẫn được giữ.

1. Metadata Parquet cung cấp số dòng nguồn chính xác khi có thống kê exact.
2. Nếu scan có predicate, số dòng nguồn chỉ được dùng làm giới hạn trên.
3. Filter không tăng số dòng: đầu ra có giới hạn dưới 0 và giới hạn trên từ đầu vào.
4. Projection và CoalesceBatches giữ số dòng. Toán tử chưa hỗ trợ: trả chưa biết.
5. Mô hình chi phí dựng = số dòng × (độ rộng cột cố định + 32 byte chi phí băm/dòng).
6. Chỉ đổi nếu chi phí mô hình tối đa bên phải nhỏ hơn tối thiểu bên trái.
7. Đổi hai đầu vào, đổi khóa và thêm Projection phục hồi thứ tự cột.

`estimated_rows` khác `lower_rows`/`upper_rows`. Không biết tỷ lệ lọc thì để
ước lượng chưa biết; không gọi giới hạn trên là số dòng dự đoán. Chẳng hạn Q17
có thể suy ra nhánh đã lọc có tối đa 2 triệu dòng mà chưa biết thực tế còn 2.044.

32 byte là tham số chung của mô hình, không phải số đo allocator. Khoảng chi phí
chỉ là giới hạn trong mô hình này, không bảo đảm RAM hoặc thời gian thực tế.
Chưa mô hình hóa độ lệch khóa, CPU, cache, cấp phát, chi phí lấy dữ liệu hay
mọi loại dữ liệu. Kiểu chuỗi/nested chưa có mô hình độ rộng thì bỏ qua.
Chỉ hỗ trợ INNER/CollectLeft không có join filter, hai đầu vào một phân vùng.
Khoảng chồng lấp, thiếu thống kê hoặc tràn số thì không đổi. Đây là mở rộng
chọn phía dựng dựa trên thống kê/giới hạn, chưa phải bộ tối ưu chi phí đầy đủ.

## Mã nguồn

- `src/statistics.rs`: bằng chứng số dòng, truyền giới hạn và mô hình byte.
- `src/q17_rule.rs`: điều kiện an toàn, so chi phí, nhật ký trước chạy và biến đổi.
- `src/main.rs`: đăng ký nguồn và quy tắc, chế độ chỉ lập kế hoạch, chạy/đo.
- `src/tests.rs`: dữ liệu nhỏ và kiểm tra bảo toàn kết quả, lược đồ, dòng trùng,
  NULL, thay tên cột và điều kiện, thứ tự đã phù hợp, thiếu thông tin và tràn số.

## Build và kiểm tra trước thực thi

Từ thư mục gốc kho benchmark:

```bash
cargo build --release --locked -j 3 --manifest-path tpch/q17-physical-rule/Cargo.toml

tpch/q17-physical-rule/target/release/q17-physical-rule "$PWD" on --plan-only
```

`--plan-only` đăng ký bảng, đọc metadata, lập kế hoạch và trả JSON.
`execution_performed=false`, `value=null`; chưa collect Q17. Nhật ký quyết định
được chốt trước collect trong cả chế độ thực thi. Không chạy COUNT hoặc lấy mẫu.

## Chạy đối chứng

```bash
tpch/q17-physical-rule/target/release/q17-physical-rule "$PWD" off
tpch/q17-physical-rule/target/release/q17-physical-rule "$PWD" on
```

Cùng binary release, SQL và collect_statistics=true. Không bắt buộc phải biến đổi
đúng một lần: quyết định phụ thuộc thống kê thực tế và phạm vi hỗ trợ.
Notebook gọi subprocess có timeout 120 giây; mỗi lệnh chạy một lần.

JSON trả chuẩn bị/đăng ký bảng (gồm thu metadata), lập kế hoạch, thực thi,
tổng kế hoạch + thực thi, và tổng cộng thêm chuẩn bị. Không tính khởi động tiến
trình, build, in kế hoạch. Không so wheel Python và binary Rust để tách hiệu quả
quy tắc. Không xóa cache; nếu không cải thiện phải ghi nhận đúng số đo.

## Kiểm thử và phụ thuộc

```bash
cargo fmt --manifest-path tpch/q17-physical-rule/Cargo.toml --all -- --check
cargo test --release --locked -j 3 --manifest-path tpch/q17-physical-rule/Cargo.toml
```

Hoặc chạy từ thư mục `tpch/q17-physical-rule`:

```bash
cargo fmt --all -- --check
cargo test --release --locked -j 3
```

Các kiểm thử chỉ dùng dữ liệu nhỏ trong bộ nhớ/Parquet tạm, không đổi SF=10.
Cargo.lock giữ nguyên. DataFusion ghim 32.0.0, Chrono 0.4.31 tương thích Arrow 47,
Tokio 1.32.0; Serde/serde_json cho JSON, Tempfile cho test. Không thêm phụ thuộc.
`target/` được Git bỏ qua; không sửa mã upstream hoặc thư viện Python.

## Nguồn

- [PhysicalOptimizerRule](https://github.com/apache/datafusion/blob/32.0.0/datafusion/core/src/physical_optimizer/optimizer.rs#L34-L52).
- [add_physical_optimizer_rule](https://github.com/apache/datafusion/blob/32.0.0/datafusion/core/src/execution/context.rs#L1654-L1661).
- [FilterExec.statistics](https://github.com/apache/datafusion/blob/32.0.0/datafusion/physical-plan/src/filter.rs#L201-L238).
- [swap_hash_join và phục hồi cột](https://github.com/apache/datafusion/blob/32.0.0/datafusion/core/src/physical_optimizer/join_selection.rs#L130-L196).

Suy luận giới hạn và mô hình chi phí do nhóm bổ sung. Đổi phía/phục hồi Projection
tham khảo DataFusion 32, thông tin bản quyền giữ trong LICENSE.txt và NOTICE.txt.
Không giới thiệu hash join hoặc giao diện mở rộng là thuật toán mới của nhóm.

A. Lamb và cộng sự, “Apache Arrow DataFusion: A Fast, Embeddable, Modular Analytic
Query Engine,” SIGMOD Companion, 2024, [DOI 10.1145/3626246.3653368](https://doi.org/10.1145/3626246.3653368), Hình 2.
