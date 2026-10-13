# Bước 1 — Lĩnh vực ứng dụng và đề xuất đề tài

## 1. Thông tin đề tài

- **Tên đề tài dự kiến:** Gom nhóm cảnh báo từ early-warning logs theo hướng cost-aware và root-cause-preserving trong hệ thống microservices.
- **Lĩnh vực ứng dụng:** Vận hành hệ thống phần mềm (SRE/DevOps), giám sát hệ thống microservices.
- **Đối tượng người dùng:** Kỹ sư trực hệ thống (on-call engineer), kỹ sư SRE, DevOps engineer và đội vận hành hệ thống microservices.
- **Câu hỏi nghiên cứu trung tâm:** Có thể giảm tối đa bao nhiêu alert cần xử lý mà vẫn giữ được tín hiệu cần thiết để nhận diện service gây lỗi gốc, đồng thời chỉ sử dụng LLM ở những trường hợp thực sự khó?

## 2. Vấn đề thực tế

Khi một hệ thống microservices có bất thường, nhiều service có thể đồng thời sinh log `WARN`/`WARNING`. Kỹ sư vận hành phải đọc nhiều cảnh báo rời rạc, kể cả các cảnh báo lặp lại hoặc chỉ là hậu quả lan truyền của cùng một lỗi gốc. Điều này tạo ra **alert fatigue** (quá tải vì cảnh báo), làm chậm việc xác định và xử lý nguyên nhân gốc.

Cụ thể, phần lớn warning sinh ra trong một incident thuộc một trong các nhóm sau:

- **duplicated signal:** cùng một warning được phát lặp lại bởi cùng một service hoặc cùng một template log;
- **propagated symptom:** warning xuất hiện ở service downstream vì service upstream đã lỗi trước đó;
- **consequence của cùng một root cause:** nhiều warning khác template, khác service nhưng cùng bắt nguồn từ một lỗi gốc duy nhất.

Vì vậy mục tiêu nghiên cứu **không** phải là gom nhóm log cho tốt hơn về mặt kỹ thuật phân cụm. Mục tiêu thực tế gồm:

> **Mục tiêu chính:** Giảm số alert mà engineer phải xem nhưng vẫn giữ được tín hiệu cần thiết để nhận diện root-cause service.

> **Mục tiêu phụ (dự đoán rủi ro tương lai):** Từ trạng thái alert đã được gom nhóm, dựng model LLM dự đoán **xác suất xảy ra lỗi hệ thống trong tương lai gần** (khoang thời gian dự báo $\Delta_h$). Xác suất này được tính từ một công thức định lượng (Failure Likelihood Score), và độ tin cậy của dự đoán được kiểm chứng bằng proper scoring rule, thay vì bằng cảm quan của người vận hành.

## 3. Lý do cần tích hợp AI

Các cách gom cảnh báo theo rule tĩnh chỉ dựa vào nhãn hoặc thuộc tính cố định, nên khó hiểu hai log khác chữ nhưng cùng ngữ nghĩa, hoặc mối quan hệ giữa các service.

AI được dự kiến sử dụng để:

- nhận diện các log có nội dung tương tự sau khi chuẩn hóa;
- kết hợp thời điểm log xuất hiện và quan hệ phụ thuộc giữa service;
- hỗ trợ suy luận nhóm cảnh báo nào có liên quan đến cùng một nguyên nhân gốc.

AI ở đây được thiết kế theo hướng **cost-aware và root-cause-preserving**, không phải theo hướng "đưa toàn bộ alert qua LLM":

- LLM **không** được dùng mặc định cho mọi alert; chỉ những case mà pipeline không dùng LLM không đủ confidence mới được route sang LLM;
- lý do: khối lượng warning trong một incident lớn, chi phí token/API và độ trễ suy luận tăng theo số lần gọi LLM;
- rủi ro thứ hai là nếu nén quá mạnh mà không có ràng buộc, tín hiệu của service gây lỗi gốc có thể bị merge hoặc bị drop.

## 4. Model AI dự kiến

