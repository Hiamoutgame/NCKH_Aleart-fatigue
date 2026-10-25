# Bước 1 — Lĩnh vực ứng dụng và đề xuất đề tài

## 1. Thông tin đề tài

- **Tên đề tài dự kiến:** Phân tích nguyên nhân gốc và dự đoán lỗi gần tương lai trong hệ thống microservices dựa trên log.
- **Lĩnh vực ứng dụng:** Vận hành hệ thống phần mềm (SRE/DevOps), giám sát hệ thống microservices.
- **Đối tượng người dùng:** Kỹ sư trực hệ thống (on-call engineer), kỹ sư SRE, DevOps engineer và đội vận hành hệ thống microservices.

## 2. Vấn đề thực tế

Khi một hệ thống microservices có bất thường, các service sinh ra lượng lớn log INFO/WARN/ERROR. Kỹ sư vận hành phải lọc qua hàng nghìn dòng log, trong đó phần lớn là lặp lại, hậu quả lan truyền, hoặc routine noise. Điều này dẫn đến **alert fatigue** và chậm xác định nguyên nhân gốc.

## 3. Lý do cần tích hợp AI

Các cách gom log theo rule tĩnh khó phân biệt log cùng ngữ nghĩa nhưng khác chữ, hoặc phân biệt root cause với propagated symptom.

AI được dự kiến sử dụng để:

- parse và cluster log theo template hoặc ngữ nghĩa;
- lọc cụm noise, giữ cụm bất thường có tín hiệu đáng nghi;
- xếp hạng root-cause candidate từ log pattern bình thường vs bất thường;
- dự đoán fault type và estimated time-to-failure từ log trend.

## 4. Model AI dự kiến

Pipeline đề xuất gồm 5 bước:

```text
(1) Log Collection       gom INFO + WARN + ERROR
(2) Log Parsing          Drain3/Spell → template
    + Clustering         Sentence-BERT → HDBSCAN
(3) Signal Filtering     giữ bất thường, bỏ routine
(4) RCA Ranking          rank service + template đáng nghi
(5) Failure Prediction   dự đoán fault type + time-to-failure
```

> Chưa chọn model cụ thể và chưa có code chạy AI trong `src`.

## 5. Kết quả mong muốn

- Root-cause candidate đúng nằm trong top-k kết quả — mục tiêu **Top-1 accuracy ≥ 70%**, **Top-3 accuracy ≥ 85%**.
- Dự đoán đúng fault type — mục tiêu **Prediction F1 ≥ 0.70**, **AUC ≥ 0.75**.
- Cảnh báo sớm trước khi service suy giảm — mục tiêu **lead time ≥ 5 phút**.

## 6. Những phần pipeline đã có trong `Resource/cp1/src`

- Registry nguồn dữ liệu tại `config/sources.yaml`.
- Tải dataset từ Hugging Face, clone repository tham khảo và lưu manifest phiên bản dữ liệu.
- Đọc log local và metadata của RCAEval.
- Quét, đếm log `WARN`/`WARNING`, `ERROR`, `INFO`, `DEBUG` theo từng case.
- Suy luận severity từ nội dung message vì RCAEval không có cột severity chuẩn.
- Chuẩn hóa timestamp, UUID, thread ID, hexadecimal ID và số thay đổi trong message để phục vụ gom nhóm sau này.
- Tách warning trước/sau thời điểm inject lỗi.
- Xuất bảng CSV và báo cáo kiểm chứng dataset.
- Có unit test cho parsing warning, normalization, path và source registry.

## 7. Những phần chưa có

- Log parsing/clustering chạy thật bằng Drain3/Spell, Sentence-BERT và HDBSCAN.
- Signal filtering theo frequency spike, new template và resource-related log.
- Root-cause candidate ranking theo service + log template.
- Failure prediction module để dự đoán fault type và estimated time-to-failure.
- Tính các metric Top-k RCA accuracy, Prediction F1/AUC, lead time và false alarm rate.

## 8. Kết luận trạng thái Bước 1

Nội dung đề xuất đề tài, lĩnh vực, vấn đề, người dùng, lý do dùng AI và kết quả kỳ vọng đã được xác định. Pipeline 5 bước đã chốt: Log Collection → Log Parsing + Clustering → Signal Filtering → RCA Ranking → Failure Prediction. Pipeline mã nguồn hiện mới hoàn thành phần **kiểm chứng và tiền xử lý dữ liệu**; phần **log clustering, RCA ranking và failure prediction** vẫn là các bước triển khai tiếp theo.
