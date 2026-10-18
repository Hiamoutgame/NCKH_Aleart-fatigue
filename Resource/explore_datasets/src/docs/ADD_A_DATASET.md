# ADD_A_DATASET — Thêm một repo dataset mới

## Các bước
1. Copy src/datasets/_template thành src/datasets/<slug> (slug snake_case).
2. Sửa dataset.yaml: nguồn, local_path, mapping cột, đơn vị incident.
3. Viết lại README.md của dataset: nguồn, vai trò, schema, việc cần làm, tiêu chí done.
4. Cài đặt adapter trong infrastructure/ để đọc dữ liệu thành DataFrame.
5. Cài đặt use case trong application/ cho các thao tác đọc incident.
6. Thêm entry point trong interface/ (CLI hoặc notebook).
7. Thêm test tối thiểu: shape, tên cột, mapping cột.
8. Cập nhật bảng registry trong src/datasets/README.md.

## Tiêu chí done
- Chạy được profiler shared trên dataset: có shape, columns, head(10), value_counts().
- Đọc được ít nhất một incident và mô tả được nội dung.
- Không có import chéo sang dataset khác.
