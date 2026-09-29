# CP1 — BẢN ĐỊNH HƯỚNG 1 TRANG (GỬI THẦY LONG)

> **Đề tài**: Nghiên cứu cơ chế gom nhóm cảnh báo (Alert Aggregation) từ dữ liệu log cảnh báo sớm nhằm giảm thiểu cảnh báo nhiễu trong kiến trúc Microservices
> **Sinh viên**: [Tên bạn]
> **Ngày**: 2026-09-28 (bản cập nhật sau khi kiểm chứng dữ liệu thật)
> **Tuần**: 1/8
> **Thay đổi so với bản 2026-09-18**: bản này đã được chỉnh theo kết quả kiểm chứng trực tiếp RCAEval. Xem `cp1/docs/data_schema_notes.md` để có toàn bộ số liệu và cách chạy lại.

---

## 1. VẤN ĐỀ NGHIÊN CỨU (Research Question)

**RQ chính**: *Cơ chế gom nhóm cảnh báo dựa trên Agent tool-calling (kết hợp semantic similarity + service topology + runbook reasoning) có giảm được tỷ lệ cảnh báo nhiễu ở mức cảnh báo sớm (early-warning level) trong microservices hiệu quả hơn các phương pháp rule-based, semantic-only và temporal-spatial hiện có, đồng thời bảo toàn tỷ lệ gốc nguyên nhân (RCPR) ≥ 95%?*

**RQ phụ**:
- RQ1: Bốn loại cảnh báo nhiễu (duplicate, transient, unactionable, cascading) phân bố như thế nào trên RCAEval?
- RQ2: Kết hợp topology knowledge vào agent tool-calling có cải thiện Pairwise F1-score so với semantic-only (Drain3 + Sentence-BERT + HDBSCAN) bao nhiêu?
- RQ3: Chi phí token/latency của LLM agent có chấp nhận được cho real-time stream processing không?

> **Lưu ý về từ ngữ**: bản trước ghi "log `WARNING`". Sau khi kiểm chứng, RCAEval **không có cột `severity`** và mức `WARNING` chỉ dồn ở một hệ thống. Vì vậy RQ dùng cụm **"early-warning level"** (mức cảnh báo sớm) thay vì buộc cứng vào một giá trị severity duy nhất. Định nghĩa cụ thể ở §4.

---

## 2. GIẢ THUYẾT SƠ BỘ (Hypotheses)

| ID | Giả thuyết | Cách verify |
|----|------------|-------------|
| H1 | Agent tool-calling (Arm 4) đạt **ARR ≥ 60%** và **RCPR ≥ 95%**, tốt hơn Rule-based (Arm 1) và Semantic-only (Arm 2) | Chạy 4 arms trên cùng alert stream từ RCAEval, so sánh metrics |
| H2 | Tool `get_service_dependency` (topology) là yếu tố quan trọng nhất để giảm **Cascading noise** | Ablation: bỏ tool-2 → đo ΔF1 trên cascading alerts |
| H3 | Fast filter (dedup + time-window) giảm 70–80% alert trước khi vào LLM, giữ latency < 500ms/100 alerts | Đo token count & latency với/không có fast filter |
| H4 | Semantic similarity alone (Arm 2) **không phân biệt được** cascading vs signal do causality-blind | Confusion matrix Arm 2: precision trên cascading thấp |

> **Điều chỉnh H2**: cần khai báo trước rằng dữ liệu WARNING cho Cascading rất mỏng (xem §4), nên H2 có thể phải kiểm chứng trên **alert stream mở rộng** (gồm cả `ERROR`), không chỉ trên tier WARNING.

---

## 3. DATASET CHÍNH & BACKUP — ĐÃ KIỂM CHỨNG

| Dataset | Scale | Modalities | License | Status |
|---------|-------|------------|---------|--------|
| **RCAEval** (`phamquiluan/RCAEval`) | 735 cases / 9 dataset / 3 systems | Log + Metric + Trace + nhãn root cause | MIT ✅ (code + data) | **Chính** |
| **LEMMA-RCA** (`Lemma-RCA-NEC/Product_Review_Original`) | 100M–1B log event | Log + Metric (log đã aggregate thành time-series) | CC-BY-NC-4.0 ⚠️ | Backup — **nhưng xem cảnh báo bên dưới** |

**Số liệu thực tế đã kiểm chứng trên RCAEval:**

