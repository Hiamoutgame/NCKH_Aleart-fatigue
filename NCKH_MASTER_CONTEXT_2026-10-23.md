# NCKH — Master Project Context & Research Handoff

**Snapshot: 2026-10-23.** Đây là context làm việc V3, hợp nhất bản bàn giao của chủ dự án và đối chiếu repository local. RQ, tên đề tài và novelty **chưa được Prof. Long phê duyệt**. Không có kết quả model V3 được xác nhận trong lần cập nhật này.

## 0. Bản chất đề tài

Nghiên cứu offline thuộc AIOps / log analysis cho microservices: **evidence-preserving hierarchical log organization + service-level root-cause candidate ranking**. Tổ chức nhiều log thành nhóm phân cấp để khám phá, giữ bằng chứng gốc và xếp hạng service đáng điều tra.

- Giảm số mục ở màn hình tổng quan, không xóa event nguồn.
- Correlation không đồng nghĩa causation.
- Nhãn root-cause service không phải nhãn root-cause log.
- Proposal, target và kết quả thực nghiệm là ba loại thông tin khác nhau.

## 1. Thứ tự đọc và nguồn bằng chứng

| Cần xác định | Nguồn ưu tiên | Giới hạn |
| --- | --- | --- |
| Scope hiện tại | Bản bàn giao của chủ dự án ngày 23/10/2026 → tài liệu này → [proposal V3](01_topic_proposal/topic_proposal.md) | Working direction, chưa phải phê duyệt của thầy |
| Code đã triển khai | Source thật trong [explore_datasets/src](Resource/explore_datasets/src/README.md) | Tên folder hoặc README không chứng minh chức năng đã chạy |
| Dữ liệu hiện có | Footer/schema kiểm tra ngày 23/10 trong [validation report](Resource/docs/validation_report.md) | Không thay thế audit nội dung và join theo incident |
| Audit raw trước đây | [DATASET_PLAN](NCKH_rawData/spec/DATASET_PLAN.md), `audit_summary.json`, `audit_findings.json`, `l1_evidence.json` | Artifact ngày 20/10, giới hạn L0/L1; không chạy lại toàn corpus |
| V1/V2 và kết quả từng báo cáo | [history index](Resource/docs/history/README.md) | Chỉ dùng với nhãn lịch sử; claim paper chưa được rà soát độc lập |

Tên `Context-cho-AGEnt-hiểu-hướng-đi-của-dự-án-(AGENTS).txt`, `sources/`, `data/`, `MANIFEST.txt` thuộc mô tả gói handoff. **Không tìm thấy các đường dẫn đó ở root checkout này**; không tạo liên kết giả hoặc khẳng định đã đọc chúng. Handoff được cung cấp trực tiếp trong hội thoại. Repository local có source và dữ liệu nhiều hơn gói upload được mô tả.

Quy ước: **SOURCE FACT** = quan sát trực tiếp ở nguồn chỉ rõ; **HISTORICAL REPORT** = tài liệu cũ báo cáo; **PROPOSAL** = phương án chưa chốt; **INFERENCE** = suy luận; **UNVERIFIED** = thiếu kiểm chứng. Kết quả kiểm thử chỉ có giá trị trong phạm vi test đã chạy.

## 2. Lịch sử scope

| Phiên bản | Trọng tâm | Trạng thái |
| --- | --- | --- |
| V1 | WARNING-only Alert Aggregation; bốn arms gồm rule, semantic, temporal-spatial, tool-calling Agent; ARR/RCPR/F1/Purity | Lịch sử: [README V1](Resource/docs/history/README_V1_before_V3.md) |
| V2 | Log-based RCA + Near-Future Failure Prediction; signal filtering và prediction | Lịch sử: [proposal V2](01_topic_proposal/history/topic_proposal_V2.md) |
| V3 | Audit → canonicalization → grouping → hierarchy → optional evidence relationships → service ranking → evaluation | Working direction mới nhất |

Không đưa WARNING-only, autonomous Agent, failure prediction, synthetic runbook, target ARR 60% hoặc Top-1 70% vào V3 theo mặc định. Timeline 8 tuần, khoảng 2 giờ/ngày là kế hoạch ban đầu, không phải tiến độ hiện tại.

## 3. Bối cảnh, người dùng và ràng buộc

Người hưởng lợi: developer, on-call engineer, SRE, DevOps. Một incident có log lặp lại và triệu chứng liên quan giữa nhiều service; cần ưu tiên điều tra nhưng vẫn mở lại được bằng chứng. Dùng máy local và dataset có sẵn, tập trung thực nghiệm, baseline, ablation và paper. Không bắt buộc production cluster, collector real-time, Grafana/Prometheus dashboard hoặc self-host LLM lớn.

