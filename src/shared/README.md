# shared — contract và helper dùng chung

Không phụ thuộc dataset cụ thể. CLI composition ở `src/interface/datasets_cli.py` được phép ghép adapters; không đưa logic riêng từng dataset vào shared.

| Layer | Source hiện có |
| --- | --- |
| domain | Profile entities/port, Incident/LogEvent/GroundTruth, BaseDatasetAdapter, DataFrame conversions |
| application | Profiling use cases |
| infrastructure | Table loaders, paths, regex normalization và severity |
| interface | File profiler CLI |

`domain/canonical.py` hiện import pandas; không khẳng định mọi domain code thuần Python. Schema dùng `log_id`, chưa có Group/Edge/Ranking. [src README](../README.md) và [implementation status](../../docs/status/implementation_status.md) ghi hiện trạng.

Default raw là `data/raw/`; adapter/CLI nhận `data_root` override. Incident có label-bearing metadata, nên tách bảng ground truth chưa bảo đảm không leakage.
