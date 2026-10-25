# rcaeval — primary dataset candidate cho V3

Nguồn được ghi trong dự án: `phamquiluan/RCAEval`. Raw thật từ root: `NCKH_rawData/raw_data/huggingface/rcaeval/`. Default adapter vẫn ở CP1 cũ, hiện không tồn tại; dùng `--data-root`.

## 1. Dữ liệu và bằng chứng

Audit raw 20/10 báo **735 cases**, **359 log files không rỗng**, **49,652,771 log rows** theo footer; 375 RE1 cases không log và một case RE2 thiếu log. Đây là artifact lịch sử, không full-scan mới ngày 23/10. Schema log: `timestamp`, `container_name`, `message`; không severity column riêng.

Metadata label `root_cause_service` là mức service; không phải nhãn từng log. Việc container name khớp canonical service/target phải được audit; timestamp integer được code coi epoch seconds và chuyển UTC, chưa thay thế kiểm chứng clock nguồn.

## 2. Mapping hiện có

| Canonical | Nguồn / xử lý |
| --- | --- |
| Incident ID | `rcaeval_` + `case` |
| Log ID | Incident ID + row index |
| Service/entity | `container_name` trực tiếp |
| Raw/parsed message | Raw `message` + regex normalization |
| Template key | MD5 12 ký tự của parsed message, chưa phải Drain3 |
| Severity | Header hoặc token regex; unknown có thể null; token match chưa chứng minh severity thật |
| Trace/span | Canonical adapter để null |
| Provenance | File path, row index, raw record reference |

`incidents.raw_label` chứa service/fault label, không được dùng làm feature. `mapping_status=verified` được code gán khi label có giá trị, chưa là independent audit.

## 3. Lệnh từ root

```bash
bash run_datasets.sh inspect rcaeval --data-root NCKH_rawData/raw_data/huggingface/rcaeval

# Chỉ chạy khi cần output mới; đọc logs và ghi vào /tmp
bash run_datasets.sh normalize rcaeval \
  --data-root NCKH_rawData/raw_data/huggingface/rcaeval \
  --output-root /tmp/nckh-normalized-preview
```

`normalize(max_cases=30)` mặc định xuất metadata/GT toàn bộ nhưng logs tối đa 30 case được chọn prefix theo system. CLI chưa expose max_cases. Writer theo case, loader vẫn đọc nguyên mỗi case vào RAM.

## 4. Trạng thái và việc cần làm

Footer canonical 23/10: **735 incidents, 735 GT rows, 5,272,618 log rows**, 30 log row groups. Không suy row-group count thành unique eligible incidents. Cần audit labels/window/inventory/provenance, missingness, aliases và repetition groups trước ranking. Chưa có grouping/hierarchy/ranker/Top-k V3 trong module này.

[Validation](../../../../docs/validation_report.md), [implementation status](../../../../docs/implementation_status.md), [master context](../../../../../NCKH_MASTER_CONTEXT_2026-10-23.md). Log/service xuất hiện nhiều không chứng minh nguyên nhân.