## 4. Problem statement và đầu ra

Từ log của một incident, tạo cấu trúc `incident → service → template/semantic group → raw event references`. Mỗi nhóm cần member IDs, service, đại diện, số event, khoảng thời gian và nguồn. Những event chưa rõ service phải vẫn truy xuất được, không tự sinh service để lấp chỗ trống.

**Ví dụ giả định, không phải output thực nghiệm:**

```text
Incident A
├── service có trong inventory
│   ├── Timeout group → [log_id_1, log_id_2, ...]
│   └── Retry group   → [log_id_3, ...]
└── nhóm chưa rõ service → [log_id_4, ...]

Ranking: service_id, score, rank, supporting_group_ids, supporting_log_ids
Optional link: co_occurs_with, method, threshold, supporting IDs
```

Organization, relationships và ranking là ba đầu ra riêng. Nhóm được chọn để giải thích điểm là **supporting evidence**, chưa phải ground-truth root-cause log. Code hiện dùng **`log_id`**, tương ứng khái niệm `event_id`/`raw_log_id` trong handoff; chưa đổi tên schema.

## 5. Working research question và novelty

> Can evidence-preserving hierarchical log organization reduce information overload while maintaining accurate service-level root cause localization in microservice systems?

Bản Việt: Liệu tổ chức log phân cấp, bảo toàn bằng chứng gốc, có thể giảm số mục cần đọc mà vẫn duy trì độ chính xác định vị service gây lỗi trong microservices?

Câu hỏi con đề xuất:

1. Template/semantic grouping giảm số mục hiển thị bao nhiêu so với raw logs?
2. Mọi event và service có còn truy ngược được không?
3. Temporal/relationship features có cải thiện held-out Top-k so với baseline đơn giản không?
4. Runtime, memory và độ ổn định thay đổi thế nào theo incident?
5. Nếu làm user study phù hợp, thời gian người dùng tìm đúng service có giảm không?

Novelty **chưa xác nhận**. Không viết “first hybrid combination” hoặc “chưa ai làm” trước systematic related-work review. Giảm số mục hiển thị chưa chứng minh giảm tải nhận thức hay Time to Locate.

## 6. Scope và invariants

**IN:** audit schema/labels; normalization/parsing/grouping; hierarchy; evidence links nếu đủ dữ liệu; service candidate ranking; baseline/ablation; traceability; tái lập.

**OUT mặc định:** WARNING-only; deletion/noise removal khỏi dữ liệu gốc; failure forecasting; causal graph accuracy khi thiếu nhãn; autonomous LLM Agent; production monitoring stack.

Các bất biến cần được kiểm tra khi triển khai:

- Mọi event trong phạm vi xử lý có ID và nguồn; mọi nhóm truy về đúng raw records. Missing service/timestamp được báo riêng, không mất event âm thầm.
- Candidate chỉ từ inventory quan sát hoặc metadata/config đáng tin; không lấy ground truth để bổ sung đáp án vào inventory.
- Split theo incident; các case lặp/chung nguồn có nguy cơ leakage phải cùng fold. Cross-system giữ nguyên một system family qua mọi phiên bản.
- Xác minh đơn vị, timezone, clock normalization và missing timestamps; chuyển sang UTC trong code không tự chứng minh đồng hồ nguồn đúng.
- Mỗi cạnh ghi loại bằng chứng, method, threshold và supporting IDs; không tự dùng `caused_by`.
- Không dùng test labels, fault code, case/path chứa nhãn, `raw_label` hoặc metadata đáp án làm feature. Không tune theo test.

## 7. Inventory local và trạng thái dữ liệu

| Thành phần | Đường dẫn thật | Trạng thái |
| --- | --- | --- |
| Raw RCAEval | `NCKH_rawData/raw_data/huggingface/rcaeval/` | Có local; audit 20/10 báo 735 case, 359 log files không rỗng |
| Raw LEMMA-RCA | `NCKH_rawData/raw_data/huggingface/lemma_rca/` | Có local; schema/kịch bản cần xác minh theo từng partition |
| Raw Nezha | `NCKH_rawData/raw_data/nezha/` | Có local; mapping pod/service và incident windows cần audit |
| Canonical outputs | `Resource/datasets/normalized/<slug>/` | Có ba bảng/dataset; footer đã đọc lại ngày 23/10 |
| Adapters + CLI + tests | `Resource/explore_datasets/` | Source có thật; chưa có pipeline V3 end-to-end |
| Metadata audit riêng | `NCKH_rawData/spec/` | Có script, tests, JSON/CSV audit L0/L1 |
| CP1/CP2 cũ | `Resource/cp1/`, `Resource/cp2/` | Không hiện diện trong checkout đang làm; có bản lịch sử dưới worktree công cụ, không dùng như source active |

