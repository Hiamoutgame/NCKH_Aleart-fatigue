# Paper 02 Summary

## Citation

- **Tên bài:** Nezha: Interpretable Fine-Grained Root Causes Analysis for Microservices on Multi-modal Observability Data
- **Tác giả:** Guangba Yu, Pengfei Chen, Yufeng Li, Hongyang Chen, Xiaoyun Li, Zibin Zheng
- **Năm:** 2023
- **Nguồn:** ESEC/FSE 2023, ACM
- **DOI/Link:** https://doi.org/10.1145/3611643.3616249

## Problem

**Root Cause Analysis — RCA** (phân tích nguyên nhân gốc — tìm lý do thực sự gây ra sự cố, không phải triệu chứng) trong hệ thống **microservices** (kiến trúc chia ứng dụng thành nhiều service nhỏ, độc lập, giao tiếp qua network) lớn khó vì dữ liệu quan sát rất nhiều và không đồng nhất. Paper chỉ ra 3 hạn chế chính của các phương pháp trước:

1. **Chưa khai thác tốt multi-modal data** (dữ liệu đa phương thức — kết hợp nhiều loại dữ liệu quan sát: metrics, traces, logs): nhiều phương pháp chỉ dùng riêng metrics, traces hoặc logs, trong khi một fault có thể chỉ biểu hiện rõ ở một số nguồn dữ liệu nhất định.
2. **Root cause còn quá coarse-grained** (thô — chỉ xác định ở mức service, không đi sâu vào bên trong service): nhiều phương pháp chỉ xác định service nghi ngờ, nên **SRE** (Site Reliability Engineer — kỹ sư phụ trách độ tin cậy, vận hành production) vẫn phải tiếp tục kiểm tra để tìm **code region** (vùng code gây lỗi) hoặc **resource type** (loại tài nguyên — CPU, memory, network, disk) gây lỗi.
3. **Khả năng giải thích còn yếu** (**interpretability** — SRE thấy được tại sao vị trí đó được kết luận là root cause): ví dụ PDiagnose chuyển log và trace thành time series nên mất **execution context** (bối cảnh thực thi — nội dung log, đường đi của request), khó giải thích lỗi xảy ra ở đâu và vì sao.

## Method

Nezha là phương pháp RCA **unsupervised** (không giám sát — không cần dữ liệu gắn nhãn để học), **interpretable** (kết quả kèm lý do) và **fine-grained** (mịn — xác định đến mức code region/resource type, không chỉ service). Ý tưởng cốt lõi: so sánh **event pattern** ở **fault-free phase** (giai đoạn bình thường, không có lỗi) với **fault-suffering phase** (giai đoạn đang có lỗi). Pipeline gồm:

1. **Anomaly Detector** (bộ phát hiện bất thường): theo dõi **success ratio** và **P90 latency** của front-end service bằng **quy tắc k-σ** (k = 3 mặc định; ngưỡng là μ ± kσ tính từ giai đoạn bình thường). Khi vượt ngưỡng thì kích hoạt RCA. Module này có thể thay bằng thuật toán khác (USAD, RRCF, JumpStarter).
2. **Data Integrator** — chuyển dữ liệu không đồng nhất về cùng một dạng **event** (sự kiện — đơn vị cơ bản của Nezha):
   - **Metrics:** không chuyển mọi metric. Chỉ các **system-level metric** vi phạm quy tắc k-σ hoặc ngưỡng tĩnh mới thành **alert event**. Alert nào cũng xuất hiện ở giai đoạn bình thường thì bị loại.
   - **Logs:** parse bằng **Drain** để lấy **log template**; mỗi log event kèm **trace ID**, **span ID** và timestamp (log phải được gắn trace ID/span ID trước).
   - **Traces:** mỗi span đồng bộ thành 2 event `_start` và `_end`; span bất đồng bộ thành event `_asyn`.
3. **Event graph construction:** với mỗi request tạo một **event graph** (đồ thị sự kiện — cạnh `e_j → e_j+1` nghĩa là `e_j` được theo sau bởi `e_j+1` khi thực thi): sắp xếp event trong cùng span theo timestamp, chèn alert event vào sau event đầu của service tương ứng, rồi chèn nhóm event của span con vào nhóm của span cha (dùng parent span ID cho lời gọi qua service để tránh lệch đồng hồ).
4. **Pattern Miner:** khai thác **pattern** (chuỗi event liền kề trong đồ thị) và đếm **support** `s(p)` ở cả hai giai đoạn; bỏ pattern có support < 5.
5. **Pattern Ranker:**
   - **Expected Ranker:** `Score_E(p) = s_C(p) / (s_C(p) + s_P(p))`. Pattern xuất hiện nhiều lúc bình thường nhưng ít lúc có lỗi sẽ điểm cao (nghi ngờ là root cause).
   - **Actual Ranker:** `Score_A(p) = s_P(p) / (s_C(p) + s_P(p))`. Pattern mới nổi lên lúc có lỗi sẽ điểm cao.
   - Chỉ giữ pattern có điểm ≥ `Score_min` = 0.67.
