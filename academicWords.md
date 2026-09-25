# 📖 Academic & Technical Words — Dự án NCKH Alert Aggregation

> Ghi chú thuật ngữ cho dự án: "Tác động của cơ chế gom nhóm cảnh báo (Alert Aggregation) lên việc giảm tỷ lệ cảnh báo nhiễu trong microservices"
> Cập nhật: 2026-09-18

---

## Thuật ngữ về kiến trúc hệ thống

### Microservice
- **EN**: Microservice architecture
- **VN**: Kiến trúc vi dịch vụ
- **Giải thích**: Thay vì viết 1 phần mềm lớn (monolith), người ta chia thành nhiều phần mềm nhỏ, mỗi phần chạy riêng biệt và gọi nhau qua mạng. Ví dụ: app thương mại điện tử chia thành service đơn hàng, service kho, service thanh toán.
- **Ví dụ trong đề tài**: Online Boutique, Sock Shop, Train Ticket là 3 microservice mẫu dùng để benchmark.

### Monitoring
- **EN**: Monitoring distributed systems
- **VN**: Giám sát hệ thống phân tán
- **Giải thích**: Phần mềm liên tục theo dõi trạng thái hoạt động của hệ thống (CPU, RAM, latency, error rate...) và phát cảnh báo khi thấy bất thường.
- **Công cụ phổ biến**: Prometheus, Grafana, ELK Stack, Datadog.

### Log
- **EN**: Application log / System log
- **VN**: Nhật ký hệ thống
- **Giải thích**: File ghi lại mọi hoạt động xảy ra trong hệ thống. Mỗi dòng log thường có: thời gian, mức độ (level), tên service, nội dung.
- **Ví dụ**: `2024-01-01 10:00:00 WARNING [payment-service] Connection timeout to database`

### Metric
- **EN**: Metric / Time-series metric
- **VN**: Số liệu giám sát / Chỉ số hiệu năng
- **Giải thích**: Dữ liệu số được thu thập theo thời gian, ví dụ: CPU usage = 85%, response time = 500ms, error rate = 2%.
- **Định dạng thường gặp**: Time-series (chuỗi thời gian) — ghi nhận giá trị tại mỗi thời điểm.

### Trace (Distributed Trace)
- **EN**: Distributed tracing
- **VN**: Truy vết phân tán
- **Giải thích**: Ghi lại đường đi của 1 request khi nó di chuyển qua nhiều service. Giúp biết request đi qua service nào, ở service nào bị chậm/lỗi.
- **Công cụ phổ biến**: Jaeger, Zipkin, OpenTelemetry.

### Dependency
- **EN**: Service dependency
- **VN**: Sự phụ thuộc giữa các service
- **Giải thích**: Service A gọi Service B → A phụ thuộc vào B. Nếu B chậm, A cũng chậm theo.
- **Trong đề tài**: `get_service_dependency(service)` là tool-2, dùng bảng dependency tĩnh (static) xây từ topology public.

### Topology
- **EN**: System topology / Service topology
- **VN**: Cấu trúc liên kết hệ thống
- **Giải thích**: Bản đồ mô tả các service kết nối với nhau như thế nào: service nào gọi service nào, qua giao thức gì.

---

## Thuật ngữ về cảnh báo (Alert)

### Alert
- **EN**: Alert / Alarm / Notification
- **VN**: Cảnh báo
- **Giải thích**: Thông báo tự động từ hệ thống monitoring khi phát hiện điều bất thường.

### Noisy Alert
- **EN**: Noisy alert / Alert noise
- **VN**: Cảnh báo nhiễu / Cảnh báo ồn ào
- **Giải thích**: Cảnh báo đúng về mặt kỹ thuật nhưng không cung cấp thông tin hành động được cho engineer. Giống chuông báo cháy reo khi chỉ đang nấu ăn.
- **4 loại trong đề tài**: Duplicate, Transient, Unactionable, Cascading.

### Alert Fatigue
- **EN**: Alert fatigue
- **VN**: Mệt mỏi vì cảnh báo
- **Giải thích**: Tình trạng engineer nhận quá nhiều alert → bắt đầu bỏ qua, kể cả alert thật. Đây là vấn đề gốc mà đề tài muốn giải quyết.

