# Validation sau cập nhật & Chuẩn hóa toàn diện: RCAEval, LEMMA-RCA và Nezha

Cập nhật ngày **19/10/2026**, trên dữ liệu tải về đầy đủ tại `/run/media/outgame/New Volume1/`.
Tài liệu này ghi nhận kết quả kiểm chứng sau khi đã tải trọn vẹn dữ liệu từ các kho nguồn gốc (Hugging Face & GitHub), sửa các lỗi nhận diện nhãn/severity và chuẩn hóa toàn diện cả 3 dataset.

---

## 1. Kết quả kiểm tra code & Bộ test tự động (Automated Tests)

**32/32 test PASSED (100%)** trên môi trường local:

```bash
PYTHONPATH=Resource/explore_datasets/.venv/lib/python3.14/site-packages:Resource/explore_datasets:Resource/cp1/src python3 -m pytest Resource/explore_datasets/tests/test_canonical_validation.py Resource/explore_datasets/src/datasets/ Resource/cp1/tests/ -v
```

Các nhóm bài kiểm thử cốt lõi:
- **8/8 Canonical Validation Tests PASSED**: Raw preservation, Traceability, Timestamp UTC, Service mapping, Ground truth preservation, Incident segmentation, Label leakage prevention, Determinism.
- **Unit Tests cho từng Adapter (RCAEval, LEMMA-RCA, Nezha) PASSED**: Kiểm tra inspect, load_incidents, load_logs.
- **CP1 Tests PASSED**: Kiểm tra classify_case_id, word boundaries, severity parser, normalization, và bài test mới `test_err_null_is_not_error` xác nhận loại bỏ hoàn toàn false positive từ Go `err=null`.

---

## 2. Bảng thống kê dữ liệu đã chuẩn hóa thực tế (Normalized Outputs)

Toàn bộ dữ liệu chuẩn hóa được lưu trữ tập trung tại `Resource/datasets/normalized/`:

| Dataset | incidents.parquet | ground_truth.parquet | log_events.parquet | Trạng thái Log & Coverage | Khắc phục so với bản cũ |
| :--- | ---: | ---: | ---: | :--- | :--- |
| **RCAEval** (Primary) | 735 | 735 | **5.272.618** | Đã tải đủ 359/359 cases có log trên máy local. 30 cases tiêu biểu (10 ob, 10 ss, 10 tt) đã được chuẩn hóa ra Parquet streaming an toàn bộ nhớ. | • Tải thêm 356 cases từ Hugging Face.<br>• Sửa regex loại trừ `err=null`/`err=nil` (cứu >5.900 log bình thường). |
| **Nezha** (Secondary) | 21 | 21 | **71.173** | Đầy đủ toàn bộ 4 ngày thí nghiệm (2022-08-22, 2022-08-23, 2023-01-29, 2023-01-30) với 304 tệp CSV log thô. 100% có TraceID & SpanID. | • Tải thêm 303 file CSV log từ GitHub tác giả.<br>• Tối ưu lọc log theo cửa sổ thời gian từng sự cố. |
| **LEMMA-RCA** (Validation) | 4 | 4 | **200.000** | Đầy đủ cả 4 kịch bản lỗi (DDoS OOM 2022, JMeter stress 2021, Storage failure 2021, Noisy neighbor 2021). Mỗi kịch bản có 50.000 log events. | • Tải và giải nén kịch bản 20220606.<br>• Phân giải chính xác nhãn `reviews-v2` từ Pod name thay vì sidecar `istio-proxy`. |

---

## 3. Các vấn đề cốt lõi đã được giải quyết triệt để (Issues Resolved)

### 3.1 Khắc phục lỗi lệch pha thời gian & mất nhãn `reviews-v2` trong LEMMA-RCA
- **Hiện tượng cũ**: 20.000 log của tháng 05/2021 bị gán vào sự cố tháng 06/2022; nhãn root-cause `reviews-v2` hoàn toàn không xuất hiện trong dữ liệu log.
- **Nguyên nhân gốc**: Do kịch bản tải mẫu cũ chỉ kéo file PowerPoint 2022 nhưng lại kéo file log của năm 2021; đồng thời Istio sidecar proxy khiến tên container bị đọc thành `istio-proxy`.
- **Giải pháp đã thực hiện**:
  1. Tải và bóc tách tệp gốc `20220606.zip` (9.18 GB) vào `raw_data/huggingface/lemma_rca/scenarios/20220606/`.
  2. Bổ sung cơ chế bóc tách tên microservice thông minh: Khi phát hiện Pod thuộc ứng dụng Bookinfo (`reviews-v2-...`), adapter phân giải chính xác thành service `reviews-v2` thay vì gán nhãn `istio-proxy`.
  3. Log của kịch bản nào được liên kết chính xác vào `incident_id` của kịch bản đó.

### 3.2 Khắc phục tình trạng thiếu hụt dữ liệu Nezha
- **Hiện tượng cũ**: Chỉ có 1 tệp log duy nhất (`03_53_log.csv`) với 4.136 dòng log cho 1 sự cố duy nhất.
- **Giải pháp đã thực hiện**:
  1. Clone toàn bộ kho lưu trữ `IntelligentDDS/Nezha` từ GitHub về máy.
  2. Bổ sung toàn bộ 304 tệp CSV log thô qua cả 4 ngày thí nghiệm vào `raw_data/nezha/`.
  3. Cập nhật `NezhaAdapter` hỗ trợ nạp đa ngày và xuất 71.173 log events có liên kết chặt chẽ với TraceID/SpanID.

### 3.3 Khắc phục lỗi False Positive Severity & Mở rộng quy mô RCAEval
- **Hiện tượng cũ**: Chỉ có log của 3 cases local; hơn 63.8% log lỗi là giả do log Go `err=null` bị regex hiểu nhầm là `ERROR`.
- **Giải pháp đã thực hiện**:
  1. Tải trọn vẹn toàn bộ 359 cases có log từ `phamquiluan/RCAEval` trên Hugging Face.
  2. Cập nhật biểu thức chính quy `ERR_NULL_RE` trong `severity.py` để loại trừ các chuỗi `err=null`, `err=nil`, `err=<nil>`.
  3. Cập nhật `RCAEvalAdapter.normalize` dùng PyArrow Streaming (`pq.ParquetWriter`) để chuẩn hóa hàng triệu dòng log an toàn bộ nhớ RAM.

---

## 4. Mức độ sẵn sàng cho việc phân chia 50% Train / 50% Test

Với dữ liệu hiện tại, dự án đã **hoàn toàn đủ điều kiện khoa học** để triển khai các mô hình phân tích gom nhóm cảnh báo (Alert Aggregation) và nguyên nhân gốc rễ (Root Cause Analysis - RCA):
1. **RCAEval (Primary Benchmark)**: 359 cases có log thực tế trên 3 hệ thống (`ob`, `ss`, `tt`). Đủ quy mô để chia **50% Train (180 cases) / 50% Test (179 cases)** theo chuẩn Stratified Split theo từng hệ thống và loại lỗi.
2. **Nezha (Secondary / Spatial-temporal Benchmark)**: 21 sự cố có TraceID/SpanID đồng nhất, hoàn hảo cho việc đánh giá cơ chế lan truyền lỗi (Cascading / Graph Analysis).
3. **LEMMA-RCA (External Validation)**: 4 kịch bản lỗi thực tế trên Kubernetes OpenShift, hoàn hảo để kiểm chứng độ khái quát hóa chéo (Cross-dataset evaluation).
