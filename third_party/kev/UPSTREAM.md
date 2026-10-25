# Kev — nguồn gốc và thay đổi của nhóm

Thư mục này là bản copy (vendored) của Kev, không còn là git repo riêng.

| Mục | Giá trị |
| --- | --- |
| Upstream | https://github.com/jaredpalmer/kev |
| Commit gốc | `2074cc44256200bb37540103fa4572901faa10f3` (2026-10-22, "[ImgBot] Optimize images (#187)") |
| License | Apache-2.0, xem [LICENSE](LICENSE). Giữ LICENSE và ghi rõ file đã sửa khi phân phối lại. |
| Ngày đưa vào repo nhóm | 2026-10-25 |
| Không đưa lên git | `runs/` (kết quả thí nghiệm của tác giả, ~711MB), `evals/**/*.jsonl` trừ `evals/smoke-v1/` (~136MB; Kev tự tải từ Hugging Face `jaredpalmer/kev-suites` khi cần) |

Lúc copy, `tools/review/package-lock.json` đã khác bản upstream (thay đổi local có từ trước, không do nhóm sửa có chủ đích).

Notebook `notebooks/kev_01_colab_kaggle.ipynb` vẫn clone Kev từ GitHub ở đúng commit trên, không dùng bản trong thư mục này.

## Thay đổi của nhóm

Ghi mỗi thay đổi theo dạng: ngày, file, lý do.

- (chưa có)
