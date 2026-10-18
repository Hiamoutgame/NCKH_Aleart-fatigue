# shared — Shared kernel

Chứa mọi thứ dùng chung cho các dataset repo. Không phụ thuộc vào bất kỳ dataset cụ thể nào.

| Layer | Nội dung |
| --- | --- |
| domain | DatasetProfile, ColumnProfile, Incident, DatasetSource (port) |
| application | profile_dataframe, format_profile |
| infrastructure | load_table cho csv/tsv/json/jsonl/parquet |
| interface | profile_cli.py |

## Quy tắc
- Thêm contract mới vào shared khi có từ 2 dataset cần.
- Không nhét logic riêng của một dataset vào đây.
- shared không được import từ datasets/.
