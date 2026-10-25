# Architecture proposal V3 — tách phần chung và phần riêng

Ngày 25/10/2026. **PROPOSAL**, chưa di chuyển file nào. Scope theo [master context](../../NCKH_MASTER_CONTEXT_2026-10-23.md). Interface (`LogGrouper`, `ServiceRanker`) do nhóm tự định nghĩa; tên dưới đây là chỗ giữ, sẽ thay bằng bản định nghĩa của nhóm.

## 1. Nguyên tắc

Một câu hỏi để quyết định file nằm đâu: **"Nếu đổi dataset hoặc đổi model, file này có phải sửa không?"**

| Trả lời | Loại | Nằm ở |
| --- | --- | --- |
| Không bao giờ | Phần chung | `core/`, `evaluation/` |
| Sửa khi đổi dataset | Riêng theo dataset | `datasets/<tên>/` |
| Sửa khi đổi cách gom nhóm | Riêng theo phương pháp | `grouping/<tên>/` |
| Sửa khi đổi model xếp hạng | Riêng theo phương pháp | `ranking/<tên>/` |
| Sửa khi Kev đổi version | Riêng theo thư viện ngoài | `integrations/kev/` |
| Chỉ nối các phần lại | Lớp điều phối | `cli/`, `pipelines/` |

## 2. Cây thư mục đề xuất

```text
src/nckh/
├── core/                    # CHUNG — không import dataset, model, kev
│   ├── schema.py            # Incident, LogEvent, GroundTruth (+ LogGroup, RankedService sau này)
│   ├── interfaces.py        # DatasetAdapter, LogGrouper, ServiceRanker (ABC)
│   ├── text.py              # normalize_message, template key
│   ├── time.py              # epoch/UTC helpers
│   └── config.py            # đọc data root từ configs/ hoặc NCKH_DATA_ROOT
├── datasets/                # RIÊNG theo dataset — chỉ import core
│   ├── rcaeval/adapter.py
│   ├── nezha/adapter.py
│   └── lemma_rca/adapter.py
├── grouping/                # RIÊNG theo phương pháp — chỉ import core
│   ├── template.py          # baseline: nhóm theo template_id
│   └── kev_merge.py         # sau này: gọi integrations/kev để quyết định gộp cặp
├── ranking/                 # RIÊNG theo phương pháp — chỉ import core
│   ├── error_count.py       # baseline
│   ├── logreg.py            # baseline
│   └── kev_ranker.py        # gọi integrations/kev
├── integrations/kev/        # CHỖ DUY NHẤT được `import kev`
│   ├── requests.py          # groups + candidates → SystemOneRequest (không chứa nhãn)
│   ├── records.py           # tạo JSONL có label cho fine-tune
│   └── decode.py            # xác suất Kev → RankedService + supporting log_id
├── evaluation/              # CHUNG — cùng thước đo cho mọi variant
│   ├── split.py             # split theo incident/nhóm case, lưu manifest
│   ├── leakage.py           # chặn raw_label, fault, case name khỏi feature/state
│   ├── metrics.py           # Top-k, candidate coverage, reduction, traceability
│   └── manifest.py          # run_id, config, seed, version
└── cli/main.py              # inspect / normalize / group / rank / evaluate

scripts/                     # script chạy một lần: audit, export
tests/                       # mirror theo src/nckh/
configs/                     # paths.local.yaml, paths.colab.yaml, experiments/*.yaml
notebooks/explore/           # khám phá dữ liệu, chạy local CPU
notebooks/colab/             # fine-tune/inference Kev trên GPU
docs/  paper/                # tài liệu, LaTeX
data/  runs/  _personal/     # .gitignore — chỉ ở local/Drive
```

## 3. Luật phụ thuộc

```text
cli ──▶ datasets, grouping, ranking, evaluation ──▶ core
ranking/kev_ranker, grouping/kev_merge ──▶ integrations/kev ──▶ kev (repo ngoài)
```

- `core` không import gì của dự án.
- Các folder cùng cấp không import lẫn nhau, ví dụ `datasets/rcaeval` không import `datasets/nezha`, `ranking` không import `grouping`. Dữ liệu đi qua schema trong `core`.
- Chỉ `integrations/kev` biết Kev tồn tại. Đổi model khác thì chỉ thêm một integration mới.
- `evaluation` không gọi model; nó chỉ nhận output theo schema chung, nên mọi ranker được đo bằng cùng một hàm.

## 4. Mapping từ code hiện có

| Hiện tại | Đề xuất | Ghi chú |
| --- | --- | --- |
| `Resource/explore_datasets/src/shared/domain/canonical.py` | `core/schema.py` | Hiện import pandas; có thể tách DataFrame conversion ra sau |
| `.../shared/domain/ports.py` (`BaseDatasetAdapter`) | `core/interfaces.py` | Thêm `LogGrouper`, `ServiceRanker` theo bản nhóm định nghĩa |
| `.../shared/infrastructure/normalization.py`, `severity.py` | `core/text.py` | |
| `.../shared/infrastructure/paths.py` | `core/config.py` | Bỏ default `cp1`, đọc từ config/env |
| `.../shared/infrastructure/loaders.py` | `core/` hoặc dataset dùng nó | Cần đọc để quyết định |
| `.../datasets/{rcaeval,nezha,lemma_rca}` | `datasets/<tên>/` | Gộp các layer "sườn" rỗng về một adapter |
| `.../datasets/_template` | `docs/add_dataset.md` | |
| `.../interface/datasets_cli.py` | `cli/main.py` | |
| `.../legacy/explore_v0.py` | xóa khỏi nhánh chính (còn trong git history) | |
| `Resource/explore_datasets/*.py` (audit, export, extract) | `scripts/` | |
| `NCKH_rawData/spec/audit_metadata.py` | `scripts/` | Artifact JSON/CSV vào `docs/` hoặc `data/` |
| `Resource/explore_datasets/tests`, `conftest.py` | `tests/` | Test đòi CP1 cần sửa hoặc đánh dấu skip |
| `Resource/notebooks/kev_01_colab_kaggle.ipynb` | `notebooks/colab/` | |
| `Resource/docs`, `note`, `requirement`, `01_*`, `02_*` | `docs/` | |
| `Resource/report`, `IEEE_template` | `paper/` | |
| `Resource/datasets/normalized`, `NCKH_rawData/raw_data` | `data/` (ignored) | Chỉ chuyển chỗ, không sửa nội dung |
| `models/kev` | ngoài repo; khóa commit trong notebook | Hoặc fork + submodule ở `third_party/kev` |

## 5. Thứ tự di chuyển

1. Branch riêng, sửa `core.filemode`, `.gitignore` mới.
2. Chuyển non-code (docs, paper, notebooks, data) bằng `git mv`.
3. Chuyển code theo bảng mapping, sửa import, chạy `pytest` và CLI `--help` sau mỗi bước.
4. Thêm interface `LogGrouper`/`ServiceRanker` và baseline `template` + `error_count`.
5. Thêm `evaluation/` (split, leakage, metrics) trước khi thêm `kev_ranker`.

## 6. Giới hạn

Tài liệu này chưa kiểm tra mọi import trong `src/`, chưa chạy test sau di chuyển và chưa chốt interface. Các tên file là đề xuất.
