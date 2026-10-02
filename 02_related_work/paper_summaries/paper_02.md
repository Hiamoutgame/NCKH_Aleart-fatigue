# Paper 02 Summary

## Citation

- **Tên bài:** Nezha: Interpretable Fine-Grained Root Causes Analysis for Microservices on Multi-modal Observability Data
- **Tác giả:** Guangba Yu, Pengfei Chen, Yufeng Li, Hongyang Chen, Xiaoyun Li, Zibin Zheng
- **Năm:** 2023
- **Nguồn:** ESEC/FSE 2023, ACM
- **DOI/Link:** https://doi.org/10.1145/3611643.3616249

## Problem

**Root Cause Analysis — RCA** (phân tích nguyên nhân gốc — tìm lý do thực sự gây ra sự cố, không phải triệu chứng) trong hệ thống **microservices** (kiến trúc chia ứng dụng thành nhiều service nhỏ, độc lập, giao tiếp qua network) lớn khó vì dữ liệu quan sát rất nhiều và phân tán. Paper chỉ ra 3 hạn chế chính của các phương pháp trước:

1. **Chưa khai thác tốt multi-modal data** (dữ liệu đa phương thức — kết hợp nhiều loại dữ liệu quan sát: metrics, traces, logs): nhiều phương pháp chỉ dùng riêng metrics, traces hoặc logs, trong khi một fault có thể chỉ biểu hiện rõ ở một số nguồn dữ liệu nhất định.
2. **Root cause còn quá coarse-grained** (thô — chỉ xác định ở mức service, không đi sâu vào bên trong service): nhiều phương pháp chỉ xác định service nghi ngờ, nên **SRE** (Site Reliability Engineer — kỹ sư phụ trách độ tin cậy, vận hành production) vẫn phải tiếp tục kiểm tra để tìm **code region** (vùng code — hàm/file cụ thể gây lỗi) hoặc **resource type** (loại tài nguyên — CPU, memory, network, disk) gây lỗi.
3. **Khả năng giải thích còn yếu** (**interpretability** — tính dễ hiểu, SRE thấy được tại sao vị trí đó được kết luận là root cause): một số phương pháp tìm được vị trí nghi ngờ nhưng không cho SRE thấy rõ **execution context** (bối cảnh thực thi — luồng request đi qua các service nào, gọi hàm nào, bao lâu).

## Method

Nezha là một phương pháp RCA **unsupervised** (không giám sát — không cần dữ liệu đã gắn nhãn trước để học), **interpretable** (dễ hiểu — kết quả kèm lý do) và **fine-grained** (mहीn — xác định đến mức code region/resource type, không chỉ service). Pipeline chính gồm:

1. **Multi-modal data transformation:** chuyển **metrics** (chỉ số định kỳ — CPU%, latency, error rate...), **traces** (dấu vết phân tán — theo dõi một request đi qua nhiều service, có **trace ID** và **span ID**), và **logs** (nhật ký sự kiện — log message có gắn trace ID/span ID) về cùng một dạng **event** (sự kiện — đơn vị thống nhất: what, where, when).
2. **Event graph construction:** liên kết các event theo timestamp, trace ID và span ID để tạo **event graph** (đồ thị sự kiện — node là event, edge là quan hệ trước/sau hoặc gọi/gọi ngược) cho từng request.
3. **Event pattern extraction:** khai thác các **execution pattern** (mẫu thực thi — chuỗi event lặp lại đặc trưng cho một loại request) xuất hiện trong event graph.
4. **Fault comparison:** so sánh pattern giữa **fault-free phase** (giai đoạn bình thường — không có fault inject) và **fault-suffering phase** (giai đoạn có fault — đang inject lỗi).
5. **Root cause localization:** tìm các **expected pattern** (pattern kỳ vọng — pattern bình thường nên có) bị thiếu hoặc thay đổi, đồng thời tìm các **actual pattern** (pattern thực tế — pattern xuất hiện khi có fault) mới xuất hiện khi lỗi xảy ra.
6. **Output:** trả về danh sách **root-cause candidate** (ứng viên nguyên nhân gốc) ở mức **code region** hoặc **resource type**, kèm thông tin giúp SRE hiểu vì sao pattern đó bất thường.