| Hạng mục | Số thực tế | Ghi chú |
|---|---|---|
| Tổng case | **735** | 9 dataset (RE1/RE2/RE3 × 3 hệ thống) |
| Case **có log** | **359** | RE1 (375 case) **không có log**; thêm 1 case lỗi ở RE2 |
| Tổng số dòng log | **49.652.771** | đã quét toàn bộ |
| Dòng chứa `WARN` | **9.738** (0,0196%) | Sock Shop 9.662 · Train Ticket 74 · **Online Boutique 2** |
| Cột của bảng log | `timestamp`, `container_name`, `message` | **Không có cột `severity`/`level`** |
| Case có `root_cause.txt` | **8** | chỉ **4** case có indicator là dòng `WARNING` |

**Hệ thống**: Online Boutique (11 service), Sock Shop (13 service), Train Ticket (40+ service) — topology dựng từ `traces.parquet` (240 case) hoặc repo public.

> ⚠️ **Cảnh báo về backup**: LEMMA-RCA **không cứu được scope cảnh báo sớm**. Log của nó đã được tổng hợp thành time-series 3 chiều, và bộ golden-signal keywords của chính dataset **chỉ gồm `error`, `exception`, `critical` — không có `warning`**. Nghĩa là nếu RCAEval thất bại, dataset dự phòng **cũng** không có mức cảnh báo sớm.

---

## 4. ĐỊNH NGHĨA CẢNH BÁO VÀ "NOISY ALERT" — ĐO LƯỜNG ĐƯỢC

### 4.1. Đơn vị "alert" (đã sửa cho khớp dữ liệu thật)

Một alert là một bộ:

$$a = \langle t,\ s,\ m,\ \ell \rangle$$

| Thành phần | Lấy từ đâu |
|---|---|
| $t$ | cột `timestamp` (epoch giây) |
| $s$ | cột `container_name` (đây chính là tên service) |
| $m$ | `message` sau khi chuẩn hoá: bỏ timestamp, UUID, trace-id, số → **message template** |
| $\ell$ | **mức cảnh báo**, gán theo 3 tầng dưới đây |

### 4.2. Ba tầng gán mức $\ell$ (vì dataset không có cột severity)

| Tầng | Áp dụng cho | Cách gán |
|---|---|---|
| **T1 — tường minh** | Sock Shop, Train Ticket (log4j/Spring Boot) | Parse mức từ `message`: `WARN` → `WARNING`, `ERROR`/`SEVERE` → `ERROR`, còn lại → `INFO` |
| **T2 — suy diễn theo tần suất** | Online Boutique (log không kèm mức) | Template được coi là **bất thường** nếu tần suất trong cửa sổ faulty cao hơn cửa sổ normal theo ngưỡng tỉ lệ $R$ (ví dụ $R \ge 3$) và tần suất tuyệt đối $\ge N_{\min}$ |
| **T3 — nhãn gốc** | 8 case có `root_cause.txt` | Dòng được RCAEval chỉ định là `ROOT_CAUSE` — dùng để đo RCPR ở **mức alert** |

**Cửa sổ thời gian** (suy từ `time_start / inject_time / time_end`, KHÔNG phải từ `normal_timesteps`):
- cửa sổ **bình thường** $= [T_{\text{start}},\ T_{\text{inject}})$
- cửa sổ **suy thoái** $= [T_{\text{inject}},\ T_{\text{end}}]$

> **Ghi chú kỹ thuật**: `normal_timesteps` và `faulty_timesteps` trong RCAEval là **số nguyên** (số điểm), **không phải danh sách timestamp**. Bản CP1 trước đây giả định sai điều này.

### 4.3. Bốn loại noisy alert

> **Noisy Alert** = cảnh báo đúng về mặt kỹ thuật nhưng **không dẫn đến hành động khắc phục có ý nghĩa** cho engineer.

| Loại | Rule code được | Bằng chứng thực tế trên RCAEval |
|------|----------------|--------------------------------|
| **Duplicate** | Cùng $s$ + cùng $m$ trong $\Delta t \le 60$s, số lần $\ge 2$ | `re3ss_carts_f3_4`: **626 dòng thô co còn 1 template** sau chuẩn hoá → `ARR ≈ 99,7%` |
| **Transient** | $t < T_{\text{inject}}$ **và** tỉ lệ tần suất faulty/normal của $m$ nhỏ hơn ngưỡng $R_{\text{transient}}$ | Họ `zipkin` của Sock Shop: **~50% số dòng nằm TRƯỚC `inject_time`**, chạy đều suốt case, không tương quan với fault |
| **Unactionable** | $m$ không map được vào bảng **runbook tổng hợp** (synthetic) của `fault_type` đang xét | Họ `zipkin` không ứng với hành động khắc phục nào. **Đây là loại yếu nhất — phải khai báo rõ runbook do ta tự viết** |
| **Cascading** | $s \ne s_{\text{root}}$ **và** $t \ge T_{\text{inject}}$ **và** tồn tại đường đi trong call graph từ $s_{\text{root}}$ tới $s$ | Mức `WARNING`: **Train Ticket** — 74 dòng phát từ **nhiều service** cùng lúc (mất kết nối MongoDB). Mức `ERROR`: **Sock Shop** — `orders` báo lỗi khi root cause là `carts` |

