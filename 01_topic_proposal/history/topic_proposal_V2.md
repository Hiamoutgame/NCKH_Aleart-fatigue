# Topic Proposal

## 1. Group Information

- Class: SE1922
- Leader: _(chưa điền)_
- Members: _(chưa điền)_

## 2. Proposed Title

English title: Log-based Root Cause Analysis and Near-Future Failure Prediction for Microservice Systems

Vietnamese title: Phân tích nguyên nhân gốc và dự đoán lỗi gần tương lai trong hệ thống microservices dựa trên log

## 3. Application Domain

Vận hành hệ thống phần mềm (SRE/DevOps), giám sát hệ thống microservices.

## 4. Problem Statement

Khi một hệ thống microservices có bất thường, các service sinh ra lượng lớn log ở mức INFO, WARN và ERROR. Kỹ sư vận hành phải đọc hàng nghìn dòng log rời rạc, trong đó phần lớn là lặp lại, là hậu quả lan truyền, hoặc là thông tin thường ngày không liên quan đến lỗi. Việc này dẫn đến hai vấn đề:

- **Alert fatigue (quá tải cảnh báo):** quá nhiều log khiến engineer không kịp phân biệt signal với noise.
- **Chậm xác định nguyên nhân gốc (RCA):** log gốc gây lỗi bị lẫn trong đống log lan truyền và log routine.

Cụ thể, log sinh ra trong một incident thường thuộc các nhóm:

- **duplicated signal:** cùng một log template lặp lại nhiều lần bởi cùng service.
- **propagated symptom:** log xuất hiện ở service downstream vì service upstream đã lỗi trước đó.
- **routine noise:** log health check, periodic info, heartbeat không liên quan đến fault.

Câu hỏi nghiên cứu trung tâm: Có thể từ log INFO/WARN/ERROR của hệ thống microservices, sau khi gom nhóm và lọc tín hiệu, xác định được root-cause candidate và dự đoán được nguy cơ lỗi gần tương lai hay không?

## 5. Motivation

1. **Log quá nhiều, signal bị chìm:** một incident có thể sinh hàng nghìn dòng log từ nhiều service, phần lớn là noise hoặc symptom lan truyền, khiến engineer mất thời gian tìm log gốc gây lỗi.
2. **Rule-based không đủ:** gom log theo rule tĩnh (service name, severity, keyword) không phân biệt được hai log khác chữ nhưng cùng ngữ nghĩa, hoặc root cause với propagated symptom.
3. **RCA hiện tại thường quá thô:** nhiều phương pháp chỉ xác định service nghi ngờ, chưa chỉ ra log template hoặc resource cụ thể gây lỗi.
4. **Cần cảnh báo sớm:** nếu chỉ phát hiện lỗi khi service đã chết thì quá muộn. Cần dự đoán fault type và thời gian ước lượng trước khi service suy giảm để engineer kịp hành động.
5. **Chưa có pipeline end-to-end từ log → RCA → prediction:** hầu hết các công trình hiện tại tập trung vào một trong ba bước (log parsing, RCA, hoặc failure prediction) riêng lẻ, chưa kết nối thành pipeline liền mạch.

## 6. Target Users

- Kỹ sư trực hệ thống (on-call engineer).
- Kỹ sư SRE (Site Reliability Engineer).
- DevOps engineer.
- Đội vận hành hệ thống microservices.

## 7. Proposed AI Model / Method

Pipeline đề xuất gồm 5 bước:

```text
(1) Log Collection
    gom INFO + WARN + ERROR từ microservices
         ↓
(2) Log Parsing + Clustering
    template extraction (Drain/Spell)
    hoặc semantic embedding clustering
         ↓
(3) Signal Filtering
    giữ cụm bất thường (frequency spike, new template, resource-related)
    bỏ cụm routine (health check, periodic info)
         ↓
(4) Root-Cause Candidate Ranking
    so sánh log pattern bình thường vs bất thường
    rank service + log template đáng nghi nhất
    dùng ERROR log làm validation signal
         ↓
(5) Failure Prediction
    từ root-cause candidate + log trend
    dự đoán fault type + thời gian tới lỗi
    output: risk score + estimated time-to-failure
```

Các model/method dự kiến:

- **Log parsing:** Drain3 / Spell — rút log thành template.
- **Embedding model:** Sentence-BERT — biến log/template thành vector ngữ nghĩa.
- **Clustering:** HDBSCAN — gom các vector tương tự thành cụm.
- **RCA ranking:** so sánh cụm log giai đoạn bình thường vs bất thường để xếp hạng root-cause candidate.
- **Failure prediction:** dùng root-cause candidate, xu hướng tần suất log và đặc trưng thời gian để dự đoán fault type và estimated time-to-failure. Có thể dùng LSTM, XGBoost hoặc LLM tùy thực nghiệm.

> LLM nếu dùng sẽ đóng vai trò hỗ trợ giải thích hoặc xử lý case khó, không thay thế toàn bộ pipeline.

