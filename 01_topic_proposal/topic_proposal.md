# Topic Proposal — Phiên bản hiện hành

> **Phiên bản đang dùng trong repository: V3 — cập nhật 23/10/2026.** Nội dung được cập nhật trực tiếp trong file `01_topic_proposal/topic_proposal.md`, giữ khung 11 mục và thay thế proposal V2 tại đường dẫn này. Định hướng hiện tại là tổ chức log phân cấp có bảo toàn bằng chứng và xếp hạng service nghi ngờ gây lỗi.
>
> **Trạng thái nghiên cứu:** bản đề xuất làm việc, chưa được Prof. Long phê duyệt; tên đề tài, RQ, novelty và thuật toán cuối cùng còn cần thống nhất. Phiên bản hiện hành trong repo không đồng nghĩa phương pháp đã được duyệt hoặc triển khai xong.

[Bản tóm tắt hiện hành](readme) · [Master context](../NCKH_MASTER_CONTEXT_2026-10-23.md). [Proposal V2](history/topic_proposal_V2.md) chỉ dùng đối chiếu lịch sử.

## 1. Group Information

- Class: SE1922.
- Leader: _(chưa điền)_.
- Members: _(chưa điền)_.
- Người hướng dẫn được ghi trong context dự án: Prof. Long.

## 2. Proposed Title

**English working title:** Evidence-preserving Hierarchical Log Organization and Service-level Root Cause Localization in Microservice Systems.

**Tên tiếng Việt dự kiến:** Tổ chức log phân cấp có bảo toàn bằng chứng và định vị service nguyên nhân gốc trong hệ thống microservices.

Tên chính thức, RQ và novelty cần thống nhất với người hướng dẫn. “Near-Future Failure Prediction” thuộc V2, không còn là mục tiêu mặc định.

## 3. Application Domain

AIOps / log analysis trong vận hành phần mềm (SRE/DevOps), observability cho microservices. Nghiên cứu **offline** trên dataset có sẵn, dùng máy local; tập trung phương pháp, thực nghiệm và paper, không xây monitoring stack production.

## 4. Problem Statement

Một incident có thể tạo nhiều log từ nhiều service. Những dòng lặp lại, thông tin thường ngày và triệu chứng liên quan khiến engineer phải đọc nhiều trước khi xác định nơi cần điều tra. Nhãn service gây lỗi không tự chỉ ra log nào là nguyên nhân hoặc log nào nên bỏ.

Bài toán V3: tổ chức log thành cấu trúc dễ khám phá, giữ toàn bộ bằng chứng nguồn và dùng đặc trưng kiểm tra được để xếp hạng service nghi ngờ. Phân biệt:

- **Organization:** incident → service → template/semantic group → raw references.
- **Relationships:** liên hệ temporal/semantic/dependency có supporting evidence, chưa phải causation.
- **Ranking:** service scores/ranks kèm groups/logs hỗ trợ kiểm tra.
- **Visibility reduction:** giảm số mục ở tổng quan, không xóa raw events.

**Working RQ:** Can evidence-preserving hierarchical log organization reduce information overload while maintaining accurate service-level root cause localization in microservice systems?

## 5. Motivation

1. Các log tương tự có thể được xem qua một nhóm rồi mở lại từng raw event khi cần.
2. Candidate ranking có thể giúp chọn service điều tra trước; phải đo held-out accuracy thay vì mặc định nhiều ERROR là nguyên nhân.
3. Provenance — thông tin file/bản ghi gốc — giúp kiểm tra nhóm và bằng chứng của ranking.
4. Scope service-level phù hợp loại nhãn đang xem xét hơn việc tự tạo nhãn root-cause-log.
5. Thiết kế nhỏ, baseline rõ và audit trước phù hợp nguồn lực local.

Đây là lý do thực hiện nghiên cứu, **chưa phải bằng chứng** phương pháp cải thiện thời gian điều tra hoặc novelty đã xác nhận.

## 6. Target Users

- Developer và on-call engineer.
- SRE, DevOps engineer và đội vận hành microservices.

User study chỉ được đưa vào deliverable nếu có protocol và người tham gia phù hợp; không mặc định có dữ liệu đánh giá con người.

## 7. Proposed AI Model / Method

```text
Dataset audit + case eligibility
    → Canonical events + raw provenance + trusted inventory + incident split
    → Parsing + grouping
    → Incident/service/group hierarchy
    → Optional evidence relationships
    → Service candidate ranking + supporting IDs
    → Held-out evaluation + ablation + error analysis
```

