# Thêm dataset vào workspace V3

Áp dụng khi chủ động mở rộng dataset; không phải yêu cầu thêm nguồn mới trong lần cập nhật docs. [src README](../README.md) và [protocol V3](../../../docs/research_protocol_v3.md) là context.

## Các bước

1. Audit schema, incident identity, timestamps/timezone, service inventory, raw provenance và label level/multiplicity. Nguồn chưa có service labels vẫn có thể dùng grouping, chưa claim RCA eligibility.
2. Copy `src/datasets/_template/` sang `<slug>`; ghi README và `dataset.yaml` là metadata mô tả.
3. Implement `BaseDatasetAdapter` trong infrastructure: inspect, load_incidents, load_logs, load_ground_truth, normalize. Canonical schema dùng `log_id`, giữ raw/source refs; không thêm đáp án vào inference fields.
4. Ghi rõ sampling/caps, error behavior, timezone assumptions, alias mapping và output scope. Không gán verified chỉ vì regex trả về chuỗi.
5. Đăng ký slug ở `src/interface/datasets_cli.py` và runtime default ở `src/shared/infrastructure/paths.py`. Sửa YAML riêng chưa đủ; không thêm CP1 registry giả khi CP1 source vắng mặt.
6. Update registry README và CLI docs. Chỉ thêm use cases/CLI riêng khi cần; tránh import chéo datasets.
7. Kiểm tra có ý nghĩa bằng fixture độc lập: mapping nguồn, raw reconstruction, incident/window boundary, label multiplicity, determinism, unknown handling và custom input/output roots. Test không được ghi đè raw.
8. Chỉ đưa vào external evaluation sau audit và trước tuning; giữ split/source-group policy của nghiên cứu.

## Gate

Profiler đọc được shape/columns/head/counts trên scope được ghi rõ; canonical records resolve đúng nguồn; eligibility/exclusions có evidence; inventory không lấy từ ground truth. Không lấy một mẫu pass hoặc ba file output tồn tại làm chứng nhận toàn dataset đủ train/test.