### Alert Aggregation
- **EN**: Alert aggregation / Alert grouping
- **VN**: Gom nhóm cảnh báo
- **Giải thích**: Gộp nhiều alert liên quan thành 1 nhóm, giảm số lượng alert engineer phải xem.
- **Trong đề tài**: Agent tool-calling quyết định cách gom nhóm (thay vì rule-based cố định).

### Alert Correlation
- **EN**: Alert correlation
- **VN**: Tương quan cảnh báo
- **Giải thích**: Xác định mối liên hệ giữa các alert — alert nào có cùng nguyên nhân, alert nào là hậu quả của alert nào.

### Duplicate Alert
- **EN**: Duplicate alert
- **VN**: Cảnh báo trùng lặp
- **Giải thích**: Nhiều alert cùng root cause trong cùng time window. Ví dụ: service A lỗi → 3 alert CPU high, latency spike, error rate up → chỉ cần xử lý 1.

### Transient Alert
- **EN**: Transient alert
- **VN**: Cảnh báo thoáng qua
- **Giải thích**: Alert tự biến mất trong thời gian ngắn mà không cần can thiệp. Ví dụ: network glitch khiến alert reo rồi tự tắt.

### Unactionable Alert
- **EN**: Unactionable alert
- **VN**: Cảnh báo không thể hành động
- **Giải thích**: Alert đúng về kỹ thuật nhưng engineer không có SOP/hướng xử lý cụ thể.

### Cascading Alert (Symptom Alert)
- **EN**: Cascading alert / Symptom alert / Downstream effect
- **VN**: Cảnh báo lan truyền / Cảnh báo triệu chứng
- **Giải thích**: Alert là hậu quả lan truyền từ root cause ở service khác. Fix service bị alert sẽ không giải quyết vấn đề gốc.
- **Ví dụ**: Service A (gốc) lỗi → B gọi A bị timeout → C gọi B cũng bị timeout. Alert ở B và C là cascading.

### Rule-based Alerting
- **EN**: Rule-based alerting
- **VN**: Cảnh báo dựa trên luật cố định
- **Giải thích**: Cách gom nhóm alert truyền thống: gom theo luật cố định (cùng service + cùng severity + cùng time window). Ví dụ: Prometheus Alertmanager.
- **Hạn chế**: Không linh hoạt, không có context về dependency giữa các service.

### Time Window
- **EN**: Time window
- **VN**: Cửa sổ thời gian
- **Giải thích**: Khoảng thời gian dùng để gom alert. Ví dụ: gom tất cả alert trong 5 phút thành 1 nhóm.

---

## Thuật ngữ về cấp độ log

### Log Level / Severity
- **EN**: Log level / Severity level
- **VN**: Cấp độ log / Mức độ nghiêm trọng
- **Giải thích**: Phân loại mức độ quan trọng của log entry.

| Level | EN | VN | Trạng thái hệ thống |
|---|---|---|---|
| INFO | Information | Thông tin | Bình thường, không cần alert |
| **WARNING** | Warning | **Cảnh báo sớm** | **Chưa sập — FOCUS của đề tài** |
| ERROR | Error | Lỗi | Đã hỏng, ngoài scope |
| FATAL | Fatal / Critical | Nghiêm trọng | Sập hoàn toàn, ngoài scope |

---

## Thu thuật ngữ về Root Cause Analysis (RCA)

### Root Cause
- **EN**: Root cause
- **VN**: Nguyên nhân gốc / Nguyên nhân gốc rễ
- **Giải thích**: Nguyên nhân thật sự gây ra sự cố, không phải hậu quả hay triệu chứng.
- **Ví dụ**: Service DB bị quá tải (root cause) → Service API gọi DB bị timeout (symptom) → Service Web hiển thị lỗi (symptom).

### Root Cause Analysis (RCA)
- **EN**: Root Cause Analysis
- **VN**: Phân tích nguyên nhân gốc
- **Giải thích**: Quy trình tìm nguyên nhân gốc của sự cố. Đây là bài toán chính mà benchmark RCAEval đánh giá.

