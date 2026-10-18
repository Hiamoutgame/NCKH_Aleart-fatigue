# lemma_rca — LEMMA-RCA

> Vai trò: **backup** (Dự phòng cho RCAEval khi cần phân tích log hệ thống phân tán microservice)  
> Nguồn: [Lemma-RCA-NEC/Product_Review_Original](https://huggingface.co/datasets/Lemma-RCA-NEC/Product_Review_Original) (HuggingFace)  
> Local: `Resource/cp1/raw_data/huggingface/lemma_rca`  

## 1. Dữ liệu có gì
- Dataset được thu thập bởi NEC Labs trên nền tảng **OpenShift OKD**, triển khai các hệ thống microservices như **Book-Info** và **Sock-Shop**.
- Đầy đủ 3 trụ cột Observability:
  1. **Logs**: Export từ Elasticsearch (`app-*` cho container ứng dụng, `infra-*` cho node/journald/k8s components).
  2. **Metrics**: Thu thập qua Prometheus (CPU usage, memory usage, bandwidth, network packets).
  3. **Traces**: Trích xuất qua Jaeger (`jaeger-span-*` JSON) ghi nhận traceID, spanID, duration và HTTP error status (503).
- **Ground Truth 4 kịch bản lỗi thực tế**:
  - `lemma-20220606-ddos-oom`: Tấn công DDoS quá tải mạng dẫn đến Java OOM crash tại pod `reviews-v2`, `reviews-v3`, làm `productpage` trả về HTTP 503.
  - `lemma-20210517-jmeter-stress`: Stress test tải cao 49 giờ bằng JMeter với 176,400 requests gây nghẽn CPU và mạng.
  - `lemma-20211203-storage-failure`: Sự cố storage NFS gắn ngoài khiến MongoDB lỗi I/O và sụt giảm hiệu năng.
  - `lemma-20210524-noisy-neighbor`: Tranh chấp tài nguyên CPU giữa các tiến trình trên cùng worker node.

## 2. Schema log và Mapping cột canonical
| Cột Canonical | Nguồn Elasticsearch JSON (`_source`) | Ghi chú |
| --- | --- | --- |
| `timestamp` | `@timestamp` | Định dạng ISO 8601 (UTC) |
| `service` | `kubernetes.container_name` hoặc `systemd.COMM` | Tên service (productpage, reviews, details...) |
| `level` | Regex trích xuất từ `message` (DEBUG, INFO, WARN, ERROR) | Field `level` gốc trong ES thường là "unknown" |
| `message` | `message` | Chuỗi log gốc của ứng dụng |
| `pod` | `kubernetes.pod_name` | Tên pod Kubernetes cụ thể |
| `host` | `kubernetes.host` hoặc `hostname` | Tên worker node OpenShift |
| `log_type` | Tiền tố index/file (`app` vs `infra`) | Phân loại log ứng dụng hay log hạ tầng |
| `root_cause` | Ground Truth kịch bản | Gán nhãn nguyên nhân gốc rễ theo kịch bản |

## 3. Cách lấy dữ liệu (Fetch) & Khám phá (CLI)

### Chế độ SAMPLE (Khuyến nghị - ~47MB, hoàn thành sau ~10s):
Trích xuất trực tiếp log JSON mẫu và slide Ground Truth qua HTTP Range requests:
```bash
PYTHONPATH=Resource/explore_datasets Resource/explore_datasets/.venv/bin/python -m src.datasets.lemma_rca.interface.cli fetch --mode sample
```

### Xem profile 4 tiêu chí bắt buộc (Shape, Columns, Head, Value Counts):
```bash
PYTHONPATH=Resource/explore_datasets Resource/explore_datasets/.venv/bin/python -m src.datasets.lemma_rca.interface.cli profile
```

### Xem danh sách sự cố Ground Truth:
```bash
PYTHONPATH=Resource/explore_datasets Resource/explore_datasets/.venv/bin/python -m src.datasets.lemma_rca.interface.cli list-incidents
PYTHONPATH=Resource/explore_datasets Resource/explore_datasets/.venv/bin/python -m src.datasets.lemma_rca.interface.cli show-incident --id lemma-20220606-ddos-oom
```

### Lọc và xem trực tiếp nội dung log:
```bash
# Xem 10 log ERROR gần nhất:
PYTHONPATH=Resource/explore_datasets Resource/explore_datasets/.venv/bin/python -m src.datasets.lemma_rca.interface.cli logs --level ERROR --limit 10

# Xem log của service productpage:
PYTHONPATH=Resource/explore_datasets Resource/explore_datasets/.venv/bin/python -m src.datasets.lemma_rca.interface.cli logs --service productpage --limit 10
```

## 4. Tiêu chí Done
- [x] Schema thực tế được kiểm chứng: file Elasticsearch scroll JSON 10,000 hits.
- [x] Đã map đầy đủ: timestamp, service, level, message, pod, host, root_cause.
- [x] Profile được 4 tiêu chí: Shape (10,000+, 8), Columns, Head(10), Value Counts (service, level, log_type).
- [x] Đã có tài liệu và kịch bản Ground Truth trích xuất từ slide tài liệu chính thức (`README.pptx`).
- [x] Có kiểm thử tự động (`pytest`) đạt 100% pass.
- [x] Có notebook trực quan (`explore_lemma_rca.ipynb`).

## 5. Cảnh báo diễn giải (BẮT BUỘC)
- Message hoặc service xuất hiện nhiều KHÔNG nhất thiết là nguyên nhân sự cố.
- Tần suất là độ phổ biến, không phải mức nghiêm trọng hay quan hệ nhân quả.
- Khi điều tra root cause, cần kết hợp đối chiếu mốc thời gian tiêm lỗi (`inject_time`) và đồ thị phụ thuộc pod/service.
