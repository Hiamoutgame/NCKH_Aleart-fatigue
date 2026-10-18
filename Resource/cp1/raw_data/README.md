# Raw data dùng chung

Nguồn local cho cả CP1 và explore_datasets. Phân tích chỉ đọc các file nguồn;
normalization ghi sang `Resource/datasets/normalized/`, report ghi vào
`Resource/cp1/artifacts/`.

```text
raw_data/
├── huggingface/
│   ├── rcaeval/
│   │   ├── cases.parquet
│   │   └── <case_id>/logs.parquet
│   └── lemma_rca/
│       ├── sample/*.json
│       ├── LEMMA_RCA_20220606_Scenario_GroundTruth.pptx
│       └── pod_topology/
├── nezha/
│   ├── fault_list.json
│   └── 03_53_log.csv
└── manifest.csv
```

Ba case RCAEval local: `re2ss_carts_cpu_1`, `re2tt_ts-route-service_mem_1`,
`re3ss_carts_f3_4`. Metadata có 735 case không có nghĩa local chứa đủ log cho mọi case.
LEMMA đang có 2 JSON sample; Nezha có 1 CSV. Xem
[validation report](../../docs/validation_report.md) để biết phạm vi và giới hạn.

GAIA đã chuyển sang `Resource/archive/excluded_datasets/gaia/raw_data/`.
`manifest.csv` giữ lịch sử fetch của nguồn được chọn, bao gồm path/revision lịch sử;
đường dẫn runtime hiện được tính từ vị trí checkout trong `explore_datasets/src/shared/infrastructure/paths.py`.
Bản manifest đầy đủ trước refactor nằm trong archive. Các downloader chuyên biệt
không nhất thiết ghi vào manifest CP1 này.

Không sửa/ghi đè raw trong lúc phân tích. Dữ liệu lớn được giữ local/gitignore;
chỉ commit manifest, mô tả và sample nhỏ khi cần.
