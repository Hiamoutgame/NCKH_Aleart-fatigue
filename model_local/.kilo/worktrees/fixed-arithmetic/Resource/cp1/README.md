# CP1 — Dataset verification workspace

CP1 kiểm chứng khả năng dùng các dataset log cho đề tài alert aggregation. Code
mới chỉ đọc dữ liệu đã tải local; raw data không bị thay đổi trong lúc phân tích.

## Setup một lần

Từ root `NCKH`:

```powershell
.\setup.ps1
```

Lệnh này tạo `.venv` tại root và cài dependency. Nó không tải dataset.

## Chạy RCAEval

```powershell
.\.venv\Scripts\python cp1\src\main_RCAEval.py fetch
.\.venv\Scripts\python cp1\src\main_RCAEval.py inspect
.\.venv\Scripts\python cp1\src\main_RCAEval.py scan-warnings
.\.venv\Scripts\python cp1\src\main_RCAEval.py timing
.\.venv\Scripts\python cp1\src\main_RCAEval.py verify
.\.venv\Scripts\python cp1\src\main_RCAEval.py all
```

`fetch` tải Hugging Face RCAEval vào `raw_data/huggingface/rcaeval` và clone
repository tham khảo vào `external_repos/github/RCAEval`. `all` chạy toàn bộ
chuỗi trên sau khi tải xong.

## Dataset phụ

Mỗi dataset có lệnh độc lập với `fetch`, `inspect` và `all`:

```powershell
.\.venv\Scripts\python cp1\src\main_LEMMA_RCA.py fetch
.\.venv\Scripts\python cp1\src\main_LogHub2.py inspect
.\.venv\Scripts\python cp1\src\main_OpsEval.py all
.\.venv\Scripts\python cp1\src\main_CorrelatedAlerts.py fetch
.\.venv\Scripts\python cp1\src\main_Suricata_CTU13.py fetch
```

Danh sách URL, revision và local path nằm tại `config/sources.yaml`.

## Quy ước thư mục

- `raw_data/`: file dataset nguyên gốc tải từ nguồn; không chỉnh sửa.
- `external_repos/`: repository GitHub clone để tham khảo; không tự chạy code.
- `artifacts/`: bảng CSV và report do source mới sinh ra.
- `docs/`: định hướng, kiểm chứng schema và thuật ngữ CP1.
- `legacy/`: script/output cũ được giữ để đối chiếu, không dùng cho workflow mới.

Xem [migration note](docs/MIGRATION.md) để đối chiếu lệnh cũ và mới.
