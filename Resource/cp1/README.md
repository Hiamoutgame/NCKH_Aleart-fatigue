# CP1 — kiểm chứng RCAEval, LEMMA-RCA và Nezha

CP1 đọc dữ liệu local trong `raw_data/`, ghi thống kê/report vào `artifacts/`.
Xem [bản đồ Resource](../README.md) cho cấu trúc toàn bộ workspace.

Từ root repository, dùng Python local:

```bash
Resource/explore_datasets/.venv/bin/python Resource/cp1/src/main_RCAEval.py --help
Resource/explore_datasets/.venv/bin/python Resource/cp1/src/main_RCAEval.py inspect
Resource/explore_datasets/.venv/bin/python Resource/cp1/src/main_RCAEval.py scan-warnings
Resource/explore_datasets/.venv/bin/python Resource/cp1/src/main_RCAEval.py timing
Resource/explore_datasets/.venv/bin/python Resource/cp1/src/main_RCAEval.py verify
Resource/explore_datasets/.venv/bin/python Resource/cp1/src/main_LEMMA_RCA.py inspect
Resource/explore_datasets/.venv/bin/python Resource/cp1/src/main_Nezha.py inspect
```

Các lệnh trên ghi lại report/bảng tương ứng. `fetch` và `all` của RCAEval/LEMMA có
bước tải dữ liệu. Nezha chỉ hỗ trợ `inspect` với `fault_list.json` và CSV đã đặt local.
Muốn chỉ xem thông tin ba adapter mà không ghi artifact: `bash run_datasets.sh inspect all`.

`config/sources.yaml` hiện gồm ba dataset và `rcaeval_github` là repo code tham khảo,
không phải dataset thứ tư. `source_registry.py` ánh xạ chúng vào raw/external_repos.
`explore_datasets/src/shared/infrastructure/` giữ rule normalization/severity dùng chung;
`cp1_core` giữ các export tương thích và logic phân tích CP1.

- `raw_data/`: nguồn local, không sửa trong quá trình phân tích.
- `artifacts/`: kết quả kiểm chứng; số liệu cũ có thể thuộc phạm vi raw khác.
- `external_repos/`: đích clone repo tham khảo RCAEval.
- `docs/`: phạm vi nghiên cứu, thuật ngữ, schema notes, migration.
- `legacy/`: script/output lịch sử được giữ để đối chiếu dữ liệu chính.
- `tests/`: kiểm tra registry, rule, paths, analysis và case log local.

Dataset phụ đã chuyển sang [archive](../archive/README.md). Báo cáo và định hướng cũ
được giữ như lịch sử; lệnh và đường dẫn hiện hành nằm trong README này.

Windows: chạy `Resource/setup.ps1` để tạo `Resource/.venv` bằng Python 3.12 và cài
`Resource/requirements.txt`; dùng Python trong môi trường đó với đường dẫn script trên.