### Cascading Effect / Cascading Failure
- **EN**: Cascading effect / Cascading failure
- **VN**: Hiệu ứng domino / Lan truyền lỗi
- **Giải thích**: Lỗi ở 1 service lan sang nhiều service khác theo chuỗi phụ thuộc.

---

## Thuật ngữ về AI Agent

### Agent
- **EN**: AI Agent / Autonomous agent
- **VN**: Tác tử AI / Agent tự trị
- **Giải thích**: Chương trình AI có khả năng tự suy nghĩ, ra quyết định, và gọi công cụ (tool) để lấy thêm thông tin. Khác với LLM thường chỉ trả lời câu hỏi.

### Tool-calling
- **EN**: Tool-calling / Function-calling
- **VN**: Gọi công cụ
- **Giải thích**: Khả năng của agent tự gọi các hàm/tool bên ngoài để lấy dữ liệu trước khi đưa ra quyết định.
- **Trong đề tài**: Agent gọi `get_related_alerts` và `get_service_dependency` trước khi quyết định gom nhóm.

### LLM (Large Language Model)
- **EN**: Large Language Model
- **VN**: Mô hình ngôn ngữ lớn
- **Giải thích**: Mô hình AI được huấn luyện trên lượng lớn dữ liệu văn bản, có khả năng hiểu và sinh ngôn ngữ tự nhiên. Ví dụ: GPT, Gemini, Claude.

### SOP (Standard Operating Procedure)
- **EN**: Standard Operating Procedure
- **VN**: Quy trình vận hành tiêu chuẩn
- **Giải thích**: Tài liệu hướng dẫn cách xử lý khi xảy ra lỗi cụ thể. Ví dụ: "Khi CPU > 90% → restart service".
- **Trong đề tài**: Tool-3 `get_runbook(fault_type)` là "SOP giả lập" do tự viết (dataset không có SOP thật) — cần ghi rõ limitation.

### Runbook
- **EN**: Runbook / Playbook
- **VN**: Sổ tay vận hành
- **Giải thích**: Tài liệu chứa các bước xử lý sự cố cụ thể. Trong đề tài, runbook được tạo synthetically (tổng hợp) cho từng fault type.

---

## Thu thuật ngữ về đánh giá (Evaluation)

### Benchmark
- **EN**: Benchmark
- **VN**: Chuẩn đánh giá / Điểm chuẩn
- **Giải thích**: Bộ dữ liệu + tiêu chí đánh giá chuẩn để so sánh nhiều phương pháp khác nhau trên cùng điều kiện.
- **Trong đề tài**: RCAEval là benchmark với 735 failure cases và 15 baseline.

### Baseline
- **EN**: Baseline
- **VN**: Đường cơ sở / Phương pháp cơ sở
- **Giải thích**: Phương pháp đơn giản, truyền thống dùng để so sánh. Nếu phương pháp mới không tốt hơn baseline → không có giá trị.
- **Trong đề tài**: 3 baseline — Rule-based (Prometheus), Time-window only, No aggregation.

### Ground Truth
- **EN**: Ground truth
- **VN**: Nhãn đúng / Sự thật chuẩn
- **Giải thích**: Dữ liệu đã được gán nhãn đúng (bởi con người hoặc quy trình thử nghiệm), dùng để đánh giá kết quả của mô hình.
- **Trong đề tài**: `root_cause_service` trong RCAEval là ground truth.

### Metric (Evaluation Metric)
- **EN**: Evaluation metric
- **VN**: Chỉ số đánh giá
- **Giải thích**: Số liệu định lượng用来 đánh giá phương pháp tốt hay xấu.

---

## Thuật ngữ về metric đánh giá trong đề tài

### ARR — Alert Reduction Ratio
- **EN**: Alert Reduction Ratio
- **VN**: Tỷ lệ giảm cảnh báo
- **Công thức**: ARR = 1 - (N_after / N_before)
- **Giải thích**: Giảm được bao nhiêu % số alert sau khi gom nhóm.
- **Ví dụ**: 100 alert → còn 25 → ARR = 75%.
- **Target**: ≥ 50%.

