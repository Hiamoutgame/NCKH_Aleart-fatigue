# rcaeval — RCAEval

> Vai trò: **primary**
> Nguồn: phamquiluan/RCAEval (HuggingFace)
> Local: Resource/cp1/raw_data/huggingface/rcaeval

## 1. Dữ liệu có gì
- 735 case; chỉ 359/735 case có log (suite RE1 gồm 375 case metric-only).
- logs.parquet của từng case chỉ có 3 cột: timestamp, container_name, message.
- Không có cột severity/level; service chính là container_name.
- Khoảng 49,6 triệu dòng log; dòng chứa WARN rất hiếm (khoảng 0,02%).
- Một case chứa log của nhiều service, không chỉ service bị inject.
- Thời gian: time_start, inject_time, time_end (epoch giây).

## 2. Đọc một incident
| Khái niệm | Cột |
| --- | --- |
| Đơn vị incident | case |
| id | case |
| timestamp | timestamp |
| service | container_name |
| message | message |
| severity | (không có) |
| root cause | root_cause_service |

## 3. Code và lệnh hiện tại

`infrastructure/adapter.py` chứa `RCAEvalAdapter`: đọc metadata, incident,
ground truth và log của tất cả case đang có local. Hiện local có 3 case log,
tổng 405.960 dòng; số liệu đầy đủ ở mục 1 là phạm vi khảo sát lịch sử.

Từ root repository:

```bash
bash run_datasets.sh inspect rcaeval
bash run_datasets.sh normalize rcaeval --output-root /tmp/normalized-preview
```

Dùng `--data-root` để đổi input. `normalize` xuất ba bảng Parquet chung schema.
Các thư mục layer khác đang là sườn; logic runtime tập trung trong adapter.

## 5. Cảnh báo diễn giải
- message xuất hiện nhiều KHÔNG nhất thiết là lỗi.
- service có nhiều log KHÔNG nhất thiết là service gây ra sự cố.
- Tần suất không phải nhân quả.
