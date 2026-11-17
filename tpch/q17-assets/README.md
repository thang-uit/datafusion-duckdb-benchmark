# Hình giải thích Q17

| Tệp | Vai trò |
|---|---|
| `01-q17-phia-dung.png` | Minh họa phía dựng bảng băm quan sát trong đợt khảo sát SF=10. Các con số trong ảnh là ví dụ đã thu, không phải kết quả của lần chạy mới. |
| `02-datafusion-chon-phia.png` | Trích mã DataFusion 32.0.0 về chọn phía dựng. `source-snippets.json` lưu đoạn nguồn, commit, URL và SHA-256. |
| `08-q17-thong-ke-truoc-chay.png` | Luồng quy tắc thống kê hiện tại do nhóm bổ sung. Tạo lại bằng `python render_q17_statistics.py` từ thư mục `tpch/`. |

Các hình này được notebook sử dụng. Thời gian và quyết định mới phải lấy từ JSON của lần chạy, không lấy từ ảnh. Hình quy tắc chuyên biệt cũ và các ảnh không còn được gọi đã được bỏ.

Nguồn kiến trúc: A. Lamb và cộng sự, SIGMOD Companion 2024, [DOI 10.1145/3626246.3653368](https://doi.org/10.1145/3626246.3653368), Hình 2. Ảnh và chú giải không thay thế bộ đếm thực thi.
