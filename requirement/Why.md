# BẢN ĐỀ XUẤT NGHIÊN CỨU KHOA HỌC (RESEARCH PROPOSAL)
## Chuyên đề: Tối ưu hóa giám sát hệ thống Microservices thông qua cơ chế gom nhóm cảnh báo (Alert Aggregation) từ dữ liệu Log Warning nhằm giảm thiểu cảnh báo nhiễu

---

## THÔNG TIN TỔNG QUAN ĐỀ TÀI

- **Tên đề tài**: Nghiên cứu cơ chế gom nhóm cảnh báo (Alert Aggregation) từ dữ liệu nhật ký cảnh báo sớm (Warning Log) nhằm giảm thiểu cảnh báo nhiễu trong kiến trúc Microservices.
- **Đối tượng nghiên cứu**: Luồng cảnh báo sớm sinh ra từ dữ liệu log cấp độ `WARNING` và các cơ chế gom cụm/phân tích tương quan cảnh báo (Alert Correlation & Aggregation).
- **Phạm vi nghiên cứu (Scope)**: Tập trung xử lý giai đoạn suy thoái hiệu năng sớm (Pre-failure / Early warning phase) trong kiến trúc Microservices. Không xử lý cảnh báo khi hệ thống đã sụp đổ hoàn toàn (Fatal/Critical downtime) — nơi mà các phương pháp Root Cause Analysis (RCA) truyền thống đã bao phủ.
- **Không gian phương pháp đối chứng (Methodology Spectrum)**:
  1. *Baseline Rule-based*: Gom nhóm theo nhãn tĩnh (Service, Severity, Cửa sổ thời gian cố định) theo chuẩn Prometheus Alertmanager.
  2. *Semantic Similarity*: Gom nhóm dựa trên biểu diễn ngữ nghĩa của log template (TF-IDF, Sentence-BERT, Word2Vec + DBSCAN/Agglomerative Clustering).
  3. *Temporal-Spatial Correlation*: Gom nhóm kết hợp topo phụ thuộc dịch vụ (Service Dependency Graph/Call Graph) và phân bố chuỗi thời gian.
  4. *LLM-based & Hybrid*: Ứng dụng mô hình ngôn ngữ lớn (Agent Tool-calling, Reasoning with Runbooks/SOPs) để xử lý các mẫu suy thoái phức tạp.

---

# PHẦN 1: TÍNH CẤP THIẾT CỦA ĐỀ TÀI (RESEARCH JUSTIFICATION)

## 1.1. Ý nghĩa thực tiễn công nghiệp (Industry Value)

### 1.1.1. Vấn nạn "Bão cảnh báo" (Alert Storm) và "Kiệt quệ vì cảnh báo" (Alert Fatigue) trong Microservices
Trong kiến trúc vi dịch vụ (Microservices), một hệ thống phân tán thường bao gồm hàng chục đến hàng trăm dịch vụ nhỏ liên kết chặt chẽ qua mạng (HTTP/gRPC/Message Queue). Khi một dịch vụ gặp hiện tượng suy giảm tài nguyên hoặc nghẽn cổ chai (ví dụ: chậm kết nối cơ sở dữ liệu, rò rỉ bộ nhớ nhẹ, phân mảnh hàng đợi), hiện tượng **lan truyền lỗi (cascading degradation)** xảy ra:
- Hàng loạt dịch vụ phụ thuộc phía hạ nguồn (downstream services) đồng loạt ghi nhận độ trễ tăng, timeout và phát ra hàng nghìn dòng log `WARNING`.
- Tình trạng này tạo ra **Cơn bão cảnh báo (Alert Storm)**, làm tê liệt khả năng nhận biết của kỹ sư trực vận hành (Site Reliability Engineer - SRE / On-call Engineer).

Hiện tượng tâm lý học và công thái học phát sinh trực tiếp từ đây là **Hội chứng kiệt quệ vì cảnh báo (Alert Fatigue)**:
- Khi khối lượng thông báo vượt quá ngưỡng dung nạp nhận thức (cognitive capacity), kỹ sư có xu hướng bỏ qua, tắt âm (mute), hoặc phản xạ đóng cảnh báo hàng loạt.
- Hậu quả nghiêm trọng nhất: **Cảnh báo suy thoái thực sự (True Signal)** bị chôn vùi dưới hàng nghìn cảnh báo nhiễu (Noisy Alerts), khiến sự cố nhỏ âm thầm tích tụ và bùng phát thành đợt sập toàn hệ thống (Outage).

### 1.1.2. Bằng chứng định lượng từ các báo cáo công nghiệp quốc tế

