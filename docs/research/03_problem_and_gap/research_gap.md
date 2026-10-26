# Research gap

Cập nhật 26/10/2026. Nguồn: [literature matrix](../02_related_work/literature_review_matrix.md). Số trang là số in trên bài báo trong `docs/references/`.

**Giới hạn:** danh sách nguồn mới có 15 mục và chưa tìm kiếm có hệ thống. Các gap dưới đây là **giả thuyết có bằng chứng từ các bài đã đọc**, chưa đủ để viết "chưa có nghiên cứu nào". Trước khi nộp bài cần tìm thêm theo [search_keywords.md](../02_related_work/search_keywords.md) và đọc toàn văn RCAEval, COLA, AlertGuardian.

## Gap statement

> Existing microservice root cause analysis approaches such as Nezha and MRCA rely on multi-modal telemetry, requiring trace identifiers in logs or trace latency and metrics, and output ranked candidates without measuring how much an engineer must read or whether evidence remains traceable to raw records. Alert aggregation work such as COLA and AlertGuardian measures reduction, but on data that is hard to reproduce. Limited attention has been given to log-only, evidence-preserving organization of incident logs that is evaluated jointly on visible-item reduction, raw-log traceability and service-level ranking accuracy on public benchmarks.

Tạm dịch: các phương pháp RCA hiện có cần nhiều loại dữ liệu và chỉ trả danh sách xếp hạng; các phương pháp gom cảnh báo đo mức giảm trên dữ liệu khó tái lập. Còn ít nghiên cứu tổ chức log chỉ từ log, giữ bằng chứng gốc, và đánh giá cùng lúc ba thứ (giảm số mục, truy về log gốc, xếp hạng đúng) trên dữ liệu public.

## Chi tiết từng gap

### G1. RCA mức service chỉ từ log

| Bài | Cần gì | Bằng chứng |
| --- | --- | --- |
| Nezha | Log phải có trace ID / span ID | Mục 6.2, tr. 562: tác giả tự nêu là mối đe dọa tính hợp lệ |
| MRCA | Latency từ trace + metric | Mục 4.2, tr. 1060 |
| RCAEval (dữ liệu của dự án) | Log chỉ có `timestamp`, `container_name`, `message` | Kiểm trên raw 26/10/2026 |

**Cái giá phải trả:** MRCA Bảng 1 (tr. 1059) cho thấy log không phản ánh CPU contention và network jam. Vì vậy log-only có thể yếu với lỗi tài nguyên. Ngược lại, MRCA Bảng 6 cho thấy bỏ log làm PR@1 giảm mạnh nhất (OB 0.589 → 0.482).

**Nhóm làm gì:** đo Top-k chỉ từ log, báo riêng cho lỗi tài nguyên/mạng (RCAEval RE2: cpu, mem, disk, delay, loss, socket) và lỗi code (RE3: f1–f5).

### G2. Đầu ra dành cho người điều tra

| Bài | Đầu ra | Đo gì |
| --- | --- | --- |
| Nezha | Danh sách cặp pattern expected → actual | AS@k, AIS@k, thời gian |
| MRCA | Danh sách (service, metric) | PR@k, MRR, thời gian |
| AlertGuardian | Nhóm alert + chẩn đoán | ARR 94.8%, accuracy 90.5% (abstract) |
| COLA | Nhóm alert | Pairwise F1 (abstract) |

Không bài nào trong danh sách đo cùng lúc **mức giảm số mục** và **khả năng mở lại log gốc** cho log của microservices. Drain có giữ danh sách log ID cho mỗi nhóm (tr. 35), nhưng chỉ đánh giá độ đúng khi parse.

**Nhóm làm gì:** báo Visible Log Reduction và Raw Log Traceability cùng với Top-k trên cùng incident.

### G3. Protocol đánh giá minh bạch

- **Mẫu số khác nhau:** MRCA báo Nezha đạt PR@1 0.321–0.378, trong khi bài Nezha báo AS@1 92.86% / 86.67%. MRCA giải thích là Nezha báo theo xác suất có điều kiện (tr. 1064).
- **Baseline tự cài lại:** MRCA (tr. 1067).
- **Lần lặp của cùng kịch bản:** MRCA chia 60/40 nhưng không nêu cách xử lý. RCAEval có 117 kịch bản, hầu hết lặp 3 lần (`_1`, `_2`, `_3`). Chia ngẫu nhiên theo case sẽ đưa bản lặp của cùng kịch bản vào cả train lẫn test.

**Nhóm làm gì:** chia theo kịch bản, báo candidate coverage, conditional Top-k và end-to-end Top-k (xem [evaluation_metrics.md](../05_methodology/evaluation_metrics.md)).

### G4. Model quyết định nhỏ, fine-tune được, chỉ chọn trong danh sách ứng viên

- Nezha (tr. 556) bỏ qua phương pháp có giám sát vì cho rằng khó có dữ liệu gán nhãn. RCAEval có nhãn service cho cả 359 case có log, nên học có giám sát là khả thi.
- COLA và AlertGuardian dùng LLM. Chưa đọc toàn văn nên chưa biết chúng có ràng buộc đầu ra trong danh sách ứng viên không.
- Kev trả xác suất cho một câu hỏi chọn một trong các phương án cho trước, nên không thể "bịa" ra service ngoài danh sách.

**Nhóm làm gì:** dùng Kev fine-tune trên tập train để chọn service, so với các baseline trên cùng split.

**Cần làm rõ trước khi viết bài:** đọc toàn văn COLA và AlertGuardian để mô tả khác biệt chính xác.