## Dataset

Paper không sử dụng một dataset RCA có sẵn theo kiểu train/test truyền thống. Nhóm tác giả tự tạo dữ liệu thực nghiệm từ 2 ứng dụng **microservices** mã nguồn mở:

- **OnlineBoutique** — hệ thống e-commerce microservices (Google Cloud demo app).
- **TrainTicket** — hệ thống đặt vé tàu microservices (Fudan University demo app).

Hai hệ thống được deploy trên **Kubernetes** (hệ điều phối container — quản lý deploy, scaling, network cho microservices) và bổ sung **observability** (khả năng quan sát — metrics + traces + logs) bằng **OpenTelemetry** (framework vendor-neutral thu thập telemetry data).

Nhóm tác giả thu thập:

- **Metrics:** system-level và application-level metrics.
- **Traces:** distributed traces có trace ID và span ID.
- **Logs:** application logs được gắn trace ID/span ID để liên kết với trace.

Dataset được tạo bằng **fault injection** (tiêm lỗi — chủ động gây ra lỗi vào hệ thống để tạo ground truth):

- **OnlineBoutique:** 56 faults gồm 42 **resource issues** (vấn đề tài nguyên — CPU contention, memory leak, network jam...) và 14 **code defects** (lỗi code — exception, error return, logic bug...).
- **TrainTicket:** 45 faults gồm 20 resource issues và 25 code defects.
- Fault chính gồm **CPU contention** (đ쟁 CPU — nhiều process争夺 CPU), **network jam** (tắc nghẽn mạng), **error return** (trả về lỗi), và **exception** (ngoại lệ).
- Mỗi fault được inject vào một microservice và duy trì khoảng 3 phút.

Nhóm tác giả cũng công khai các phiên bản đã tăng cường observability của hai application tại repository **Augmented-OnlineBoutique** và **Augmented-TrainTicket**.

## Evaluation

Paper đánh giá Nezha theo 3 câu hỏi chính:

- Hiệu quả RCA ở **service level** (mức service — xác định service nào bị lỗi).
- Hiệu quả RCA ở **inner-service level** (mức bên trong service — code region hoặc resource type).
- Mức đóng góp của từng nguồn **multi-modal data**.

**Metric chính:**