6. **Pattern Aggregator:** gộp các pattern dư thừa ở phía downstream (cùng một lỗi làm nhiều pattern đổi theo), rồi ghép mỗi **expected pattern** với **actual pattern** có chung tiền tố. Khi điểm bằng nhau, pattern nằm sâu hơn trong event graph được xếp trên, vì pattern nông dễ là do lan truyền lỗi.
7. **Output:** danh sách **root-cause candidate** gồm cặp (expected → actual) ở mức **code region** hoặc **resource type**, giúp SRE thấy "đáng lẽ chạy gì, thực tế chạy gì".

## Dataset

Paper không dùng dataset RCA có sẵn. Nhóm tác giả tự tạo dữ liệu từ 2 ứng dụng **microservices** mã nguồn mở:

- **OnlineBoutique (OB)** — hệ thống e-commerce microservices.
- **TrainTicket (TT)** — hệ thống đặt vé tàu microservices, khoảng 41 service.

Hai hệ thống được triển khai trên **Kubernetes** (12 máy ảo) và được bổ sung **observability** bằng **OpenTelemetry**: trace đầy đủ, và log được chèn trace ID/span ID. Dữ liệu thu thập:

- **Metrics:** system-level (cAdvisor, Node Exporter) và application-level (Istio), lưu trong Prometheus.
- **Traces:** lưu trong Grafana Tempo.
- **Logs:** thu thập bằng Promtail, lưu trong Loki.

Dữ liệu được tạo bằng **fault injection** (tiêm lỗi — chủ động gây lỗi để có ground truth). Mỗi lần tiêm một lỗi vào một service, kéo dài 3 phút:

- **OnlineBoutique:** 56 lỗi, gồm 42 **resource issues** và 14 **code defects**.
- **TrainTicket:** 45 lỗi, gồm 20 resource issues và 25 code defects.
- **Resource issues:** **CPU contention** (tranh chấp CPU) và **network jam** (nghẽn mạng).
- **Code defects:** **error return** (trả về lỗi) và **exception** (ngoại lệ).

Nhóm tác giả công khai hai ứng dụng đã tăng cường observability: **Augmented-OnlineBoutique** và **Augmented-TrainTicket** (GitHub IntelligentDDS).

## Evaluation

Paper đánh giá Nezha theo 3 câu hỏi:

- **RQ1:** hiệu quả RCA ở **service level**.
- **RQ2:** hiệu quả RCA ở **inner-service level** (code region hoặc resource type).
- **RQ3:** mức đóng góp của từng nguồn **multi-modal data** (ablation).

**Metric:**

- **AS@k** (top-k accuracy at service level): root-cause service có nằm trong top-k kết quả không.
- **AIS@k** (top-k accuracy at inner-service level): code region/resource type đúng có nằm trong top-k không.

**Baseline** (chỉ chọn phương pháp unsupervised):

- Dựa trên metrics: **MicroScope**, **MicroRCA**.
- Dựa trên logs: **SBLD**, **LogFaultFlagger**.
- Dựa trên traces: **MicroRank**, **TraceAnomaly**.
- Đa phương thức: **PDiagnose**.
- Ở inner-service level chỉ so với SBLD, LogFaultFlagger và PDiagnose vì chỉ ba phương pháp này xác định được mức đó.

**Ablation:** ba biến thể **Nezha w/o ML** (bỏ metrics và logs), **w/o M** (bỏ metrics), **w/o L** (bỏ logs).

## Results

- **Service level:** AS@1 là 92.86% (OB) và 86.67% (TT), trung bình khoảng 90%; hơn baseline 61.45%–74.63% ở AS@1.
- **Inner-service level:** AIS@1 trong bảng là 92.86% (OB) và 86.67% (TT), giống hệt AS@1; hơn baseline 67.47%–74.85% ở AIS@1.
- **Con số 89.77%** trong Abstract (top-1 trung bình, được gắn với mức code region/resource type) là trung bình đơn giản của hai giá trị 92.86% và 86.67%. Paper không nhất quán: phần Introduction gắn cùng con số này với mức service, còn phần RQ2 viết AIS@1 trung bình là 87%. Khi trích dẫn nên ghi "khoảng 90%" và nêu rõ là trung bình trên hai hệ thống.
- **Ablation:** cả metrics và logs đều đóng góp; bản đầy đủ tốt nhất, w/o ML kém nhất. Nezha w/o L tốt hơn ở OB (nhiều lỗi tài nguyên), w/o M tốt hơn ở TT (nhiều lỗi code). Ablation không bỏ trace; paper chỉ lập luận rằng trace là phần cốt lõi vì nối log giữa các service và dựng event graph.
- **Hiệu năng:** thời gian chẩn đoán tăng tuyến tính theo số event; với 50,000 event mất khoảng 16 giây (OB) và 30 giây (TT).
- **Độ nhạy:** `Score_min` = 0.67 cho kết quả tốt nhất, ổn định khi đặt trên 0.6.

