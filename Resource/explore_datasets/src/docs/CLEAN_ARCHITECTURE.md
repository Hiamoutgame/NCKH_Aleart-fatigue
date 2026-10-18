# CLEAN ARCHITECTURE cho src/datasets

## 1. Dependency rule
~~~
interface/datasets_cli --> datasets/{rcaeval,lemma_rca,nezha}
datasets/<x> --> shared
cp1 --> shared/infrastructure
datasets/<x> --X--> datasets/<y>    (cam)
shared       --X--> datasets/*      (cam)
~~~
Trong mỗi dataset:
~~~
domain <-- application <-- infrastructure
                       \-- interface
~~~
Lớp ngoài được biết lớp trong; lớp trong không được biết lớp ngoài.

## 2. Vai trò từng layer trong một dataset repo
| Layer | Chứa gì | Không chứa gì |
| --- | --- | --- |
| domain | Entity của dataset (Incident, LogEvent), port đọc dữ liệu, luật thuần | pandas, đường dẫn file, HTTP |
| application | Use case: describe_dataset, read_incident, explain_incident | đọc file trực tiếp |
| infrastructure | Adapter đọc dữ liệu, mapping cột raw sang canonical | luật nghiệp vụ |
| interface | CLI, notebook, entry point | logic nặng |
| config | dataset.yaml mô tả nguồn và mapping | code |

## 3. Kết nối qua shared
- shared/domain: contract chung (DatasetProfile, ColumnProfile, DatasetSource).
- shared/application: use case dùng lại (profile_dataframe).
- shared/infrastructure: loader dùng chung (load_table).
- shared/interface: CLI chung (profile_cli).
Khi hai dataset cần dùng chung một thứ, đưa contract vào shared thay vì import chéo.

## 4. Khi nào thêm vào shared
- Khi có từ 2 dataset trở lên cần.
- Khi contract ổn định, không gắn với một dataset cụ thể.

## Helper dùng chung trong exploration

`src/shared/infrastructure/` giữ path, normalization và severity dùng chung với CP1.
Các helper này không import CP1 hay adapter. `src/interface/datasets_cli.py` là nơi
ghép các module vào CLI, nên được phép import từng adapter; `src/shared/` vẫn
không import dataset cụ thể. Các quy tắc layer ở trên là định hướng thiết kế;
code canonical hiện có thêm hàm chuyển DataFrame và use case gọi loader trực tiếp.
