# Dataset

Cập nhật 26/10/2026. Mọi con số ghi **[REPO]** đã được đếm trực tiếp trên `data/raw/` ngày 26/10/2026. Con số lấy từ bài báo có ghi số trang.

## 1. Tổng quan

| Dataset | Vai trò | Có log | Nhãn | Dùng để |
| --- | --- | --- | --- | --- |
| **RCAEval** (Pham et al., WWW Companion 2025) | Chính | 359 / 735 case | 1 service mỗi case | Train, chọn cấu hình, test |
| **Nezha** (Yu et al., ESEC/FSE 2023) | Đánh giá ngoài | 101 lần tiêm lỗi (101 incident) | 1 pod mỗi lỗi → ánh xạ sang service | Chỉ test cuối, không dùng để chỉnh |
| LEMMA-RCA | Đã bỏ (26/10/2026) | — | — | Không dùng |

## 2. RCAEval

### Số liệu [REPO]

- `cases.parquet`: 735 case, cả 735 có `root_cause_service`. 376 case không có log: toàn bộ 375 case suite RE1 và 1 case RE2 của tt.
- **359 case có log**, chia như sau:

| Suite | Loại lỗi | ob | ss | tt | Tổng |
| --- | --- | ---: | ---: | ---: | ---: |
| RE2 | Tài nguyên / mạng: cpu (44), mem, disk, delay, loss, socket (45 mỗi loại) | 90 | 90 | 89 | 269 |
| RE3 | Lỗi code: f1 (26), f2 (13), f3 (26), f4 (19), f5 (6) | 30 | 30 | 30 | 90 |

- ob = Online Boutique, ss = Sock Shop, tt = Train Ticket.
- 18 service đáp án khác nhau: ob 7, ss 6, tt 5.
- Mỗi case có một service đáp án; không có case nhiều đáp án.
- Log có 3 cột: `timestamp`, `container_name`, `message`. Không có cột severity, không có trace ID.
- Mỗi case có khoảng 24 phút log (trung vị), gồm khoảng 12 phút trước và 12 phút sau `inject_time`. 1 case không có log trước thời điểm lỗi.
- Số service xuất hiện trong log mỗi case: 9–49, trung vị 11.
- **Coverage:** service đáp án có xuất hiện trong log của chính case đó ở 333/359 case. 26 case còn lại là service lỗi không ghi dòng log nào, ví dụ `re2ob_productcatalogservice_cpu_*`.
- **Kịch bản lặp:** 117 kịch bản (tên case bỏ hậu tố `_1`, `_2`...). 109 kịch bản có 3 lần chạy, 6 có 4 lần, 1 có 6 lần, 1 có 2 lần.

### Rủi ro rò rỉ đáp án

- Tên case chứa đáp án: `re2ob_currencyservice_delay_2` có cả service và loại lỗi.
- `Incident.raw_label` trong bảng chuẩn hóa chứa `service:fault`.
- Các lần chạy của cùng một kịch bản rất giống nhau. Nếu tách chúng ra train và test, model có thể "nhớ" thay vì học.

## 3. Nezha

### Số liệu [REPO] và từ bài báo

| Thư mục raw | Hệ thống | Số lỗi | Loại lỗi |
| --- | --- | ---: | --- |
| `2022-08-22`, `2022-08-23` | OnlineBoutique | 24 + 32 = 56 | cpu_contention, cpu_consumed, network_delay, return, exception |
| `2023-01-29`, `2023-01-30` | TrainTicket (pod `ts-*`) | 28 + 17 = 45 | return, exception, cpu_contention, network_delay |

- Khớp với bài Nezha: OB 56 lỗi, TT 45 lỗi, mỗi lỗi 3 phút (tr. 560). MRCA cũng đánh giá trên dữ liệu này (tr. 1063–1064).
- 101 chuỗi `inject_time` khác nhau, nên có **101 incident**.
- Log nằm trong 303 file CSV, mỗi file 1 phút, tên `HH_MM_log.csv` theo giờ UTC. Tổng 4,175,406 bản ghi, trong đó:
  - 1 bản ghi hỏng: `2023-01-29/log/10_06_log.csv`, bản ghi số 629 tính từ 0, có 10 trường thay vì 8;
  - 124 bản ghi không có `TimeUnixNano`.
- Log có kèm TraceID/SpanID. Dự án **không dùng** trace để giữ điều kiện log-only giống RCAEval.
- Nhãn ở mức pod. Adapter ánh xạ pod → service bằng regex và một danh sách tên cố định.
- Phần log có sẵn quanh mỗi lần tiêm lỗi chỉ khoảng 1–1.5 phút trước và 1.5–2 phút sau (đo trên 3 incident đầu). RCAEval có khoảng 12 phút mỗi bên.

### Thời điểm tiêm lỗi: dùng chuỗi `inject_time`, không dùng epoch

- Chuỗi `inject_time`, đọc theo giờ UTC, khớp với tên file log ở cả 101/101 bản ghi.
- Số epoch `inject_timestamp` của ngày 2023-01-29 sai:
  - 24/28 bản ghi sớm khoảng 8 giờ (lệch UTC+8);
  - hai lần tiêm khác nhau (09:03:53 và 09:12:56, cùng `ts-basic-service`, `return`) bị ghi **cùng một** epoch `1674954273`.
