# shared/infrastructure

Adapter đọc dữ liệu thành pandas DataFrame.

- load_table(path, **kwargs): hỗ trợ .csv, .tsv, .json, .jsonl, .parquet.

Quy ước: chỉ đọc, không ghi đè raw data.

Helper dùng chung cho các adapter và CP1:

- `paths.py`: đường dẫn raw/normalized được neo theo checkout.
- `normalization.py`: chuẩn hóa message theo rule CP1 hiện có.
- `severity.py`: regex severity và hàm tương thích CP1.

CP1 dùng các module này qua `src.shared.infrastructure`; các helper không import CP1.
