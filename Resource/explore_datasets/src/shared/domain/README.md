# shared/domain

Entity và port thuần Python. Không import pandas.

- ColumnProfile: mô tả một cột (name, dtype, non_null, null, unique, sample).
- DatasetProfile: kết quả profile một dataset (shape, columns, head, value_counts).
- DatasetSource (port): interface để lớp infrastructure cài đặt khi đọc dữ liệu.

Quy ước: nếu cần thêm entity mới, thêm vào models.py kèm docstring.