1. **Khảo sát toàn cầu PagerDuty (2020, 2026)**:
   - 62% chuyên gia IT/DevOps phải làm việc thêm ít nhất 10 giờ/tuần chỉ để giải quyết sự cố, do số lượng sự cố tăng 47% khi phân rã hệ thống sang đám mây và microservices.
   - Báo cáo *State of AI-First Operations (2026)* của PagerDuty chỉ ra thiệt hại kinh tế: **68% doanh nghiệp mất hơn 300.000 USD cho mỗi giờ gián đoạn dịch vụ**, trong đó 34% mất trên 500.000 USD/giờ và 8% mất hơn 1.000.000 USD/giờ.
2. **Khảo sát toàn cầu Grafana Labs Observability Survey (2025)** (*N=1.255 chuyên gia vận hành toàn cầu*):
   - 87% tổ chức phụ thuộc vào dữ liệu Log và 95% vào Metrics; doanh nghiệp vận hành trung bình **101 công nghệ giám sát khác nhau**.
   - **39% người tham gia khẳng định sự phức tạp và quá tải thông tin (overhead/complexity) là rào cản lớn nhất** đối với độ tin cậy hệ thống. Giảm nhiễu cảnh báo (reduced alert noise) và tối ưu thời gian khôi phục (MTTR) được xếp là ưu tiên hàng đầu, vượt qua cả mục tiêu cắt giảm chi phí hạ tầng.
3. **Báo cáo New Relic AI Impact Report (2026)** (*Khảo sát dựa trên dữ liệu thực tế từ 6,6 triệu người dùng*):
   - Các hệ thống giám sát truyền thống không có cơ chế tương quan AI ghi nhận **tỷ lệ cảnh báo nhiễu (noisy-alert rate) thường xuyên vượt quá 70%** (trung bình 63%-70%+).
   - Việc gom cụm thông minh giúp giảm 27% độ ồn cảnh báo và tăng gấp đôi tỷ lệ liên kết đúng giữa các triệu chứng với nguyên nhân gốc.
4. **Phân tích công nghiệp ITOC360 (2026) trên 1 triệu cảnh báo thực tế**:
   - **60% đến 80% cảnh báo phát sinh hàng tháng hoàn toàn không đòi hỏi hành động của con người (Unactionable/Noisy)**: chúng là bản sao trùng lặp, triệu chứng lan truyền từ một nguyên nhân gốc duy nhất, hoặc tự biến mất trong vài phút.
5. **Tiêu chuẩn chuẩn mực từ Google SRE (Rob Ewaschuk, Jamie Wilkinson et al., Google SRE Book & Workbook)**:
   - Nguyên lý nền tảng của Google SRE: *“Mỗi cảnh báo gửi tới kỹ sư trực (Page) bắt buộc phải đòi hỏi sự can thiệp chủ động của con người ngay lập tức (Actionable)”*.
   - Google SRE khuyến nghị hạn mức tối đa cho một ca trực là **không quá 2 cảnh báo/ca trực (2 actionable pages/shift)** để duy trì khả năng phản xạ và sức khỏe tâm lý cho kỹ sư. Hiện thực cảnh báo trong microservices hiện nay đang vi phạm ngưỡng này gấp hàng chục đến hàng trăm lần.
6. **Báo cáo ITIC (Information Technology Intelligence Consulting, 2024–2025)**:
   - 90% doanh nghiệp xác nhận 1 giờ ngừng hoạt động gây thiệt hại tối thiểu 300.000 USD (~5.000 USD/phút). Bất kỳ sự chậm trễ nào trong phát hiện sớm từ log warning đều chuyển hóa thành tổn thất tài chính trực tiếp.
7. **Bằng chứng mở rộng từ miền vận hành an ninh (SOC) — Báo cáo Microsoft / Omdia (2026) & Vectra AI (2023)**:
   - Khảo sát *State of the SOC* của Microsoft & Omdia (2026, *N=300*) ghi nhận: **46% cảnh báo là dương tính giả (False Positives)** và **42% cảnh báo bị bỏ qua không điều tra** do vượt quá năng lực xử lý; kỹ sư mất 20% thời gian mỗi tuần chỉ để gom nhóm thủ công.
   - Báo cáo *Vectra AI State of Threat Detection (2023, N=2.000)*: trung bình 4.484 cảnh báo/ngày, 67% bị bỏ qua và 83% là cảnh báo rác.
   *(Lưu ý phương pháp luận: Dữ liệu SOC đóng vai trò dẫn chứng đối sánh bổ trợ về mặt công thái học và tâm lý học nhận thức của con người khi xử lý dòng tín hiệu máy).*

---

## 1.2. Ý nghĩa hàn lâm và Khoảng trống nghiên cứu (Academic Value & Research Gap)

