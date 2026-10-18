# Nezha

Dataset secondary, dữ liệu local ở `Resource/cp1/raw_data/nezha/`:
`fault_list.json` (24 incident) và `03_53_log.csv` (4.136 record).

`infrastructure/adapter.py` chứa `NezhaAdapter`: đọc fault metadata, tạo cửa sổ
[-2 phút, +3 phút] quanh inject time, map PodName sang service, parse nested JSON
trong cột Log, giữ TraceID/SpanID và chuyển timestamp nanosecond về UTC.

Từ root repository:

```bash
bash run_datasets.sh inspect nezha
bash run_datasets.sh normalize nezha --output-root /tmp/normalized-preview
```

Adapter hiện export log cho incident đầu tiên; metadata/ground truth chứa cả 24
incident. Chưa có downloader Nezha tự động. Dùng `--data-root` nếu input ở nơi khác.
Schema chung tại `src/shared/domain/canonical.py`; helper chung tại
`src/shared/infrastructure/`. Các thư mục layer còn lại là sườn để mở rộng.
