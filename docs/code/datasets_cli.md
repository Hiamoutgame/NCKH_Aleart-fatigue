# explore_datasets — đọc và chuẩn hóa hai dataset (RCAEval, Nezha)

**23/10/2026.** Đây là phần code chuẩn bị dữ liệu cho [V3 log organization + service RCA](../../NCKH_MASTER_CONTEXT_2026-10-23.md), chưa phải pipeline grouping/ranking hoàn chỉnh. [repo map](../README.md) phân biệt raw/source/normalized.

| Slug | Source adapter | Raw thật từ root repo |
| --- | --- | --- |
| `rcaeval` | `src/datasets/rcaeval/infrastructure/adapter.py` | `data/raw/huggingface/rcaeval/` |
| `nezha` | `src/datasets/nezha/infrastructure/adapter.py` | `data/raw/nezha/` |

## Lệnh từ root repository

```bash
bash run_datasets.sh --help
bash run_datasets.sh list
bash run_datasets.sh inspect rcaeval --data-root data/raw/huggingface/rcaeval
bash run_datasets.sh inspect nezha --data-root data/raw/nezha
```

`list` in default paths (`data/raw/...`); không kiểm raw existence. `inspect all` không override các raw roots; `--data-root` chỉ dùng một slug. RCAEval inspect đọc metadata; Nezha inspect chỉ đếm list đầu.

Chạy thử trên vài incident, ghi vào thư mục riêng, rồi kiểm tra:

```bash
bash run_datasets.sh normalize rcaeval --max-cases 6 --output-root /tmp/nckh-normalized-preview
bash run_datasets.sh verify rcaeval --output-root /tmp/nckh-normalized-preview
```

Chạy thật cho toàn bộ dữ liệu, ghi vào `data/normalized/<slug>/` (RCAEval khoảng 50 phút, 49.6 triệu dòng, khoảng 5 GB):

```bash
bash run_datasets.sh normalize rcaeval > data/runs/normalize.log 2>&1   # theo dõi: tail -f data/runs/normalize.log
bash run_datasets.sh verify rcaeval
bash run_datasets.sh normalize nezha && bash run_datasets.sh verify nezha
```

Python tương đương: `.venv/bin/python scripts/run_datasets.py ...`. `--output-root` ghi các bảng dưới `<root>/<slug>/`; bỏ cờ sẽ ghi vào thư mục mặc định.

Mỗi thư mục dataset sau khi chạy có:

| File | Nội dung |
| --- | --- |
| `incidents.parquet`, `ground_truth.parquet` | Mọi incident và đáp án của dataset |
| `log_events.parquet` | Log đã chuẩn hóa, **mỗi incident một row group** (đọc từng incident bằng `pq.ParquetFile(...).read_row_group(i)`) |
| `manifest.json` | Thời điểm chạy, commit git (và có thay đổi chưa commit hay không), phiên bản thư viện, `drain_config`, `max_cases`, danh sách file input kèm sha256, số dòng ra. Nezha có thêm: cửa sổ thời gian, bản ghi CSV hỏng, độ lệch epoch |
| `verification_report.json` | Kết quả `verify`: từng kiểm tra đạt hay không, kèm ví dụ lỗi; thống kê mỗi incident (số log, số nhóm G1/G2, Visible Log Reduction, có log của service đáp án không, số phút log trước/sau lỗi) |

`verify` trả exit code 2 nếu có kiểm tra không đạt. Các kiểm tra chính:

- số incident và ground truth khớp với raw;
- số dòng mỗi incident khớp với số đếm lại từ raw; mỗi dòng raw cần giữ thì được giữ đúng một lần trong mỗi file;
- lấy ngẫu nhiên 20 dòng mỗi incident, mở lại dòng gốc theo `source_file` / `source_row_id`, so `raw_message`, timestamp, `entity_id`;
- template có đủ và đúng MD5; Nezha: mọi log nằm trong cửa sổ của incident.

### Template: regex (G1) và Drain (G2)

Mỗi log có hai loại template, cả hai cùng nằm trong `log_events.parquet`:

| Cột | Cách tạo | Dùng cho |
| --- | --- | --- |
| `parsed_message`, `template_id` | Regex `normalize_message`, rồi MD5 12 ký tự | Baseline G1 |
| `drain_template`, `drain_template_id` | `parsed_message` → tách header → Drain ([drain.py](../../src/shared/infrastructure/drain.py)) → MD5 12 ký tự | G2 |

Drain được tự viết theo bài ICWS 2017, mục III. Mỗi incident có một cây Drain riêng, đọc log theo thứ tự thời gian (sắp ổn định theo `timestamp_utc`; cùng thời điểm thì giữ thứ tự file và dòng). Mỗi `log_id` thuộc đúng một nhóm, và mọi log trong nhóm nhận template cuối cùng của nhóm.

Header đã biết (Spring Boot, go-kit `ts=`, Nezha `TraceID: .. SpanID: ..`) được tách ra trước khi đưa vào Drain. `LEVEL logger` được giữ làm tiền tố cố định của template.

Tham số có thể đổi bằng cờ `--drain-depth` (mặc định 4), `--drain-st` (0.4) và `--drain-max-child` (100). Kết quả `normalize` ghi lại tham số đã dùng trong `drain_config`. Giá trị mặc định nằm giữa khoảng tham số bài báo dùng (bảng II), chưa được chỉnh trên tập train.

## Giới hạn hiện tại

- Mỗi lần chỉ nạp một incident vào bộ nhớ (máy hiện có 7 GB RAM). RCAEval xử lý khoảng 16,000–21,000 dòng/giây.
- Các lỗi adapter Nezha đã sửa ngày 26/10/2026, chi tiết ở [dataset.md](../research/05_methodology/dataset.md) mục 3. Cửa sổ [−2, +3] phút của Nezha là quy tắc tự đặt.
- `LogEvent` (dùng qua `load_logs`) giữ timestamp đến micro giây; `log_events.parquet` giữ đến nano giây.
- Canonical `log_id`/raw references, template regex và template Drain đã có; chưa có bảng Group/Hierarchy/Edge/Ranker.
- Drain đã biết: gộp hai câu chỉ khác một từ (`Get Ads by Category start`/`finish`); tách nhiều nhóm khi dòng có nhiều ID chưa bị regex bắt (`product_ids=['66VCHSJNUP', ...]`).
- `dataset.yaml` là metadata mô tả, không tự cấu hình runtime. Sửa paths/registry cần code riêng.

Schema và kiến trúc: [src README](../../src/README.md), [clean architecture](src_docs/CLEAN_ARCHITECTURE.md). Kiểm chứng và giới hạn: [implementation status](../status/implementation_status.md), [validation report](../status/validation_report.md). Không dùng số rows/file hoặc tên test để claim dữ liệu đã đủ training.
