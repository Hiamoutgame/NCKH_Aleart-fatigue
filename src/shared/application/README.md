# shared/application

Use case dùng lại cho mọi dataset.

- profile_dataframe(df, name, head_n, value_count_columns): trả về DatasetProfile.
- format_profile(profile): render thành text dễ đọc (shape, columns, head, value_counts).

Không đọc file trực tiếp ở đây; việc đọc do infrastructure/loaders.py đảm nhiệm.
