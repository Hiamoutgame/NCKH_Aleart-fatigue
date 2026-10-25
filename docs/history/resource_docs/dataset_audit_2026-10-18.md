# Dataset Audit Report: Multi-Dataset Normalization

> **Thời điểm kiểm tra**: 2026-10-18  
> **Mục tiêu**: Kiểm tra cấu trúc trường thực tế (schema audit) của 3 dataset: RCAEval, Nezha, LEMMA-RCA để chuẩn bị cho việc xây dựng Dataset Adapters và Canonical Schema.  
> **Nguyên tắc**: Không suy đoán khi chưa kiểm tra dữ liệu thực tế (FACT-based only).

---

## 1. RCAEval (Primary Dataset)

### 1.1 Tệp dữ liệu thực tế
- **Nguồn**: `phamquiluan/RCAEval` trên Hugging Face.
- **Tệp metadata**: `cases.parquet` (735 cases, 22 cột).
- **Tệp log chi tiết**: `{case_id}/logs.parquet` (chỉ có tại 359/735 cases; 375 cases thuộc suite RE1 không có log, 1 case lỗi thuộc RE2).
- **Tệp phụ trợ khác**: `metrics.parquet`, `traces.parquet` (240 cases), `inject_time.txt`, `root_cause.txt` (8 cases).

### 1.2 Bảng đối chiếu trường (Field Mapping Matrix)

| Trường trong RCAEval | Kiểu thực tế | Tồn tại | Cần ánh xạ sang Canonical | Ghi chú kỹ thuật |
|---|---|---|---|---|
| `cases.parquet: case` | `object` (str) | Có | `Incident.source_case_id`, `Incident.incident_id` | Định danh duy nhất của ca sự cố (vd: `re2ss_carts_cpu_1`) |
| `cases.parquet: dataset` / `system` | `object` (str) | Có | `Incident.dataset_source`, `Incident.system_id` | `system`: `ob`, `ss`, `tt` |
| `cases.parquet: time_start` | `int64` | Có | `Incident.start_time` | Epoch giây $\to$ UTC datetime |
| `cases.parquet: time_end` | `int64` | Có | `Incident.end_time` | Epoch giây $\to$ UTC datetime |
| `cases.parquet: inject_time` | `int64` | Có | `Incident.inject_time` | Epoch giây $\to$ UTC datetime |
| `cases.parquet: fault` / `fault_description` | `object` (str) | Có | `Incident.fault_type`, `GroundTruth.fault_type` | vd: `cpu`, `delay`, `loss`, `f1`,... |
| `cases.parquet: root_cause_service` | `object` (str) | Có | `GroundTruth.original_target`, `GroundTruth.canonical_target` | Nhãn mức service (label_level: `service`) |
| `logs.parquet: timestamp` | `Int64` | Có | `LogEvent.timestamp_utc` | Epoch giây $\to$ UTC datetime |
| `logs.parquet: container_name` | `string` | Có | `LogEvent.service_id`, `LogEvent.entity_id` | Trong RCAEval, `container_name` đóng vai trò là tên microservice |
| `logs.parquet: message` | `string` | Có | `LogEvent.raw_message`, `LogEvent.parsed_message` | Chuẩn hóa template qua `normalize_message` |
| `severity` / `level` | **KHÔNG CÓ** | **Thiếu** | `LogEvent.severity` | Dataset gốc không có cột này. Trích xuất thận trọng từ log header (Log4j/Spring Boot) hoặc để `null` |
| `trace_id` / `span_id` | **KHÔNG CÓ** | **Thiếu** | `LogEvent.trace_id`, `LogEvent.span_id` | Không có trong bảng log (để `null`, trừ một số log Sock Shop có nhúng trong message) |
| `source_file` / `raw_record_ref` | — (Suy xuất) | Có | `LogEvent.source_file`, `LogEvent.raw_record_ref` | Lưu đường dẫn tương đối và `{case_id}#row_{index}` |

---

## 2. Nezha (Secondary Dataset)

### 2.1 Tệp dữ liệu thực tế
- **Nguồn**: `https://github.com/IntelligentDDS/Nezha` (và Zenodo 8276375).
- **Tệp fault metadata**: `rca_data/{date}/{date}-fault_list.json` (chứa danh sách tiêm lỗi theo giờ).
- **Tệp log chi tiết**: `rca_data/{date}/log/{hh}_{mm}_log.csv` (chứa log từng phút, có nanosecond timestamp).

### 2.2 Bảng đối chiếu trường (Field Mapping Matrix)