- **Pipeline semantic-only dự kiến:** `Drain3 → Sentence-BERT → HDBSCAN`.
  - Drain3: rút log thành template.
  - Sentence-BERT: biến nội dung log thành vector ngữ nghĩa.
  - HDBSCAN: gom các vector tương tự thành cụm.
- **Hướng nâng cao dự kiến:** mở rộng pipeline trên thành các baseline tăng dần, và thêm cơ chế phát hiện độ khó để chỉ gọi LLM khi cần.

### Các baseline dự kiến

- **A. Rule-based:** gom cảnh báo theo nhãn/thuộc tính tĩnh (ví dụ theo service, alert name, severity, cửa sổ thời gian).
- **B. Semantic-only:** `Drain3 → Sentence-BERT → HDBSCAN`.
- **C. Semantic + temporal:** thêm tín hiệu thời điểm xuất hiện của alert.
- **D. Semantic + temporal + service topology:** thêm quan hệ phụ thuộc giữa các service.
- **E. Proposed approach:** `Semantic + temporal + topology → uncertainty/difficulty detection → selective LLM`.

> LLM KHÔNG được sử dụng mặc định cho toàn bộ alert.

### Định nghĩa "trường hợp khó"

Một case được coi là **difficult/ambiguous** khi pipeline không dùng LLM không đủ confidence để quyết định grouping hoặc reduction mà có nguy cơ làm mất root-cause information. Các tín hiệu có thể dùng để nhận diện difficult case:

- **Semantic ambiguity:** một alert có similarity gần tương đương với từ 2 cluster trở lên.
- **Cluster uncertainty:** ví dụ HDBSCAN đánh dấu alert là noise, hoặc membership confidence/probability thấp.
- **Topology conflict:** semantic similarity cho rằng hai alert cùng nhóm nhưng service topology không cho thấy quan hệ dependency hợp lý.
- **Temporal conflict:** các alert giống nhau về nội dung nhưng timing không ủng hộ giả thuyết chúng thuộc cùng một incident/root cause.
- **Root-cause preservation risk:** một alert chuẩn bị bị merge/drop nhưng có khả năng là tín hiệu duy nhất còn lại của service gây lỗi gốc.
- **Cross-service ambiguity:** nhiều service đồng thời phát warning và pipeline hiện tại chưa phân biệt được cause với propagated symptom.
- **Novel/unseen template:** log template mới hoặc nằm xa các cluster đã biết.

### Difficulty / uncertainty score

Cơ chế định lượng đề xuất để route difficult case sang LLM, dạng conceptual:

```text
D = w1 * semantic_uncertainty
  + w2 * cluster_uncertainty
  + w3 * topology_conflict
  + w4 * root_cause_risk
```

Nếu `D > threshold` thì case được route sang LLM; nếu `D <= threshold` thì pipeline thông thường tự xử lý.

> Đây là proposed design/hypothesis. Chưa khẳng định threshold tối ưu, trọng số tối ưu hay công thức cuối cùng khi chưa có thực nghiệm.

### Vai trò của LLM

LLM chỉ xử lý difficult/ambiguous cases. Khi cần, LLM có thể được cấp tool để tra cứu:

- related alerts;
- service dependency/topology;
- incident timeline;
- runbook nếu dataset/repository có.

LLM có thể hỗ trợ quyết định: **merge**, **keep separate**, hoặc **uncertain**.

### Định nghĩa cost-aware

Cost-aware không được hiểu đơn giản là "dùng model/API rẻ". Cost cần xem xét tối thiểu gồm: số alert engineer còn phải xử lý, số lần gọi LLM, token/API cost, processing latency, và chi phí/risk nếu làm mất root-cause signal. Conceptual objective:

```text
Total Cost =
    alert handling cost
  + LLM invocation cost
  + processing latency
  + root-cause-loss penalty
```

> Đây chỉ là conceptual formulation. Không tự ý khẳng định trọng số hoặc công thức cuối cùng nếu chưa có thực nghiệm chứng minh.

> Chưa chọn model LLM/API cụ thể và chưa có code chạy AI trong `src`.

## 5. Kết quả mong muốn

### Primary objectives

