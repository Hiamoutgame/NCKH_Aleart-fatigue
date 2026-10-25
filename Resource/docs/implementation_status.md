# Implementation status — V3, 23/10/2026

Phạm vi đối chiếu: source active trong `Resource/explore_datasets/`, metadata audit ở `NCKH_rawData/spec/`, footer canonical outputs. [Master context](../../NCKH_MASTER_CONTEXT_2026-10-23.md) quy định scope; tài liệu này ghi **code thực sự làm gì**, không tự chứng nhận chất lượng khoa học.

## 1. Code đã có và khoảng trống V3

| Stage | SOURCE FACT: vị trí và hành vi | Chưa được chứng minh / còn thiếu |
| --- | --- | --- |
| Raw audit | [audit_metadata.py](../../NCKH_rawData/spec/audit_metadata.py), JSON/CSV artifacts ngày 20/10 | Eligibility/join/ground truth đầy đủ cho ranking chưa xác nhận |
| Canonical schema | [canonical.py](../explore_datasets/src/shared/domain/canonical.py): `Incident`, `LogEvent`, `GroundTruth` | Không có Group/Edge/Ranking model; schema riêng chưa bảo đảm leakage-free |
| CLI | [datasets_cli.py](../explore_datasets/src/interface/datasets_cli.py): registry ba adapters, list/inspect/normalize | Không có group/train/rank/evaluate commands; `all` không nhận `--data-root` |
| RCAEval | [adapter.py](../explore_datasets/src/datasets/rcaeval/infrastructure/adapter.py): metadata/log loading, UTC conversion, regex severity, export | Default log cap 30 case; metadata/GT toàn bộ không tương đương coverage log |
| LEMMA-RCA | [adapter.py](../explore_datasets/src/datasets/lemma_rca/infrastructure/adapter.py), [loader.py](../explore_datasets/src/datasets/lemma_rca/infrastructure/loader.py): JSON loading, bốn scenario hard-code, service mapping | Scenario/time/label nguồn cần đối chiếu; output giới hạn 50,000 logs/incident |
| Nezha | [adapter.py](../explore_datasets/src/datasets/nezha/infrastructure/adapter.py): CSV/nested JSON, fault windows, pod mapping, trace/span fields | Lỗi vòng lặp metadata; export logs chỉ incident đầu; coverage nhiều ngày chưa được chứng minh |
| Normalization | [normalization.py](../explore_datasets/src/shared/infrastructure/normalization.py): mask timestamp/UUID/thread/hex/numbers; adapter tạo MD5 12 ký tự | Chưa là parser Drain3/Spell được đánh giá; masking quá mạnh có thể gộp nhầm |
| Grouping + hierarchy | Chưa tìm thấy module thực thi trong source active | Cần groups/members/tree, unknown bucket, raw reconstruction checks |
| Evidence relationships | Chưa tìm thấy module thực thi | Cần type/method/threshold/supporting IDs; không tự có causal labels |
| Ranker + evaluation | Chưa tìm thấy feature/training/ranking/Top-k pipeline | Training note là thiết kế; chưa có model hoặc metric V3 xác nhận |

## 2. Các điểm phải xử lý trước khi claim sẵn sàng

### 2.1 Path và phạm vi export

[paths.py](../explore_datasets/src/shared/infrastructure/paths.py) trỏ raw vào `Resource/cp1/raw_data/`, nhưng raw thật ở `NCKH_rawData/raw_data/`. CP1 source/config/tests không hiện diện trong checkout active. Dùng `--data-root` từng dataset; việc sửa default path là công việc code sau, không thuộc lần cập nhật docs.

RCAEval ghi Parquet theo case nhưng vẫn đọc nguyên `logs.parquet` của mỗi case và tạo list events/DataFrame. Vì vậy không gọi là streaming từng record với bộ nhớ bị chặn. `select_balanced_cases()` chọn prefix theo `ob/ss/tt`, không phải random/stratified split để đánh giá. CLI chưa expose `max_cases` hoặc `limit_per_incident`.

### 2.2 Nezha: số incident và cửa sổ

Trong `load_incidents()` và `load_ground_truth()`, phần tạo record bị đặt **ngoài** vòng `for item in items`. Với mỗi hour bucket có nhiều faults, chỉ `item` cuối được tạo; `seen_ids` ở vòng trong không bảo đảm record ngoài vòng được deduplicate đúng. Đây là quan sát control flow, không suy ra con số incident thật toàn corpus.

