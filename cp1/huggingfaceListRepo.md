# Danh sách Dataset HuggingFace — Đã Chốt

> Cập nhật: 2026-09-18 | CP1 — Tuần 1

---

## 1. ⭐ Dataset Chính: RCAEval

| Field | Value |
|---|---|
| **HF URL** | https://huggingface.co/datasets/phamquiluan/RCAEval |
| **GitHub** | https://github.com/phamquiluan/RCAEval |
| **Paper** | RCAEval: A Benchmark for Root Cause Analysis of Microservice Systems with Telemetry Data |
| **Venue** | WWW 2025 (arXiv:2412.17015), also ASE'24, FSE'26 |
| **License** | MIT ✅ |
| **Size** | 735 failure cases |
| **Systems** | Online Boutique, Sock Shop, Train Ticket |
| **Modality** | Log + Metric + Trace + Root Cause Label |
| **Format** | Parquet (cases config, 1 split: train) |
| **Keywords** | root-cause-analysis, microservices, observability, aiops, telemetry, anomaly-detection |
| **Creator** | Luan Pham (phamquiluan) |

### Schema (Parquet fields per case)

```
case, dataset, suite, system, system_name,
root_cause_service, fault, fault_description,
repetition, inject_time,
n_metrics, n_timesteps, time_start, time_end, duration_minutes,
normal_timesteps, faulty_timesteps,
has_logs, n_logs, has_traces, n_traces, has_root_cause_file
```

### Lý do chọn làm dataset chính
- **735 ca lỗi** từ 3 microservice thật (public, tái lập được)
- Có **log + metric + trace + nhãn root cause** → đa modal, đủ cho agent tool-calling
- Paper đi kèm có **15 baseline** (bao gồm rule-based, graph-based, RL) → dễ so sánh
- License MIT → không cản trở publish
- 3 hệ thống benchmark đều là **microservice mẫu phổ biến** (Online Boutique của Google, Sock Shop của Weaveworks, Train Ticket) → topology đã public, build được dependency table cho tool-2

---

## 2. Dataset Backup: LEMMA-RCA / Product_Review_Original

| Field | Value |
|---|---|
| **HF URL** | https://huggingface.co/datasets/Lemma-RCA-NEC/Product_Review_Original |
| **Paper** | LEMMA-RCA: A Large Multi-modal Multi-domain Dataset for Root Cause Analysis |
| **Authors** | Lecheng Zheng, Zhengzhang Chen, Dongjie Wang, Chengyuan Deng, Reon Matsuoka, Haifeng Chen (NEC) |
| **License** | CC-BY-NC-4.0 ⚠️ (non-commercial) |
| **Size** | 100M < n < 1B (large-scale) |
| **System** | Product Review Microservice Platform (hundreds of entities) |
| **Fault Types** | DDoS attack, external storage failure, node resource contention stress test, noisy neighbor issue |
| **Modality** | Log + Metric |
| **Keywords** | time-series-forecasting, root cause analysis, microservice system, multi-modal learning, time series analysis, log analysis |

### Lý do chọn làm backup
- 4 fault types **thực tế mô phỏng** (DDoS, storage failure, resource contention, noisy neighbor)
- Multi-modal (log + metric) nhưng **thiếu trace** so với RCAEval
- License CC-BY-NC-4.0 → **chỉ dùng cho nghiên cứu**, không thương mại → cần ghi rõ trong paper
- Scale lớn hơn (hundreds of entities) → hữu ích cho stress-test agent

### Khi nào dùng backup?
- Khi muốn **validate cross-system generalization** (agent train trên RCAEval, test trên LEMMA-RCA)
- Khi cần fault type mà RCAEval không có (noisy neighbor, DDoS)

---

## 3. Dataset Tham khảo Phụ

### 3a. bolu61/loghub_2

| Field | Value |
|---|---|
| **HF URL** | https://huggingface.co/datasets/bolu61/loghub_2 |
| **Vai trò** | Log parsing baseline — benchmark cho log template extraction |
| **Sử dụng** | Tham khảo cách parse log raw → structured log → sinh alert |

### 3b. Junetheriver/OpsEval

| Field | Value |
|---|---|
| **HF URL** | https://huggingface.co/datasets/Junetheriver/OpsEval |
| **Vai trò** | Benchmark AIOps QA — đánh giá năng lực reasoning của LLM trong vận hành |
| **Sử dụng** | Tham khảo cách đánh giá agent decision quality |

### 3c. mldiakhame/* (alert correlation)

| Field | Value |
|---|---|
| **HF URL** | https://huggingface.co/mldiakhame |
| **Vai trò** | Alert correlation format reference |
| **Sử dụng** | Tham khảo format dữ liệu alert correlation |

---

## 4. Dataset KHÔNG có trên HuggingFace

### Alibaba Microservice Trace 2021/2022

| Field | Value |
|---|---|
| **Nguồn** | GitHub: alibaba/clusterdata |
| **Lý do không dùng** | Không upload lên HF, chỉ có trên GitHub Alibaba → đã xác nhận để tránh tìm nhầm |
| **Ghi chú** | Chỉ dùng nếu cần scale-test thêm, không nằm trong scope chính |

---

# CP1: Định nghĩa "Noisy Alert Warning" — Đo lường được

## 1. Bối cảnh: Tại sao cần định nghĩa này?

Trong microservices, hệ thống monitoring (Prometheus, Grafana, ELK...) sinh ra số lượng cảnh báo rất lớn. Phần lớn là **cảnh báo nhiễu (noisy alerts)** — chúng đúng về mặt kỹ thuật nhưng không cung cấp thông tin hành động được cho on-call engineer. Văn bản này định nghĩa "noisy alert warning" một cách **đo lường được** để làm nền tảng cho toàn bộ đề tài.

