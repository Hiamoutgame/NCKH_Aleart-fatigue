# explore_datasets — đọc và chuẩn hóa ba dataset

**23/10/2026.** Đây là phần code chuẩn bị dữ liệu cho [V3 log organization + service RCA](../../NCKH_MASTER_CONTEXT_2026-10-23.md), chưa phải pipeline grouping/ranking hoàn chỉnh. [repo map](../README.md) phân biệt raw/source/normalized.

| Slug | Source adapter | Raw thật từ root repo |
| --- | --- | --- |
| `rcaeval` | `src/datasets/rcaeval/infrastructure/adapter.py` | `data/raw/huggingface/rcaeval/` |
| `lemma_rca` | Adapter + loader/downloader/application/CLI trong `src/datasets/lemma_rca/` | `data/raw/huggingface/lemma_rca/` |
| `nezha` | `src/datasets/nezha/infrastructure/adapter.py` | `data/raw/nezha/` |

## Lệnh từ root repository

```bash
bash run_datasets.sh --help
bash run_datasets.sh list
bash run_datasets.sh inspect rcaeval --data-root data/raw/huggingface/rcaeval
bash run_datasets.sh inspect lemma_rca --data-root data/raw/huggingface/lemma_rca
bash run_datasets.sh inspect nezha --data-root data/raw/nezha
```

`list` in default paths (`data/raw/...`); không kiểm raw existence. `inspect all` không override ba raw roots; `--data-root` chỉ dùng một slug. RCAEval inspect đọc metadata; LEMMA liệt kê kịch bản hard-code; Nezha inspect chỉ đếm list đầu.

Khi cần export mới sau audit, dùng output riêng:

```bash
bash run_datasets.sh normalize rcaeval \
  --data-root data/raw/huggingface/rcaeval \
  --output-root /tmp/nckh-normalized-preview
```

Python tương đương: `.venv/bin/python scripts/run_datasets.py ...`. `--output-root` ghi ba bảng dưới `<root>/<slug>/`; bỏ cờ sẽ ghi canonical mặc định. Lệnh normalize đọc logs, không cần chạy để đọc docs.

## Giới hạn hiện tại

- RCAEval default tối đa 30 log cases; writer theo case, loader vẫn nạp nguyên case vào bộ nhớ.
- LEMMA default 50,000 logs/scenario; bốn scenarios hard-code; canonical target bị rút còn target đầu.
- Nezha chỉ export logs incident đầu; fault iteration có lỗi indentation, mapping/windows cần audit.
- Canonical `log_id`/raw references và template hash đã có; chưa có Group/Hierarchy/Edge/Ranker.
- `dataset.yaml` là metadata mô tả, không tự cấu hình runtime. Sửa paths/registry cần code riêng.

Schema và kiến trúc: [src README](../../src/README.md), [clean architecture](src_docs/CLEAN_ARCHITECTURE.md). Kiểm chứng và giới hạn: [implementation status](../status/implementation_status.md), [validation report](../status/validation_report.md). Không dùng số rows/file hoặc tên test để claim dữ liệu đã đủ training.
