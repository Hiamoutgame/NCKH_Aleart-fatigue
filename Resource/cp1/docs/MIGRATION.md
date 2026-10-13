# CP1 migration note

## Workflow mới

| Mục tiêu cũ | Lệnh mới |
|---|---|
| Kiểm tra schema RCAEval | `python cp1/src/main_RCAEval.py inspect` |
| Quét warning toàn bộ local snapshot | `python cp1/src/main_RCAEval.py scan-warnings` |
| Phân tích normal/faulty window | `python cp1/src/main_RCAEval.py timing` |
| Kiểm chứng template warning | `python cp1/src/main_RCAEval.py verify` |
| Chạy chuỗi RCAEval | `python cp1/src/main_RCAEval.py all` |

Mọi lệnh chạy từ root repository, ưu tiên dùng `.venv/Scripts/python`.

## Khác biệt cấu trúc

- `_warning_per_case.csv` mới nằm ở `artifacts/rcaeval/tables/` và đã có sẵn
  `suite`, `system`, `sys`, `sys2`; không còn cần `recompute_per_system.py`.
- Dữ liệu tải về nằm ở `raw_data`, không dùng cache ẩn làm nguồn chính.
- Script cũ và output cũ giữ nguyên trong `legacy` để bảo toàn số liệu lịch sử.
- Normalization mới dùng một implementation duy nhất dựa trên
  `legacy/scripts/final_verification.py`.

## Lưu ý về kết quả

Refactor không đổi research question, metric hay scope CP1. Số template trong
output mới có thể khác report cũ nếu script cũ từng dùng normalization khác;
đó là thay đổi được ghi nhận rõ, không phải dữ liệu raw bị sửa.
