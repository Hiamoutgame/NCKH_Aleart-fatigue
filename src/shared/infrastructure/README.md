# shared/infrastructure — I/O và helpers hiện có

- `loaders.py`: load_table cho CSV/TSV/JSON/JSONL/Parquet thành pandas DataFrame.
- `paths.py`: neo path theo checkout; raw default `data/raw/`, canonical `data/normalized/`; override `data_root` từng adapter.
- `normalization.py`: mask timestamp/UUID/thread/hex/numbers bằng regex; không phải Drain3/Spell parser.
- `severity.py`: regex và compatibility helpers; `infer_severity()` legacy mặc định INFO khi unknown, khác canonical adapter có thể trả null.

Không ghi đè raw. CP1 từng dùng helpers nhưng source CP1 không có active trong snapshot này. Các helpers không import CP1 hoặc adapters. [Implementation status](../../../docs/status/implementation_status.md) nêu timestamp/severity/provenance assumptions; không tự chứng nhận field mapping đúng nguồn.
