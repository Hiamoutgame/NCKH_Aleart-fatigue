# System overview

Cập nhật 26/10/2026. Tài liệu mô tả **hệ thống đề xuất**. Cột "Trạng thái" ghi rõ phần nào đã có code trong `src/`, phần nào chưa.

## 1. Hệ thống làm gì

Nhận log của một sự cố, tổ chức thành cây `incident → service → nhóm template → log gốc`, rồi xếp hạng các service theo tỉ lệ nghi ngờ là nguyên nhân. Mỗi service trong kết quả có kèm nhóm log làm bằng chứng, và mỗi nhóm mở lại được tới từng dòng log gốc.

Hệ thống có hai chế độ:

| Chế độ | Dùng khi nào | Đầu vào |
| --- | --- | --- |
| **Offline evaluation** (chế độ chính của nghiên cứu) | Chạy trên toàn bộ dataset để đo kết quả | Log của các incident trong RCAEval / Nezha |
| **Demo tương tác** | Minh họa kịch bản người vận hành | Đoạn log người dùng dán vào + tên hệ thống |

## 2. Người dùng chính

| Người dùng | Nhu cầu |
| --- | --- |
| On-call engineer, SRE, DevOps | Biết nên kiểm tra service nào trước, và xem log nào để kiểm chứng |
| Developer của service | Mở lại đúng dòng log gốc để sửa lỗi |
| Nhóm nghiên cứu | Chạy lại thực nghiệm, so sánh các phương pháp trên cùng dữ liệu |

## 3. Chức năng chính

| # | Chức năng | Mô tả | Trạng thái |
| --- | --- | --- | --- |
| F1 | Đọc và chuẩn hóa dữ liệu | Adapter đọc RCAEval / Nezha thành ba bảng chuẩn: `incidents`, `log_events`, `ground_truth` | **Đã có** (`src/datasets/`). Adapter Nezha còn lỗi, xem [dataset.md](../05_methodology/dataset.md) |
| F2 | Audit và chia tập | Đánh dấu case dùng được, chia train/validation/test theo kịch bản lỗi | Chưa có |
| F3 | Chia cửa sổ trước/sau lỗi | Tách log thành giai đoạn trước và sau thời điểm lỗi | Chưa có |
| F4 | Gom nhóm log | Gom theo service + template (regex hiện có, sau đó Drain). Mỗi log thuộc đúng một nhóm | Mới có `template_id` dạng MD5 |
| F5 | Tạo cây phân cấp | `incident → service → nhóm → log_id`, có nhóm riêng cho log chưa rõ service | Chưa có |
| F6 | Xếp hạng service | Baseline luật, Logistic Regression, Kev; cùng một interface | Chưa có |
| F7 | Chọn bằng chứng | Chọn vài nhóm log tiêu biểu cho mỗi service trong kết quả | Chưa có |
| F8 | Đánh giá | Top-k, MRR, coverage, reduction, traceability, thời gian chạy | Chưa có |
| F9 | Demo | Giao diện dán log → bảng service + tỉ lệ + nhóm bằng chứng | Chưa có, làm sau F1–F8 |

## 4. Dữ liệu đầu vào

| Nguồn | Nội dung | Ghi chú |
| --- | --- | --- |
| RCAEval (dataset chính) | 359 case có log, mỗi case khoảng 24 phút log, nhãn 1 service | Chi tiết ở [dataset.md](../05_methodology/dataset.md) |
| Nezha (đánh giá ngoài) | 101 lần tiêm lỗi trên OnlineBoutique và TrainTicket, log kèm trace ID | Chỉ dùng log, không dùng trace để giữ điều kiện giống RCAEval |
| Danh sách service của hệ thống | Gom từ log của tập train | Không lấy từ đáp án |
| Đoạn log người dùng dán (chế độ demo) | Các dòng log tại thời điểm lỗi | Cần biết thuộc hệ thống nào để lấy danh sách service |

## 5. Model AI

**Kev** (model quyết định nhỏ dựa trên Qwen, mã nguồn mở) được dùng làm bộ xếp hạng chính, bọc sau interface `ServiceRanker` của dự án. Lý do chọn và cách tích hợp ở [ai_model_integration.md](ai_model_integration.md).

**Drain** được dùng để parse log thành template. Đây là thuật toán, không phải model học máy.

## 6. Đầu ra

1. **Cây phân cấp** cho mỗi incident, kèm số log và khoảng thời gian của từng nhóm.
2. **Bảng xếp hạng** cho mỗi incident: `service_id`, `score` (tỉ lệ), `rank`, `supporting_group_ids`, `supporting_log_ids`.
3. **Báo cáo đánh giá** cho mỗi lần chạy: metric, số incident trong mẫu số, cấu hình, phiên bản dữ liệu.

Ví dụ minh họa (giả định, không phải kết quả đo):

```text
Incident re2ob_..._1   hệ thống: ob   (11 service ứng viên)
1. cartservice      0.62   nhóm: g17 "redis timeout <*>" (412 dòng), g18 ...
2. frontend         0.21   nhóm: g03 "request error <*>" (1,930 dòng)
3. checkoutservice  0.07   ...
```

Tỉ lệ là xác suất Kev trả về sau khi hiệu chỉnh. Đó là độ tin của model, không phải xác suất nhân quả đã được chứng minh.

## 7. Ngoài phạm vi

- Thu thập log thời gian thực, dashboard production, cảnh báo tự động.
- Xóa hay lọc bỏ log gốc.
- Dự đoán lỗi trước khi xảy ra.
- LLM tự sinh văn bản giải thích.

## Tài liệu liên quan

[system_architecture.md](system_architecture.md) · [ai_model_integration.md](ai_model_integration.md) · [data_flow.md](data_flow.md) · [problem_statement.md](../03_problem_and_gap/problem_statement.md)