| Bước | Phương án nghiên cứu | Output / gate |
| --- | --- | --- |
| Audit | Schema, incident/label/window/service join, null/duplicate | Biết rõ case dùng cho grouping và case dùng cho RCA |
| Preparation | Timestamp/service canonicalization, IDs, controlled masking | Giữ raw strings và nguồn, không mất incident boundary |
| Parsing/grouping | Exact normalized-template baseline; Drain3/Spell; SBERT/HDBSCAN là ứng viên | Group members và representative; kiểm tra coverage, determinism |
| Hierarchy | Indexed tree, không bắt buộc frontend | Mọi event truy ngược được, kể cả thiếu service |
| Relationships | Time overlap, semantic similarity, observed dependency | Edge type/method/threshold/supporting IDs; có thể bỏ nếu thiếu bằng chứng |
| Ranking | Time/frequency heuristic; Logistic Regression/XGBoost nếu đủ nhãn | Chỉ rank service trong trusted inventory, giữ evidence references |

**Trạng thái implementation:** có adapters, canonical tables, regex normalization và hash template key. Chưa có implementation V3 grouping/hierarchy/ranker trong source active. `log_id` là event ID hiện có. [Implementation status](../Resource/docs/implementation_status.md) ghi chi tiết, gồm lỗi/giới hạn cần xử lý trước thực nghiệm.

Model cuối cùng, feature set và hyperparameters chưa chốt. [Training note System One](../Resource/note/pineline_training_model.md) là thiết kế MVP để thử, chưa phải model đã train.

## 8. System Features

Các chức năng nghiên cứu dự kiến:

1. **Dataset audit:** data card, eligibility và lý do loại từng incident.
2. **Normalization/provenance:** canonical schema và mapping về raw records.
3. **Grouping/hierarchy:** nhóm theo service/template hoặc semantic, giữ member IDs và log chưa phân giải.
4. **Evidence relationships, tùy chọn:** liên kết nhóm có loại bằng chứng rõ.
5. **Service ranking:** Top-k candidates, score và groups/logs hỗ trợ.
6. **Reproducible evaluation:** cùng split/candidate/data scope, run manifest và error analysis.

Không bắt buộc collector real-time, dashboard production, LLM Agent, prediction hoặc noise deletion. Những mục trên là chức năng dự kiến, không phải danh sách đã hoàn thành.

## 9. Expected Contribution

Các đóng góp **cần kiểm chứng**, chưa claim novelty:

1. Một cách biểu diễn hierarchy có provenance cho khám phá log microservices.
2. Phân tích trade-off giữa số mục hiển thị, traceability và service-level RCA ranking.
3. Protocol so sánh baseline/ablation, candidate coverage và lỗi trên held-out incidents.

Systematic related-work review và kết quả thực nghiệm mới quyết định có đóng góp phương pháp mới hay chủ yếu đóng góp đánh giá/tái lập. Không claim log-level causal diagnosis khi chỉ có service labels.

## 10. Evaluation Plan

### Dataset và mức bằng chứng

RCAEval là nguồn chính dự kiến; LEMMA-RCA và Nezha là ứng viên external/cross-system sau audit. Raw hiện ở `NCKH_rawData/raw_data/`, khác path CP1 mặc định trong source.

| Dataset | Canonical incident / GT rows | Canonical log rows | Giới hạn |
| --- | ---: | ---: | --- |
| RCAEval | 735 / 735 | 5,272,618 | Footer đã đọc lại 23/10; code cap tối đa 30 case logs mặc định |
| LEMMA-RCA | 4 / 4 | 200,000 | 4 scenario hard-code, cap 50,000/scenario; label/time alignment cần audit |
| Nezha | 21 / 21 | 71,173 | Code chỉ export logs incident đầu; fault loop và pod mapping cần kiểm tra |

Các con số là rows của file, **không chứng minh số eligible incidents**. Audit raw 20/10 báo 359 RCAEval cases có log nhưng chưa xác minh ranking labels cho tập có log trong giới hạn mẫu. Nguồn: [dataset audit](../Resource/docs/dataset_audit.md), [validation](../Resource/docs/validation_report.md), [raw audit plan](../NCKH_rawData/spec/DATASET_PLAN.md).

### Baselines và ablation đề xuất

