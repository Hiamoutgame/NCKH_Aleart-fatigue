# Problem statement

Cập nhật 26/10/2026. Dựa trên [master context](../../../NCKH_MASTER_CONTEXT_2026-10-23.md), [literature matrix](../02_related_work/literature_review_matrix.md) và kiểm tra dữ liệu raw trong `data/raw/` cùng ngày.

## 1. Vấn đề thực tế

Khi một service trong hệ thống microservices gặp lỗi, lỗi lan sang các service gọi tới nó. Trong vài phút, nhiều service cùng ghi ra hàng nghìn đến hàng trăm nghìn dòng log. Người trực sự cố (on-call engineer, SRE) phải trả lời hai câu hỏi:

1. **Nên kiểm tra service nào trước?**
2. **Những dòng log nào là bằng chứng cho nghi vấn đó, và mở lại chúng ở đâu?**

Ví dụ thật từ dataset RCAEval của dự án: mỗi case có khoảng 24 phút log; tính theo từng hệ thống và nhóm lỗi, số dòng trung vị mỗi case từ khoảng 57,000 đến gần 268,000, đến từ 9–49 service khác nhau (trung vị 11). Đáp án chỉ là **một** service.

Kịch bản sử dụng nhóm hướng tới: người vận hành thấy dấu hiệu bất thường (ví dụ CPU tăng), dán các dòng log ERROR/WARN tại thời điểm đó vào hệ thống. Hệ thống trả về danh sách service có khả năng là nguyên nhân, kèm tỉ lệ cho từng service và các nhóm log làm bằng chứng.

## 2. Vì sao quan trọng

Các số liệu dưới đây đã được đối chiếu nguồn gốc trong [Why_FactCheck.md](../requirement/Why_FactCheck.md) (mục đánh dấu đúng):

- 39% trong 1,255 người được khảo sát cho rằng độ phức tạp và quá tải là rào cản lớn nhất của observability (Grafana Labs 2025).
- 62% người làm IT/DevOps phải làm thêm hơn 10 giờ mỗi tuần để xử lý sự cố (PagerDuty 2020).
- Hơn hai phần ba tổ chức mất trên 300,000 USD cho mỗi giờ sự cố (PagerDuty 2026).
- Google SRE đặt giới hạn tối đa 2 sự cố cho mỗi ca trực 12 giờ (SRE Book, ch. 11). Muốn giữ giới hạn đó, mỗi sự cố phải được định vị nhanh.

Ba số liệu đầu là khảo sát công nghiệp. Chúng cho thấy vấn đề có thật, nhưng không đo trực tiếp lợi ích của phương pháp này.

## 3. Các bài trước đã giải quyết thế nào

Tóm tắt từ [literature matrix](../02_related_work/literature_review_matrix.md):

| Hướng | Đại diện | Cách làm |
| --- | --- | --- |
| RCA đa phương thức | Nezha (FSE 2023), MRCA (ASE 2024) | Kết hợp metric, log, trace; so sánh giai đoạn bình thường với giai đoạn lỗi; trả danh sách xếp hạng |
| Gom cảnh báo | COLA (ICSE-SEIP 2024), AlertGuardian (ASE 2025) | Gom alert bằng thống kê + LLM, đo mức giảm số alert |
| Parse log | Drain (ICWS 2017) | Chuyển log thành template, chia log thành các nhóm không giao nhau, mỗi nhóm giữ danh sách log ID |

## 4. Hạn chế còn lại

Chi tiết và bằng chứng ở [research_gap.md](research_gap.md). Tóm tắt:

- Nezha bắt buộc log có trace ID; MRCA cần thêm trace và metric. Log của RCAEval chỉ có `timestamp`, `container_name`, `message`.
- Các bài RCA trả danh sách xếp hạng nhưng không đo người dùng phải đọc bao nhiêu mục, cũng không đo khả năng mở lại log gốc.
- Các bài gom alert đo mức giảm trên dữ liệu khó tái lập.
- Cùng một phương pháp có thể được báo với mẫu số khác nhau: MRCA báo Nezha đạt PR@1 0.32–0.38, trong khi bài Nezha báo khoảng 90%.

## 5. Bài toán của nhóm

**Đầu vào:** log của một incident (hoặc đoạn log người dùng dán vào), danh sách service quan sát được của hệ thống.

**Đầu ra:**

1. Cây phân cấp `incident → service → nhóm template → log_id gốc`. Mọi dòng log thuộc đúng một nhóm và mở lại được.
2. Danh sách service xếp theo tỉ lệ nghi ngờ, mỗi service kèm các nhóm log hỗ trợ.

**Ràng buộc:**

- Chỉ dùng log. Không cần trace ID hay metric.
- Không xóa log gốc. Giảm số mục hiển thị, không giảm dữ liệu.
- Service ứng viên chỉ lấy từ service quan sát được, không lấy từ đáp án.
- Nhãn chỉ có ở mức service. Không coi nhóm log được chọn là "log nguyên nhân" đã xác nhận.

## 6. Nhóm sẽ cải tiến điểm nào

1. Tổ chức log phân cấp có giữ bằng chứng, đo được cả mức giảm số mục và khả năng truy về log gốc.
2. Xếp hạng service chỉ từ log, dùng một model quyết định nhỏ (Kev) fine-tune được và chỉ được chọn trong danh sách service ứng viên.
3. Protocol đánh giá minh bạch: chia theo nhóm kịch bản lỗi, báo candidate coverage, conditional và end-to-end Top-k.

## 7. Định vị nghiên cứu

> This study does not aim to propose a new AI model from scratch. Instead, it investigates how an existing small decision model (Kev) can be integrated into an evidence-preserving log investigation pipeline for microservices, and evaluates whether it improves service-level root cause ranking compared with rule-based and statistical baselines on public benchmarks.

Bản tiếng Việt: nghiên cứu này không đề xuất một mô hình AI hoàn toàn mới. Nhóm khảo sát cách tích hợp một mô hình quyết định nhỏ có sẵn (Kev) vào quy trình điều tra log có giữ bằng chứng cho hệ thống microservices, và đánh giá xem nó có xếp hạng service gây lỗi tốt hơn các baseline luật và thống kê trên benchmark public hay không.

## 8. Đóng góp dự kiến

Đây là đóng góp **dự kiến**. Chỉ khẳng định được sau khi có kết quả thực nghiệm.

1. Một pipeline tổ chức log phân cấp có provenance (thông tin nguồn gốc của từng dòng log) trên dữ liệu public, với hai metric Visible Log Reduction và Raw Log Traceability.
2. Một bộ xếp hạng service dùng Kev, được bọc sau interface chung của dự án, so sánh với các baseline luật đơn giản và Logistic Regression trên cùng split.
3. Phân tích kết quả theo loại lỗi (tài nguyên/mạng so với lỗi code) và theo hệ thống, để biết log-only làm được tới đâu.
4. Bộ protocol đánh giá và mã nguồn tái lập được, kèm các phát hiện audit dữ liệu (ví dụ dataset Nezha gồm cả OnlineBoutique và TrainTicket).