## 8. System Features

Các chức năng chính của hệ thống:

1. **Log Collection & Parsing:** thu thập log INFO/WARN/ERROR từ nhiều microservice, parse thành template chuẩn.
2. **Log Clustering & Signal Filtering:** phân cụm log theo ngữ nghĩa hoặc template, lọc bỏ noise (health check, periodic info), giữ cụm bất thường.
3. **Root-Cause Candidate Ranking:** so sánh log pattern bình thường vs bất thường, xếp hạng service + log template đáng nghi nhất, dùng ERROR log làm validation signal.
4. **Failure Prediction & Early Warning:** dự đoán fault type (DB overload, server overload, node failure...) và estimated time-to-failure, đưa ra risk score và cảnh báo sớm cho engineer.

## 9. Expected Contribution

Đóng góp dự kiến:

1. Một pipeline log-based RCA gồm log parsing, clustering, signal filtering và root-cause candidate ranking cho hệ thống microservices.
2. Một failure prediction module dự đoán fault type và estimated time-to-failure từ log trend và RCA signal.
3. Một experimental analysis so sánh các baseline về Top-k RCA accuracy, Prediction F1/AUC, lead time và false alarm rate.

> Đóng góp không được mô tả đơn giản là "dùng AI để gom log" hay "dùng LLM để tìm root cause".

## 10. Evaluation Plan

### Dataset

- Dự kiến dùng log từ hệ thống microservices mã nguồn mở có fault injection (ví dụ: OnlineBoutique, TrainTicket, hoặc dataset từ RCAEval).
- Log gồm INFO, WARN, ERROR với timestamp, service name.
- Ground truth được xác định từ fault injection (biết trước lỗi inject ở service nào, fault type nào).

### Baseline

- A. Rule-based (gom theo service + severity + time window).
- B. Template-only (Drain3/Spell + template frequency).
- C. Semantic clustering (Drain3/Spell + Sentence-BERT + HDBSCAN).
- D. Semantic + temporal (C + frequency trend + time window).
- E. Proposed approach (D + signal filtering + RCA ranking + failure prediction).

### Metrics

- **Top-1 accuracy** ≥ 70%, **Top-3 accuracy** ≥ 85% — root-cause service/template đúng nằm trong top-k kết quả.
- **Prediction F1** ≥ 0.70, **AUC** ≥ 0.75 — dự đoán đúng fault type gần tương lai.
- **Lead time** ≥ 5 phút — cảnh báo sớm trước khi service thật sự suy giảm.
- **Signal Filtering Rate** — tỉ lệ log noise bị loại, giám sát để đảm bảo không loại mất root-cause signal.
- **False Alarm Rate** — tỉ lệ dự đoán sai, càng thấp càng tốt.

> Các chỉ số trên đều là target metric, không phải kết quả đã đo được.

### Research Questions

- **RQ1.** Signal filtering giảm được bao nhiêu log noise mà không làm mất root-cause signal?
- **RQ2.** Log clustering + temporal signal có cải thiện RCA accuracy so với template-only hoặc rule-based không?
- **RQ3.** Pipeline đề xuất có đạt Top-1/Top-3 RCA accuracy tốt hơn các baseline không?
- **RQ4.** Prediction module dự đoán fault type và time-to-failure với F1/AUC và lead time như thế nào?
- **RQ5.** ERROR log khi dùng làm validation signal có cải thiện RCA accuracy so với khi bỏ ERROR?

### Expert evaluation

- _(chưa xác định — có thể mời SRE/DevOps engineer đánh giá tính hữu ích của output)_

### User survey

- _(chưa xác định)_

## 11. Related Papers

| No  | Title                                                                                                      | Year | Source             | Link / DOI                                                                       |
| --- | ---------------------------------------------------------------------------------------------------------- | ---- | ------------------ | -------------------------------------------------------------------------------- |
| 1   | Nezha: Interpretable Fine-Grained Root Causes Analysis for Microservices on Multi-modal Observability Data | 2023 | ESEC/FSE 2023, ACM | https://doi.org/10.1145/3611643.3616249                                          |
| 2   | Intelligent Logging and Monitoring Strategies                                                              | 2026 | IJSTC Vol. 8 No. 8 | https://ijcdra.us/index.php/IJSTC/article/view/69                                |
| 3   | Drain: An Online Log Parsing Approach with Fixed Depth Tree                                                | 2017 | IEEE ICWS 2017     | https://www.computer.org/csdl/proceedings-article/icws/2017/0752a033/12OmNBInLkZ |
| 4   | Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks                                             | 2019 | EMNLP-IJCNLP 2019  | https://doi.org/10.18653/v1/D19-1410                                             |
| 5   | Density-Based Clustering Based on Hierarchical Density Estimates                                           | 2015 | ACM TKDD           | https://doi.org/10.1145/2733381                                                  |
