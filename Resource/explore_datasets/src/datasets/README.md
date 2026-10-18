# Các module dataset đang dùng

| Slug | Vai trò | Nguồn | Đơn vị incident |
| --- | --- | --- | --- |
| `rcaeval` | Primary | `phamquiluan/RCAEval` trên Hugging Face | Case |
| `lemma_rca` | Backup / external validation | `Lemma-RCA-NEC/Product_Review_Original` trên Hugging Face | Scenario |
| `nezha` | Secondary | Nezha, file raw cung cấp local | Fault window |

Các thư mục ở đây chứa **code**, không chứa raw dataset. `_template/` là sườn tạo
module mới, không tham gia registry CLI. GAIA và các dataset phụ đã chuyển sang
`Resource/archive/excluded_datasets/`.

Các module không import chéo. Canonical schema/contract nằm trong `src/shared/`;
path, normalization và severity dùng chung nằm trong `src/shared/infrastructure/`.
CLI ghép adapter ở `src/interface/datasets_cli.py`. Để thêm dataset đang chạy, cần
cập nhật cả mapping trong `src/shared/infrastructure/paths.py`, registry CLI, CP1 registry nếu
có fetch/inspect, và test tương ứng; sửa `dataset.yaml` riêng chưa đủ.