| Trường trong Nezha | Kiểu thực tế | Tồn tại | Cần ánh xạ sang Canonical | Ghi chú kỹ thuật |
|---|---|---|---|---|
| `fault_list.json: inject_time` | `string` | Có | `Incident.inject_time` | Chuỗi datetime local (vd: `2022-08-22 03:53:54`) $\to$ UTC datetime |
| `fault_list.json: inject_timestamp` | `string` (int) | Có | `Incident.inject_time` | Epoch giây |
| `fault_list.json: inject_pod` | `string` | Có | `GroundTruth.original_target` | Tên pod bị tiêm lỗi (vd: `frontend-579b9bff58-t2dbm`) |
| — | — | **Cần ánh xạ** | `GroundTruth.canonical_target` | Ánh xạ qua regex pod-to-service (vd: `frontend`) |
| `fault_list.json: inject_type` | `string` | Có | `Incident.fault_type`, `GroundTruth.fault_type` | vd: `cpu_contention`, `return`, `exception` |
| `log.csv: Timestamp` | `string` (ISO8601) | Có | Dự phòng | Chuỗi ISO nanosecond |
| `log.csv: TimeUnixNano` | `int64` | Có | `LogEvent.timestamp_utc` | Nanoseconds từ epoch $\to$ UTC datetime |
| `log.csv: PodName` | `string` | Có | `LogEvent.entity_id`, `LogEvent.service_id` | `entity_type="pod"`, `service_id` ánh xạ qua regex pod-to-service |
| `log.csv: Container` | `string` | Có | `LogEvent.entity_type` / metadata | Thường là "server" |
| `log.csv: TraceID` | `string` | Có | `LogEvent.trace_id` | Hex string OpenTelemetry TraceID |
| `log.csv: SpanID` | `string` | Có | `LogEvent.span_id` | Hex string OpenTelemetry SpanID |
| `log.csv: Log` | `string` (nested JSON) | Có | `LogEvent.raw_message`, `LogEvent.severity` | Nested JSON. Cần parse JSON để lấy `message` và `severity` |
| Phân đoạn Incident | **KHÔNG CÓ CỘT INCIDENT_ID** | **Cần xử lý** | `LogEvent.incident_id` | Ghép nối log vào Incident dựa vào cửa sổ thời gian xung quanh `inject_time` của `fault_list.json` |

---

## 3. LEMMA-RCA (External Validation Dataset)

### 3.1 Tệp dữ liệu thực tế
- **Nguồn**: `Lemma-RCA-NEC/Product_Review_Original` trên Hugging Face.
- **Tệp log chi tiết**: Elasticsearch scroll JSON dump (vd: `app-000174log20210517_132254.json`, 10.000 records/file).
- **Tệp metadata & Ground Truth**: `LEMMA_RCA_20220606_Scenario_GroundTruth.pptx`, `pod_topology/`.

### 3.2 Bảng đối chiếu trường (Field Mapping Matrix)

| Trường trong LEMMA-RCA | Kiểu thực tế | Tồn tại | Cần ánh xạ sang Canonical | Ghi chú kỹ thuật |
|---|---|---|---|---|
| `hits._id` | `string` | Có | `LogEvent.source_row_id`, `LogEvent.raw_record_ref` | Định danh duy nhất từ Elasticsearch |
| `_source.@timestamp` | `string` (ISO8601) | Có | `LogEvent.timestamp_utc` | ISO 8601 UTC timestamp |
| `_source.kubernetes.container_name` | `string` | Có | `LogEvent.service_id` | Tên microservice (vd: `productpage`, `reviews`) |
| `_source.kubernetes.pod_name` | `string` | Có | `LogEvent.entity_id` | `entity_type="pod"` |
| `_source.message` | `string` | Có | `LogEvent.raw_message`, `LogEvent.parsed_message` | Message thô |
| `_source.level` | `string` | Có (nhưng thường "unknown") | `LogEvent.severity` | Nếu là "unknown", trích xuất bằng regex header hoặc để `null` |
| Ground Truth metadata | Tài liệu kịch bản / PPTX | Có ngoài file | `Incident`, `GroundTruth` | 4 kịch bản lỗi: DDoS OOM, JMeter stress, Storage failure, Noisy neighbor |
| `trace_id` / `span_id` | **KHÔNG CÓ TRONG LOG APP** | **Thiếu** | `LogEvent.trace_id`, `LogEvent.span_id` | Nằm ở modality Trace riêng (Jaeger), không có trong bảng log ES (để `null`) |

---

## 4. Tổng hợp & Kết luận cho Canonical Schema

1. **Timestamp**:
   - RCAEval dùng Epoch giây (`int64`).
   - Nezha dùng `TimeUnixNano` (`int64`).
   - LEMMA-RCA dùng ISO 8601 string (`@timestamp`).
   $\to$ Canonical Schema chuẩn hóa toàn bộ về **UTC datetime** (ISO 8601 / timezone-aware UTC datetime).
2. **Service & Pod Entity**:
   - RCAEval: Chỉ có `container_name` (được dùng trực tiếp làm `service_id`).
   - Nezha: Có `PodName`, cần regex phân giải thành `service_id`.
   - LEMMA-RCA: Có cả `container_name` và `pod_name`.
3. **Traceability (Truy nguyên)**:
   - RCAEval: `{case_id}/logs.parquet#row_{index}`.
   - Nezha: `{file_name}#row_{index}`.
   - LEMMA-RCA: `{file_name}#{_id}`.
4. **Severity**:
   - Tuyệt đối không tự bịa đặt. Chỉ ghi nhận khi có trong raw JSON (Nezha) hoặc parse được tường minh từ header log. Nếu không xác định được, giữ `null`.
