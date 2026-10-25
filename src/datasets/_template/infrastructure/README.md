# infrastructure/

Adapter đọc dữ liệu.

- Cài đặt port của domain.
- Đọc csv/parquet/json bằng pandas hoặc load_table của shared.
- Mapping cột raw sang canonical theo dataset.yaml.
- Chỉ đọc raw data, không sửa.
