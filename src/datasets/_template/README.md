# _template — Khung để tạo repo dataset mới

Copy folder này thành src/datasets/<slug> rồi điền thông tin.

## Cấu trúc
| Path | Nội dung |
| --- | --- |
| dataset.yaml | Nguồn dữ liệu, local_path, mapping cột, đơn vị incident |
| README.md | Mô tả dataset: nguồn, schema, việc cần làm, tiêu chí done |
| domain/ | Entity + port của dataset, luật thuần Python |
| application/ | Use case đọc/mô tả incident |
| infrastructure/ | Adapter đọc dữ liệu, mapping cột raw sang canonical |
| interface/ | CLI hoặc notebook entry point |
| notebooks/ | Notebook khám phá nhanh |
| tests/ | Test shape, cột, mapping |

## Quy tắc
- Không import sang dataset khác; dùng src/shared/.
- domain/ không import pandas.
- Raw data chỉ đọc.

## Sau khi copy
1. Đổi slug trong dataset.yaml và README.
2. Cài adapter đọc dữ liệu.
3. Viết use case đọc một incident.
4. Thêm test tối thiểu.
5. Cập nhật registry ở src/datasets/README.md.
