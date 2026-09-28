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

> Đây là schema của **config `cases`** (bảng chỉ mục 735 dòng). **Log KHÔNG nằm ở đây** — xem phần dưới.

```
case, dataset, suite, system, system_name,
root_cause_service, fault, fault_description,
repetition, inject_time,
n_metrics, n_timesteps, time_start, time_end, duration_minutes,
normal_timesteps, faulty_timesteps,
has_logs, n_logs, has_traces, n_traces, has_root_cause_file
```

### Schema của log (đã kiểm chứng 2026-09-28)

Log nằm ở **file riêng `<case>/logs.parquet`**. Chỉ **359/735 case** có file này.

```
timestamp       Int64    epoch giây
container_name  string   tên service  <-- đây chính là "service"
message         string   nội dung log thô
```

**Không có cột `severity` / `level`.** Mức log phải parse từ `message`.
Ngoài ra: `inject_time.txt` (735 case), `metrics.parquet` (735), `traces.parquet` (240), `root_cause.txt` (8 case).

### Lý do chọn làm dataset chính
- **735 ca lỗi** từ 3 microservice thật (public, tái lập được) — **nhưng chỉ 359 case có log**, suite RE1 (375 case) là metric-only
- Có **log + metric + trace + nhãn root cause** → đa modal, đủ cho agent tool-calling
- Paper đi kèm có **15 baseline** (bao gồm rule-based, graph-based, RL) → dễ so sánh
- License MIT → không cản trở publish
- 3 hệ thống benchmark đều là **microservice mẫu phổ biến** (Online Boutique của Google, Sock Shop của Weaveworks, Train Ticket) → dựng được dependency table cho tool-2, **có thể lấy trực tiếp từ `traces.parquet` (240 case) thay vì phải dựa vào repo ngoài**

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

> ⚠️ **ĐÃ KIỂM CHỨNG 2026-09-28**: RCAEval **KHÔNG có cột `severity`/`level`**. Bảng log chỉ có 3 cột `timestamp`, `container_name`, `message`. Mức log (nếu có) **nằm bên trong nội dung `message`** và **chỉ có ở Sock Shop và Train Ticket** (định dạng log4j của Spring Boot); Online Boutique **hoàn toàn không có mức log**. Xem `cp1/docs/data_schema_notes.md`.

| Cấp độ | Mô tả | Hệ thống | Trạng thái |
|---|---|---|---|
| **INFO** | Hoạt động bình thường | Chạy đúng | Không cần alert |
| **WARNING / WARN** | Dấu hiệu bất thường sớm | **Chưa sập** | ⭐ **Focus của đề tài** — 9.738 dòng trên toàn dataset |
| **ERROR** | Lỗi chức năng | **Đã hỏng** | Dùng làm mở rộng cho Cascading — 167.309 dòng |
| **FATAL/CRITICAL** | Hệ thống crash | **Sập hoàn toàn** | Ngoài scope — **0 dòng** trong toàn dataset |

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
| root_cause_service | Ground truth → đánh giá RCPR (mức service, 359 case) |
| n_logs + has_logs | Nguồn sinh alert cảnh báo sớm (**chỉ 359/735 case có log**) |
| **`timestamp` (cột trong `logs.parquet`)** | **Cửa sổ thời gian — dùng `timestamp < inject_time` cho normal window** |
| `normal_timesteps` / `faulty_timesteps` | ⚠️ **KHÔNG dùng** — đây là **số nguyên** (số điểm), **không phải danh sách timestamp** |
| inject_time | Timestamp fault injection → mốc chia cửa sổ bình thường / suy thoái |
| system (Online Boutique/Sock Shop/Train Ticket) | Topology → build dependency table cho tool-2 |
| `container_name` (cột trong `logs.parquet`) | Chính là **service name** — dataset không có cột tên `service` |

## 6. Quy trình sinh alert cảnh báo sớm từ RCAEval (đã sửa theo dữ liệu thật)

> ⚠️ Log **không nằm trong config `cases`**. Mỗi case có file riêng `logs.parquet` với 3 cột `timestamp`, `container_name`, `message`. Chỉ **359/735 case** có file này.

```
Step 1: Load cases có has_logs=True (359 case)
Step 2: Với mỗi case, tải <case>/logs.parquet
Step 3: Sinh alert object từ mỗi dòng log:
        {alert_id, service=container_name, timestamp, message_template, severity}
        - message_template: chuẩn hoá message (bỏ timestamp, UUID, trace-id, số)
        - severity: gán theo 3 tầng
            T1: parse mức từ message (Sock Shop, Train Ticket) -> WARNING/ERROR/INFO
            T2: suy diễn theo tần suất faulty/normal (Online Boutique, vì không có mức)
            T3: đánh dấu ROOT_CAUSE nếu dòng nằm trong root_cause.txt (8 case)
Step 4: Gán nhãn noisy/signal (dùng inject_time, KHÔNG dùng normal_timesteps):
        - timestamp <  inject_time                          -> "noisy" (transient)
        - service == root_cause_service                    -> "signal"
        - service != root_cause_service + timestamp >= inject_time
          + có đường đi trong call graph từ root_cause      -> "cascading/noisy"
Step 5: Áp dụng aggregation -> đo ARR, RCPR, Pairwise F1, Group Purity
```

**Số liệu thực tế để đối chiếu khi chạy pipeline:**

| Chỉ số | Giá trị đã kiểm chứng |
|---|---|
| Case có log | 359 |
| Tổng dòng log | 49.652.771 |
| Dòng `WARN` | 9.738 (Sock Shop 9.662 · Train Ticket 74 · Online Boutique 2) |
| Dòng `ERROR` | 167.309 |
| Dòng `FATAL`/`CRITICAL` | 0 |

---

## 7. Checklist CP1

- [x] RCAEval: đã verify trên HF + arXiv + GitHub
- [x] RCAEval: **đã kiểm chứng schema và log thật** (`cp1/docs/data_schema_notes.md`)
- [x] LEMMA-RCA: đã verify trên HF (CC-BY-NC-4.0, non-commercial)
- [x] loghub_2: đã verify trên HF
- [x] Định nghĩa "noisy alert" — 4 loại (duplicate, transient, unactionable, cascading), **rule đã viết được**
- [x] Metric đo lường: ARR, RCPR (định nghĩa kép), Pairwise F1, Group Purity
- [x] Baseline: rule-based (Prometheus), semantic-only, temporal-spatial, no-aggregation
- [x] Mapping sang RCAEval fields
- [x] Quy trình sinh alert cảnh báo sớm từ RCAEval
- [x] Kết luận Go/No-go: **CONDITIONAL GO** — chốt dùng RCAEval, thực nghiệm chính trên Sock Shop
- [ ] CP3: chạy pipeline thật để sinh `alerts.csv` và đếm số alert/group