- **Top-k accuracy at service level:** **root-cause service** (service gây ra lỗi gốc) có nằm trong top-k kết quả hay không.
- **Top-k accuracy at inner-service level:** **code region**/**resource type** đúng có nằm trong top-k kết quả hay không.

**Các baseline** (phương pháp so sánh — baseline là phương pháp hiện có dùng làm mốc so sánh) gồm những phương pháp RCA dựa trên metrics, logs và traces như **MicroScope**, **MicroRCA**, **SBLD**, **LogFaultFlagger**, **MicroRank**, **TraceAnomaly** và **PDiagnose**.

## Results

- **Top-1 accuracy trung bình khoảng 89.77%** khi xác định root cause ở mức **fine-grained**.
- Nezha vượt các **baseline** trong cả **service-level RCA** và **inner-service-level RCA**.
- **Ablation study** (thử nghiệm loại bỏ — bỏ từng thành phần để xem đóng góp của nó) cho thấy cả metrics, logs và traces đều có đóng góp; hiệu quả tốt nhất đạt được khi sử dụng đầy đủ **multi-modal data**.
- **Trace** đặc biệt quan trọng vì giúp liên kết logs giữa nhiều service và giữ **execution context** của request.

## Limitations

- Nezha phụ thuộc vào **anomaly detector** (bộ phát hiện bất thường — module quyết định có fault hay không trước khi chạy RCA); nếu fault không bị anomaly detector phát hiện thì RCA cũng không chạy.
- Phương pháp chỉ hiệu quả khi fault tạo ra sự thay đổi có thể quan sát trong metrics, traces hoặc logs.
- Một số fault không làm thay đổi **observable pattern** (mẫu quan sát được — pattern thay đổi trong metrics/traces/logs) có thể bị bỏ sót.
- Kết quả phụ thuộc vào chất lượng **fault-free data**; nếu dữ liệu bình thường thiếu **request type** (loại request — ví dụ: login, checkout, search...) hoặc chứa nhiều **noise** (nhiễu — dữ liệu không liên quan, ngẫu nhiên) thì accuracy có thể giảm.
- Paper **không đánh giá các metric phục vụ bài toán alert reduction** như **ARR** (Alert Reduction Rate — tỷ lệ giảm cảnh báo: (số alert trước - số alert sau) / số alert trước), **RCPR** (Root Cause Preservation Rate — tỷ lệ bảo toàn nguyên nhân gốc: % alert gốc của root cause vẫn còn sau khi gom nhóm), **Pairwise F1** (F1-score cặp — đo độ chính xác gom cặp alert: precision/recall trên từng cặp alert có cùng group không), **Group Purity** (độ tinh khiết nhóm — % alert trong một group thực sự thuộc cùng một root cause).

## Relevance to our topic

- **Liên quan cao về domain:** cùng nghiên cứu **microservices**, **observability**, **fault propagation** (lan truyền lỗi — lỗi từ service A gây lỗi service B, C...) và **root cause analysis**.
- **Liên quan cao về dữ liệu:** Nezha cho thấy chỉ dựa vào **log text** (nội dung log) là chưa đủ; **trace**, **topology** (tổ chức mạng service — ai gọi ai) và **temporal/execution context** (bối cảnh thời gian/thực thi) có thể giúp phân biệt **root cause** với **propagated symptom** (triệu chứng lan truyền — alert ở service downstream do service upstream lỗi, không phải gốc).
- **Khác nhau về mục tiêu:** Nezha cố gắng tìm **root cause**, còn đề tài hiện tại cố gắng giảm số alert phải xử lý nhưng vẫn giữ **root-cause signal** (tín hiệu nguyên nhân gốc — alert chứa thông tin về root cause).
- **Khác nhau về output:** Nezha trả về **code region**/**resource type**; đề tài hiện tại trả về **alert groups** / **reduced alerts** (alert đã gom nhóm, giảm số lượng).
- **Có giá trị cho thiết kế baseline:** Nezha hỗ trợ lập luận rằng pipeline **semantic-only** (chỉ dùng độ tương đồng ngữ nghĩa log) nên được so sánh với các phiên bản có thêm **temporal** (thời gian) và **service topology**.
- **Có giá trị cho dataset design:** cách chia **fault-free/fault-suffering phase** và dùng **fault injection** để xác định **ground truth** (nhãn thật — root cause thực tế đã biết trước khi inject) rất phù hợp để tham khảo khi xây dựng **RCPR**.

## Possible improvement

- Kết hợp ý tưởng **multi-modal context** của Nezha vào **alert aggregation** (gom nhóm cảnh báo) thay vì chỉ dùng **semantic similarity** (độ tương đồng ngữ nghĩa — so sánh embedding log text) của log.
- Dùng **trace**/**topology** để tránh **merge nhầm root-cause alert với propagated symptoms**.
- Bổ sung cơ chế **root-cause-preserving constraint** (ràng buộc bảo toàn nguyên nhân gốc — khi gom nhóm, bắt buộc giữ alert gốc của root cause) khi thực hiện **alert reduction**.
- Chỉ dùng **LLM** (Large Language Model — mô hình ngôn ngữ lớn) cho các **case khó** (trường hợp khó — semantic similarity, temporal signal và topology đưa ra kết luận mâu thuẫn).
- Đánh giá **trade-off** (sự đánh đổi) giữa **Alert Reduction Rate (ARR)** và **Root Cause Preservation Rate (RCPR)** thay vì chỉ đánh giá RCA accuracy.
