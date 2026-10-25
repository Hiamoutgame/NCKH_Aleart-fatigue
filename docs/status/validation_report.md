# Validation report — snapshot local ngày 23/10/2026

Báo cáo này chỉ ghi những kiểm tra thực hiện khi đồng bộ docs V3: đọc source/docs, xem artifact audit trước đó, đọc footer/schema chín Parquet, chạy CLI help/list và ba regression checks dùng dữ liệu tạm. **Không full-scan raw, không normalize lại outputs hiện có, không training và không đo RCA/grouping quality.**

Báo cáo ngày 19/10 được giữ nguyên tại [history](../history/resource_docs/validation_report_2026-10-19.md). Các claim “32/32 pass”, “đã giải quyết triệt để”, “hoàn toàn đủ điều kiện khoa học” và “50% train/50% test” trong bản đó **không được tái xác nhận** cho checkout hiện tại.

## 1. Môi trường và path

- Có source adapters trong `Resource/explore_datasets/`, raw ở `NCKH_rawData/raw_data/`, outputs ở `Resource/datasets/normalized/`.
- Không có `Resource/cp1/`, `Resource/cp2/` hoặc `Resource/archive/` trong workspace active. Bản sao công cụ dưới `.kilo/worktrees/` không được dùng thay source hiện hành.
- `Resource/explore_datasets/.venv/bin/python`: Python 3.14.4, import được pandas/pyarrow/pytest. Python hệ thống trong lần kiểm tra này thiếu ba modules trên.
- `bash run_datasets.sh --help` và `bash run_datasets.sh list` chạy thành công. `list` vẫn in path mặc định `Resource/cp1/raw_data/` đã vắng mặt; thành công của lệnh không chứng minh raw ở default tồn tại.

Không chạy `inspect all` hoặc normalize raw trong lần này. `--data-root` chỉ áp dụng một slug; hướng dẫn hiện hành ở [Resource map](../history/resource_map_2026-10-23.md).

## 2. Footer/schema Parquet đọc lại

| Dataset | incidents rows | ground_truth rows | log_events rows | Log row groups |
| --- | ---: | ---: | ---: | ---: |
| RCAEval | 735 | 735 | 5,272,618 | 30 |
| LEMMA-RCA | 4 | 4 | 200,000 | 1 |
| Nezha | 21 | 21 | 71,173 | 1 |

Cả chín file có schema columns khớp các dataclasses hiện tại. `log_events` có `log_id`, `incident_id`, `raw_message`, provenance fields, time/service/entity/severity/template/trace/span fields. `incidents` có `raw_label`, `fault_type`, `inject_time`, nên cần chặn leakage khi tạo features. Ground truth có original/canonical target và mapping status.

**Điều đã xác nhận:** file đọc được metadata/schema, số rows và row groups như bảng. **Chưa xác nhận:** unique incident coverage, nhãn đúng nguồn, raw record reconstruction, null/duplicate rates, inventory coverage, window alignment hoặc eligibility. Số row groups không phải phép đo số incident độc lập.

Đọc lại metadata từ root bằng môi trường local:

```bash
Resource/explore_datasets/.venv/bin/python - <<'PYMETA'
from pathlib import Path
import pyarrow.parquet as pq
for path in sorted(Path('Resource/datasets/normalized').glob('*/*.parquet')):
    pf = pq.ParquetFile(path)
    print(path, pf.metadata.num_rows, pf.metadata.num_row_groups, pf.schema_arrow.names)
PYMETA
```

Lệnh chỉ đọc footer/schema, không yêu cầu load bảng logs. Không gọi normalize để tái hiện bảng metadata này.

## 3. Kiểm tra CLI trên dữ liệu tạm

Đã chạy từ root:

```bash
PYTHONDONTWRITEBYTECODE=1 Resource/explore_datasets/.venv/bin/python -m pytest \
  -c Resource/pytest.ini Resource/explore_datasets/tests/test_dataset_workflow.py \
  -q -p no:cacheprovider -k 'shell_wrappers or custom_input or export_module'
```