> **Giới hạn phải khai báo (Threats to Validity)**: mức `WARNING` **gần như không lan sang service khác** trong Sock Shop (mỗi case chỉ 1 service phát WARN). Cascading chỉ có **74 dòng** ở Train Ticket. Vì vậy H2 sẽ được kiểm chứng trên alert stream **có mở rộng** (bao gồm tier `ERROR`) và phải ghi rõ đây là mở rộng ngoài scope cảnh báo sớm thuần.

---

## 5. METRICS VÀ BASELINE

### Metrics chính

| Metric | Formula | Target |
|--------|---------|--------|
| **ARR** (Alert Reduction Ratio) | $1 - N_{\text{groups}} / N_{\text{raw\_alerts}}$ | ≥ 60% |
| **RCPR** (Root Cause Preservation Rate) | **Chính (mức service, 359 case)**: $\frac{1}{M}\sum_k \mathbb{I}(s_{\text{root}}^{(k)} \in g_{\text{primary}}^{(k)})$ — **Phụ (mức alert, 4–8 case)**: $\mathbb{I}(a_{\text{root\_cause\_indicator}} \in g_{\text{primary}})$ | ≥ 95% |
| **Pairwise F1** | $2PR/(P+R)$ trên cặp alert cùng nhóm | ≥ 0.85 |
| **Group Purity** | $\sum (\text{max\_count per group}) / N_{\text{total}}$ | ≥ 0.80 |

> **Vì sao RCPR phải định nghĩa kép**: RCAEval chỉ có **4 case** mà `root_cause_indicator` là dòng `WARNING`. Nếu chỉ đo RCPR ở mức alert thì mẫu số quá nhỏ, không kết luận được. Đo ở mức service cho mẫu số 359 case.

### Baseline so sánh

1. **Rule-based**: Prometheus Alertmanager (`group_by: service,alertname,severity`; `group_wait=30s`, `group_interval=5m`, `repeat_interval=4h`)
2. **Semantic-only**: Drain3 → Sentence-BERT (`all-MiniLM-L6-v2`) → HDBSCAN
3. **Temporal-spatial**: service call graph + sliding window $\Delta t \in \{30, 60, 120\}$s, hop $k \le 2$
4. **No aggregation**: mỗi alert = 1 group (ARR = 0%) — nhóm đối chứng

> **Lưu ý về COLA và AlertGuardian**: hai công trình này dùng dataset **không public** và COLA cần **SOP 3–4 trang/A4 cho mỗi alert** mà RCAEval không có. Vì vậy chúng chỉ dùng làm **mốc so sánh khái niệm trong Related Work**, **không** tái lập được dưới dạng baseline chạy trên RCAEval. Chi tiết ở `cp2/CP2_Gap_Analysis.md`.

---

## 6. PHƯƠNG PHÁP 4 NHÁNH (4 ARMS)

| Arm | Phương pháp | Tools / Key Tech | Expected Strength | Expected Weakness |
|-----|-------------|------------------|-------------------|-------------------|
| **1. Rule-based** | Mô phỏng Prometheus Alertmanager | Nhãn tĩnh + cửa sổ thời gian | Nhanh, tất định | Mù topology, bảo trì luật thủ công |
| **2. Semantic-only** | Drain3 → Sentence-BERT → HDBSCAN | `sentence-transformers`, `sklearn` | Không cần topology | Mù nhân quả; **Drain3 khuyến nghị bỏ severity trước khi parse → tự mất tín hiệu mức** |
| **3. Temporal-Spatial** | Service Call Graph + sliding window | Topology từ `traces.parquet` hoặc repo public, $\Delta t = 30/60/120$s | Bắt được cascading | Nhạy ngưỡng thời gian, cứng nhắc |
| **4. LLM Agent** | Fast Filter → Agent → 3 tools | Tool-calling, CoT, synthetic runbook | Suy luận nhân quả, linh hoạt | Latency, token cost, không tất định |

**Agent Tools (tối đa 2 lượt gọi/quyết định)**:
- `get_related_alerts(service, time_window)` → danh sách alert liên quan
- `get_service_dependency(service)` → service upstream/downstream
- `get_runbook(fault_type)` → SOP tổng hợp (**synthetic, không phải SOP production**)