| ID | Method | Mục tiêu so sánh |
| --- | --- | --- |
| B0 | Flat raw logs, timestamp order | Workload reference; không có rank thì không so Top-k |
| B1 | Service + explicit severity nếu có + time window | Rule grouping |
| B2 | Template-only + frequency | Parsing/grouping cơ bản |
| B3 | B2 + semantic clustering | Semantic grouping |
| B4 | B3 + temporal/dependency links | Quan hệ có bằng chứng |
| P | Hierarchy + explicit service ranker, có thể dùng B4 | Proposed combination |

Không coi đây là sáu RCA models có thể so thẳng. Muốn đo grouping, giữ ranker/candidates cố định; muốn đo ranking, giữ grouping/input cố định. Ablate semantic, temporal và topology riêng.

### Split và leakage

Tách theo incident/nhóm nguồn; các repetition của cùng cấu hình lỗi không nằm khác fold nếu có nguy cơ cùng dữ liệu. Cross-system giữ trọn một system family qua mọi phiên bản. Chưa khóa tỷ lệ split: docs cũ có 50/50, 70/15/15 và 60/20/20; chọn sau eligibility, trước test score, lưu actual IDs/seed/group key. Preprocessing có fit chỉ học train, tuning dùng validation.

Không dùng ground truth, `raw_label`, fault type, inject annotation, tên case/path chứa nhãn làm feature hoặc để thêm đáp án vào inventory. Ground truth chỉ dạy ranker trong train và chấm đánh giá.

### Metrics

- **Visible Log Reduction:** `1 - N_visible_items/N_raw_events_in_scope`; khai báo rõ tree level, không tính xóa event.
- **Raw Log Traceability:** số unique events truy đúng raw / số events trong phạm vi; mục tiêu kỹ thuật 100%, chưa đo toàn corpus.
- **Top-1/Top-3 service RCA:** báo candidate coverage, conditional và end-to-end scores; candidate thiếu đáp án không bị loại âm thầm. Với ít hơn K candidates, dùng tất cả candidates.
- **Runtime/Memory/Cost:** ghi riêng per-stage và end-to-end, máy/config/data size.
- **Time to Locate:** chỉ đo/claim nếu thực hiện user study.

Multi-target phải giữ tập nhãn và định nghĩa Hit@k/Recall@k phù hợp; không lấy riêng target đầu làm ground truth hoàn chỉnh. N/A nếu mẫu số rỗng. Chưa chốt target accuracy; target V1/V2 chỉ là lịch sử, không phải số đo V3.

### Research Questions đề xuất

- **RQ1:** Template/semantic grouping giảm số mục hiển thị thế nào ở cùng tree level?
- **RQ2:** Có bảo toàn raw events, service inventory và truy vết đúng nguồn không?
- **RQ3:** Template/temporal/relationship features có cải thiện held-out service RCA so với baseline đơn giản không?
- **RQ4:** Runtime, memory, error patterns và độ ổn định thay đổi ra sao theo system/incident?
- **RQ5, nếu khả thi:** Cùng giao diện khám phá, engineer tìm đúng service nhanh hơn không?

### Expert evaluation / user survey

Chưa xác định protocol, số người hoặc tính khả thi. Không dùng nhận xét không kiểm soát để claim cải thiện workload.

### Gate và threats

Trước train: xác minh labels/windows/inventory và exclusion reasons; trước kết luận: kiểm tra candidate misses, imbalance, repetition leakage, mapping và export caps. Không đủ service labels/join thì thu hẹp sang log organization/exploration. Thiếu edge labels thì không claim causal graph accuracy.

## 11. Related Papers

Giữ các nhóm bibliography của khung cũ nhưng coi là **candidate reading list**: Nezha/RCAEval/LEMMA-RCA cho RCA/dataset; Drain/Sentence-BERT/HDBSCAN cho parsing/grouping; COLA/AlertGuardian cho alert organization; SRE material cho background. “Intelligent Logging and Monitoring Strategies” là candidate từ V2, chưa xác minh chất lượng/metadata.

Không chép paper scores, venue/year hoặc “first/no prior work” thành source fact khi chưa đọc nguồn gốc. [Paper list](../02_related_work/paper_list.md), [matrix](../02_related_work/literature_review_matrix.md) và [search plan](../02_related_work/search_keywords.md) theo dõi việc kiểm chứng; lần đồng bộ này không thực hiện literature review mới.
