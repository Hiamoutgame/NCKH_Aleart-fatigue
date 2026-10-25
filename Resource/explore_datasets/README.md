# explore_datasets — đọc và chuẩn hóa ba dataset

**23/10/2026.** Đây là phần code chuẩn bị dữ liệu cho [V3 log organization + service RCA](../../NCKH_MASTER_CONTEXT_2026-10-23.md), chưa phải pipeline grouping/ranking hoàn chỉnh. [Resource map](../README.md) phân biệt raw/source/normalized.

| Slug | Source adapter | Raw thật từ root repo |
| --- | --- | --- |
| `rcaeval` | `src/datasets/rcaeval/infrastructure/adapter.py` | `NCKH_rawData/raw_data/huggingface/rcaeval/` |
| `lemma_rca` | Adapter + loader/downloader/application/CLI trong `src/datasets/lemma_rca/` | `NCKH_rawData/raw_data/huggingface/lemma_rca/` |
| `nezha` | `src/datasets/nezha/infrastructure/adapter.py` | `NCKH_rawData/raw_data/nezha/` |

## Lệnh từ root repository

```bash
bash run_datasets.sh --help
bash run_datasets.sh list
bash run_datasets.sh inspect rcaeval --data-root NCKH_rawData/raw_data/huggingface/rcaeval
bash run_datasets.sh inspect lemma_rca --data-root NCKH_rawData/raw_data/huggingface/lemma_rca
bash run_datasets.sh inspect nezha --data-root NCKH_rawData/raw_data/nezha
```

`list` in default paths CP1 cũ; không kiểm raw existence. `paths.py` vẫn trỏ `Resource/cp1/raw_data/`, hiện không có. `inspect all` không override ba raw roots; `--data-root` chỉ dùng một slug. RCAEval inspect đọc metadata; LEMMA liệt kê kịch bản hard-code; Nezha inspect chỉ đếm list đầu.

Khi cần export mới sau audit, dùng output riêng:

```bash
bash run_datasets.sh normalize rcaeval \
  --data-root NCKH_rawData/raw_data/huggingface/rcaeval \
  --output-root /tmp/nckh-normalized-preview
```

Python tương đương: `Resource/explore_datasets/.venv/bin/python Resource/explore_datasets/run_datasets.py ...`. `--output-root` ghi ba bảng dưới `<root>/<slug>/`; bỏ cờ sẽ ghi canonical mặc định. Lệnh normalize đọc logs, không cần chạy để đọc docs.

## Giới hạn hiện tại

- RCAEval default tối đa 30 log cases; writer theo case, loader vẫn nạp nguyên case vào bộ nhớ.
- LEMMA default 50,000 logs/scenario; bốn scenarios hard-code; canonical target bị rút còn target đầu.
- Nezha chỉ export logs incident đầu; fault iteration có lỗi indentation, mapping/windows cần audit.
- Canonical `log_id`/raw references và template hash đã có; chưa có Group/Hierarchy/Edge/Ranker.
- `dataset.yaml` là metadata mô tả, không tự cấu hình runtime. Sửa paths/registry cần code riêng.

Schema và kiến trúc: [src README](src/README.md), [clean architecture](src/docs/CLEAN_ARCHITECTURE.md). Kiểm chứng và giới hạn: [implementation status](../docs/implementation_status.md), [validation report](../docs/validation_report.md). Không dùng số rows/file hoặc tên test để claim dữ liệu đã đủ training.