### 1.2.1. Bản chất 4 loại cảnh báo nhiễu ở cấp độ Log Warning
Khác với log `ERROR` hay `FATAL` (vốn xuất hiện khi luồng nghiệp vụ đã gãy vỡ), log `WARNING` biểu thị **tín hiệu cảnh báo sớm (Early Warning Signals)**: hệ thống vẫn đang hoạt động nhưng bắt đầu xuất hiện sự bất thường. Trong môi trường Microservices, log warning sinh ra 4 hình thái nhiễu đặc trưng:

1. **Cảnh báo trùng lặp (Duplicate Warning Alerts)**: Cùng một tiến trình/dịch vụ gặp sự cố tạm thời phát ra liên tục hàng chục log warning giống nhau trong một khoảng thời gian ngắn (ví dụ: *Connection retry 1/5, 2/5...*).
2. **Cảnh báo thoáng qua / Dao động (Transient / Flapping Alerts)**: Các cảnh báo xuất hiện chớp nhoáng do dao động mạng hoặc tải tăng tức thời, tự biến mất trong vòng 1-2 phút mà không cần can thiệp.
3. **Cảnh báo không thể hành động (Unactionable Warning Alerts)**: Log cảnh báo phản ánh trạng thái bất thường nhưng không vi phạm cam kết chất lượng dịch vụ (SLO), không kèm quy trình xử lý chuẩn (SOP/Runbook), chỉ làm phân tâm kỹ sư.
4. **Cảnh báo triệu chứng lan truyền (Cascading / Symptom Warning Alerts)**: Dịch vụ A (nguyên nhân gốc) bị chậm $\rightarrow$ Dịch vụ B gọi A bị tăng thời gian chờ $\rightarrow$ Dịch vụ C gọi B cảnh báo timeout. Log warning ở B và C là "nhiễu triệu chứng", can thiệp vào B hay C không giải quyết được gốc rễ vấn đề.

### 1.2.2. Phân tích 3 Khoảng trống nghiên cứu chính (Research Gaps)

```
+-----------------------------------------------------------------------------------+
| TIẾP CẬN TRUYỀN THỐNG TRONG LITERATURE:                                           |
| [Hệ thống chạy bình thường] -> (Bỏ qua Warning) -> [SỰ CỐ SẬP] -> [Phân tích RCA] |
|                                                                                   |
| TIẾP CẬN ĐỀ TÀI ĐỀ XUẤT:                                                         |
| [Log Warning xuất hiện] ----> [Gom nhóm & Tương quan Sớm] ---> [Chặn trước Outage]|
|                               (Giảm 60-80% cảnh báo nhiễu)                        |
+-----------------------------------------------------------------------------------+
```

#### **Khoảng trống 1 (Gap 1): Sự lệch pha giữa "Phân tích nguyên nhân hậu sự cố (Post-failure RCA)" và "Giám sát cảnh báo sớm (Early-warning Monitoring)"**
- *Hiện trạng Literature*: Đa số các nghiên cứu AIOps và RCA tiêu biểu (như RCAEval - *Pham et al., WWW 2025*; BARO - *Pham et al., FSE 2024*; MicroCause, CIRCA, E-Diagnosis) tập trung vào giai đoạn **sau khi sự cố đã bùng phát** (Fault Injection $\rightarrow$ Metric/Trace spike $\rightarrow$ tìm root cause service).
- *Khoảng trống*: Rất ít công trình nghiên cứu cơ chế gom nhóm và khử nhiễu cho các cảnh báo sớm ở mức `WARNING`. Khi đợi đến khi xuất hiện log `ERROR/CRITICAL`, hệ thống đã ngừng trệ, vi phạm SLO/SLA và gây thiệt hại kinh tế. Xử lý sớm ở mức `WARNING` có thể ngăn chặn sự cố (Proactive Mitigation), nhưng literature hiện tại chưa coi "Warning-level Alert Aggregation" là một bài toán độc lập với các thước đo định lượng chuẩn tắc.

#### **Khoảng trống 2 (Gap 2): Hạn chế căn bản của các phương pháp gom nhóm cảnh báo hiện hữu**
Khi áp dụng vào môi trường Microservices, 4 trường phái tiếp cận hiện nay đều bộc lộ điểm nghẽn kỹ thuật:

