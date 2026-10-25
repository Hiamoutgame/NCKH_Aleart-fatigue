# shared/domain — entities và ports hiện có

- `models.py`: ColumnProfile và DatasetProfile; không có DatasetSource class trong source hiện tại.
- `canonical.py`: Incident, LogEvent (**log_id**), GroundTruth và chuyển đổi DataFrame.
- `ports.py`: BaseDatasetAdapter với inspect/load_incidents/load_logs/load_ground_truth/normalize.

**Dependency hiện tại:** `canonical.py` có import pandas; không mô tả toàn bộ domain là thuần Python/không pandas. Tách conversion khỏi domain là hướng cải thiện kiến trúc, chưa thực hiện trong lần cập nhật docs.

Chưa có Group/Edge/Ranking entities. [Protocol V3](../../../docs/research/research_protocol_v3.md) là thiết kế mới, chưa phải contract runtime. Incident chứa raw_label/fault_type/inject_time; không feed nguyên record vào model. Source references và mapping_status cần audit, không tự chứng nhận traceability/label correctness.
