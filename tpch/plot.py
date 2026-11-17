"""Vẽ thời gian trung bình và độ lệch chuẩn từ CSV benchmark đã lưu."""

# Matplotlib xuất hình PDF, không chạy lại truy vấn.
import matplotlib.pyplot as plt
# Pandas ghép các mẫu thời gian thành bảng.
import pandas as pd
# Seaborn nhóm mẫu theo truy vấn và bộ máy.
import seaborn as sns


# Chỉ thực hiện quy trình khi chạy tệp trực tiếp, không tự chạy lúc import.
if __name__ == "__main__":
    # Thứ tự danh sách cũng là thứ tự bộ máy trong chú giải.
    engines = ["duckdb", "datafusion"]
    # Dùng lưới nền để dễ so độ cao các cột.
    sns.set_theme(style="whitegrid", palette="bright")
    # Giữ kích thước hình của mã tác giả.
    plt.figure(figsize=(15, 5))
    # Một hàng dữ liệu vẽ tương ứng với một lượt đo đã được ghi vào CSV.
    data = {"duration": [], "engine": [], "query": []}
    # Đọc kết quả của cả hai bộ máy từ results/latest.
    for engine in engines:
        # CSV gồm query, cores, iteration, duration và không có tiêu đề.
        with open(f"../results/latest/tpch_{engine}.csv") as stream:
            # Chỉ lấy số câu và thời gian, hai trường còn lại không dùng để vẽ.
            for line in stream:
                # Tách dòng CSV thành bốn trường.
                fields = line.strip().split(",")
                # Đưa số câu về kiểu số để nhóm đúng Q1–Q22.
                data["query"].append(int(fields[0]))
                # Nhãn bộ máy xuất hiện ở chú giải của biểu đồ.
                data["engine"].append(engine)
                # Thời gian đo dùng đơn vị giây.
                data["duration"].append(float(fields[3]))
    # Ghép các cột để Seaborn đọc theo tên trường.
    frame = pd.DataFrame(data)
    # Chiều cao là trung bình, thanh sai số là độ lệch chuẩn của các mẫu hiện có.
    axes = sns.barplot(x="query", y="duration", hue="engine", data=frame,
                       errorbar="sd", err_kws={"linewidth": 0.1}, capsize=0.2)
    # Đặt tên trục mà không thay đổi dữ liệu thời gian.
    axes.set(xlabel="Query", ylabel="Duration (s)")
    # PDF là kết quả trên máy đang chạy, không phải hình gốc bài báo.
    output = "../results/latest/comparison.tpch.pdf"
    # Thông báo đường dẫn để mở kết quả.
    print(f"Writing results to {output}...")
    # Bỏ khoảng trắng thừa quanh hình khi lưu.
    plt.savefig(output, bbox_inches="tight")
    # Giải phóng figure nếu chạy lại tập lệnh trong cùng tiến trình.
    plt.close()