## 2. Phân biệt các cấp độ log

| Cấp độ | Mô tả | Hệ thống | Trạng thái |
|---|---|---|---|
| **INFO** | Hoạt động bình thường | Chạy đúng | Không cần alert |
| **WARNING** | Dấu hiệu bất thường sớm | **Chưa sập** | ⭐ **Focus của đề tài** |
| **ERROR** | Lỗi chức năng | **Đã hỏng** | Ngoài scope |
| **FATAL/CRITICAL** | Hệ thống crash | **Sập hoàn toàn** | Ngoài scope |

> **Novelty**: Đề tài tập trung vào WARNING-level — cảnh báo sớm khi hệ thống **chưa sập**. Đây là gap mà literature hiện có phần lớn bỏ qua (COLA, AlertGuardian, rule-based đều tập trung error/failure).

## 3. Định nghĩa chính thức

> **Noisy Alert Warning** là một cảnh báo ở mức WARNING được hệ thống monitoring sinh ra nhưng **không dẫn đến hành động khắc phục có ý nghĩa** từ on-call engineer, do một trong các nguyên nhân sau:
>
> (a) **Duplicate**: Nhiều cảnh báo cùng root cause trong cùng time window → engineer xử lý 1 cái, các cái còn lại là nhiễu
>
> (b) **Transient**: Cảnh báo tự biến mất trong thời gian ngắn mà không cần can thiệp → false positive thoáng qua
>
> (c) **Unactionable**: Cảnh báo đúng về mặt kỹ thuật nhưng engineer không có SOP/hành động cụ thể để xử lý → "biết rồi, khổ lắm, nói mãi"
>
> (d) **Cascading (symptom)**: Cảnh báo là hậu quả lan truyền (downstream effect) của root cause ở service khác → fixing service bị alert sẽ không giải quyết vấn đề gốc

## 4. Metric đo lường

### Metric chính: Alert Reduction Ratio (ARR)

ARR = 1 - (N_after / N_before)

Trong đó:
- N_before: Số lượng alert warning **trước** khi áp dụng aggregation
- N_after: Số lượng alert warning **sau** khi áp dụng aggregation

**Ví dụ**: Nếu có 100 warning alerts trước aggregation và còn 25 sau → ARR = 75% (giảm 75%)

### Metric bổ sung: Root Cause Preservation Rate (RCPR)

RCPR = (Số group chứa đúng root cause service) / (Tổng số fault cases)

**Mục đích**: Đảm bảo aggregation **không nuốt mất signal** — group nào cũng phải giữ lại thông tin root cause.

### Metric bổ sung: Group Purity (tùy chọn, nếu thời gian cho phép)

Purity = (Số alert trong group đúng là cùng root cause) / (Tổng số alert trong group)

**Mục đích**: Đánh giá chất lượng gom nhóm — group có "sạch" không hay gom nhầm alert không liên quan.

### Baseline để so sánh

| Baseline | Mô tả | Nguồn |
|---|---|---|
| **Rule-based (Prometheus Alertmanager)** | Group theo service + severity + time_window | Prometheus docs |
| **Time-window only** | Gom mọi alert trong cùng window (e.g. 5 phút) | Tự implement |
| **No aggregation** | Mỗi alert là 1 group → ARR = 0% | Control group |

### Target kỳ vọng

- **ARR >= 50%** với agent tool-calling (tốt hơn rule-based)
- **RCPR >= 95%** (không được nuốt root cause signal)

## 5. Mapping sang RCAEval dataset

| RCAEval Field | Mapping sang Noisy Alert Definition |
|---|---|
| fault + fault_description | Loại fault → xác định root cause service |
| root_cause_service | Ground truth → đánh giá RCPR |
| n_logs + has_logs | Nguồn sinh alert warning (parse từ log) |
| normal_timesteps vs faulty_timesteps | Alert trong normal period → nhiều khả năng là noisy (transient/cascading) |
| inject_time | Timestamp fault injection → xác định time window cho aggregation |
| system (Online Boutique/Sock Shop/Train Ticket) | Topology → build dependency table cho tool-2 |

## 6. Quy trình sinh alert warning từ RCAEval

```
Step 1: Load cases có has_logs=True từ RCAEval
Step 2: Parse log → extract entries có level=WARNING
Step 3: Map mỗi warning log → 1 alert object:
        {alert_id, service, timestamp, message_template, severity="warning"}
Step 4: Label mỗi alert là "noisy" hay "signal" dựa trên:
        - Timestamp nằm trong normal_timesteps → "noisy" (transient)
        - Service == root_cause_service + timestamp trong faulty_timesteps → "signal"
        - Service != root_cause_service + timestamp trong faulty_timesteps → "cascading/noisy"
Step 5: Áp dụng aggregation → đo ARR và RCPR
```

---

## 7. Checklist CP1

- [x] RCAEval: đã verify trên HF + arXiv + GitHub
- [x] LEMMA-RCA: đã verify trên HF (CC-BY-NC-4.0, non-commercial)
- [x] loghub_2: đã verify trên HF
- [x] Định nghĩa "noisy alert warning" — 4 loại (duplicate, transient, unactionable, cascading)
- [x] Metric đo lường: ARR, RCPR, Group Purity
- [x] Baseline: rule-based (Prometheus), time-window only, no-aggregation
- [x] Mapping sang RCAEval fields
- [x] Quy trình sinh alert warning từ RCAEval