### RCPR — Root Cause Preservation Rate
- **EN**: Root Cause Preservation Rate
- **VN**: Tỷ lệ bảo toàn nguyên nhân gốc
- **Công thức**: RCPR = (Số group chứa đúng root cause) / (Tổng số fault cases)
- **Giải thích**: Gom nhóm xong có còn giữ được thông tin quan trọng không? Root cause có bị "nuốt mất" không?
- **Target**: ≥ 95%.

### Group Purity
- **EN**: Group purity
- **VN**: Độ tinh khiết của nhóm
- **Công thức**: Purity = (Alert cùng root cause trong group) / (Tổng alert trong group)
- **Giải thích**: Group có "sạch" không? Hay gom nhầm alert không liên quan?

---

## Thuật ngữ về dữ liệu & format

### Parquet
- **EN**: Apache Parquet
- **VN**: Định dạng Parquet (cột)
- **Giải thích**: Định dạng lưu trữ dữ liệu dạng cột (columnar), hiệu quả cho dữ liệu lớn. Nhanh hơn CSV nhiều khi đọc dữ liệu lớn.
- **Trong đề tài**: RCAEval lưu dữ liệu ở định dạng Parquet.

### Modality (Multi-modal)
- **EN**: Multi-modal data
- **VN**: Đa phương thức / Đa mô-đun dữ liệu
- **Giải thích**: Nhiều loại dữ liệu khác nhau từ cùng 1 hệ thống. Ví dụ: log (văn bản) + metric (số) + trace (đồ thị) = 3 modal.

### Dataset
- **EN**: Dataset
- **VN**: Bộ dữ liệu
- **Giải thích**: Tập hợp dữ liệu được tổ chức có cấu trúc, dùng để huấn luyện hoặc đánh giá mô hình.

### HuggingFace (HF)
- **EN**: Hugging Face
- **VN**: Nền tảng chia sẻ mô hình & dataset AI
- **Giải thích**: Platform phổ biến để chia sẻ dataset, mô hình AI, và công cụ ML. Địa chỉ: huggingface.co.

### License (MIT, CC-BY-NC-4.0)
- **EN**: MIT License / CC-BY-NC-4.0
- **VN**: Giấy phép sử dụng
- **Giải thích**:
  - **MIT**: Dùng thoải mái, kể cả thương mại, chỉ cần ghi credit.
  - **CC-BY-NC-4.0**: Chỉ dùng cho phi thương mại (nghiên cứu, giáo dục), phải ghi credit.

---

## Thuật ngữ về quy trình nghiên cứu

### Novelty
- **EN**: Novelty / Contribution
- **VN**: Đóng góp mới / Điểm mới
- **Giải thích**: Điểm mà đề tài này khác với các nghiên cứu trước. Đây là yếu tố quyết định bài báo có được chấp nhận không.
- **Trong đề tài**: Tập trung WARNING-level (hệ thống chưa sập) — khác với literature (tập trung ERROR/FATAL).

### Literature Review / Related Work
- **EN**: Related work / Literature review
- **VN**: Công trình liên quan / Tổng quan tài liệu
- **Giải thích**: Phần trong bài báo tổng hợp các nghiên cứu trước đã làm gì, và đề tài này khác gì.

### Gap Analysis
- **EN**: Gap analysis
- **VN**: Phân tích khoảng trống nghiên cứu
- **Giải thích**: Xác định nghiên cứu trước đã giải quyết gì, chưa giải quyết gì → tìm "lỗ hổng" mà đề tài này lấp vào.

### Methodology
- **EN**: Methodology
- **VN**: Phương pháp luận
- **Giải thích**: Phần trong bài báo mô tả cách thức thực hiện nghiên cứu: dùng gì, làm gì, theo trình tự nào.

### Baseline Comparison
- **EN**: Baseline comparison
- **VN**: So sánh với phương pháp cơ sở
- **Giải thích**: Đánh giá phương pháp mới bằng cách so sánh với baseline (phương pháp cũ/đơn giản hơn).

