# lemma_rca — backup/external dataset candidate

Nguồn được ghi trong dự án: `Lemma-RCA-NEC/Product_Review_Original`. Raw thật: `NCKH_rawData/raw_data/huggingface/lemma_rca/`; default code vẫn CP1 cũ. Vai trò external ranking chỉ được xác lập sau audit labels/windows/services, chưa phải benchmark đã sẵn sàng.

## 1. Source hiện có

Module có domain models, application use cases, loader/downloader, canonical adapter, CLI và notebook. JSON log là Elasticsearch scroll format `hits.hits[*]._source`. Loader có bốn scenario hard-code cho DDoS/OOM, JMeter stress, storage failure, noisy neighbor; code này không tự chứng minh đã đối chiếu đầy đủ tài liệu gốc.

## 2. Canonical mapping và giới hạn

| Field | Source / hành vi |
| --- | --- |
| `timestamp_utc` | `@timestamp` ISO; thiếu timezone thì code gán UTC |
| `service_id` | App pod prefix/version ưu tiên; fallback container hoặc pod prefix |
| `entity_id` | Pod name hoặc container |
| `raw_message` | `_source.message` |
| `severity` | `level` nếu không unknown; fallback message regex; có thể null |
| `template_id` | MD5 12 ký tự của regex-normalized message |
| `trace_id/span_id` | Canonical adapter để null; không join trace modality |
| Provenance | File, ES `_id`/fallback và raw record reference |

`load_ground_truth()` giữ original target string nhưng canonical target chỉ lấy phần đầu trước `,` hoặc `/`. Không đánh giá multi-target/resource label bằng cách âm thầm dùng target đầu. `mapping_status=verified` là giá trị code gán. `locate_log_files()` tìm theo date tag/path; chưa chứng minh timestamps thật đúng scenario window. `normalize()` mặc định cap **50,000 logs/incident**.

Đường khám phá cũ `LemmaLoader.load_canonical_rows()` có cột `root_cause` gán từ service name; đó là heuristic, không GT log-level và không dùng làm feature/label chính thống.

## 3. Lệnh hiện có

Từ root repo:

```bash
bash run_datasets.sh inspect lemma_rca --data-root NCKH_rawData/raw_data/huggingface/lemma_rca
bash run_lemma_rca.sh --help
bash run_lemma_rca.sh profile --data-root NCKH_rawData/raw_data/huggingface/lemma_rca --limit 1000
bash run_lemma_rca.sh logs --data-root NCKH_rawData/raw_data/huggingface/lemma_rca --service productpage --limit 5
bash run_lemma_rca.sh list-incidents
```

Profile/logs có đọc dữ liệu mẫu; list-incidents chỉ in danh sách hard-code. Không cần fetch lại raw để cập nhật docs; lệnh downloader không phải bước bắt buộc V3. Không dùng default CP1 hoặc nhãn exploration để claim evaluation quality.

## 4. Trạng thái kiểm chứng

Footer canonical 23/10: **4 incident rows, 4 GT rows, 200,000 log rows**. Đây là số rows, không tự chứng minh coverage từng scenario, thời gian hoặc chất lượng nhãn. Cần xác minh nguồn scenario label, nhiều targets và alias service/resource; raw audit 20/10 vẫn ghi external eligibility chưa xác nhận.

[Validation report](../../../../docs/validation_report.md), [implementation status](../../../../docs/implementation_status.md). Chưa có grouping/hierarchy/service-ranker V3 hoặc kết quả Top-k trong module này; tần suất và semantic similarity không chứng minh causation.
