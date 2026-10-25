# Research protocol V3 — bản thiết kế để review

**23/10/2026, PROPOSAL.** Tài liệu biến [working scope](../../NCKH_MASTER_CONTEXT_2026-10-23.md) thành output/gate có thể triển khai. Những bảng/tên artifact dưới đây **chưa phải module hoặc file đã tồn tại**. [Implementation status](implementation_status.md) là nguồn trạng thái code.

## 1. Đơn vị nghiên cứu và eligibility

Đơn vị chấm RCA là incident; log event là đơn vị bảo toàn. Tách hai phạm vi:

| Phạm vi đề xuất | Điều kiện | Không được làm |
| --- | --- | --- |
| Grouping pool | Có logs đọc được, incident/source identity và provenance đáng tin | Đòi RCA label cho mọi log hoặc bỏ unknown events âm thầm |
| RCA evaluation pool `E` | Incident/window/source hợp lệ và nhãn service/tập service có bằng chứng, mapping ở đúng resolution | Loại case chỉ vì candidate thiếu đáp án |
| Training subset | Thuộc train; candidate labels hợp lệ và đủ class theo thuật toán | Dùng test labels để tạo feature/candidate |
| External evaluation | Nguồn/case qua audit, chưa dùng chọn feature/config | Gọi là external test sau khi đã tune theo nó |

Case eligibility cần số log, valid timestamps, source/window status, service resolution, original/canonical targets, label level/source/multiplicity, inventory coverage, lý do exclude và số raw events chưa phân giải. Distinguish `invalid`, `unverified`, `missing_information`; mọi case loại vẫn xuất hiện trong báo cáo.

Inventory baseline có thể là service quan sát trong logs; nếu mở rộng bằng traces/config phải chỉ rõ nguồn và availability tại inference. Đo riêng ground-truth-in-inventory coverage. Service đáp án không có trong log/inventory là giới hạn coverage, không được thêm đáp án từ ground truth.

## 2. Output contracts đề xuất

Schema source hiện dùng `LogEvent.log_id` và ba bảng canonical. Không đổi tên cột thành `event_id` chỉ để khớp ý tưởng. Các bảng mới có thể thiết kế như sau sau khi review:

| Artifact dự kiến | Trường tối thiểu / mục đích |
| --- | --- |
| Case eligibility | Incident/source/window/label status, counts, exclusions và coverage |
| Provenance registry | Snapshot/source file identity, row reference, `log_id`, raw content reference, transformation/config version |
| Service inventory | Incident, observed/canonical service ID, alias/source và mapping status |
| Split manifest | Incident/source group, train/validation/test, seed, protocol và input/config hashes |
| Groups | Group ID, incident/service, representative, count, time range, method/config |
| Group members | Group ID ↔ `log_id`; baseline partition đúng một membership/event |
| Hierarchy index | Incident → service/unknown bucket → group → member references |
| Evidence edges, tùy chọn | Source/target group, relation type, score, method, threshold, supporting IDs |
| Ranking | Incident, service ID, score, rank, supporting group/log IDs, method version |
| Run manifest + metrics | Input/split/config/code versions, environment, timing, denominator/exclusions |

Nhóm chưa rõ service là navigation bucket, không phải một service candidate mới. Unknown template không gom tất cả missing values thành cùng một nhóm; cần fallback rõ và giữ raw references. Cross-links không làm nhân số event trong traceability/reduction. Nếu thử multi-membership, ghi rõ policy và đếm unique IDs.

Group count/member coverage phải đối chiếu tập event đầu vào; có reference string chưa đủ, cần resolve đúng raw record. Giữ raw file nguyên bản, không tái ghi chỉ để tạo normalized output.

## 3. Baselines và câu hỏi của mỗi so sánh

B0–P trong [proposal](../../01_topic_proposal/topic_proposal.md) là các variant nghiên cứu. Không ép triển khai tất cả trước pilot.

Pilot gợi ý: flat logs → service/normalized-template groups → hierarchy; so service log-count/time heuristic với simple ranker nếu đủ nhãn. `normalize_message` hiện có là baseline regex; Drain3/Spell và SBERT/HDBSCAN là phương án tiếp theo, chưa tự chốt.

Muốn claim semantic/grouping giúp ranking: giữ cùng dataset, candidates, split và ranker; chỉ đổi grouping/features cần nghiên cứu. Muốn claim hierarchy giúp navigation: khai báo cùng displayed level hoặc làm user study với cùng giao diện. Tree bọc ngoài cùng groups không tự cải thiện RCA score. Edge ablation giữ phần còn lại cố định.

## 4. Split và feature policy

Chọn **một protocol** sau audit, trước test score; chưa tự khóa tỷ lệ. Các docs cũ đề xuất 50/50, 70/15/15 và 60/20/20. [DATASET_PLAN](../../NCKH_rawData/spec/DATASET_PLAN.md) còn đề xuất A case-wise, B held-out fault, C held-out system family. Đây là phương án cần reconcile, không phải các split đã chạy.