`inspect()` chỉ đếm fault list đầu tiên. `normalize()` chỉ gọi `load_logs()` cho incident đầu tiên dù xuất metadata nhiều incidents. Cửa sổ `[-2 phút,+3 phút]` quanh injection là quy tắc adapter, chưa là incident boundary được dataset chứng nhận. Window chồng lấn, nhiều ngày, timestamp thiếu và incident không hợp lệ cần audit; timestamp có field trace/span không chứng minh quan hệ lan truyền lỗi.

### 2.3 Labels, inventory và leakage

- `GroundTruth.mapping_status="verified"` được adapter gán theo quy tắc hiện tại; không phải kết quả xác minh độc lập.
- `incidents.parquet` có `raw_label`, `fault_type`, `inject_time`; RCAEval `raw_label` chứa service đáp án. Không feed nguyên Incident/DataFrame vào model.
- LEMMA `load_ground_truth()` lấy phần đầu trước dấu phẩy hoặc `/`, làm mất multi-target/resource context ở `canonical_target`; `original_target` còn giữ chuỗi. Không dùng target đầu để tự chứng nhận full-label RCA accuracy.
- LEMMA scenarios và thời gian nằm trong code; `locate_log_files()` tìm theo tag/ngày trong path. Tên file không đủ xác minh event thuộc đúng time window.
- Nezha pod regex có danh sách tên cố định và fallback lấy token đầu; LEMMA có pod-prefix rules. Cần đối chiếu alias/inventory thật trước ranking, không thêm service từ nhãn vào candidate.
- LEMMA exploration `LemmaLoader.load_canonical_rows()` có cột `root_cause` gán từ service name. Đó là heuristic trong đường khám phá cũ, **không phải GT log-level** và không dùng làm feature/training label chính thống.

### 2.4 Raw preservation và IDs

Nezha `raw_message` giữ message đã tách từ nested `Log`, không giữ nguyên toàn CSV payload trong cột đó. Muốn tái dựng raw record phải giữ file nguồn và resolve đúng `source_file/source_row_id/raw_record_ref`.

IDs hiện dựa trên incident và row/index hoặc Elasticsearch `_id`; chưa có snapshot/file hash registry. Nezha cùng raw record có thể vào nhiều windows; LEMMA `_id` có thể cần thêm source scope để tránh collision. Đây là rủi ro cần đo, chưa phải duplicate rate đã quan sát. Không claim traceability 100% chỉ vì có chuỗi reference.

### 2.5 Timestamp và severity

RCAEval code coi integer timestamp là epoch giây và đổi UTC; audit raw 20/10 vẫn để một số đơn vị/timezone/anomaly chưa xác nhận. Nezha chia nanoseconds qua số thực trước `datetime`, cần kiểm tra độ chính xác nếu dùng time differences nhỏ. LEMMA gán UTC khi timestamp không có timezone: đây là assumption code, không tự chứng minh timezone nguồn.

RCAEval severity fallback tìm token trên message, không chỉ header, nên token `ERROR/WARN` có thể là nội dung thông báo. Helper legacy `infer_severity()` mặc định INFO khi unknown; canonical adapters dùng đường khác và có thể để null. Không mô tả cả repo là explicit-header-only hoặc unknown-always-null. Không suy severity từ ground truth.

## 3. Test có chứng minh gì?

[test_canonical_validation.py](../explore_datasets/tests/test_canonical_validation.py) kiểm tra mẫu rất nhỏ, có test chỉ kiểm tra field tồn tại, timezone marker hoặc tên field không thuộc blacklist. Chúng chưa chứng minh:

- Raw strings/payload tái dựng chính xác toàn corpus.
- Every eligible event thuộc đúng một group hoặc đúng incident window.
- Label/service mapping đúng nguồn hoặc model không leakage qua giá trị/path.
- Split independence, inventory coverage hoặc Top-k accuracy.

Nhiều test dùng raw mặc định CP1; [test_dataset_workflow.py](../explore_datasets/tests/test_dataset_workflow.py) còn đòi entrypoints CP1 đã vắng mặt. Báo cáo 32/32 ngày 19/10 là lịch sử. [Validation report](validation_report.md) ghi riêng những kiểm tra thực hiện trong lần cập nhật docs.

## 4. Thứ tự công việc đề xuất

1. Xác minh path, nguồn labels và case eligibility; không normalize đè file hiện có.
2. Sửa/kiểm chứng iteration Nezha, label multiplicity LEMMA, time/window/service aliases, provenance và export scope.
3. Khóa inventory + split/group keys + feature allowlist; tạo run manifest.
4. Baseline normalized-template groups/hierarchy, kiểm tra event membership và raw reconstruction.
5. Simple service scores rồi ranker nếu đủ nhãn; held-out evaluation, ablation riêng.

Đây là danh sách kỹ thuật cần làm, không tự chốt parser/model/RQ/target V3 và không ghi nhận rằng các lỗi đã được sửa.