- Tối đa hóa **Alert Reduction Rate (ARR)** — mục tiêu hiện tại **ARR ≥ 60%**.
- Duy trì **Root Cause Preservation Rate (RCPR)** ở mức cao — mục tiêu hiện tại **RCPR ≥ 95%**: không làm mất tín hiệu service gây lỗi gốc.

### Supporting clustering metrics

- **Pairwise F1** — mục tiêu hiện tại **≥ 0.85**.
- **Group Purity** — mục tiêu hiện tại **≥ 0.80**.

> Pairwise F1 và Group Purity là **chỉ số hỗ trợ** để kiểm chứng chất lượng gom nhóm, **không phải mục tiêu cuối cùng** của hệ thống. Mục tiêu cuối cùng là giảm alert mà vẫn bảo toàn root-cause signal. Hai chỉ số này cũng dùng để chặn lạm dụng ARR: gom quá thô có thể làm ARR rất cao nhưng Group Purity rất thấp.

Bốn chỉ số trên đều là **target metric**, không phải kết quả đã đo được.

### Câu hỏi thực nghiệm cần trả lời

- **RQ1.** ARR tối đa đạt bao nhiêu nếu yêu cầu RCPR ≥ 95%?
- **RQ2.** Selective LLM có cải thiện RCPR hoặc grouping quality so với pipeline không dùng LLM hay không?
- **RQ3.** Bao nhiêu phần trăm case thực tế phải gọi LLM?
- **RQ4.** Selective LLM giảm bao nhiêu token/API cost so với LLM-all?
- **RQ5.** Difficulty threshold ảnh hưởng như thế nào đến trade-off giữa ARR, RCPR, clustering quality và LLM cost?

### Thiết kế so sánh dự kiến

- A. Rule-based baseline.
- B. Semantic-only.
- C. Semantic + temporal + topology.
- D. C + selective LLM.
- E. Optional upper-bound: LLM xử lý toàn bộ ambiguous cases, hoặc LLM-all nếu tài nguyên cho phép.

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

- Sinh alert chuẩn từ log WARNING.
- Các baseline gom nhóm rule-based, semantic-only và temporal-spatial chạy thật.
- Service dependency/topology graph.
- LLM agent, tool-calling và runbook.
- Tính các metric ARR, RCPR, Pairwise F1, Group Purity.

> Các thành phần trong mục này chưa triển khai, do đó chưa có kết quả thực nghiệm nào cho chúng.

## 8. Kết luận trạng thái Bước 1

Nội dung đề xuất đề tài, lĩnh vực, vấn đề, người dùng, lý do dùng AI và kết quả kỳ vọng đã được xác định. Pipeline mã nguồn hiện mới hoàn thành phần **kiểm chứng và tiền xử lý dữ liệu**; phần **AI gom nhóm cảnh báo** vẫn là các bước triển khai tiếp theo.

### Expected contribution

1. Một pipeline alert reduction có ràng buộc root-cause preservation.
2. Một cơ chế difficulty/uncertainty-aware routing để chỉ gọi LLM khi pipeline thông thường không đủ confidence.
3. Một experimental analysis về trade-off giữa Alert Reduction ↔ Root Cause Preservation ↔ LLM/Computational Cost.

> Contribution không được mô tả đơn giản là "dùng LLM để gom log".

### Quy tắc khoa học áp dụng cho tài liệu này

Tài liệu phân biệt rõ bốn loại thông tin:

1. **Current implementation:** những gì repository đã thật sự có (mục 6).
2. **Proposed design:** những gì đang được thiết kế, chưa chạy (mục 4, mục 5 — thiết kế so sánh).
3. **Research hypothesis:** các giả thuyết cần kiểm chứng bằng thực nghiệm (cơ chế difficulty routing, hiệu quả của selective LLM).
4. **Target metric:** các ngưỡng mục tiêu ARR ≥ 60%, RCPR ≥ 95%, Pairwise F1 ≥ 0.85, Group Purity ≥ 0.80.

> Không có kết quả thực nghiệm nào được tạo ra trong tài liệu này. Chưa khẳng định model LLM cụ thể, API cụ thể, threshold cụ thể, optimal weights hay kết quả metric khi repository hoặc thí nghiệm chưa chứng minh.