| Nhóm phương pháp | Cơ chế hoạt động | Hạn chế cốt lõi trong cảnh báo sớm Microservices |
|---|---|---|
| **1. Baseline Rule-based** *(e.g., Prometheus Alertmanager)* | Gom theo khớp nhãn tĩnh: `group_by: [alertname, cluster, service]` + cửa sổ thời gian `group_wait`, `group_interval`. | **Mù quan hệ phụ thuộc (Topology-blind)**: Không thể gom cảnh báo từ Service B và Service A vào cùng một nhóm dù B bị lỗi do A. Tốn chi phí bảo trì luật thủ công khổng lồ khi microservices thay đổi liên tục. |
| **2. Semantic Similarity** *(e.g., TF-IDF, Word2Vec, Sentence-BERT, Drain Log Clustering)* | Tính khoảng cách cosine/vector giữa văn bản thông điệp log để gom cụm (DBSCAN, HDBSCAN). | **Mù quan hệ nhân quả (Causality-blind)**: Hai cảnh báo có câu chữ giống nhau (ví dụ: *"Timeout connecting to host"*) ở 2 dịch vụ độc lập bị gom nhầm thành 1 cụm. Ngược lại, hai cảnh báo có từ ngữ khác hẳn nhau (*"Thread pool exhausted"* và *"HTTP 504 Gateway Timeout"*) nhưng cùng một nguyên nhân gốc lại bị tách rời. |
| **3. Temporal-Spatial Correlation** *(e.g., Topology Graph + Co-occurrence Window)* | Xây dựng đồ thị phụ thuộc tĩnh/động từ Tracing (Jaeger, OpenTelemetry) kết hợp thuật toán lan truyền trên đồ thị. | **Nhạy cảm với nhiễu thời gian**: Khi vi dịch vụ phát sinh cảnh báo không đồng thời (độ trễ lan truyền không đồng đều), ngưỡng thời gian (time window) cố định dễ cắt đứt chuỗi tương quan hoặc gom nhầm các lỗi độc lập xảy ra đồng thời. Khó xử lý cảnh báo hiếm (infrequent alerts). |
| **4. LLM-based Reasoning** *(e.g., COLA - ICSE SEIP 2024, AlertGuardian - ASE 2025)* | Sử dụng LLM để đọc nội dung cảnh báo kết hợp quy trình vận hành chuẩn (SOP/Runbooks). | **Chi phí tính toán và độ trễ cao (High Latency & Token Cost)**: Không thể đẩy trực tiếp hàng chục nghìn log warning vào LLM theo thời gian thực (Real-time stream). Cần một kiến trúc lai (Hybrid) lọc và phân tầng thông minh. |

#### **Khoảng trống 3 (Gap 3): Thiếu hụt Benchmark và Thước đo toàn diện cho bài toán Gom nhóm Cảnh báo Sớm**
- Bộ benchmark chuẩn quốc tế mới nhất cho microservices như **RCAEval (WWW 2025)** cung cấp 735 ca lỗi nhưng schema dữ liệu log thô (`logs.csv`) chỉ gồm `[time, service, message]` mà **không có sẵn nhãn phân định độ nghiêm trọng (Severity/Level)** hoặc **nhãn gom nhóm cảnh báo (Alert Group Ground Truth)**.
- Các nghiên cứu hiện tại thường đo lường đơn chiều bằng *Alert Reduction Ratio (ARR)*. Tuy nhiên, nếu một thuật toán gom tất cả cảnh báo vào duy nhất 1 nhóm thì ARR đạt 100% nhưng hoàn toàn vô giá trị vận hành. Cần thiết lập một bộ tiêu chí đánh giá đa chiều chuẩn hóa: **Alert Reduction Ratio (ARR)**, **Root Cause Preservation Rate (RCPR)**, **Pairwise Grouping F1-Score**, và **Group Purity**.

---

## 1.3. Bằng chứng & Trích dẫn học thuật quốc tế (Evidence & Academic Citations)

Các luận điểm trên được bảo chứng trực tiếp từ các công trình nghiên cứu hàng đầu tại các hội nghị phần mềm và hệ thống phân tán danh giá (ICSE, ASE, FSE, WWW, ACM CSUR):

1. **Về tính tất yếu của cơ chế gom nhóm và tương quan cảnh báo**:
   > *"Due to the scale and complexity of cloud systems, a system failure triggers an alert storm... Existing methods typically utilize semantic similarity or statistical methods. However, semantic similarity overlooks the causal rationale of alerts, while statistical methods can hardly handle infrequent alerts."*  
   — **Kuang et al. (2024)**, *Proceedings of the 46th IEEE/ACM International Conference on Software Engineering: Software Engineering in Practice (ICSE-SEIP 2024)*, nghiên cứu khung giải pháp COLA.

2. **Về việc tối ưu hóa vòng đời cảnh báo và giảm tải Alert Fatigue bằng AI**:
   > *"Alerts are critical for detecting anomalies, but current systems generate overwhelming volumes of alerts... AlertGuardian achieves 94.8% alert reduction ratios and 90.5% diagnosis accuracy through graph learning and LLM reasoning."*  
   — **Yu et al. (2025/2026)**, *Proceedings of the 40th IEEE/ACM International Conference on Automated Software Engineering (ASE 2025)*, arXiv:2601.14912.