**Path mismatch:** `paths.py` vẫn mặc định về `Resource/cp1/raw_data/`, hiện không có. CLI `list` chỉ in cấu hình, không chứng minh raw tồn tại. Dùng `--data-root` cho từng dataset; chưa đổi code trong lần cập nhật docs.

Footer canonical xác nhận:

| Dataset | Incident rows | Ground-truth rows | Log-event rows | Phạm vi chưa được chứng minh |
| --- | ---: | ---: | ---: | --- |
| RCAEval | 735 | 735 | 5,272,618 | Không phải toàn bộ 359 case logs; code mặc định tối đa 30 case |
| LEMMA-RCA | 4 | 4 | 200,000 | Code mặc định 50,000 logs/scenario; chưa xác minh đầy đủ alignment/labels |
| Nezha | 21 | 21 | 71,173 | `normalize()` chỉ xuất log cho incident đầu tiên; số metadata rows không phải log coverage |

Nguồn: [validation report](Resource/docs/validation_report.md). Footer chỉ xác nhận số dòng/cột/row groups; chưa đo unique incident coverage, null rates, inventory recall hay correct raw reconstruction.

Audit raw 20/10 báo tổng 400.362 GB theo kích thước file, chưa khử trùng, LEMMA chiếm phần lớn. RCAEval có 49,652,771 log rows theo footer; 240 cases có traces. Đây là kết quả artifact trước đó, **không phải full scan vừa chạy lại**. Số WARN 9,738 (Sock Shop 9,662; Train Ticket 74; Online Boutique 2), 8 `root_cause.txt`, 4 WARNING indicators thuộc báo cáo V1, chưa tái kiểm trong phiên này.

`DATASET_PLAN.md` chỉ xác minh prefix 200 nhãn thuộc RE1 không có log; **0 ranking case đã xác minh trong audit đó** không có nghĩa dataset không có nhãn. Không lấy 359 case có log làm số incident chắc chắn đủ điều kiện RCA.

## 8. Pipeline: input → output → gate

| Bước | Input / phương án | Output cần có | Gate |
| --- | --- | --- | --- |
| 1. Audit | Raw metadata/log schema/labels | Data card, case eligibility, missingness và lý do loại | Biết số case hợp lệ cho từng mục tiêu |
| 2. Preparation | IDs, timestamp/service normalization, controlled masking | Canonical events, provenance, inventory, split manifest | Không mất raw strings/incident boundaries; audit mapping |
| 3. Parsing | Regex hiện có; Drain3/Spell là ứng viên | Template/parameter/reference | Đo coverage và lỗi parse; không gọi regex hash là Drain3 |
| 4. Grouping | Exact template baseline; SBERT/HDBSCAN là ứng viên | Group records và member mapping | Đủ event, tái lập config/seed |
| 5. Hierarchy | Incident/service/groups | Indexed tree + raw references | Mọi event reachable; không thêm service |
| 6. Relationships, tùy chọn | Time overlap/semantic/dependency | Annotated edges + evidence | Chỉ claim loại liên hệ có bằng chứng |
| 7. Ranking | Features hợp lệ từ log/groups/inventory | Service scores/ranks + supporting IDs | Candidates hợp lệ, held-out evaluation, không leakage |
| 8. Evaluation | Cùng dataset/split cho variants | Metrics, ablation, error analysis, paper figures | Mỗi con số kèm protocol và run manifest |

Hiện code có `normalize_message` và MD5 12 ký tự của chuỗi đã mask làm `template_id`; chưa thấy implementation Drain3/Spell, semantic clustering, group/tree/edge/ranker/training/evaluation V3 trong source active. [Implementation status](Resource/docs/implementation_status.md) nêu bằng chứng và các giới hạn cụ thể.

## 9. Baselines và ablation — đề xuất

| ID | Variant | Đánh giá được |
| --- | --- | --- |
| B0 | Flat raw logs, timestamp order | Workload reference; không có rank thì không so Top-k |
| B1 | Service + explicit severity nếu có + time window | Grouping theo rule |
| B2 | Template-only + frequency | Parsing/grouping baseline; parser chưa chốt |
| B3 | B2 + semantic clustering | Lợi ích semantic grouping |
| B4 | B3 + temporal/dependency relationships | Lợi ích liên hệ có bằng chứng |
| P | Hierarchy + explicit service ranker, có thể kết hợp B4 | Proposed combination, chưa chứng minh tốt hơn |

