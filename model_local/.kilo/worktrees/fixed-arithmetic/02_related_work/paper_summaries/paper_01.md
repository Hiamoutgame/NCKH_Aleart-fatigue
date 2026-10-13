# Paper 01 Summary

## Citation

- **Tên bài:** Intelligent Logging and Monitoring Strategies
- **Tác giả:** Mallikarjun Bellundagi
- **Năm:** 2026
- **Nguồn:** IJSTC (International Journal of Science, Technology and Convergence), Vol. 8 No. 8
- **DOI/Link:** https://ijcdra.us/index.php/IJSTC/article/view/69

## Problem

Trong các ứng dụng Java phân tán và kiến trúc **microservices** (kiến trúc chia ứng dụng thành nhiều service nhỏ, độc lập, giao tiếp qua network), việc giám sát và ghi log truyền thống bằng **Log4j** (thư viện logging phổ biến cho Java) không đủ để xử lý quy mô lớn và động của hệ thống. Các phương pháp giám sát dựa trên quy tắc (**rule-based** — xác định trước các điều kiện if/else để phát hiện sự cố) không đủ để phát hiện bất thường và dự đoán sự cố trong môi trường phức tạp.

## Method

Bài báo đề xuất một chiến lược ghi log và giám sát thông minh tích hợp Log4j với **Machine Learning (ML)**:

1. **Structured logging** (ghi log có cấu trúc — log theo format JSON/key-value thay vì plain text, dễ parse và query) sử dụng Log4j để tạo log dữ liệu chất lượng cao, nhất quán qua nhiều service.
2. **ML models** phân tích log patterns:
   - **Clustering** (phân cụm không giám sát — gom các log giống nhau vào cùng nhóm mà không cần nhãn trước): định dạng log, nhóm patterns tương tự.
   - **Classification** (phân loại có giám sát — gán nhãn cho log: bình thường/bất thường): phân biệt bình thường vs bất thường.
   - **Time-series analysis** (phân tích chuỗi thời gian — xem giá trị thay đổi theo thời gian để dự đoán xu hướng): dự đoán xu hướng.
3. **Centralized log management** (quản lý log tập trung — gom log từ nhiều service về một nơi như ELK/EFK stack) với **real-time dashboards** (bảng điều khiển thời gian thực).

## Dataset

Không nêu rõ dataset cụ thể. Bài báo sử dụng các ví dụ về hệ thống microservices chung, không dùng dataset công khai nào.

## Evaluation

- **Anomaly detection accuracy** (độ chính xác phát hiện bất thường — % log bị flag đúng là anomaly).
- **Mean Time To Resolution — MTTR** (thời gian trung bình để khắc phục sự cố — từ khi alert đến khi fix xong).
- **System reliability** (độ tin cậy hệ thống — uptime, error rate).

Kết quả cho thấy cải thiện đáng kể so với approaches truyền thống.

## Results

- Tăng độ chính xác phát hiện bất thường.
- Giảm **MTTR**.
- Cải thiện độ tin cậy hệ thống.
- Hỗ trợ **adaptive learning** (học thích ứng — mô hình tự cập nhật khi hành vi hệ thống thay đổi, không cần retrain thủ công).

## Limitations

- Không có số liệu định lượng cụ thể (không có bảng số liệu hoặc chỉ số metric rõ ràng).
- Không so sánh với baseline công khai (COLA, **Drain3** — thuật toán parse log online phổ biến, etc.).
- Không đánh giá trên dataset chuẩn (RCAEval, LEMMA-RCA).
- Không có đánh giá về khả năng bảo toàn **root cause** (nguyên nhân gốc — lý do thực sự gây ra sự cố, khác với symptom/triệu chứng).

## Relevance to our topic

- **Liên quan về domain:** logging/monitoring trong microservices (tương tự C1 trong paper_list).
- **Phù hợp về phương pháp:** sử dụng ML cho log analysis (tương tự A1).
- **Hạn chế:** Bài báo không tập trung vào **alert aggregation** (gom nhóm cảnh báo — gộp nhiều alert liên quan thành 1 nhóm để giảm noise) hay **early-warning level** (mức cảnh báo sớm — cảnh báo trước khi sự cố nghiêm trọng xảy ra, thường là level WARNING) — nó là tổng quan về logging/monitoring, không giải quyết vấn đề gom nhóm cảnh báo nhiễu.

## Possible improvement

- Áp dụng các kỹ thuật **clustering**/**classification** từ bài này vào **alert stream** (luồng cảnh báo — dòng alert liên tục từ hệ thống) để giảm **noisy alerts** (cảnh báo nhiễu — alert không cần xử lý, duplicate, transient, unactionable, cascading) trước khi gom nhóm.
- Kết hợp với **topology service** (sơ đồ phụ thuộc service — ai gọi ai, quan hệ upstream/downstream) để tăng độ chính xác phát hiện **cascading alerts** (cảnh báo dây chuyền — alert lan truyền từ service gốc lỗi sang các service downstream).
- Xây dựng metric **RCPR** (Root Cause Preservation Rate — tỷ lệ bảo toàn nguyên nhân gốc: % alert gốc của root cause vẫn còn sau khi gom nhóm) để đánh giá khả năng bảo toàn signal gốc (điểm mà bài này bỏ qua).