3. **Về chuẩn mực Benchmark hệ thống Microservices**:
   > *"RCAEval introduces an open-source benchmark comprising 735 failure cases collected from three microservice systems (Online Boutique, Sock Shop, Train Ticket) covering various fault types with 15 reproducible baselines."*  
   — **Pham et al. (2025)**, *Companion Proceedings of the ACM Web Conference 2025 (WWW Companion '25)*, DOI: `10.1145/3701716.3715290`.

4. **Về thực trạng định nghĩa cấp độ log và sự mơ hồ của cảnh báo sớm**:
   > *"The choice of log severity levels can be challenging and cause problems in producing reliable logging data... our multivocal mapping reveals substantial semantic ambiguity and redundancy across industrial logging practices."*  
   — **Mendes & Petrillo (2021)**, *arXiv:2109.01192*, phân tích trên 40 thư viện logging và 27 công trình nghiên cứu.

5. **Về khảo cứu hệ thống tình trạng quá tải cảnh báo trên tạp chí đầu ngành**:
   > *"Recent reports indicate that most organisations receive over 10,000 alerts daily, with more than 50% being false positives, driving severe alert fatigue."*  
   — **Jalalvand, Tariq et al. (2024/2025)**, *ACM Computing Surveys (CSUR)*, DOI: `10.1145/3695462` & `10.1145/3723158`.

---

# PHẦN 2: THIẾT KẾ PHƯƠNG PHÁP NGHIÊN CỨU & KHUNG ĐÁNH GIÁ (PROPOSED METHODOLOGY & EVALUATION FRAMEWORK)

## 2.1. Thiết kế 4 nhánh phương pháp thực nghiệm đối chứng (Experimental Arms)

Nghiên cứu sẽ triển khai thực nghiệm song song và so sánh định lượng 4 hướng tiếp cận trên cùng một tập dữ liệu cảnh báo sớm chuẩn hóa:

```
                          +-------------------------------+
                          |    Raw Warning Log Stream     |
                          +---------------+---------------+
                                          |
        +------------------+--------------+----------------+------------------+
        |                  |                               |                  |
        v                  v                               v                  v
+---------------+  +---------------+               +---------------+  +---------------+
|  Arm 1: Rule  |  | Arm 2: Sem    |               | Arm 3: Topo   |  |  Arm 4: LLM   |
|  Alertmanager |  | S-BERT+DBSCAN |               | CallGraph+Win |  | Agent + SOP   |
+-------+-------+  +-------+-------+               +-------+-------+  +-------+-------+
        |                  |                               |                  |
        +------------------+--------------+----------------+------------------+
                                          |
                                          v
                    +-------------------------------------------+
                    |    Bộ chỉ số đánh giá đa chiều            |
                    |    (ARR, RCPR, Pairwise F1, Purity, Lat)  |
                    +-------------------------------------------+
```

### Nhánh 1: Baseline Rule-based (Prometheus Alertmanager Standard)
- **Cơ chế**: Triển khai mô phỏng chuẩn xác thuật toán của Prometheus Alertmanager.
- **Quy tắc gom nhóm**: Các cảnh báo có cùng bộ nhãn cố định `[service, alert_name, severity]` phát sinh trong khoảng thời gian `group_wait = 30s` và `group_interval = 5m` được gộp thành 1 notification.
- **Vai trò**: Đóng vai trò mốc cơ sở tối thiểu (Lower-bound Baseline) mà mọi hệ thống giám sát công nghiệp hiện nay đang sử dụng.

### Nhánh 2: Semantic Similarity-based (NLP Clustering)
- **Cơ chế**:
  1. Sử dụng bộ trích xuất mẫu log **Drain3** để chuẩn hóa log raw thành các log template (loại bỏ biến động số, ID, IP, URL).
  2. Mã hóa template văn bản thành vector nhúng ngữ nghĩa (Dense Embeddings) thông qua mô hình `sentence-transformers/all-MiniLM-L6-v2` (384 chiều, gọn nhẹ, tối ưu cho xử lý chuỗi ngắn) hoặc `bge-small-en-v1.5`.
  3. Áp dụng thuật toán phân cụm mật độ **HDBSCAN / DBSCAN** (với khoảng cách Cosine) để tự động gom nhóm các log có sự tương đồng ngữ nghĩa cao mà không cần định trước số cụm $k$.
- **Mục tiêu đánh giá**: Kiểm chứng xem mức độ hiểu ngôn ngữ tự nhiên có thể giải quyết được bài toán gom nhóm log warning hay không khi không có đồ thị liên kết dịch vụ.

### Nhánh 3: Temporal-Spatial Correlation (Topology-aware Graph Correlation)
- **Cơ chế**:
  1. Trích xuất cấu trúc liên kết mạng tĩnh (Service Topology / Static Call Graph) từ 3 hệ thống benchmark (Online Boutique: 11 services; Sock Shop: 13 services; Train Ticket: 40+ services).
  2. Xây dựng ma trận kề biểu diễn quan hệ phụ thuộc cha - con (Caller - Callee).
  3. Khi log warning xuất hiện, thuật toán mở một cửa sổ trượt thời gian động $\Delta t$ (Time Window: $30s, 60s, 120s$). Nếu hai dịch vụ $S_i$ và $S_j$ cùng phát sinh cảnh báo trong $\Delta t$ và tồn tại đường đi phụ thuộc $S_i \rightarrow S_j$ có độ dài bước đi $k \le 2$, cảnh báo sẽ được liên kết vào cùng một đồ thị sự cố (Incident Subgraph).
- **Mục tiêu đánh giá**: Đo lường tác động vượt trội của tri thức cấu trúc hệ thống (Topology Knowledge) trong việc khử các cảnh báo lan truyền (Cascading Noise).

### Nhánh 4: LLM-based Reasoning & Agentic Triage (Hybrid SRE Agent)
- **Cơ chế**:
  1. Tầng lọc nhanh (Fast Filter): Sử dụng Rule/Spatial để lọc bỏ trùng lặp hiển nhiên (Deduplication) và gom sơ bộ trong cửa sổ thời gian.
  2. Tầng suy luận nhận thức (Cognitive Reasoning): Đối với các cụm cảnh báo đa dịch vụ phức tạp, hệ thống chuyển ngữ cảnh (Prompt gồm: danh sách alert, service topology, và tóm tắt runbook/SOP) cho một LLM Agent (sử dụng GPT-4o-mini hoặc DeepSeek-V3/Llama-3-8B).
  3. Agent thực hiện chuỗi suy luận phân tích quan hệ nhân quả (Chain-of-Thought), xác định cảnh báo nào là "triệu chứng giả" và tổng hợp thành 1 phiếu sự cố duy nhất (Single Consolidated Incident Ticket) kèm theo đề xuất dịch vụ nghi vấn gốc.
- **Mục tiêu đánh giá**: Đánh giá sự đánh đổi giữa độ chính xác vượt trội (F1-score cao, giữ nguyên Root Cause) với chi phí tính toán (Token Cost) và độ trễ phản hồi (Inference Latency).

---

## 2.2. Dữ liệu thực nghiệm (Benchmark Datasets)

Nghiên cứu sử dụng nguồn dữ liệu mở tiêu chuẩn quốc tế đã được cộng đồng kiểm chứng:
1. **RCAEval Benchmark (WWW 2025 / RMIT)**:
   - 735 ca lỗi thực tế trên 3 hệ thống vi dịch vụ công nghiệp mã nguồn mở:
     - **Online Boutique** (Google Cloud Microservices Demo - 11 services, đa ngôn ngữ Go, C#, Node.js, Python, Java).
     - **Sock Shop** (Weaveworks - 13 services, Java/Spring Boot, Node.js, Go).
     - **Train Ticket** (Fudan University - 40+ microservices, mô phỏng luồng đặt vé phức tạp quy mô lớn).
   - Bao gồm 11 dạng lỗi thực tế: Ép tải CPU (CPU stress), Quá tải bộ nhớ (Memory stress), Nghẽn đĩa (Disk I/O), Trễ mạng (Network delay), Mất gói tin (Packet loss), Cạn kiệt socket, và các lỗi mã nguồn (Code-level faults).
2. **Quy trình xây dựng tập Warning Alert từ RCAEval**:
   - Sử dụng bộ lọc phân tích cú pháp log kết hợp từ điển mẫu để phân loại log thành 3 cấp độ: `INFO`, `WARNING`, `ERROR`.
   - Giai đoạn tiền sự cố (từ $T_{\text{inject}} - \text{window}$ đến $T_{\text{inject}}$) và giai đoạn suy thoái ban đầu trong $T_{\text{faulty}}$ được trích xuất để làm tập dữ liệu huấn luyện/kiểm thử cho bài toán Warning Alert Aggregation.

---

## 2.3. Hệ thống tiêu chí đánh giá khoa học (Evaluation Metrics)

Để đảm bảo tính khách quan và chống hiện tượng tối ưu hóa gian lận (metric gaming), đề tài thiết lập bộ 4 chỉ số đo lường toàn diện:

### 1. Tỷ lệ giảm cảnh báo (Alert Reduction Ratio - ARR)
Đo lường mức độ giảm tải thông báo cho kỹ sư SRE:
$$\text{ARR} = \left( 1 - \frac{N_{\text{groups}}}{N_{\text{raw\_alerts}}} \right) \times 100\%$$
*(Kỳ vọng: $\text{ARR} \ge 60\% - 80\%$ phản ánh đúng tỷ lệ nhiễu thực tế trong công nghiệp).*

### 2. Tỷ lệ bảo toàn nguyên nhân gốc (Root Cause Preservation Rate - RCPR)
Chỉ số an toàn vận hành quan trọng nhất — đảm bảo việc gom nhóm không làm thất lạc hoặc chôn vùi cảnh báo gốc của dịch vụ gây lỗi:
$$\text{RCPR} = \frac{\sum_{i=1}^{M} \mathbb{I}(\text{RootCauseAlert}_i \in \text{PrimaryGroup}_i)}{M} \times 100\%$$
*(Trong đó $M$ là tổng số ca sự cố có nhãn ground truth, $\mathbb{I}$ là hàm chỉ thị. Kỳ vọng bắt buộc: $\text{RCPR} \ge 95\%$).*

### 3. Chất lượng phân cụm cặp (Pairwise Grouping Precision, Recall, F1-Score)
Đánh giá độ chính xác của quyết định xếp hai cảnh báo $A_x$ và $A_y$ vào cùng một nhóm sự cố:
- **Pairwise Precision ($P_p$)**: Tỷ lệ các cặp cảnh báo được xếp chung nhóm thực sự có cùng nguyên nhân gốc.
- **Pairwise Recall ($R_p$)**: Tỷ lệ các cặp cảnh báo có cùng nguyên nhân gốc được thuật toán gom thành công vào cùng một nhóm.
- **Pairwise F1-Score ($F1_p$)**: Trung bình điều hòa giữa $P_p$ và $R_p$:
  $$F1_p = 2 \times \frac{P_p \times R_p}{P_p + R_p}$$

### 4. Độ tinh khiết cụm (Group Purity) và Độ trễ tính toán (Computational Latency)
- **Group Purity**: Đo lường mức độ đồng nhất về nguyên nhân bên trong mỗi nhóm cảnh báo tạo ra (tránh tình trạng gom gộp bừa bãi hai sự cố độc lập xảy ra đồng thời vào cùng một nhóm).
- **Processing Latency & Token Overhead**: Thời gian xử lý trung bình trên 100 cảnh báo (miligiây) và chi phí token LLM (đối với Arm 4) để chứng minh tính khả thi khi triển khai thời gian thực (Real-time Stream Processing).

---

# BẢNG PHÂN TÍCH HIỆN TRẠNG (FACT / INFERENCE / UNVERIFIED)

Theo chuẩn kiểm chứng thông tin và phương pháp luận NCKH:

- **FACT (Bằng chứng đã xác minh chính xác từ nguồn gốc)**:
  - Báo cáo Grafana Labs (2025) xác nhận 87% hệ thống dùng Log, độ phức tạp giám sát là rào cản #1 của 39% doanh nghiệp.
  - Báo cáo New Relic AI Impact (2026) chứng minh tỷ lệ cảnh báo nhiễu trong vận hành thực tế ở mức 63%-70%+.
  - Báo cáo PagerDuty (2020, 2026) ghi nhận 62% kỹ sư tăng giờ làm vì sự cố, chi phí downtime $\ge 300.000$ USD/giờ ở 68% tổ chức.
  - Khảo sát Microsoft/Omdia (2026) xác nhận 46% cảnh báo là false positive và 42% bị bỏ qua không điều tra.
  - Các công trình COLA (ICSE SEIP 2024), AlertGuardian (ASE 2025), RCAEval (WWW 2025) đã công bố và cung cấp mã nguồn/bài báo chuẩn.
- **INFERENCE (Suy luận hợp lý có căn cứ khoa học)**:
  - Việc chuyển dịch trọng tâm phân tích từ log `ERROR` sang log `WARNING` kết hợp tri thức đồ thị phụ thuộc (Topology) sẽ giúp giảm mạnh thời gian chết của hệ thống (MTTR) và ngăn ngừa sự cố bùng phát (Proactive SRE).
  - Kiến trúc lai (kết hợp Temporal-Spatial Filter ở tầng 1 và LLM Agent ở tầng 2) sẽ đạt điểm cân bằng tối ưu giữa độ chính xác phân cụm ($F1 > 0.90$) và chi phí tính toán chấp nhận được trong sản xuất.
- **UNVERIFIED (Các điểm cần thực nghiệm kiểm chứng trong giai đoạn CP2-CP3)**:
  - Phân bố tỷ lệ chính xác của log `WARNING` trên từng hệ thống cụ thể của RCAEval (Online Boutique vs Train Ticket) cần chạy mã nguồn trích xuất log parser thực tế để thống kê số liệu tuyệt đối.
  - Mức độ suy giảm chất lượng phân cụm của LLM khi không có tài liệu Runbook/SOP đi kèm cho từng dịch vụ cụ thể.

---

# DANH MỤC TÀI LIỆU THAM KHẢO (REFERENCES - APA 7th Edition)

1. Catchpoint. (2024). *The SRE Report 2024: Making IT Better*. Catchpoint Systems Inc. https://www.catchpoint.com/asset/2024-sre-report
2. Grafana Labs. (2025). *Observability Survey Report 2025: Key Findings from 1,255 Practitioners*. Grafana Labs. https://grafana.com/observability-survey/2025/
3. ITIC. (2024). *2024 Hourly Cost of Downtime Survey*. Information Technology Intelligence Consulting (ITIC Corp). https://itic-corp.com/itic-2024-hourly-cost-of-downtime-report/
4. Jalalvand, F., Tariq, S., Chhetri, M. B., Nepal, S., & Paris, C. (2024). Alert Prioritisation in Security Operations Centres: A Systematic Survey on Criteria and Methods. *ACM Computing Surveys*, *57*(2), 1–38. https://doi.org/10.1145/3695462
5. Kuang, J., Liu, J., Huang, J., Zhong, R., Gu, J., Yu, L., Tan, R., Yang, Z., & Lyu, M. R. (2024). Knowledge-aware Alert Aggregation in Large-scale Cloud Systems: A Hybrid Approach. In *Proceedings of the 46th IEEE/ACM International Conference on Software Engineering: Software Engineering in Practice (ICSE-SEIP 2024)* (pp. 303–314). ACM. https://doi.org/10.1145/3639477.3639745 (arXiv:2403.06485)
6. Mendes, E., & Petrillo, F. (2021). Log severity levels matter: A multivocal mapping. *arXiv preprint arXiv:2109.01192*. https://doi.org/10.48550/arXiv.2109.01192
7. Microsoft Security. (2026, February 17). *Unify now or pay later: New research exposes the operational cost of a fragmented SOC*. Microsoft Security Blog. https://www.microsoft.com/en-us/security/blog/2026/02/17/unify-now-or-pay-later-new-research-exposes-the-operational-cost-of-a-fragmented-soc/
8. New Relic. (2026). *2026 AI Impact Report: How AIOps is Solving the Firefighting Crisis for Engineers*. New Relic Inc. https://newrelic.com/blog/ai/new-relic-ai-impact-report-2026
9. PagerDuty. (2020). *PagerDuty Study Finds Pressure on Digital Services Increased by 80% Since Start of Pandemic*. PagerDuty Inc. https://www.pagerduty.com/newsroom/pagerduty-survey-pressure-digital-services-2020/
10. PagerDuty. (2026). *State of AI-First Operations Report 2026*. PagerDuty Inc. https://www.pagerduty.com/newsroom/2026-state-of-ai-first-operations/
11. Pham, L., Zhang, H., Ha, H., Salim, F., & Zhang, X. (2025). RCAEval: A Benchmark for Root Cause Analysis of Microservice Systems with Telemetry Data. In *Companion Proceedings of the ACM Web Conference 2025 (WWW Companion '25)*. ACM. https://doi.org/10.1145/3701716.3715290 (arXiv:2412.17015)
12. Prometheus Authors. (2026). *Alertmanager Configuration and Grouping Architecture*. The Linux Foundation / CNCF. https://prometheus.io/docs/alerting/latest/alertmanager/
13. Tariq, S., Chhetri, M. B., Nepal, S., & Paris, C. (2025). Alert Fatigue in Security Operations Centres: Research Challenges and Opportunities. *ACM Computing Surveys*, *57*(8), 1–36. https://doi.org/10.1145/3723158
14. Thurgood, S., Frame, J., Lenton, A., Quinito, C., Tolchanov, A., & Trdin, N. (2018). Alerting on SLOs. In B. Beyer, N. R. Murphy, D. K. Rensin, K. Kawahara, & S. Thorne (Eds.), *The Site Reliability Workbook: Practical Ways to Implement SRE* (Chapter 5). O'Reilly Media. https://sre.google/workbook/alerting-on-slos/
15. Vectra AI. (2023). *2023 State of Threat Detection Report*. Vectra AI Inc. https://www.vectra.ai/resources/2023-state-of-threat-detection
16. Wilkinson, J., & Guliani, K. (2016). Practical Alerting from Time-Series Data. In B. Beyer, C. Jones, J. Petoff, & N. R. Murphy (Eds.), *Site Reliability Engineering: How Google Runs Production Systems* (Chapter 10). O'Reilly Media. https://sre.google/sre-book/practical-alerting/
17. Yu, G., Mai, G., Wang, R., Li, R., Chen, P., Pan, L., & Xu, R. (2025). AlertGuardian: Intelligent Alert Life-Cycle Management for Large-scale Cloud Systems. In *Proceedings of the 40th IEEE/ACM International Conference on Automated Software Engineering (ASE 2025)*. ACM. https://doi.org/10.48550/arXiv.2601.14912
