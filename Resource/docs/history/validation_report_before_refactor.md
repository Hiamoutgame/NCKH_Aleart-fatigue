# Validation & Compatibility Report: Multi-Dataset Normalization

> **Thời điểm thực hiện**: 2026-10-18  
> **Phạm vi kiểm thử**: RCAEval, Nezha, LEMMA-RCA  
> **Bộ test**: `Resource/explore_datasets/tests/test_canonical_validation.py` (8/8 PASSED)  
> **Tổng số test toàn bộ explore_datasets**: 27/27 PASSED (100%)

---

## 1. Kết quả kiểm chứng 8 tiêu chí cốt lõi (Automated Validation Matrix)

| # | Tiêu chí (Test) | Kết quả mong đợi | Kết quả RCAEval | Kết quả Nezha | Kết quả LEMMA-RCA | Đánh giá |
|---|---|---|---|---|---|---|
| 1 | **Raw preservation** | Không mất hoặc chỉnh sửa log gốc | `raw_message` giữ nguyên 100% | `raw_message` bóc tách từ nested JSON mà không sửa text | `raw_message` giữ nguyên từ trường `message` của ES | **ĐẠT (PASSED)** |
| 2 | **Traceability** | Mọi log truy ngược được bản ghi nguồn | Lưu `{case_id}/logs.parquet#row_{idx}` | Lưu `{csv_file}#row_{idx}` | Lưu `{json_file}#{_id}` | **ĐẠT (PASSED)** |
| 3 | **Timestamp UTC** | Chuẩn hóa về UTC và đúng đơn vị | Epoch s $\to$ `datetime[UTC]` | TimeUnixNano $\to$ `datetime[UTC]` | ISO8601 $\to$ `datetime[UTC]` | **ĐẠT (PASSED)** |
| 4 | **Service mapping** | Không tự tạo service không có bằng chứng | `container_name` $\equiv$ service | Regex pod-to-service đối chiếu từ manifest K8s | `container_name` / `pod_name` prefix | **ĐẠT (PASSED)** |
| 5 | **Ground truth** | Giữ đúng nhãn gốc và cấp độ nhãn | Service level (`cases.parquet`) | Pod level (`fault_list.json`) $\to$ canonical service | Service level (Scenario PPTX) | **ĐẠT (PASSED)** |
| 6 | **Incident segmentation** | Log được gán incident có căn cứ | Gắn theo `case_id` | Cửa sổ thời gian $[T_{\text{inj}} - 2m, T_{\text{inj}} + 3m]$ | Scenario ID | **ĐẠT (PASSED)** |
| 7 | **Label leakage** | Ground truth không rò rỉ vào model input | `LogEvent` không chứa nhãn GT | `LogEvent` không chứa nhãn GT | `LogEvent` không chứa nhãn GT | **ĐẠT (PASSED)** |
| 8 | **Determinism** | Chạy lại cho cùng kết quả | Idempotent | Idempotent | Idempotent | **ĐẠT (PASSED)** |

---

## 2. Chi tiết Normalization của từng Dataset

### 2.1 RCAEval (Primary Dataset)
- **Tình trạng dữ liệu**: Đã kiểm chứng 735 cases metadata và các case log có sẵn tại local.
- **Ánh xạ Entity**: `container_name` là đơn vị microservice duy nhất trong RCAEval. Đã ánh xạ $1:1$ sang `service_id` và `entity_id` (`entity_type="container"`).
- **Xử lý Severity**: Dataset gốc không có cột `severity`. Adapter áp dụng bộ parser log header Log4j/Spring Boot; nếu không có header tường minh, trường `severity` được giữ là `null` (không tự gán mặc định `INFO` để tránh nhiễu).
- **Đánh giá mức độ sẵn sàng cho Log Grouping & RCA**: **SẴN SÀNG CAO (Primary)**. Cấu trúc case phân lập rõ ràng, nhãn root cause service chuẩn xác.

### 2.2 Nezha (Secondary Dataset)
- **Tình trạng dữ liệu**: Đã tích hợp `fault_list.json` (24 incidents tiêm lỗi) và log CSV (`03_53_log.csv` với 4.136 bản ghi chi tiết).
- **Ánh xạ Entity**: `PodName` (vd: `frontend-579b9bff58-t2dbm`) được phân giải qua regex chính xác sang canonical microservice (vd: `frontend`).
- **Xử lý Nested JSON & Nanoseconds**: Bóc tách trường lồng `Log -> log -> message/severity`. Chuyển đổi `TimeUnixNano` thành timezone-aware UTC datetime.
- **Trace & Span Correlation**: Giữ nguyên `TraceID` và `SpanID` trong `LogEvent` để phục vụ cho các thuật toán phân tích lan truyền lỗi (Cascading).
- **Đánh giá mức độ sẵn sàng cho Log Grouping & RCA**: **SẴN SÀNG CAO (Secondary)**. Cực kỳ giá trị cho việc đánh giá lan truyền và gom nhóm alert nhờ có TraceID/SpanID đầy đủ.

### 2.3 LEMMA-RCA (External Validation Dataset)
- **Tình trạng dữ liệu**: Đã tích hợp 2 file log Elasticsearch dump (20.000 log records) và 4 kịch bản lỗi chuẩn (DDoS OOM, JMeter stress, Storage failure, Noisy neighbor).
- **Ánh xạ Entity**: Bóc tách `kubernetes.container_name` làm `service_id` và `pod_name` làm `entity_id`.
- **Giới hạn kỹ thuật**: Log thô của LEMMA không chứa Trace ID / Span ID trong tầng log ứng dụng (Trace được lưu ở backend Jaeger riêng). Nhãn mức cảnh báo `WARNING` trong dữ liệu gốc rất hiếm do bộ từ khóa chỉ gom `error`, `exception`, `critical`.
- **Đánh giá mức độ sẵn sàng**: **PHÙ HỢP CHO EXTERNAL VALIDATION (Scenario-level)**. Không nên dùng làm tập huấn luyện chính nhưng rất tốt để kiểm thử độ tổng quát (generalizability) của thuật toán gom nhóm.

---

## 3. Khuyến nghị cho Nghiên cứu tiếp theo (Next Steps)
1. Sử dụng **RCAEval** làm tập dữ liệu chuẩn chính thức (Primary Benchmark) để chạy cả 4 Arms: Rule-based, Semantic-only, Temporal-spatial, và LLM Agent.
2. Sử dụng **Nezha** để kiểm chứng Arm 3 (Temporal-Spatial) và ablation study về Topology/Cascading nhờ ưu thế có TraceID/SpanID đồng nhất giữa log và trace.
3. Sử dụng **LEMMA-RCA** cho external validation trên kịch bản DDoS OOM và JMeter stress để kiểm tra khả năng chuyển giao mô hình (cross-dataset evaluation).
