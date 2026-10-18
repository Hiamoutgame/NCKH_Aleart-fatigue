# src — Kiến trúc đọc dataset

## Cây thư mục
~~~
src/
|-- interface/           # CLI composition: datasets_cli.py
|-- shared/
|   |-- domain/            # entity + port thuan Python
|   |-- application/       # use case dung lai
|   |-- infrastructure/    # loader pandas/csv/parquet
|   \-- interface/         # CLI chung
|-- datasets/
|   \-- <dataset_slug>/
|       |-- dataset.yaml   # nguon + mapping cot
|       |-- domain/
|       |-- application/
|       |-- infrastructure/
|       |-- interface/
|       |-- notebooks/
|       \-- tests/
|-- legacy/                # script cu, khong dung cho workflow moi
\-- docs/
~~~

## Dependency rule
~~~
interface/datasets_cli --> datasets/{rcaeval,lemma_rca,nezha}
datasets/<x> --> shared
cp1 --> shared/infrastructure (paths, normalization, severity)
datasets/<x> --X--> datasets/<y>    (cam)
shared       --X--> datasets/*      (cam)
~~~
Trong mỗi dataset: domain <-- application <-- infrastructure/interface.
Nghĩa là lớp ngoài được phép biết lớp trong, lớp trong không được biết lớp ngoài.

## Vai trò từng layer
| Layer | Vai trò |
| --- | --- |
| domain | Entity, port, luật thuần Python, không phụ thuộc pandas |
| application | Use case: describe_dataset, read_incident, explain_incident |
| infrastructure | Adapter đọc dữ liệu (pandas/csv/parquet), mapping cột |
| interface | Entry point: CLI, notebook, API nội bộ |
| config | dataset.yaml: nguồn + mapping cột + đơn vị incident |

## Chạy thử shared profiler
Từ thư mục Resource/explore_datasets:
~~~
PYTHONPATH=. python -m src.shared.interface.profile_cli <duong_dan_file> --name <ten> --value-cols service message
~~~

## Quy ước đặt tên
- Dataset đang dùng: `rcaeval`, `lemma_rca`, `nezha`.
- Một dataset một folder trong datasets/.
- Không để logic riêng của một dataset trong shared/.

CP1 thiết lập đường dẫn tới `explore_datasets` khi chạy trực tiếp để dùng helper
trong `src/shared/infrastructure/`. Adapter không phụ thuộc `cp1_core`. Các file
dataset.yaml mô tả nguồn/mapping; đường dẫn mặc định runtime được định nghĩa tại
`src/shared/infrastructure/paths.py`.
