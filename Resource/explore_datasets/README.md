# explore_datasets — RCAEval, LEMMA-RCA, Nezha

Code khám phá và chuẩn hóa cho ba dataset. Xem [bản đồ Resource](../README.md)
để phân biệt raw, artifact và normalized.

| Slug | Code chính | Raw mặc định |
| --- | --- | --- |
| `rcaeval` | `src/datasets/rcaeval/infrastructure/adapter.py` | `../cp1/raw_data/huggingface/rcaeval/` |
| `lemma_rca` | Loader, downloader, adapter, CLI trong `src/datasets/lemma_rca/` | `../cp1/raw_data/huggingface/lemma_rca/` |
| `nezha` | `src/datasets/nezha/infrastructure/adapter.py` | `../cp1/raw_data/nezha/` |

Từ root repository:

```bash
bash run_datasets.sh list
bash run_datasets.sh inspect all
bash run_datasets.sh normalize all --output-root /tmp/normalized-preview
bash run_lemma_rca.sh logs --service productpage --limit 5
```

Hoặc từ thư mục này:

```bash
.venv/bin/python run_datasets.py inspect all
.venv/bin/python run_lemma_rca.py profile --limit 1000
```

`run_datasets.py` là entrypoint chung, `run_lemma_rca.py`/`run_lemma.sh` là CLI chi tiết
cho LEMMA. `export_all_normalized.py` tương thích lệnh cũ, gọi `normalize all` với tên
output chuẩn `lemma_rca`. `extract_lemma_logs.py` hỗ trợ DataFrame/CSV/JSON xem nhanh;
`audit_datasets.py` in schema raw. `output/` chứa file khám phá đã xuất trước đó.

`src/interface/` ghép ba adapter vào CLI. `src/shared/` giữ canonical schema và profiler.
Helper normalization/severity/path ở `src/shared/infrastructure/`; không cần import `cp1_core`.
Mỗi adapter hỗ trợ `data_root` tùy chọn. `dataset.yaml` là mô tả mapping, chưa được
loader tự đọc để thay đường dẫn runtime.

Raw chỉ đọc. Lệnh normalize ghi ba bảng Parquet vào `<output-root>/<slug>/`;
output-root mặc định là `Resource/datasets/normalized/`. CSV/JSON từ CLI LEMMA khác
schema canonical Parquet. Phạm vi sample và giới hạn segmentation được ghi trong
[validation report](../docs/validation_report.md).