### Cross-system Generalization
- **EN**: Cross-system generalization
- **VN**: Tổng quát hóa liên hệ thống
- **Giải thích**: Agent huấn luyện trên hệ thống A có hoạt động tốt trên hệ thống B không? LEMMA-RCA dùng để test điều này.

### Coarse-grained vs Fine-grained
- **EN**: Coarse-grained / Fine-grained
- **VN**: Thô / Chi tiết
- **Giải thích**:
  - **Coarse-grained**: Xác định service nào gây lỗi (mức service).
  - **Fine-grained**: Xác định chính xác nguyên nhân (mức dòng code, metric cụ thể).

---

## Thu thuật ngữ về paper đã tham khảo

### COLA (ICSE 2024)
- **EN**: COLA: Log-based Alert Reduction via Correlation-aware Aggregation
- **VN**: COLA: Giảm cảnh báo dựa trên log qua gom nhóm có nhận thức tương quan
- **Paper**: arXiv:2403.06485
- **Vai trò**: Paper trung tâm nhất — phương pháp gom nhóm alert có xét đến tương quan giữa log entries.

### AlertGuardian (ASE 2025)
- **EN**: AlertGuardian
- **Paper**: arXiv:2601.14912
- **Vai trò**: Paper liên quan trực tiếp đến alert aggregation trong microservice.

### RCAEval (WWW 2025)
- **EN**: RCAEval: A Benchmark for Root Cause Analysis of Microservice Systems with Telemetry Data
- **Paper**: arXiv:2412.17015
- **Vai trò**: Benchmark chính — 735 failure cases, 3 microservice, 15 baselines.

### LEMMA-RCA
- **EN**: LEMMA-RCA: A Large Multi-modal Multi-domain Dataset for Root Cause Analysis
- **Vai trò**: Dataset backup — multi-modal (log + metric) từ Product Review Microservice.

### Google SRE Book
- **EN**: Site Reliability Engineering (Google SRE Book)
- **VN**: Kỹ thuật vận hành tin cậy
- **Chapters liên quan**: Ch.6 Monitoring Distributed Systems, Ch.10 Practical Alerting.
- **Vai trò**: Tài liệu nền tảng lý thuyết về monitoring và alerting.

### Prometheus Alertmanager
- **EN**: Prometheus Alertmanager
- **Giải thích**: Công cụ alerting phổ biến trong Kubernetes/microservice. Hỗ trợ grouping, inhibition, silencing. Dùng làm rule-based baseline.

---

## Thuật ngữ về microservice benchmark

### Online Boutique
- **EN**: Online Boutique (Google)
- **VN**: Cửa hàng trực tuyến mẫu
- **Giải thích**: Microservice mẫu của Google, mô phỏng app thương mại điện tử với 11 service. Topology public, dễ build dependency table.

### Sock Shop
- **EN**: Sock Shop (Weaveworks)
- **VN**: Cửa hàng bán tất mẫu
- **Giải thích**: Microservice mẫu của Weaveworks, mô phỏng app bán tất với nhiều service. Dùng phổ biến trong benchmark microservice.

### Train Ticket
- **EN**: Train Ticket
- **VN**: Hệ thống đặt vé tàu mẫu
- **Giải thích**: Microservice mẫu mô phỏng hệ thống đặt vé tàu với nhiều service phức tạp.

### AIOps
- **EN**: AIOps (Artificial Intelligence for IT Operations)
- **VN**: AI cho vận hành CNTT
- **Giải thích**: Sử dụng AI/ML để tự động hóa quy trình vận hành IT: phát hiện lỗi, phân tích nguyên nhân, dự đoán sự cố.

### Log Parsing / Template Extraction
- **EN**: Log parsing / Log template extraction
- **VN**: Phân tích log / Trích xuất mẫu log
- **Giải thích**: Chuyển log thô (raw log) thành log có cấu trúc bằng cách trích xuất template (mẫu). Ví dụ: "Connection timeout to host 192.168.1.1" → template "Connection timeout to host <IP>".
- **Tham khảo**: bolu61/loghub_2.