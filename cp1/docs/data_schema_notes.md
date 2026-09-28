# CP1 — GHI CHÚ KIỂM CHỨNG DỮ LIỆU RCAEval

> **Mục đích**: Trả lời Ưu tiên 1 của `note/28-09.md` — kiểm tra trực tiếp RCAEval về schema và log `WARNING`, rồi kết luận Go/No-go.
> **Ngày chạy**: 2026-09-28
> **Nguồn dữ liệu**: `phamquiluan/RCAEval` trên HuggingFace (config `cases`, và các file `logs.parquet` theo từng case)
> **Script đã dùng**: `cp1/legacy/scripts/verify_rcaeval.py`, `cp1/legacy/scripts/deep_scan_logs.py`, `cp1/legacy/scripts/scan_severity_exact.py`, `cp1/legacy/scripts/full_scan_warning.py`, `cp1/legacy/scripts/recompute_per_system.py`, `cp1/legacy/scripts/warn_samples_and_lemma.py`, `cp1/legacy/scripts/timing_analysis.py`, `cp1/legacy/scripts/final_verification.py`, `cp1/legacy/scripts/close_gaps.py`
> **Log thô**: `cp1/legacy/artifacts/_final_verify_out.txt`, `cp1/legacy/artifacts/_timing_out.txt`, `cp1/legacy/artifacts/_severity_scan_out.txt`, `cp1/legacy/artifacts/_warn_samples_out.txt`, `cp1/legacy/artifacts/_full_scan_out.txt`, `cp1/legacy/artifacts/_gaps_out.txt`, `cp1/legacy/artifacts/_warning_per_case.csv`

> **Cách đọc tài liệu này**: mỗi kết luận được gắn nhãn
> **FACT** = đọc trực tiếp từ dữ liệu/nguồn, có thể chạy lại để kiểm chứng;
> **INFERENCE** = suy luận từ FACT;
> **UNVERIFIED** = chưa kiểm chứng được.

---

## 0. Tóm tắt cho người đọc vội

**FACT:** RCAEval tải được, có 735 case. Nhưng chỉ **359/735 case có log** (RE1 không có log). File log thật nằm ở `logs.parquet` riêng của từng case, **không** nằm trong config `cases`.

**FACT:** Bảng log chỉ có **3 cột**: `timestamp`, `container_name`, `message`. **Không có cột `severity` / `level`.** Trường `service` cũng không tồn tại — phải dùng `container_name`.

**FACT:** Quét toàn bộ **49.652.771 dòng log** của 359 case: chỉ **9.738 dòng chứa chữ `WARN`** (0,0196%). Trong đó **9.662 dòng (99,2%) thuộc Sock Shop**, Online Boutique chỉ có **2 dòng trên 17,1 triệu dòng**.

**FACT:** Toàn bộ suite **RE1 (375 case) không có log**, cộng thêm 1 case lỗi ở RE2 → **376/735 case không dùng được**.

**FACT:** Tìm được **3 họ `WARNING`** khác nhau về bản chất: Duplicate (Sock Shop code-level), Transient/Unactionable (Sock Shop hạ tầng), và mất kết nối MongoDB lan nhiều service (Train Ticket).