- Incident không xuất hiện ở nhiều phần. Các repeated runs/chung nguồn hoặc cửa sổ chồng lấn phải cùng group khi có nguy cơ share events; kiểm tra bằng source record identity.
- Group key `(system family, service, fault configuration)` là đề xuất chống repetition leakage, cần xác minh ý nghĩa mã fault và tính độc lập thực tế.
- Cross-system giữ trọn `ob`/`ss`/`tt` qua các suite; chia `re2ob` và `re3ob` khác fold chưa thành unseen-system test.
- Exclude dev cases và các source/repetition groups đã dùng chỉnh thủ công khỏi đánh giá, công bố scope giảm.
- Stratification không được bảo đảm khi thiếu nhóm. Báo actual counts và rare strata; không nhân bản case để đạt tỷ lệ.
- Thresholds/windows/vocabulary/scaler/parser có fit chỉ từ train hoặc định trước; tune trên validation/CV ngoài test. Refit trong từng CV fold.
- Candidate/feature extraction lúc inference không cần ground truth. Không dùng nguyên `incidents` hoặc output exploration có heuristic label.

Các feature ứng viên: log counts/rates/shares, explicit severity counts + unknown ratio, unique templates/dominant share, relative time offsets/spans/trends, relationship summaries nếu evidence có sẵn. Không dùng tên service/case/path, fault label, ngày tuyệt đối hoặc injection annotation làm feature MVP. Cần xác minh observation window thực sự có ở inference. Anomaly baseline chỉ dùng khi nguồn normal reference có bằng chứng.

Logistic Regression trong [training note](../note/pineline_training_model.md) là candidate MVP; điểm model chưa là xác suất causal root cause đã hiệu chuẩn. Evidence IDs minh họa dữ liệu hỗ trợ score, không tạo ground-truth log labels.

## 5. Metrics và denominator

Gọi `N` là unique raw events trong scope đã khai báo, `G` là số group hiển thị ở **cùng group level**, `R` là unique events resolve đúng nguồn. Với baseline partition, tổng member count phải bằng `N`, mỗi ID đúng một group.

| Metric | Công thức / định nghĩa |
| --- | --- |
| Visible Log Reduction ở group level | `1 - G/N`; ghi cả counts và per-incident distribution; `N=0` → N/A |
| Raw Log Traceability | `R/N`; missing/unresolved provenance tính failure, không loại khỏi denominator âm thầm |
| Any-candidate coverage | Số incident trong `E` có ít nhất một target trong inventory / `|E|` |
| Full-candidate coverage | Số incident trong `E` có đủ targets trong inventory / `|E|` |
| End-to-end Hit@k | Số incident có ít nhất một true target trong Top-k / `|E|` |
| Conditional Hit@k | Cùng tử số / số incident có any-candidate coverage |
| MRR | Trung bình `1/rank` của true target đầu tiên trên `E`; absent/no ranking → 0 |
| Recall@k cho multi-target | Trung bình số targets trong Top-k / số true targets mỗi incident trong `E` |
| Runtime/memory/cost | Per-stage và end-to-end; ghi data counts, CPU/RAM, versions và resource method |

Với single-target, Hit@1/3 tương ứng Top-1/3 service accuracy. `k'=min(k, số candidate)`; không có candidates/ranking tính 0 end-to-end. Denominator rỗng là N/A. Tie-break rule phải cố định, chẳng hạn service ID tăng dần; báo tỷ lệ ties. Không dùng riêng Top-3 selected evidence để tính Visible Log Reduction.

Traceability 100% là invariant kỹ thuật cần xác nhận, không phải số đo đã đạt. Pairwise F1/purity đòi grouping labels/annotation phù hợp; service root-cause labels không cung cấp nhãn đó. Time to Locate chỉ có ý nghĩa khi có user-study protocol; compression không chứng minh engineer tìm nhanh hơn.

## 6. Reproducibility, error analysis và go/no-go

Mỗi run lưu input version/hashes, case IDs, exclusions, source groups/split/seed, inventory/alias mappings, code/local changes, config, library versions, model selection rule, resource measurements và metrics denominators. Không đổi test sau khi thấy score.

Phân tích riêng theo system, candidate coverage, label multiplicity, missing severity, time/window quality, group size và errors. Nếu bootstrap/ước lượng độ bất định, lấy mẫu theo incident/source groups độc lập và cùng groups giữa các phương pháp; không coi từng service row là mẫu độc lập.

**Go/no-go:** chưa xác minh label/window/service join thì chưa mở claim service RCA; có thể tiếp tục grouping/exploration có provenance. Không có relationship ground truth thì chỉ đánh giá loại evidence quan sát được, không claim causal graph accuracy. Novelty/RQ/targets/model/split cuối cùng vẫn cần review với người hướng dẫn.