- Vì vậy adapter:
  - lấy thời điểm và ID (`nezha_<epoch tính từ chuỗi inject_time>`) theo chuỗi `inject_time`;
  - ghi độ lệch của epoch vào `manifest.json` (`epoch_mismatch_seconds`).

  Với năm 2022, cách này cho ID trùng với ID cũ.

### Lỗi adapter đã sửa (26/10/2026)

| Lỗi | Hậu quả trước khi sửa | Cách sửa |
| --- | --- | --- |
| Phần tạo incident nằm ngoài vòng `for item in items` | Chỉ ra 21 incident | Tạo đủ trong vòng lặp; bỏ bản ghi trùng hoàn toàn; trùng thời điểm nhưng khác pod hoặc loại lỗi thì báo lỗi |
| `normalize()` chỉ xuất log cho incident đầu tiên | Bảng log gần như rỗng | Xuất mọi incident, mỗi incident một row group |
| `system_id="onlineboutique"` cho mọi incident | 45 lỗi TrainTicket bị ghi sai hệ thống | `SYSTEM_BY_DATE`: 2022 là `ob`, 2023 là `tt` |
| `pd.read_csv` dừng cả file khi gặp 1 bản ghi hỏng | Không đọc được ngày 2023-01-29 | Đọc bằng module `csv`; bản ghi hỏng được ghi lại, không bỏ âm thầm |
| Đọc cả file mẫu `03_53_log.csv` ở thư mục gốc (bản cắt 4,136 dòng của `2022-08-22/log/03_53_log.csv`) | Log của incident đầu bị lặp | Chỉ đọc `<ngày>/log/*.csv` |
| Dùng epoch `inject_timestamp` | 24 incident TrainTicket ra 0 dòng log; 2 lần tiêm bị gộp làm một | Dùng chuỗi `inject_time` (xem trên) |

Cửa sổ [−2 phút, +3 phút] quanh thời điểm tiêm lỗi vẫn là quy tắc tự đặt, chưa đối chiếu với bài báo. Một dòng log nằm trong hai cửa sổ sẽ xuất hiện ở cả hai incident; `verify` có đếm số dòng như vậy.

## 4. Chia tập

**Đơn vị chia:** kịch bản lỗi (117 nhóm), không phải case. Mọi lần chạy của một kịch bản nằm cùng một tập.

**Tỉ lệ:** 70 / 15 / 15 (train / validation / test) theo số kịch bản, phân tầng theo `suite × system` (6 tầng) để mỗi tập có đủ cả lỗi tài nguyên và lỗi code của cả ba hệ thống. Seed 42. Danh sách incident thực tế được lưu vào `splits.parquet` trước khi chạy bất kỳ model nào, và không đổi sau khi đã xem kết quả test.

Ước tính: khoảng 82 / 17 / 18 kịch bản, tức khoảng 250 / 50 / 55 incident. Con số thật phụ thuộc phân tầng.

**Nezha** không chia; toàn bộ dùng làm test ngoài sau khi model đã khóa. Lưu ý OnlineBoutique và TrainTicket cũng có trong RCAEval, nên đây là kiểm tra trên **dữ liệu thu thập khác** của cùng loại ứng dụng, chưa phải hệ thống hoàn toàn mới.

## 5. Danh sách service ứng viên

Với mỗi hệ thống, ứng viên là hợp của các `container_name` xuất hiện trong log tập train. Không thêm service từ đáp án.

Cách này cho phép service không ghi log trong một case (như `productcatalogservice` ở trên) vẫn là ứng viên, vì nó có log ở các case khác cùng hệ thống. Coverage thật phải đo lại sau khi có split.

## 6. Việc cần làm trước khi thực nghiệm

1. ~~Sửa lỗi adapter Nezha, thêm test cho từng lỗi.~~ Xong 26/10/2026 (`tests/test_normalization_pipeline.py`).
2. ~~Bỏ giới hạn 30 case mặc định của RCAEval.~~ Xong: mặc định chuẩn hóa toàn bộ; `--max-cases` chỉ dùng để chạy thử.
3. ~~Sinh `data/normalized/` cho cả hai dataset và chạy `verify`.~~ Xong 27/10/2026, `verify` đạt mọi kiểm tra:
   - RCAEval: 359 incident có log, 49,652,771 dòng (khớp đúng số dòng raw), coverage 92.8%;
   - Nezha: 101 incident, 4,176,325 dòng. Trong đó có 1,044 dòng nằm ở hai cửa sổ chồng nhau nên xuất hiện ở hai incident; 1 bản ghi hỏng và 124 dòng không có timestamp bị loại và có ghi lại. Coverage 100%.

   Chi tiết trong `verification_report.json` của từng thư mục.
4. Sinh `incident_audit.parquet` và `splits.parquet`, rồi khóa split.

## 7. Nguồn và license

- RCAEval: arXiv:2412.17015, doi 10.1145/3701716.3715290. Ghi chú cũ ghi license MIT; cần kiểm lại trên trang dataset trước khi trích.
- Nezha: dữ liệu và code public trên Zenodo và GitHub `IntelligentDDS/Nezha` (bài báo tr. 563).
