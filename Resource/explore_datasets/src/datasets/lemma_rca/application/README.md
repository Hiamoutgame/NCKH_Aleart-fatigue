# application — LEMMA-RCA exploration use cases

Source hiện có trong `use_cases.py`: describe_lemma_use_case, inspect_lemma_logs_use_case, export_lemma_logs_use_case, list_lemma_incidents_use_case, get_lemma_incident_use_case và fetch_lemma_use_case.

Use cases hiện gọi concrete loader/downloader từ infrastructure; không mô tả là chỉ gọi domain hoặc đã hoàn toàn tách I/O. Đây là đường khám phá dữ liệu, không service RCA model. Danh sách incidents lấy từ scenario hard-code; cột root_cause trong exploration là heuristic, không GT log-level.

[Dataset README](../README.md) nêu commands/raw paths và [implementation status](../../../../../docs/implementation_status.md) nêu giới hạn trước V3 training.