`pineline_training_model.md` đề xuất MVP ranker Logistic Regression và các experiment E1–E5, ưu tiên E1–E3 trước. Đây là kế hoạch triển khai chi tiết, **không thay thế RQ hoặc tự chốt thuật toán V3**. B0–P là các variant mức nghiên cứu, E1–E5 là so sánh features/ranker trong MVP; không đồng nhất hai bảng.

Ablation: template vs semantic; bỏ temporal; bỏ topology; giữ candidate/ranker cố định khi đo grouping; giữ grouping cố định khi đo ranker. Feature/scaler/parser có fit chỉ học trên train. Tune validation, khóa test. Chia 50/50 (báo cáo 19/10), 70/15/15 (training note), 60/20/20 (audit plan) là **các đề xuất khác nhau, chưa có split thực thi được chốt**. Lưu actual IDs, group keys và seed trước khi chạy; không chọn tỷ lệ theo test score.

## 10. Metrics và protocol

| Metric | Định nghĩa làm việc | Điều kiện diễn giải |
| --- | --- | --- |
| Visible Log Reduction | `1 - N_visible_items / N_raw_events_in_scope` | Khai báo tree level; so sánh grouping tại cùng group level; không dùng xóa log hoặc top-3 evidence làm reduction |
| Raw Log Traceability | `N_unique_raw_events_correctly_reachable / N_raw_events_in_scope` | Kiểm tra nguồn thực, deduplicate ID; mục tiêu bất biến 100%, chưa có số đo toàn corpus |
| Top-1 / Top-3 RCA | Tỷ lệ incident có service ground truth trong Top-k | Nhãn service hợp lệ; `k'=min(k, số candidate)`; candidate-missing phải báo |
| Runtime / Memory / Cost | Per-stage và end-to-end | Ghi CPU/RAM, kích thước dữ liệu, versions/config |
| Time to Locate | Thời gian người dùng tìm đúng service | Chỉ claim nếu có user study phù hợp |

Đề xuất báo **candidate coverage**, conditional Top-k và end-to-end Top-k riêng; không loại âm thầm case inventory thiếu đáp án để nâng điểm. Với multi-target ghi Hit@k/Recall@k/MRR theo protocol rõ; không âm thầm rút nhãn còn một service. Mẫu số rỗng là `N/A`. Grouping purity/pairwise F1 cần nhãn grouping thật hoặc annotation có protocol, không lấy service root-cause label làm log cluster label.

V1 targets: ARR ≥60%, RCPR ≥95%, pairwise F1 ≥0.85, purity ≥0.80; tài liệu có xung đột ARR 50/60%. V2 targets: Top-1 ≥70%, Top-3 ≥85%, prediction F1 ≥0.70, AUC ≥0.75, lead time ≥5 phút. **Không phải kết quả hoặc target V3.**

## 11. Vai trò AI và mô hình

AI hỗ trợ embedding/grouping, feature learning và ranking; output phải truy về dữ liệu. Bắt đầu từ baseline đơn giản. Drain3/Spell, Sentence-BERT/HDBSCAN, Logistic Regression/XGBoost và tên “System One” là ứng viên/thiết kế. Không mặc định LLM Agent, LSTM prediction, synthetic runbook hoặc model tự suy diễn nguyên nhân.

## 12. Related work

[Related-work matrix](02_related_work/literature_review_matrix.md) phân biệt candidate papers với kết luận đã kiểm chứng. COLA, AlertGuardian, RCAEval, LEMMA-RCA, Nezha, Drain, SBERT, HDBSCAN, SRE Book là các tên đã xuất hiện trong tài liệu cũ; metadata, paper results và reproducibility claims chưa được rà soát web/paper gốc trong lần đồng bộ docs này. Không dùng danh sách này làm bằng chứng novelty.

## 13. Threats to validity

1. Severity thiếu hoặc regex nhận sai; unknown không mặc định INFO.
2. Case/log coverage và số log mỗi system không đều; export có sampling/cap.
3. Service-level labels không cung cấp noise/symptom/causal/log-level labels.
4. Mapping pod/container/service, clock/window hoặc multi-target bị đơn giản hóa có thể làm sai eligibility.
5. Nhãn/đường dẫn/fault code hoặc synthetic topology/runbook có thể leak đáp án.
6. Temporal proximity, similarity, trace calls chưa chứng minh causal fault propagation.
7. Reduction, grouping quality, ranking accuracy và human workload là các kết luận riêng.
8. Same-system split không chứng minh cross-system generalization; case lặp có thể leak.
9. Tune windows/thresholds trên test gây lạc quan sai; phải báo exclusions/candidate misses.
10. Metadata `mapping_status="verified"` do code gán và tên test không thay thế audit độc lập.