## Limitations

- Nezha phụ thuộc vào **anomaly detector**: nếu fault không bị phát hiện thì RCA không được kích hoạt.
- Chỉ xử lý được fault tạo ra **abnormal pattern** trong dữ liệu đa phương thức. Các **byzantine fault** (ví dụ trả về kết quả vô lý cho người dùng) không bị phát hiện.
- Kết quả phụ thuộc chất lượng **fault-free data**: nếu thiếu loại request hoặc chứa nhiễu thì accuracy giảm.
- **Cần trace ID/span ID trong log.** Đây là điều kiện bắt buộc của bước tích hợp log với trace; paper tự nêu là mối đe dọa ngoại tại vì nhiều hệ thống thực tế chưa có.
- Chỉ đánh giá trên hai hệ thống benchmark chạy Kubernetes, chưa kiểm chứng trên hệ thống công nghiệp thực.
- Nezha không phải bài toán giảm cảnh báo, nên paper **không đánh giá** các metric của alert aggregation như **ARR** (Alert Reduction Ratio), **RCPR** (Root Cause Preservation Rate), **Pairwise F1** và **Group Purity**.

## Relevance to our topic

- **Liên quan cao về domain:** cùng nghiên cứu **microservices**, **observability** và **root cause analysis**; Nezha có xét **anomaly propagation** (lan truyền lỗi) khi xếp hạng và gộp pattern.
- **Liên quan về dữ liệu:** Nezha cho thấy chỉ dựa vào nội dung log là chưa đủ. **Trace** (quan hệ span cha–con) và **temporal/execution context** giúp phân biệt root cause với triệu chứng lan truyền. Lưu ý Nezha không dùng service topology tường minh mà dùng cấu trúc span của trace.
- **Điểm tương đồng với loại nhiễu Transient:** Nezha loại các metric alert cũng xuất hiện ở giai đoạn bình thường vì chúng không giúp RCA, tương tự cách đề tài xem cảnh báo xuất hiện trước `inject_time` là nhiễu.
- **Khác nhau về mục tiêu:** Nezha tìm root cause; đề tài giảm số alert phải xử lý nhưng vẫn giữ **root-cause signal**.
- **Khác nhau về output:** Nezha trả về code region/resource type; đề tài trả về alert group (alert đã gom).
- **Khác nhau về điều kiện dữ liệu:** Nezha cần log có trace ID/span ID. Bảng log RCAEval chỉ có `timestamp`, `container_name`, `message`; riêng log Sock Shop có chuỗi dạng `[carts,<trace>,<span>,false]` ngay trong message. Vì vậy **không thể tái hiện nguyên vẹn Nezha trên RCAEval**, chỉ dùng làm mốc so sánh khái niệm trong Related Work.
- **Gợi ý cho thiết kế baseline** *(suy luận của nhóm, không phải lập luận của paper)*: có thể lập luận rằng pipeline **semantic-only** nên được so sánh với các phiên bản có thêm tín hiệu **temporal** và **service topology**.
- **Gợi ý cho dataset design** *(suy luận của nhóm)*: cách chia fault-free/fault-suffering phase và dùng fault injection để có ground truth là cơ sở tham khảo khi xây dựng RCPR.

## Possible improvement

- Đưa ý tưởng **multi-modal context** của Nezha vào **alert aggregation**, thay vì chỉ dùng **semantic similarity** của log.
- Dùng **trace** hoặc **topology** để tránh gom nhầm alert của root cause với triệu chứng lan truyền.
- Thêm **root-cause-preserving constraint** (ràng buộc bảo toàn nguyên nhân gốc) khi gom nhóm: không được gộp mất alert gốc.
- Chỉ gọi **LLM** (Large Language Model) cho các **case khó**, tức khi semantic similarity, temporal signal và topology cho kết luận mâu thuẫn.
- Đánh giá **trade-off** giữa **ARR** và **RCPR**, thay vì chỉ đánh giá accuracy của RCA.
