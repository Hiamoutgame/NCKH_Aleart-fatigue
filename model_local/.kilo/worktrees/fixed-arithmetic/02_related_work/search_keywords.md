# Search Keywords — Alert Aggregation / LLM Agent / Microservices RCA

> Mục đích: tài liệu hóa từ khóa tìm kiếm để cậu tự research và tìm bài báo phù hợp.
> Sau khi tìm được bài, cập nhật vào `paper_list.md` và `literature_review_matrix.md`.

---

## 1. Phân loại từ khóa theo chủ đề

### 1A. Alert aggregation / alert correlation (trực tiếp nhất với đề tài)

```
alert aggregation microservices
alert correlation microservices
alert grouping root cause analysis
alert fatigue reduction SRE
alert noise reduction microservices
log-based alert aggregation
early-warning alert grouping
WARNING log clustering microservices
alert deduplication distributed system
alert storm management observability
```

### 1B. Root cause analysis — microservices (domain gần nhất)

```
root cause analysis microservices
root cause localization microservices logs
fault localization distributed system
microservice failure diagnosis
cascading failure detection microservices
RCA microservices machine learning
service dependency fault propagation
anomaly propagation microservices
```

### 1C. LLM agent / LLM for AIOps (phương pháp AI)

```
LLM agent AIOps
LLM-based alert triage
LLM log analysis
large language model fault diagnosis
LLM tool-calling observability
GPT log monitoring
chain-of-thought reasoning incident management
LLM root cause analysis
generative AI SRE operations
LLM-based alert correlation
```

### 1D. Semantic log clustering / log parsing (phương pháp AI phụ trợ)

```
log parsing Drain3 template extraction
sentence BERT log clustering
HDBSCAN log anomaly detection
semantic log grouping
log template clustering microservices
log embedding anomaly detection
SBERT log similarity
unsupervised log clustering
```

### 1E. AIOps / Observability (domain rộng hơn)

```
AIOps alert management
AIOps microservices observability
intelligent log monitoring
MLOps observability platform
AI-powered incident management
ML-based anomaly detection microservices
AI log analysis production system
automated incident triage
```

### 1F. Failure prediction / risk scoring (mục tiêu phụ — dự đoán lỗi tương lai)

```
failure prediction microservices machine learning
system failure forecasting logs
proactive fault detection microservices
failure likelihood estimation distributed system
log-based failure prediction
early warning system software failure
predictive anomaly detection microservices
uncertainty-aware failure prediction
```

---

## 2. Từ khóa theo nguồn tìm kiếm

### Google Scholar / IEEE Xplore / ACM DL

Ưu tiên các từ khóa tổ hợp với filter năm **2021–2025** và venue: ICSE, ASE, FSE, ISSRE, SOSP, OSDI, NSDI, SRE-related workshops.

```
"alert correlation" microservices 2022..2025
"alert aggregation" "root cause" logs site:ieeexplore.ieee.org
"log clustering" "root cause" microservices
"LLM" "alert" "microservices" 2023..2025
"AIOps" "alert noise" reduction
"WARNING log" aggregation fault localization
```

### arXiv (kỹ thuật mới nhất)

```
arxiv: cs.SE LLM alert AIOps
arxiv: cs.LG log clustering microservices
arxiv: cs.DC fault propagation cascading failure
```

### SpringerLink / ScienceDirect / MDPI

```
"microservice monitoring" "log analysis" AI
"alert fatigue" SRE machine learning
"observability" "root cause" LLM
```

### CEUR Workshop

```
AIOps workshop alert aggregation
log analysis workshop microservices fault
```

---

## 3. Bài báo đã có (seed — từ README hiện tại)

| ID | Tên bài | Venue | arXiv / DOI | Ghi chú |
|----|---------|-------|-------------|---------|
| S1 | COLA: Alert Correlation | ICSE-SEIP 2024 | arXiv:2403.06485 | Pairwise F1 0.901–0.930; cần 3,000 SOPs |
| S2 | AlertGuardian | ASE 2025 | arXiv:2601.14912 | ARR 94.8%; dataset không public |
| S3 | RCAEval | WWW 2025 Companion | arXiv:2412.17015 | 735 cases, MIT; không có alert ground truth |
| S4 | LEMMA-RCA | CIKM 2026 | arXiv:2406.05375 | Backup dataset; không có WARNING signal |
| S5 | Intelligent Logging and Monitoring Strategies | IJSTC (IJCDRA) | https://ijcdra.us/index.php/IJSTC/article/view/69 | Đang đọc — logging/monitoring domain |

---

## 4. Số lượng cần tìm theo format yêu cầu

| Loại | Yêu cầu | Đã có seed | Còn cần tìm |
|------|---------|------------|-------------|
| Bài liên quan trực tiếp | ≥ 5 | 4 (S1–S4) | ≥ 1 thêm |
| Bài về model AI / phương pháp AI | ≥ 3 | 1 (S2 dùng LLM) | ≥ 2 thêm |
| Bài về domain ứng dụng | ≥ 2 | 1 (S5) | ≥ 1 thêm |

> **Bước tiếp theo cho cậu:** Dùng các từ khóa ở mục 1 và 2, search trên Google Scholar / IEEE Xplore.
> Tìm được bài nào thì ghi vào `paper_list.md`. Khi có đủ danh sách mới điền `literature_review_matrix.md`.

---

## 5. Hướng dẫn đánh giá bài có phù hợp không

Bài **phù hợp** nếu đáp ứng ≥ 2 trong các tiêu chí:

- [ ] Đề cập microservices / distributed system / cloud-native
- [ ] Xử lý log, alert, hoặc metric từ production system
- [ ] Giải quyết alert noise, alert fatigue, hoặc alert grouping
- [ ] Dùng ML/LLM cho fault diagnosis, RCA, hoặc anomaly detection
- [ ] Có metric đo chất lượng grouping hoặc root-cause recall
- [ ] Xuất bản từ 2020 trở về sau (ưu tiên 2022–2025)

Bài **không phù hợp** nếu:

- Chỉ nói về network intrusion detection (khác domain)
- Chỉ nói về log compression / storage (không phải alert grouping)
- Không liên quan đến fault / failure / anomaly