**Kết luận:** **CONDITIONAL GO (Go có điều kiện)** — RCAEval dùng được, nhưng **phải thu hẹp phạm vi** hoặc **phải đổi định nghĩa đơn vị "alert"**. Không thể giữ nguyên đề cương hiện tại. Chi tiết ở [mục 8](#8-kết-luận-go-no-go).

---

## 1. FACT — Tải được dataset và số case thực tế

**FACT:** `load_dataset("phamquiluan/RCAEval", "cases", split="train")` chạy được, trả về **735 dòng**, 22 cột:

```
case, dataset, suite, system, system_name, root_cause_service, fault,
fault_description, repetition, inject_time, n_metrics, n_timesteps,
time_start, time_end, duration_minutes, normal_timesteps, faulty_timesteps,
has_logs, n_logs, has_traces, n_traces, has_root_cause_file
```

**FACT:** Đếm file trong repo HF: **2.080 file**.

| Loại file | Số lượng | Ý nghĩa |
|---|---|---|
| `inject_time.txt` | 735 | Thời điểm inject lỗi (mọi case đều có) |
| `metrics.parquet` | 735 | Metric của mọi case |
| `logs.parquet` | **359** | **Chỉ 359 case có log** |
| `traces.parquet` | 240 | Chỉ 240 case có trace |
| `root_cause.txt` | **8** | Chỉ 8 case có "root cause indicator" dạng log |

**FACT:** `has_logs=True` là **359/735**. Phân bố theo hệ thống:

| Hệ thống | Không có log | Có log |
|---|---|---|
| Online Boutique | 125 | 120 |
| Sock Shop | 125 | 120 |
| Train Ticket | 126 | 119 |

**FACT:** Đối chiếu cột `suite` với `has_logs`:

| suite | `has_logs=False` | `has_logs=True` | Tổng |
|---|---|---|---|
| RE1 | **375** | 0 | 375 |
| RE2 | **1** | 269 | 270 |
| RE3 | 0 | 90 | 90 |
| **Tổng** | **376** | **359** | 735 |

**FACT:** Toàn bộ RE1 (375 case) không có log — khớp với README chính thức ("RE1: Logs = N/A").
**FACT:** Có **1 case ngoại lệ** ở RE2: `re2tt_ts-auth-service_cpu_1` (`has_logs=False`) dù cùng nhóm `re2tt_ts-auth-service_cpu_2` và `_cpu_3` đều có log. Đây là **lỗ hổng dữ liệu đơn lẻ** của dataset.

**INFERENCE:** 51% dataset (suite RE1) là metric-only, không dùng được cho đề tài log. Trong 49% còn lại, chỉ 359 case dùng được.

> **Hệ quả cho đề cương:** câu "735 failure cases" không sai, nhưng khi nói về log phải nói **359 case**, không phải 735. Nếu viết "735 cases có log" trong báo cáo là **sai số liệu**.

### 1.1. Ba lỗi schema trong tài liệu hiện tại

**FACT:** `normal_timesteps` và `faulty_timesteps` là **số nguyên (int)**, không phải danh sách timestamp.

```
normal_timesteps  = 2100   <- SỐ ĐIỂM, không phải list
faulty_timesteps  = 2101   <- SỐ ĐIỂM, không phải list
```

**FACT:** Quan hệ thời gian của case mẫu `re1ob_adservice_cpu_1`:

```
time_start    = 1685200588
inject_time   = 1685202688      (time_start + 2100)
time_end      = 1685204788      (inject_time + 2100)
n_timesteps   = 4201
```

**INFERENCE:** `normal_timesteps` = số điểm **trước** inject; `faulty_timesteps` = số điểm **từ** inject trở đi. Cửa sổ thời gian phải suy ra từ `time_start / inject_time / time_end`, **không** được index vào list.

> **Hệ quả:** quy tắc trong `CP1_Ban_Dinh_Huong.md` §4 viết "Timestamp ∈ normal_timesteps" và trong `huggingfaceListRepo.md` §6 Step 4 viết "Timestamp nằm trong normal_timesteps → noisy" đều **không code được**. Phải sửa thành `timestamp < inject_time`.

**FACT:** `logs.parquet` chỉ có 3 cột, không có cột phân mức:

| Cột | dtype | Ví dụ | Ghi chú |
|---|---|---|---|
| `timestamp` | `Int64` | `1705353846` | **epoch giây, độ phân giải 1 giây** |
| `container_name` | `string` | `checkoutservice`, `carts`, `ts-auth-service` | **đây chính là "service"** |
| `message` | `string` | `conversion request successful` | nội dung log thô |

**FACT:** Trong 1 case, log chứa log của **nhiều service**, không phải chỉ service bị inject:

| Hệ thống | Số service trung bình trong 1 case | Min – Max |
|---|---|---|
| Online Boutique | 10,0 | 9 – 11 |
| Sock Shop | 11,0 | 10 – 15 |
| Train Ticket | 45,2 | 39 – 49 |

Không có case nào chỉ có 1 service (0/359).

**INFERENCE:** Đây là tin tốt: ta có log **xuyên service** trong cùng một case, nên về nguyên tắc có thể phân tích lan truyền (cascading). Nhưng xem [mục 6](#6-fact-cascading-không-đo-được-ở-mức-warning) — ở mức `WARNING` thì không.

---

## 2. FACT — Log `WARNING` có tồn tại, nhưng cực hiếm và lệch hệ thống

**FACT:** Quét `\bWARN(?:ING)?\b` trên **toàn bộ 359 case, 49.652.771 dòng log**:

| Hệ thống | Case có log | Tổng dòng log | Dòng chứa `WARN` | Case có WARN>0 | Median WARN/case | Max WARN/case |
|---|---|---|---|---|---|---|
| Online Boutique | 120 | 17.148.429 | **2** | 2 / 120 | 0 | 1 |
| Sock Shop | 120 | 9.864.458 | **9.662** | 114 / 120 | 54 | 626 |
| Train Ticket | 119 | 22.639.884 | **74** | 36 / 119 | 0 | 7 |
| **Tổng** | **359** | **49.652.771** | **9.738** | **152 / 359** | — | 626 |

Tỷ lệ `WARN` toàn dataset: **9.738 / 49.652.771 = 0,0196%**.

**FACT:** Số dòng chứa `ERROR` để so sánh: **167.309** (gấp ~17 lần `WARN`).

**INFERENCE:** Nhận xét quan trọng — **đề tài chọn đúng chỗ literature bỏ trống, nhưng chính vì thế dữ liệu cũng nghèo**. RCAEval không được thiết kế cho bài toán alert mức `WARNING`. Chỉ Sock Shop có đủ mật độ `WARNING` để làm thực nghiệm.

**FACT:** 2 dòng `WARN` của Online Boutique nằm rải ở `re3ob_adservice_f4_2` và `re3ob_adservice_f5_2`, mỗi case đúng 1 dòng. Với 1 dòng thì **không thể** gom nhóm, không thể đo ARR, không thể đo F1.

**INFERENCE:** Online Boutique **không dùng được** cho scope `WARNING`-only. Đây là mất mát lớn vì Online Boutique là hệ thống nhỏ, dễ hiểu nhất (11 service).

---

## 3. FACT — `WARNING` "ẩn" trong cột `message`, không phải cột riêng

**FACT:** Vì không có cột `severity`, mức log phải tìm trong nội dung `message`. Kiểm tra 9 case (3 case đầu mỗi hệ thống) với nhiều mẫu regex:

| Mẫu regex | Số dòng khớp (9 case) | Case khớp |
|---|---|---|
| `\bWARN(?:ING)?\b` | 165 | 6/9 |
| dạng log4j `LEVEL <pid>` | 818.615 | 6/9 |
| `[WARN]` trong ngoặc vuông | 0 | 0/9 |
| `level=warn` | 0 | 0/9 |
| `severity=warn` | 0 | 0/9 |
| `\bERROR\b` | 4.426 | 5/9 |
| `\bFATAL\b|\bCRITICAL\b` | **0** | 0/9 |
| từ khóa exception | 4.765 | 5/9 |
| `timeout` | **0** | 0/9 |
| `failed / unavailable / refused` | 14 | 4/9 |

**FACT:** Cách log thể hiện mức rất khác nhau giữa 3 hệ thống:

| Hệ thống | Ngôn ngữ / framework | Có mức log trong `message`? | Ví dụ |
|---|---|---|---|
| Online Boutique | Go, C#, Node.js, Python | **Không** | `conversion request successful` |
| Sock Shop | Java / Spring Boot (log4j) | **Có** | `2024-11-24 13:10:42.906  WARN [carts,...] 7 --- [p-nio-80-exec-6] o.s.web.servlet.PageNotFound : Request method 'POST' not supported` |
| Train Ticket | Java / Spring Boot (log4j) | **Có** | `2024-01-23 15:38:31.234  INFO 1 --- [o-18898-exec-13] seat.service.SeatServiceImpl : ...` |

**INFERENCE:** Online Boutique log ở dạng "structured message" (message mô tả hành vi, không kèm mức). Vì vậy **không có cách nào** gán nhãn `WARNING` cho Online Boutique từ dữ liệu gốc — muốn có thì phải tự suy diễn (xem Phương án B ở [mục 9](#9-ba-phương-án-và-khuyến-nghị)).

**FACT:** Với Train Ticket, `97%` dòng log là log4j `INFO`. Điều đó có nghĩa Train Ticket log **rất đầy đủ nhưng gần như toàn bộ là INFO**, nên lọc `WARNING` sẽ ra gần như rỗng.

---

## 4. FACT — Có HAI họ `WARNING` hoàn toàn khác nhau trong Sock Shop

Đây là phát hiện quan trọng nhất của buổi kiểm chứng. Sau khi chuẩn hóa template (bỏ timestamp, UUID, trace-id, số), thấy rõ 2 họ:

### Họ 1 — Lỗi code-level (suite RE3, fault `f1` / `f3`, service `carts`)

```
WARN [carts,<HEX>,<HEX>,false] <N> --- <THREAD> o.s.web.servlet.PageNotFound : Request method 'POST' not supported
```

| Case | Số WARN | Template thô | **Template sau chuẩn hóa** | WARN trong faulty window |
|---|---|---|---|---|
| `re3ss_carts_f3_4` | 626 | 626 | **2** | 626 / 626 (100%) |
| `re3ss_carts_f1_4` | 618 | 618 | **3** | 617 / 618 (99,8%) |
| `re3ss_carts_f3_3` | 611 | 611 | **2** | 611 / 611 (100%) |
| `re3ss_carts_f1_3` | 608 | 608 | **3** | 607 / 608 (99,8%) |
| `re3ss_carts_f1_1` | 571 | 571 | **3** | 570 / 571 (99,8%) |

**FACT:** Template chiếm ưu thế chiếm **99,6 – 99,8%** số dòng WARN trong mỗi case.

**INFERENCE (Duplicate):** Mỗi dòng thô là duy nhất **chỉ vì** chứa trace-id khác nhau. Sau khi bỏ trace-id, 626 dòng co lại còn **1 template**. Đây là **Duplicate noise điển hình** — và đo được: `ARR ≈ 1 − 2/626 = 99,7%` nếu chỉ dedup ở case này.

**FACT:** `container_name` phát WARN chỉ có **1 service** (`carts`) — đúng bằng `root_cause_service` của case.

**FACT đặc biệt quan trọng:** RCAEval công bố `root_cause.txt` cho 8 case, và với `re3ss_carts_f1_1`, `f1_2`, `f3_1`, `f3_2` thì **dòng được chỉ định làm "root cause indicator" chính là dòng `WARN` PageNotFound này**:

```
02:51,1732243919404637792,carts,"2024-11-22 02:51:59.404  WARN [carts,37dd0e6423df9dc9,37dd0e6423df9dc9,false] 7 --- [-nio-80-exec-17] o.s.web.servlet.PageNotFound : Request method 'POST' not supported",carts-7f4f67d778-nfbfj,ip-192-168-83-253.ap-southeast-2.compute.internal
```

**INFERENCE:** Với 4 case này, **WARNING không phải nhiễu — nó chính là tín hiệu gốc**. Nghĩa là tồn tại ground truth ở **mức alert** (không chỉ mức service). Nhưng chỉ **8 case** (2,2% của 359), nên không thể dùng làm thước đo chính.

### Họ 2 — Cảnh báo hạ tầng (suite RE2, fault `cpu` / `mem` / `disk` / `delay` / `loss` / `socket`)

```
WARN [carts,,,] <N> --- [tion/x-thrift})] z.r.AsyncReporter$BoundedAsyncReporter : Dropped <N> spans due to UnknownHostException(zipkin)
```

| Case | Số WARN | Template chuẩn hóa | WARN trong **normal** window | % normal |
|---|---|---|---|---|
| `re2ss_carts_cpu_1` | 50 | **1** | 26 | 52,0% |
| `re2ss_carts_mem_1` | 62 | **1** | 43 | 69,4% |
| `re2ss_carts_disk_1` | 81 | **1** | 43 | 53,1% |
| `re2ss_carts_delay_1` | 49 | **1** | 18 | 36,7% |
| `re2ss_carts_loss_1` | 49 | **1** | 26 | 53,1% |
| `re2ss_carts_socket_1` | 50 | **1** | 25 | 50,0% |

**FACT:** Họ 2 chỉ có **đúng 1 template** trên toàn bộ case, và khoảng **50% số dòng nằm TRƯỚC `inject_time`** — tức là xuất hiện cả khi hệ thống chưa bị inject lỗi.

**INFERENCE (Transient / Unactionable):** Cảnh báo này do service `carts` không kết nối được `zipkin` (tracing collector) nên phải bỏ span. Nó chạy suốt case, **không tương quan với lỗi được inject**, và engineer không có hành động khắc phục nào gắn với nó. Đây là ví dụ rất sạch cho **Transient/Unactionable noise**.

**FACT:** Đối chiếu với phân bố toàn Sock Shop: **98 case có ≥10 WARN**. Trong đó **8 case là Họ 1** (RE3 `carts` `f1`/`f3`, mỗi case ~570–626 dòng) và **90 case còn lại là Họ 2** (`zipkin`, mỗi case 34–81 dòng). Vậy **Họ 2 mới là loại WARNING phổ biến của Sock Shop** — nó chiếm đa số *case*, còn Họ 1 chiếm đa số *dòng*.

**FACT (ngoại lệ nhỏ):** Nhóm fault `f4` của RE3 cũng có 1–2 dòng WARN, nhưng đó là thông báo khởi động của framework (`Cannot enhance @Configuration bean definition 'refreshScope'`), không phải triệu chứng lỗi. Tương tự, một số case `f1` có thêm đúng 1 dòng `ConditionalRejectingErrorHandler : Execution of Rabbit message listener failed` ở container `queue-master`.

> **Lưu ý phương pháp luận:** họ 2 nằm trong `message`, không có field severity. Việc gán nó là "WARNING" dựa vào chữ `WARN` do chính ứng dụng in ra. Đây là **FACT** vì đọc trực tiếp được, nhưng cần ghi rõ trong báo cáo là "severity do ta parse từ message, không phải dataset cung cấp".

### Họ 3 — Mất kết nối MongoDB (suite RE2, Train Ticket) — **họ DUY NHẤT lan nhiều service**

```
WARN <N> --- <THREAD> org.mongodb.driver.connection : Got socket exception on connection [connectionId{...}] to ts-<X>-mongo:27017. All connections to ts-<X>-mongo:27017 will be closed.
```

**FACT:** Toàn bộ Train Ticket chỉ có **74 dòng `WARN`**, sau chuẩn hóa gom thành **16 template** — nhưng cả 16 template **chỉ khác nhau ở tên instance MongoDB** (`ts-auth-mongo`, `ts-route-mongo`, `ts-train-mongo`, …). Về mặt ngữ nghĩa đây là **một loại cảnh báo duy nhất**: "mất kết nối tới MongoDB".

**FACT:** Trong cùng một case, `WARN` phát ra từ **nhiều service khác nhau**:

| Case | Số WARN | Các service phát WARN |
|---|---|---|
| `re2tt_ts-route-service_mem_1` | 7 | ts-auth-service, ts-order-other-service, ts-price-service, ts-route-service, ts-train-service, ts-travel2-service |
| `re2tt_ts-auth-service_mem_2` | 5 | ts-config-service, ts-order-other-service, ts-order-service, ts-route-service, ts-train-service |
| `re2tt_ts-train-service_socket_2` | 5 | ts-contacts-service, ts-order-other-service, ts-train-service, ts-travel-service |

**INFERENCE (Cascading):** Đây là **họ WARNING duy nhất cho thấy hiện tượng lan truyền**. Nhiều service cùng lúc mất kết nối tới các instance MongoDB khác nhau, trong khi lỗi chỉ được inject vào **một** service. Đây đúng là dạng "triệu chứng lan từ nguyên nhân dùng chung" — nhưng **khối lượng quá nhỏ**: 74 dòng trên 36 case, tối đa 7 dòng/case.

**INFERENCE (bài học về semantic vs lexical):** Nếu dedup theo **chữ** (lexical), 16 template này thành **16 nhóm khác nhau**. Nếu gom theo **nghĩa**, chúng thành **1 nhóm**. Đây là ví dụ rất tốt để biện luận cho arm Semantic (Arm 2) — và cũng cho thấy arm Rule-based sẽ thất bại ở đây.

---

## 5. FACT — Cửa sổ thời gian và phân bố WARN theo loại fault

**FACT:** Với các case có log (RE2/RE3), cửa sổ quan sát là **1.440 giây (24 phút)**, chia đôi:

```
re3ss_carts_f3_4:  time_start=1732452999  inject_time=1732453719  time_end=1732454439
                   normal = 720s          faulty = 720s
```

**FACT:** Vị trí WARN so với `inject_time`:

| Nhóm fault | Ví dụ | WARN trong normal window | WARN trong faulty window |
|---|---|---|---|
| **Code-level** (`f1`, `f3`) | `re3ss_carts_f3_4` | 0 – 1 dòng (~0%) | 570 – 626 dòng (~100%) |
| **Hạ tầng** (`cpu`,`mem`,`disk`,`delay`,`loss`,`socket`) | `re2ss_payment_loss_1` | 35 – 43 dòng (~50%) | 23 – 40 dòng (~50%) |

**FACT:** Với nhóm hạ tầng, WARN đầu tiên xuất hiện khoảng **710 giây TRƯỚC** `inject_time` (ví dụ `re2ss_carts_disk_1`: WARN đầu ở 1705817238, inject ở 1705817948).

**INFERENCE:** Quy tắc **Transient** trong đề cương ("WARN trong normal window là nhiễu") là **đúng và code được**, nhưng chỉ đúng cho nhóm hạ tầng. Với nhóm code-level thì WARN trong faulty window lại **chính là root cause**, nên nếu gom mất nó là mất tín hiệu — đúng tình huống mà `RCPR` muốn bảo vệ. Điều này làm cho thực nghiệm có ý nghĩa: hai tình huống ngược nhau nằm trong cùng một dataset.

---

## 6. FACT — Cascading: gần như không đo được ở mức WARNING

**FACT:** Trong **Sock Shop**, mọi case đã kiểm đều chỉ có **1** `container_name` phát ra `WARN` (ngoại lệ duy nhất: `queue-master` góp đúng **1 dòng** trong vài case `f1`).

| Case | Service bị inject (`root_cause_service`) | Service phát WARN |
|---|---|---|
| `re3ss_carts_f3_4` | carts | carts |
| `re2ss_carts_disk_1` | carts | carts |
| `re2ss_payment_loss_1` | payment | carts |

**FACT:** Trong **Train Ticket**, ngược lại, `WARN` **có** phát từ nhiều service trong cùng case (xem Họ 3 ở mục 4) — nhưng tổng cộng chỉ **74 dòng trên 36 case**, tối đa **7 dòng/case**.

**INFERENCE:** Vậy quy tắc **Cascading** ở mức `WARNING`:
- Trên Sock Shop: **không có dữ liệu** (1 service/case).
- Trên Train Ticket: **có** dữ liệu nhưng chỉ 74 dòng → không đủ để huấn luyện hay đánh giá thống kê, chỉ đủ để **minh hoạ**.

**FACT:** Hiện tượng lan truyền **có** tồn tại với khối lượng lớn, nhưng nằm ở mức `ERROR`. Ví dụ `re3ss_carts_f3_4` (root cause = `carts`) có `ERROR` phát ra từ container **`orders`**:

```
faulty=89  normal=19  ratio=4.5   ERROR [orders,,,] ... o.a.c.c.C.[.[.[/].[dispatcherServlet] : Servlet.service() ...
faulty=118 normal=27  ratio=4.2   Order response: {"statusCode":<N>,"body":{...,"error":"Internal Server Error",...}}
faulty=118 normal=27  ratio=4.2   org.springframework.web.client.HttpServerErrorException: <N> Service Unavailable
```

**INFERENCE:** `orders` gọi `carts`, `carts` lỗi → `orders` trả 500. Đây là **cascading thật**, nhưng biểu hiện ở `ERROR`, không ở `WARNING`. Muốn đo loại nhiễu Cascading một cách nghiêm túc thì **buộc phải mở rộng đơn vị alert ra ngoài mức WARNING** — hoặc chuyển Cascading thành một nghiên cứu tình huống (case study) trên 74 dòng của Train Ticket.

---

## 7. FACT — `root_cause.txt`: ground truth ở mức alert chỉ có 8 case

**FACT:** Chỉ **8 case** có `root_cause.txt`, tất cả thuộc **RE3 Sock Shop**:

`re3ss_carts_f1_1`, `re3ss_carts_f1_2`, `re3ss_carts_f3_1`, `re3ss_carts_f3_2`, `re3ss_front-end_f1_1`, `re3ss_front-end_f1_2`, `re3ss_front-end_f2_1`, `re3ss_front-end_f2_2`

**FACT:** Định dạng file:

```
<HH:MM>,<timestamp_nanosecond>,<service>,"<raw log line>",<pod>,<node>
```

**FACT:** Loại dòng được chỉ định làm root cause indicator:

| Case | Dòng root cause indicator | Có phải WARNING? |
|---|---|---|
| `re3ss_carts_f1_1/2`, `f3_1/2` | `WARN ... o.s.web.servlet.PageNotFound : Request method 'POST' not supported` | **Có** |
| `re3ss_front-end_f1_1/2` | `POST /cart 500 54.305 ms - 70` (access log) | **Không** |
| `re3ss_front-end_f2_1/2` | `POST /cart 500 72.969 ms - 70` (access log) | **Không** |

**INFERENCE:** Kể cả trong 8 case có ground truth mức alert, chỉ **4 case** root cause indicator là `WARNING`. Vậy nếu định nghĩa `RCPR = tỷ lệ giữ được alert gốc`, mẫu số hợp lệ chỉ là **4 case** → không đủ để nói gì về thống kê.

**INFERENCE:** Nếu định nghĩa `RCPR = tỷ lệ giữ được root cause **service**`, mẫu số là **359 case** → đo được. Đây là lựa chọn thực tế hơn nhiều, nhưng phải khai báo rõ là RCPR đo ở mức service, không phải mức alert.

**FACT:** README chính thức của RCAEval xác nhận: *"Each failure case includes annotated root cause service and root cause indicator (e.g., specific metric or log indicating the root cause)"* — và 15 baseline tái lập được, 9 dataset (RE1/RE2/RE3 × 3 hệ thống), license MIT cho code và data do nhóm tác giả làm.

---

## 8. KẾT LUẬN GO/NO-GO

| # | Tiêu chí (theo `CP1_Ban_Dinh_Huong.md` §8) | Kết quả kiểm chứng | Verdict |
|---|---|---|---|
| 1 | Tải được RCAEval | Tải được, 735 case, 2.080 file | **PASS** |
| 2 | Có field `timestamp` | Có (`Int64`, epoch giây) | **PASS** |
| 3 | Có field `service` | Có, tên là `container_name` | **PASS** |
| 4 | Có field `message` | Có | **PASS** |
| 5 | Có field `severity` / `level` | **KHÔNG có** — phải parse từ `message` | **FAIL** |
| 6 | Parse được log `WARNING` | Chỉ Sock Shop; OB 2 dòng, TT 74 dòng | **PASS có điều kiện** |
| 7 | Sinh alert stream ≥1 service | Sock Shop: 114 case, 9.662 WARN | **PASS** |
| 8 | Sinh alert stream trên cả 3 hệ thống | OB gần như rỗng | **FAIL** |
| 9 | Rule `Duplicate` code được | 626 dòng → 1 template sau chuẩn hóa | **PASS** |
| 10 | Rule `Transient` code được | Dùng `timestamp < inject_time` | **PASS** (phải sửa công thức) |
| 11 | Rule `Cascading` code được ở mức WARNING | Sock Shop: không có (1 service/case). Train Ticket: có nhưng chỉ 74 dòng/36 case | **PASS yếu** |
| 12 | Đo `RCPR` ở mức alert | Chỉ 4 case có root cause indicator là WARNING | **FAIL** |
| 13 | Đo `RCPR` ở mức service | 359 case có `root_cause_service` | **PASS** |
| 14 | `normal_timesteps` là danh sách timestamp (theo đề cương) | Thực tế là **số nguyên** | **FAIL** (đề cương sai) |

### Verdict tổng: **CONDITIONAL GO**

**FACT:** Dataset tải được, log parse được, `WARNING` có thật, và tồn tại tình huống thú vị (cùng một mức WARNING vừa là nhiễu vừa là tín hiệu gốc).

**FACT:** Nhưng bốn trụ của đề cương hiện tại **không đứng vững nguyên trạng**:
1. Không có cột `severity` → phải tự parse từ `message`; Online Boutique **hoàn toàn không có mức log** trong nội dung.
2. `WARNING` chỉ dồn ở Sock Shop (99,2%) → mất khả năng so sánh liên hệ thống (cross-system) trên 3 hệ thống.
3. `Cascading` gần như không quan sát được ở mức `WARNING`: Sock Shop không có, Train Ticket chỉ 74 dòng → loại nhiễu thứ tư thiếu cơ sở dữ liệu.
4. 51% dataset (suite RE1) không có log → mọi tuyên bố "trên 735 case" đều sai.

**Khuyến nghị:** chọn **Phương án B** ở mục 9. Nếu giảng viên yêu cầu bám chặt chữ "log WARNING", chọn **Phương án A** nhưng phải chấp nhận chỉ còn 1 hệ thống.

---

## 9. BA PHƯƠNG ÁN VÀ KHUYẾN NGHỊ

### Phương án A — Giữ nguyên định nghĩa, thu hẹp còn Sock Shop
Giữ đơn vị alert = dòng log có mức `WARNING`. Chạy chính trên **Sock Shop (114 case, 9.662 WARN)**.
- **Được:** trung thành với đề cương; sạch về mặt định nghĩa; có đủ cả tình huống WARNING-là-nhiễu (Họ 2) lẫn WARNING-là-tín-hiệu-gốc (Họ 1).
- **Mất:** không còn so sánh 3 hệ thống; `Cascading` gần như mất (Sock Shop 1 service/case).
- **Biến thể A′ (đáng cân nhắc):** thêm Train Ticket như **nghiên cứu tình huống 74 dòng** cho Cascading, không dùng để tính metric chính. Như vậy vẫn giữ được "có xét lan truyền" mà không phải bịa số liệu.
- **Rủi ro:** phản biện "chỉ 1 hệ thống thì kết luận tổng quát được gì?"

### Phương án B — Đổi đơn vị alert thành "log bất thường giai đoạn tiền sự cố" **(khuyến nghị)**
Đổi định nghĩa: alert = một log line (hoặc một template + cửa sổ thời gian) xuất hiện trong **cửa sổ tiền sự cố**, với `WARNING` là **tier chính**, và có bảng ánh xạ mức cho từng hệ thống:

| Hệ thống | Cách xác định mức |
|---|---|
| Sock Shop, Train Ticket | parse từ `message` (đã có log4j header) |
| Online Boutique | **không có mức** → suy ra bằng độ mới của template: template chỉ xuất hiện trong faulty window, hoặc tần suất tăng đột biến so với normal window |

- **Được:** dùng được cả **359 case, 3 hệ thống**; đo được `Cascading` qua `ERROR` và qua dịch chuyển template giữa hai cửa sổ; giữ được thông điệp "pre-failure / early-warning".
- **Mất:** phải khai báo rõ trong Threats to Validity rằng severity là **do ta suy diễn**, không phải dataset cung cấp; và RQ phải đổi từ "log WARNING" thành "early-warning level logs".
- **Bằng chứng ủng hộ:** đã có sẵn tín hiệu phân biệt mạnh — ví dụ `POST /cart 500` xuất hiện 742 lần trong faulty window so với 34 lần trong normal window (ratio 21,2). Ngoài ra họ WARNING MongoDB của Train Ticket (16 template chỉ khác tên instance) là ví dụ sạch cho việc **gom theo nghĩa thì 1 nhóm, gom theo chữ thì 16 nhóm** — rất hợp để biện luận cho arm Semantic.

### Phương án C — Đổi sang dataset backup
**Không giải quyết được.**
**FACT:** `Lemma-RCA-NEC/Product_Review_Original` trên HuggingFace chỉ có **4 file zip + README** (không có schema Parquet/CSV xem trước). License **cc-by-nc-4.0**. Theo mô tả của chính dataset, log đã được **tổng hợp thành time-series** bằng Drain + golden-signal keywords, và bộ keyword đó **chỉ gồm `error`, `exception`, `critical` — không có `warning`**.
**INFERENCE:** LEMMA-RCA còn tệ hơn RCAEval cho scope `WARNING`: log đã bị aggregate nên mất luôn dòng log gốc. Chuyển sang backup **không** cứu được scope WARNING-only.

---

## 10. UNVERIFIED

1. **Chưa kiểm 100% template của cả 9.662 dòng WARN ở Sock Shop.** Đã kiểm sâu 14 case (8 case RE3 + 6 case RE2). Có thể còn họ WARNING thứ tư chưa thấy. Train Ticket thì **đã kiểm 100%** (74/74 dòng).
2. **Chưa xem `traces.parquet`** (240 case). Trace có thể dùng để dựng service call graph thật thay cho topology tĩnh — cần kiểm ở CP4b. Đây là cách kiểm chứng độc lập cho "Train Ticket có thật sự lan truyền".
3. **Chưa xác nhận `container_name` là "service" theo đúng định nghĩa topology.** Đã kiểm: giá trị là tên service (`carts`, `ts-auth-service`, `frontend`). Chưa đối chiếu với danh sách service chính thức của 3 hệ thống.
4. **Chưa kiểm vì sao `queue-master` xuất hiện trong log của Sock Shop** mà không nằm trong danh sách 13 service chuẩn của Sock Shop.
5. **Chưa ước lượng thời gian chạy thực nghiệm.** 49,6 triệu dòng log là khối lượng lớn; nếu agent gọi LLM cho từng cụm thì cần tính ngân sách token trước.
6. **Chưa kiểm file `_raw_run5.txt` bị lỗi phân loại hệ thống** (regex gán mọi case thành `tt`). Số liệu trong tài liệu này đã được tính lại bằng `recompute_per_system.py` và `final_verification.py`, nhưng nếu ai đọc lại `_raw_run5.txt` thì sẽ thấy số sai — **đừng dùng file đó**, dùng `_warning_per_case.csv`.

---

## 11. CÁC SỬA ĐỔI ĐÃ ÁP DỤNG VÀO TÀI LIỆU KHÁC

> **Trạng thái: TẤT CẢ ĐÃ SỬA XONG ngày 2026-09-28** (theo Phương án B đã chốt).

| File | Chỗ sai | Đã sửa thành |
|---|---|---|
| `cp1/docs/CP1_Ban_Dinh_Huong.md` §3 | "735 cases" ngụ ý dùng được hết | Ghi rõ **359 case có log**, RE1 là metric-only ✅ |
| `cp1/docs/CP1_Ban_Dinh_Huong.md` §4 | "Transient: Timestamp ∈ normal_timesteps" | Đổi thành `timestamp < inject_time` + ngưỡng tỉ lệ tần suất ✅ |
| `cp1/docs/CP1_Ban_Dinh_Huong.md` §4 | "Cascading: Service ≠ root_cause_service trong faulty_timesteps" | Thêm điều kiện reachable trong call graph + ghi rõ giới hạn dữ liệu ✅ |
| `cp1/docs/CP1_Ban_Dinh_Huong.md` §4.2 | Giả định dataset có `severity` | Thêm **quy trình gán mức 3 tầng** ✅ |
| `cp1/docs/CP1_Ban_Dinh_Huong.md` §5 | `RCPR` dùng `root_cause_alert` | **Định nghĩa kép**: mức service (359 case) chính, mức alert (4 case) phụ ✅ |
| `cp1/docs/CP1_Ban_Dinh_Huong.md` §8 | Tiêu chí Go/No-go chưa có dữ liệu | Cập nhật theo kết quả kiểm chứng ✅ |
| `cp1/docs/huggingfaceListRepo.md` §1 | Schema ngụ ý log nằm trong `cases` | Thêm schema `logs.parquet` và cảnh báo log ở file riêng ✅ |
| `cp1/docs/huggingfaceListRepo.md` §2 | Bảng cấp độ log ngụ ý dataset có severity | Ghi rõ **không có cột severity, phải parse từ message** ✅ |
| `cp1/docs/huggingfaceListRepo.md` §6 | "Timestamp nằm trong normal_timesteps" | `timestamp < inject_time` ✅ |
| `cp1/docs/huggingfaceListRepo.md` §7 | Checklist `[x]` sai sự thật | Cập nhật, thêm mục CP3 còn lại ✅ |
| `report/main.tex` Abstract | "warning-level logs", "735 failure cases" | Đổi thành `early-warning`, nêu **359 case có log** + quy trình 3 tầng ✅ |
| `report/main.tex` §Methodology | $\ell_i = \texttt{WARNING}$ như thể dataset có sẵn | Thêm **Tier 1/2/3** và ghi rõ $\ell_i$ do ta gán ✅ |
| `report/main.tex` §Experimental Setup | "735 annotated failure cases" | Thêm số liệu kiểm chứng (359 case, 49.652.771 dòng, 9.738 WARN) ✅ |
| `report/main.tex` §Results | Trình bày số như **kết quả thật** | Đổi tên thành **"Expected Outcomes and Analysis Plan"**, ghi rõ là target chưa đo ✅ |
| `report/main.tex` §Threats to Validity | Chỉ có 1 threat | Thêm threat về severity do ta gán, scarcity, và runbook tổng hợp ✅ |
| `report/glossary.tex` | RCPR chỉ 1 định nghĩa; `Normal/Faulty Timesteps` sai | RCPR kép; đổi thành `Normal Window` / `Fault Window` ✅ |
| `academicWords.md` | RCPR 1 công thức; "735 cases" không kèm cảnh báo | RCPR kép + cảnh báo 359 case / thiếu severity ✅ |
| `note/28-09.md` | Rule Transient dựa trên `normal_timesteps` | Giữ nguyên phần lịch sử, **thêm mục "CẬP NHẬT SAU PHIÊN"** ghi rõ giả định bị bác bỏ ✅ |
| `PROJECT_MINDMAP.md` | Số liệu lỗi thời (735, ARR 50% vs 60% mâu thuẫn) | Thêm banner cảnh báo trỏ về tài liệu đúng ✅ |
| `cp1/legacy/scripts/test_load_rcaeval.py` | Lỗi `TypeError` + tìm log sai chỗ | Thêm banner DEPRECATED và sửa lỗi subscript ✅ |

---

## 12. CÁCH CHẠY LẠI ĐỂ KIỂM CHỨNG

```bash
.\\setup.ps1
.\\.venv\\Scripts\\python cp1\\src\\main_RCAEval.py fetch
.\\.venv\\Scripts\\python cp1\\src\\main_RCAEval.py inspect
.\\.venv\\Scripts\\python cp1\\src\\main_RCAEval.py scan-warnings
.\\.venv\\Scripts\\python cp1\\src\\main_RCAEval.py timing
.\\.venv\\Scripts\\python cp1\\src\\main_RCAEval.py verify
```

> Lưu ý: các script trong `cp1/legacy/scripts/` chỉ giữ lại để đối chiếu lịch sử. Workflow mới ghi raw data vào `cp1/raw_data/`, còn table/report vào `cp1/artifacts/`.

---

*Trạng thái: **Ưu tiên 1 và 2 đã xong**. Scope đã chốt theo **Phương án B**. Bước tiếp theo là CP3 — viết pipeline sinh `alerts.csv` theo quy trình gán mức 3 tầng ở §4.2 của `cp1/docs/CP1_Ban_Dinh_Huong.md`.*