---

## 7. SCOPE LOẠI TRỪ (Exclusions)

| Loại trừ | Lý do |
|----------|-------|
| Log `FATAL` / `CRITICAL` | Thuộc giai đoạn đã sập, ngoài scope cảnh báo sớm |
| Gom nhóm dựa trên metric/trace làm **đầu vào chính** | Scope là log; metric/trace chỉ làm context cho tool |
| Triển khai streaming thời gian thực | Chỉ đánh giá offline trên RCAEval |
| Runbook/SOP production thật | Chỉ dùng runbook tổng hợp cho các `fault_type` trong dataset |
| Multi-cluster / multi-region | 3 hệ thống benchmark đơn lẻ |
| Suite **RE1** của RCAEval | 375 case **không có log** — không dùng được cho đề tài |

---

## 8. TIÊU CHÍ ĐÁNH GIÁ (Go / No-go) — ĐÃ KIỂM CHỨNG

| Tiêu chí | Kết quả kiểm chứng thực tế | Verdict |
|----------|---------------------------|---------|
| **Tải được dataset** | 735 case, 2.080 file, 359 case có log | **GO** |
| **Có `timestamp` / `service` / `message`** | Có đủ (service = `container_name`) | **GO** |
| **Có cột `severity`/`level`** | **Không có** → đã có quy trình gán mức 3 tầng ở §4.2 | **GO có điều kiện** |
| **Có log cảnh báo sớm đủ dùng** | Sock Shop: 114 case / 9.662 dòng. Train Ticket: 36 case / 74 dòng. Online Boutique: 2 dòng | **GO (chỉ Sock Shop đủ mật độ)** |
| **Rule Duplicate code được** | 626 dòng → 1 template | **GO** |
| **Rule Transient code được** | Dùng `timestamp < inject_time` + ngưỡng tỉ lệ tần suất | **GO** |
| **Rule Unactionable code được** | Cần bảng runbook tổng hợp — phải tự viết, khai báo rõ | **GO có điều kiện** |
| **Rule Cascading code được** | Chỉ 74 dòng ở Train Ticket; Sock Shop không có ở tier WARNING | **GO yếu — phải kiểm chứng trên stream mở rộng** |
| **Đo RCPR** | Mức service: 359 case (**GO**). Mức alert: chỉ 4 case (**NO-GO**) | **GO với định nghĩa kép** |
| **Chốt dùng RCAEval** | — | **CHỐT RCAEval** (LEMMA-RCA không có mức cảnh báo sớm) |

> **Kết luận**: **GO có điều kiện**. Đề tài khả thi, nhưng phải ghi rõ trong báo cáo: (1) mức cảnh báo do ta parse/suy diễn, không do dataset cung cấp; (2) thực nghiệm chính chạy trên Sock Shop, Train Ticket chỉ đủ cho case study.

---

## 9. TIMELINE TUẦN 2–3 (Next Steps)

| Tuần | Mục tiêu | Deliverable |
|------|----------|-------------|
| **Tuần 2** | Literature review COLA/AlertGuardian, gap analysis 1 trang, chốt experiment design | **CP2: Gap Analysis 1 trang → Gửi thầy Long** (đã có bản nháp: `cp2/CP2_Gap_Analysis.md`) |
| **Tuần 3** | Parse RCAEval → alert stream (CSV/JSON), verify rule code cho 4 loại noisy | **CP3/4: alerts.csv + parse issues log** |

---

## 10. YÊU CẦU PHẢN HỒI TỪ THẦY LONG

1. **Xác nhận**: sau khi biết RCAEval **không có cột `severity`** và mức `WARNING` chỉ dồn ở Sock Shop, hướng **"early-warning level + agent tool-calling"** với định nghĩa mức 3 tầng ở §4.2 có hợp lệ không?
2. **Chỉ đạo**: baseline rule-based nên mô phỏng y hệt Prometheus Alertmanager, hay bản đơn giản là đủ?
3. **Đề xuất**: LLM model nào cho agent (GPT-4o-mini vs DeepSeek-V3 vs Llama-3-8B local) phù hợp budget/timeline?
4. **Scope**: có nên thêm **Arm 5 (Hybrid: Rule + Semantic + Topology, không dùng LLM)** để tách riêng phần đóng góp của LLM không?
5. **Rủi ro**: với Cascading chỉ có 74 dòng ở mức WARNING, thầy cho phép mở rộng alert stream sang tier `ERROR` để kiểm chứng H2 không, hay giữ Cascading như case study?

---

**Ký tên**: _______________   **Ngày**: _______________