**Kết quả: 3 passed, 5 deselected (5.18s).** Phạm vi:

1. Shell wrappers chạy từ thư mục khác với repo.
2. Một fixture RCAEval do test tạo có custom raw/output roots, một log được export đúng raw string và source ref.
3. Import export wrapper không tự chạy normalization hoặc tạo outputs.

Đây là regression checks có sẵn, không phải test mới cho V3. Năm case không được chọn gồm kiểm tra entrypoints, trong đó có CP1 đã vắng mặt; kết quả trên không đại diện full suite.

## 4. Kiểm tra control flow Nezha bằng fixture riêng

Tạo `fault_list.json` tổng hợp trong temporary directory, một hour bucket có hai faults khác nhau. Kết quả trên source hiện tại:

| Giá trị fixture | Kết quả |
| --- | ---: |
| Fault records trong JSON / `inspect()` | 2 / 2 |
| `load_incidents()` | 1 |
| `load_ground_truth()` | 1 |
| Record được tạo | Fault cuối bucket |

Fixture này tái hiện phần tạo record ở ngoài vòng từng `item`; **không phải thống kê corpus Nezha**. Không sửa adapter trong lần cập nhật docs. Xem [implementation status](implementation_status.md).

## 5. Kết quả audit cũ và code assumptions

[DATASET_PLAN 20/10](../data/DATASET_PLAN.md) báo raw tổng 400.362 GB theo file sizes, chưa deduplicate; RCAEval 735 cases/359 log files/49,652,771 log rows/240 trace cases. Audit chỉ xác minh prefix 200 label rows thuộc RE1 không log, nên chưa xác nhận eligible ranking cases. Đây là artifact lịch sử, không phép đo full corpus mới.

Những khác biệt đáng chú ý so với báo cáo 19/10:

- RCAEval `normalize(max_cases=30)` cap logs; metadata/GT 735 rows không chứng minh log coverage toàn corpus. Writer theo case, loader vẫn full-case memory.
- Nezha chỉ export log incident đầu; vòng metadata làm mất faults trong bucket; không claim 21 incidents đều có log hoặc 100% TraceID/SpanID.
- LEMMA có scenario hard-code, file matching theo date/path, multi-target bị rút ở canonical target. Chưa claim đã khắc phục alignment/label hoàn toàn.
- Test canonical hiện hữu kiểm tra mẫu/fields; chưa kiểm chứng full provenance, leakage qua values/path hoặc split independence.

## 6. Kiểm tra docs và bảo toàn file

Đối chiếu với snapshot local lấy trước khi sửa: **74 file source/config/artifact/Parquet** được ghi nhận có hash không đổi, gồm cả **9 canonical Parquet**. Sáu bản sao lịch sử khớp byte với docs local trước sửa. Không hash toàn raw corpus 400 GB; không có thao tác ghi raw trong phiên này.

Kiểm tra 41 docs/phần bổ sung hiện hành: **187 liên kết local resolve được**, Markdown fences cân bằng, proposal giữ đủ **11 mục** theo khung cũ. Phần lịch sử nguyên văn được giữ riêng hoặc dưới banner, không được coi là hướng dẫn runtime đã kiểm chứng.

## 7. Kết luận có thể sử dụng

Checkout có data-preparation source và canonical outputs để tiếp tục audit. **Chưa đủ bằng chứng để chứng nhận sẵn sàng train/evaluate service RCA V3**, chưa có split protocol được khóa hoặc Top-k/grouping metric thực đo.

Tiếp theo là case eligibility và xác minh labels/windows/inventory/provenance, xử lý code gaps, rồi baseline theo [research protocol](../research/research_protocol_v3.md). Việc xác minh nội dung/raw và sửa code là công việc tiếp theo, không được ghi thành đã hoàn thành trong docs.