## 14. Decision log

**Working decisions:** offline/dataset-first; giữ raw và provenance; hierarchy để khám phá; relationships tùy bằng chứng; ranking service trước; trusted inventory; split theo incident/nhóm nguồn; không mặc định WARNING-only hay prediction.

**Còn mở:** tên/RQ/novelty với thầy; parser/grouping/ranker/hyperparameters; dataset mix và label mapping; annotation cho groups/relationships; split protocol/tỷ lệ; user study; target metrics; go/no-go sau pilot. Tài liệu này không tự phê duyệt những lựa chọn đó.

## 15. Roadmap đề xuất

| Milestone | Deliverable / gate | Trạng thái |
| --- | --- | --- |
| M0 Reconcile | Context, docs, source/data inventory nhất quán | Đã đồng bộ docs ngày 23/10; còn path/code gaps |
| M1 Audit | Case eligibility, schema, evidence/label availability | Có audit L0/L1 lịch sử, chưa xong eligibility RCA |
| M2 Canonical | IDs, mapping/provenance, timestamp, inventory, split | Có adapters/Parquet; cần kiểm chứng và sửa gaps |
| M3 Baseline | Rule/template grouping + simple RCA score | Chưa xác nhận implementation |
| M4 Grouping | Hierarchy, reversibility, semantic option/ablation | Chưa xác nhận implementation |
| M5 Ranking | Valid candidates, features, held-out Top-k | Chưa có kết quả |
| M6 Analyze | Errors, robustness, runtime/memory | Chưa có kết quả V3 |
| M7 Paper | Related work, method, experiments, limitations | Bản thảo cũ là lịch sử; V3 cần evidence mới |

Go/no-go: thiếu incident labels hoặc event/service join đáng tin thì chưa hứa service RCA; tiếp tục grouping/exploration và xem dataset khác. Thiếu relationship labels thì không claim causal graph accuracy. Roadmap là kế hoạch, không phải cam kết thời hạn.

## 16. Prompt chuyển giao

> Đọc NCKH_MASTER_CONTEXT_2026-10-23.md và Resource/docs/implementation_status.md trước khi đề xuất. Mặc định V3 evidence-preserving hierarchy + service-level candidate ranking. Phân biệt source fact, historical report, proposal, inference, unverified. Giữ raw và mapping log_id→group→service; không bịa service/metric/paper results/code đã có. Audit→canonicalization→baseline grouping→hierarchy→optional evidence links→ranking→held-out evaluation. Không coi correlation là causation hoặc service label là log label. Kiểm tra path/schema nguồn thực; không dùng worktree lịch sử như source active. Những lựa chọn chưa chốt phải giữ trạng thái đề xuất.

## 17. Bản đồ tài liệu

- [README](README.md): lối vào và quick start.
- [Proposal V3](01_topic_proposal/topic_proposal.md): giữ khung 11 mục đề xuất ban đầu.
- [Resource map](Resource/README.md), [src architecture](Resource/explore_datasets/src/README.md): cấu trúc code thật.
- [Implementation status](Resource/docs/implementation_status.md), [dataset audit](Resource/docs/dataset_audit.md), [validation](Resource/docs/validation_report.md): bằng chứng/giới hạn.
- [Research protocol](Resource/docs/research_protocol_v3.md): phương án đánh giá và output contract chưa triển khai.
- [Training note](Resource/note/pineline_training_model.md): thiết kế MVP để tra cứu, chưa là code.
- [History](Resource/docs/history/README.md): V1/V2 và báo cáo cũ.
- [Docs reconciliation](Resource/docs/docs_reconciliation_2026-10-23.md): thay đổi và cách kiểm tra.

## 18. Giới hạn snapshot

Lần cập nhật này đọc docs/source, artifact audit cũ và footer 9 Parquet; không tải dữ liệu, không normalize lại, không full-scan raw, không huấn luyện, không đo Top-k/grouping/user study, không xác minh literature ngoài repo. Không có package manifest SHA-256 do chủ dự án cung cấp tại root; không giả lập tính toàn vẹn của gói upload. Raw/Parquet và source thực thi được giữ nguyên.
