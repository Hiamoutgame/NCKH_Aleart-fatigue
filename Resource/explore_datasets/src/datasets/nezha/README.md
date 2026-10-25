# nezha — secondary/external dataset candidate

Raw thật từ root: `NCKH_rawData/raw_data/nezha/`. Source mặc định vẫn trỏ CP1 cũ; dùng `--data-root`. Chưa có downloader Nezha trong workflow adapter.

## 1. Source và canonical mapping

`infrastructure/adapter.py` tìm fault lists nhiều ngày và CSV log; đọc `TimeUnixNano`, `PodName`, `Log`, `TraceID`, `SpanID`. Message/severity được tách từ JSON lồng; `raw_message` giữ extracted message, không toàn payload CSV. Muốn phục hồi raw record phải giữ file và resolve row/source reference.

Incident là quy tắc `[-2 phút,+3 phút]` quanh inject epoch. Nhãn gốc mức pod; service target từ regex/fallback pod prefix. Đây là mapping cần kiểm chứng inventory/alias, không tự trở thành service GT đã xác minh. Window overlap, missing timestamps, trace/span completeness và clock precision chưa được audit toàn corpus.

## 2. Giới hạn code cần xử lý

- `inspect()` đếm fault list đầu tiên, không toàn bộ ngày.
- `load_incidents()`/`load_ground_truth()` tạo record ngoài vòng `for item in items`, nên bucket nhiều fault chỉ tạo từ item cuối. Fixture tổng hợp hai faults cùng bucket đã tái hiện: inspect=2 nhưng loaded incidents=1 và GT=1. Không suy con số này thành thống kê corpus.
- `normalize()` xuất metadata nhiều incidents nhưng chỉ logs incident đầu.
- ID chứa incident và CSV stem/row; cùng source record có thể thuộc nhiều windows. Cần source identity độc lập để tránh split leakage.

## 3. Lệnh từ root

```bash
bash run_datasets.sh inspect nezha --data-root NCKH_rawData/raw_data/nezha
```

Inspect liệt kê metadata/file paths, chưa kiểm chứng incident eligibility. Nếu normalize, dùng output riêng theo [exploration README](../../../README.md); code hiện vẫn có các giới hạn trên.

## 4. Bằng chứng hiện có

Footer canonical 23/10: **21 incident rows, 21 GT rows, 71,173 log rows**. Chưa đo unique incident log coverage, completeness labels/trace/span hoặc raw reconstruction. Báo cáo lịch sử có mẫu 24 annotations trong một ngày; các count khác scope, không đồng nhất với số rows canonical.

[Implementation status](../../../../docs/implementation_status.md) và [validation](../../../../docs/validation_report.md). Trace/span ID hoặc cạnh gọi quan sát không tự chứng minh causal fault propagation. Chưa có graph/ranker V3 trong module này.
