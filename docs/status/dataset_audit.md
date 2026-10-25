# Dataset audit — schema, phạm vi và bằng chứng V3

**Đối chiếu docs/source ngày 23/10/2026.** Không full-scan raw. [Audit 18/10](../history/resource_docs/dataset_audit_2026-10-18.md) được giữ nguyên; [raw audit L0/L1 20/10](../data/DATASET_PLAN.md) và artifact JSON/CSV là bằng chứng lịch sử gần hơn. [Validation report](validation_report.md) ghi footer mới đọc, tách khỏi kiểm chứng nội dung.

## 1. Phạm vi nguồn thật

Raw ở `data/raw/`, canonical ở `data/normalized/`, source adapters ở `src/`. `paths.py` mặc định đọc raw ở `data/raw/` (sửa ngày 25/10/2026); `--data-root` vẫn override được từng dataset; không sửa/move raw để làm docs khớp đường dẫn cũ.

| Dataset | Raw / đơn vị | Bằng chứng hiện có | Eligibility RCA |
| --- | --- | --- | --- |
| RCAEval | `huggingface/rcaeval/`; case | Audit 20/10: 735 case, 359 log không rỗng, 49,652,771 rows theo footer; 240 traces | Có nguồn service label nhưng chưa audit đầy đủ join label/log/window/inventory |
| LEMMA-RCA | `huggingface/lemma_rca/`; partition/scenario | Mẫu ES JSON và scenario metadata hard-code trong loader | Chưa xác minh toàn bộ thời gian/nguồn label/multi-target/service resolution |
| Nezha | `nezha/`; fault window | Mẫu CSV + fault annotation, trace/span fields | Pod-to-service và window/alignment cần xác minh; adapter fault loop có gap |

Các count raw là **HISTORICAL REPORT từ artifact 20/10**, chưa được full-run lại trong phiên 23/10. Audit prefix 200 RCAEval labels đều thuộc RE1 không log; kết quả “0 ranking case đã xác minh” trong audit đó chỉ là giới hạn kiểm tra, không phải kết luận thiếu ground truth toàn dataset.

## 2. Field mapping: source evidence và assumption code

| Canonical field | RCAEval | Nezha | LEMMA-RCA |
| --- | --- | --- | --- |
| `incident_id` | `rcaeval_` + `case` | `nezha_` + inject epoch | `lemma_` + scenario ID trong loader |
| `timestamp_utc` | `timestamp`; code coi epoch seconds | `TimeUnixNano`; code chia 1e9 | `_source.@timestamp`, ISO parsing |
| `service_id` | `container_name` trực tiếp | Regex/fallback từ `PodName` | Pod rules ưu tiên app/version hoặc container |
| `entity_id` | Container name | PodName | Pod hoặc container |
| `raw_message` | Chuỗi `message` | Message tách từ nested `Log`, không toàn raw payload | `_source.message` |
| `parsed_message` | Regex normalization | Regex trên message đã tách | Regex normalization |
| `template_id` | MD5 12 ký tự của parsed message | Tương tự | Tương tự |
| `severity` | Không cột riêng; header/token regex hoặc null | Nested JSON severity/level hoặc null | `level` nếu xác định, fallback message regex hoặc null |
| `trace_id` / `span_id` | Canonical adapter để null | Lấy TraceID/SpanID nếu có | Canonical adapter để null |
| `source_file` / `source_row_id` | File path + DataFrame index | File path + CSV row index | File path + ES `_id`/fallback |
| `raw_record_ref` | Case/log file + row | CSV basename + row | JSON basename + record ID |

Canonical dataclasses và ports: [canonical.py](../../src/shared/domain/canonical.py), [ports.py](../../src/shared/domain/ports.py). Mapping trên mô tả **hành vi source**, không chứng nhận alias/time/source identity đã đúng toàn corpus.

RCAEval audit xác nhận schema log có `timestamp`, `container_name`, `message`, không severity column. Đổi sang timezone-aware UTC trong code chưa chứng minh clock nguồn; raw audit còn để unit/timezone/anomalous index values chưa xác nhận. LEMMA timestamp thiếu timezone bị code gán UTC; Nezha precision qua số thực cần kiểm nếu dùng thời gian rất nhỏ.

## 3. Ground truth và boundaries

| Dataset | Label source mà code dùng | Giới hạn |
| --- | --- | --- |
| RCAEval | `cases.parquet:root_cause_service`, `label_level=service` | Kiểm tra completeness, aliases và presence trong candidate trước evaluation |
| Nezha | `fault_list.json:inject_pod`, `label_level=pod` | Service target là mapping của pod; không tự trở thành service GT đã xác minh |
| LEMMA-RCA | Bốn scenario hard-code, `label_source` trỏ tên PPTX | `canonical_target` lấy phần đầu trước `,` hoặc `/`; chưa đủ multi-target/resource semantics |

`mapping_status=verified` là giá trị code gán, không phải audit độc lập. `Incident.raw_label`, `fault_type`, `inject_time` là metadata nhạy về leakage; dùng allowlist feature, không feed nguyên bảng.

Nezha mặc định [-2,+3] phút quanh inject là **heuristic window**. LEMMA tìm file theo tag/ngày không chứng minh timestamps thật trong window; raw audit đã ghi mẫu tên file và ngày event khác nhau. Cần kiểm window overlap/shared source records trước split.

Không có nhãn chính thống trong các bảng này cho routine noise, propagated symptom, root-cause evidence log, group membership hoặc causal edges. Mọi nhãn suy từ rule phải ghi heuristic/synthetic; ERROR không phải nhãn kiểm chứng nguyên nhân.

## 4. Canonical outputs không đồng nghĩa toàn corpus

| Dataset | Incident / GT rows | Log rows ở footer 23/10 | Hành vi code cần lưu ý |
| --- | ---: | ---: | --- |
| RCAEval | 735 / 735 | 5,272,618 | `normalize(max_cases=30)`; metadata toàn bộ nhưng log subset |
| LEMMA-RCA | 4 / 4 | 200,000 | `limit_per_incident=50000`; bốn scenario hard-code |
| Nezha | 21 / 21 | 71,173 | `normalize()` log incident đầu; fault loop tạo record ngoài vòng từng item |

Số rows và số row groups không tự cung cấp unique incident count hoặc chứng minh export lineage. Chưa kiểm tra nội dung full outputs, null/duplicate rates, inventory coverage, raw reconstruction hoặc incident eligibility trong phiên này.

## 5. Audit tiếp theo cần tạo gì?

Data card + case eligibility + evidence references theo [research protocol](../research/research_protocol_v3.md): case/source identity, event/window/service mapping, label level/multiplicity/source, timestamp quality, provenance resolution, exclusions, candidate coverage và repetition/overlap groups. Grouping có thể dùng case không RCA labels; service ranking chỉ claim trên phạm vi labels hợp lệ. Không chọn 50/50 hoặc bất kỳ tỷ lệ nào chỉ vì có 359 log cases.

Thứ tự: reconcile paths → verify labels/windows/inventory → canonical provenance → freeze split → baseline. [Implementation status](implementation_status.md) chỉ rõ các code gaps; tài liệu này chưa ghi nhận chúng đã được sửa.
