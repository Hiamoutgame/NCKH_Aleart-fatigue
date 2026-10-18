# Validation sau refactor: RCAEval, LEMMA-RCA và Nezha

Kiểm tra ngày **18/10/2026**, trên dữ liệu local hiện có. Báo cáo cũ được giữ tại
[history/validation_report_before_refactor.md](history/validation_report_before_refactor.md).
Bản này phân biệt việc code chạy đúng sau refactor với độ đúng của nhãn nghiên cứu.

## 1. Kết quả kiểm tra code

**39/39 test PASSED** trên môi trường local:

```bash
Resource/explore_datasets/.venv/bin/python -m pytest -c Resource/pytest.ini -q -p no:cacheprovider
```

Suite gồm CP1, ba adapter, canonical validation và test hồi quy mới:

- Các entrypoint CP1/LEMMA/CLI chung chạy từ thư mục tạm, không có `PYTHONPATH`.
- Wrapper Bash tìm đúng Python và source khi gọi bằng đường dẫn tuyệt đối từ nơi khác.
- Registry chỉ có `rcaeval`, `lemma_rca`, `nezha` và repo code `rcaeval_github`.
- Đường dẫn raw trong CP1 registry trùng đường dẫn mặc định adapter.
- Chuẩn hóa RCAEval với raw tùy chọn nằm ngoài repository, output vào thư mục tạm,
  giữ nguyên raw message và liên kết incident/provenance.
- Import script export không tự chạy normalization.

`bash -n` cho cả ba wrapper và kiểm tra cú pháp Python đều qua.
`git diff --check` không phát hiện lỗi whitespace.
Archive, môi trường ảo và worktree Kilo nằm ngoài phạm vi thu thập test.
Một số test adapter/validation dùng raw local đang có, chưa phải suite độc lập với data.

Trước refactor, bộ test ba dataset có **29 pass, 1 fail**: test registry còn đòi các
nguồn phụ đã bị bỏ khỏi cấu hình. Test này đã được cập nhật theo phạm vi ba dataset.

## 2. Bảo toàn dữ liệu

Đã chụp SHA-256 trước refactor và đối chiếu sau khi hoàn tất:

- **27 file raw/artifact/normalized chính giữ nguyên checksum**.
- **3 file bị bỏ là bản trùng hoàn toàn**, giữ nguyên nội dung tương ứng tại
  `datasets/normalized/lemma_rca/`.
- Không ghi đè raw hoặc Parquet normalized hiện có khi kiểm thử.
- Symlink `normalized/lemma_rca/lemma -> lemma` tự trỏ đã được bỏ.
- Code/raw/report dataset phụ được chuyển sang archive. Bản registry/manifest cũ
  được lưu tại đó để giữ provenance; manifest đang dùng chỉ còn nguồn được chọn.

Danh sách checksum và ánh xạ bản trùng:
[refactor_preservation.json](refactor_preservation.json).
Phạm vi checksum không gồm cache tải dữ liệu và file cấu hình được chủ đích refactor.

## 3. Kiểm tra luồng export thật

Đã gọi `export_all_normalized.py --output-root <thư mục tạm>` từ `/tmp`, bỏ
`PYTHONPATH`, và kiểm tra đủ chín file Parquet. Output dùng đúng ba thư mục:
`rcaeval`, `lemma_rca`, `nezha`; không sinh thêm tên `lemma`.

| Dataset | incidents.parquet | ground_truth.parquet | log_events.parquet | Incident có log |
| --- | ---: | ---: | ---: | ---: |
| RCAEval | 735 | 735 | 405.960 | 3 |
| LEMMA-RCA | 4 | 4 | 20.000 | 1 |
| Nezha | 24 | 24 | 4.136 | 1 |

Đã đọc cả chín bảng và so sánh với output trước refactor bằng
`pandas.testing.assert_frame_equal`: giữ cùng schema và các giá trị xử lý.
Riêng `source_file` đổi sang một quy ước nhất quán: tương đối với root repository;
nếu raw ngoài repository thì tương đối với `data_root`. Trước đây mỗi adapter
chọn một mốc thư mục khác nhau. `raw_record_ref`, raw message, timestamp, template,
severity, incident và nhãn không bị thay đổi bởi refactor.

Các Parquet chính đang có vẫn là bản gốc. Chuẩn hóa lại sau này sẽ áp dụng quy ước
`source_file` mới. Export kiểm tra được đặt trong thư mục tạm ngoài repository.

## 4. Những thay đổi cấu trúc

- Helper path/normalization/severity được gom vào
  `Resource/explore_datasets/src/shared/infrastructure/`. CP1 dùng chung qua import
  tương thích; package riêng ở cấp Resource đã được gộp vào exploration.
- Adapter không còn import `cp1_core`; CP1 giữ export tương thích cho helper cũ.
- Registry thêm Nezha dạng `local_directory`, chưa có bước download tự động.
- CLI chung: `bash run_datasets.sh list`, `inspect <slug|all>`,
  `normalize <slug|all> --output-root <folder>`.
- CLI/menu LEMMA cũ tiếp tục dùng được mà không cần thêm CP1 vào import path.
- GAIA, LogHub2, OpsEval, CorrelatedAlerts, Suricata CTU-13 được đưa khỏi workflow
  đang chạy; xem [archive](../archive/README.md).

## 5. Giới hạn dữ liệu và nhãn chưa được sửa trong refactor

### RCAEval

Metadata có 735 case nhưng checkout này chỉ có log cho 3 case, tổng 405.960 dòng.
Kết quả scan đầy đủ trong artifact/tài liệu lịch sử không mô tả cùng phạm vi local.
Không suy ra mọi case có metadata đều có log để đánh giá.

### LEMMA-RCA

`load_incidents()` lấy bốn scenario từ danh sách khai báo trong loader.
`normalize()` hiện lấy scenario đầu tiên và gán mọi log sample vào scenario đó;
`load_logs()` chưa lọc log theo cửa sổ thời gian scenario.

**Có sai lệch quan sát được**: 20.000 log sample có timestamp trong tháng 05/2021,
nhưng scenario đầu tiên là DDoS năm 2022. Cần sửa segmentation/đối chiếu nhãn
trước khi dùng bộ này để đánh giá RCA. Test hiện tại xác nhận incident ID tồn tại,
không chứng minh timestamp nằm đúng trong scenario.

CSV/JSON xuất qua CLI khám phá còn dùng cột `root_cause` gán theo tên service
(`reviews` → `reviews-v2/reviews-v3`, còn lại → `normal`). Cột này chưa phải nhãn
incident đã xác minh. CLI loader có fallback level `INFO`, khác canonical adapter
cho phép severity thiếu là `null`. Hai dạng output không cùng schema/ngữ nghĩa.

### Nezha

Có 24 incident metadata, 1 CSV raw và 4.136 log. `normalize()` chỉ xuất log cho
incident đầu tiên; chưa tạo log_events bao phủ toàn bộ incident. Cửa sổ hiện dùng
[-2 phút, +3 phút] quanh inject time. Cần xác định phạm vi quan sát và log sẵn có
cho từng incident trước khi đánh giá toàn dataset.

Các giới hạn này được giữ rõ để refactor cấu trúc không làm thay đổi âm thầm
kết quả nghiên cứu. **39 test pass xác nhận các kiểm tra đã nêu, không xác nhận
mọi nhãn ground truth đã đúng hoặc dataset đã sẵn sàng cho đánh giá toàn diện.**
