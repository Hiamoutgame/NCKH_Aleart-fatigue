# CP2 — GAP ANALYSIS (1 TRANG): GOM NHÓM CẢNH BÁO MỨC WARNING TRONG MICROSERVICES

> **Đề tài**: Nghiên cứu cơ chế gom nhóm cảnh báo (Alert Aggregation) từ dữ liệu Log Warning nhằm giảm thiểu cảnh báo nhiễu trong kiến trúc Microservices
> **Sinh viên**: [Tên bạn] — **Tuần**: 2/8
> **Nguồn dữ liệu duy nhất**: `F:\study\NCKH\cp2\_research_raw.md` (908 dòng, thu thập 2026-09-28)
> **Nguyên tắc**: mọi con số trong file này đều lấy từ file raw hoặc từ CP1. Không có số liệu nào được thêm mới.

---

## 0. CÁCH ĐỌC TÀI LIỆU NÀY

Ba nhãn trạng thái được dùng xuyên suốt, đúng theo quy tắc trong `OUTPUT.md`:

| Nhãn | Nghĩa tiếng Việt | Cách hiểu |
|---|---|---|
| **FACT** | Sự thật đọc trực tiếp được | Đọc được nguyên văn trong paper/docs/dataset card. Có URL kèm theo. |
| **INFERENCE** | Suy luận | Không có câu nào nói thẳng, nhưng suy ra được từ cơ chế đã đọc. Nêu rõ là suy luận. |
| **UNVERIFIED** | Chưa kiểm chứng | Không truy cập được full text (403/CAPTCHA/paywall), chỉ có abstract/snippet. **Không dùng để kết luận.** |

Viết tắt dùng trong bảng: **ARR** = Alert Reduction Ratio (tỷ lệ giảm cảnh báo); **RCPR** = Root Cause Preservation Rate (tỷ lệ bảo toàn nguyên nhân gốc); **SOP** = Standard Operating Procedure (quy trình xử lý chuẩn, tài liệu hướng dẫn on-call engineer); **OCE/SRE** = kỹ sư trực vận hành; **RCA** = Root Cause Analysis (phân tích nguyên nhân gốc).

---

## 1. BẢNG GAP ANALYSIS CHÍNH (mỗi dòng 1 công trình)

| Công trình | Năm/Venue | Bài toán | Phương pháp | Dataset | Kết quả | Hạn chế | Khoảng trống cho đề tài này | Nguồn (URL) |
|---|---|---|---|---|---|---|---|---|
| **Prometheus Alertmanager** | Docs (truy cập 2026-09) | Gom nhóm + định tuyến + silence + inhibition cảnh báo | Gom theo **label tĩnh** `group_by`; `group_wait=30s`, `group_interval=5m`, `repeat_interval=4h`, `resolve_timeout=5m`; `inhibit_rules` theo `source_matchers`/`target_matchers` + danh sách `equal` | — (không có) | Không có kết quả đo lường. Giá trị default là **FACT** đọc từ docs | Docs tự nêu: alert resolve trước `group_wait` → **không gửi notification nào**; `--alerts.per-alertname-limit` drop alert mới; `mute_time_intervals` không kế thừa từ route cha | Không đọc nội dung message/log; **không dùng topology**; **không có runbook reasoning**; **không có metric nào đo bảo toàn root cause** → đây là arm-1 của đề tài và là "sàn" cần vượt | [configuration.md](https://raw.githubusercontent.com/prometheus/alertmanager/main/docs/configuration.md), [alertmanager.md](https://raw.githubusercontent.com/prometheus/alertmanager/main/docs/alertmanager.md), [alerting_rules.md](https://raw.githubusercontent.com/prometheus/prometheus/main/docs/configuration/alerting_rules.md) **[FACT]** |
| **Prometheus alert rule engine** | Docs | Sinh cảnh báo từ PromQL | Rule = `expr` + `for` + `keep_firing_for` + `labels` + `annotations`; `for: 10m` → trạng thái `pending` trước khi firing; `evaluation_interval=1m` | — | Nguyên văn: *"Prometheus's alerting rules are good at figuring what is broken right now, but they are not a fully-fledged notification solution."* | Prometheus core **không có khái niệm severity/log level**; `severity` chỉ là label do người dùng tự đặt. Muốn log WARNING thành alert phải tự viết rule (Loki/LogsQL) | Xác nhận đề tài phải **tự sinh alert từ log level** — không có sẵn cơ chế trong công cụ phổ biến nhất | [alerting_rules.md](https://raw.githubusercontent.com/prometheus/prometheus/main/docs/configuration/alerting_rules.md) **[FACT]** |
| **COLA** (baseline đối chứng trung tâm #1) | **ICSE-SEIP 2024**, pp.369–380, DOI 10.1145/3639477.3639745, arXiv:2403.06485 | Alert aggregation mức **cặp alert** (pairwise) trong cloud system lớn | Preprocess (chia region, window **10 phút**, sliding **½**); Correlation Mining: temporal `P(a2\|a1)`, khử nhiễu **Jaccard**, spatial **service topology graph xây từ lịch sử alert** + random walk kiểu DFS + skip-gram; score = `max{T} − α·norm(S)` với **α = 3.5**; score<0 → đẩy sang **LLM** (2 vòng CoT tóm tắt SOP, ICL FastText 750-dim, top-1 positive + top-1 negative, 3 rule tự định nghĩa, **SFT p-tuning v2, 1800 steps**) | 3 dataset production **Cloud X (Huawei Cloud)**, 2023/01–06, **>60 services**, **14 regions**, **~500.000 alerts**, **3.000 SOP**, mỗi SOP **3–4 trang A4**. **KHÔNG PUBLIC** | **F1: A 0.908 / B 0.930 / C 0.901** (P/R: A 0.892/0.924; B 0.916/0.943; C 0.921/0.882). SOTA trước đó iPACK chỉ 0.661/0.621/0.633. Ablation F1: bỏ temporal **−39,3%**, bỏ spatial **−5,5%**, bỏ LLM **−31,8%**. Latency **7,4 s/cặp** (5,78/8,94/7,48), fine-tune **~12 giờ** | Dataset + SOP **không public**; baseline so sánh **không open-source** → nhóm tác giả tự viết lại; có **rủi ro overfitting** do train set nhỏ; **không nêu tên LLM** dùng; spatial chỉ đóng góp **+5,5%**; **KHÔNG đánh giá tách theo severity**; **KHÔNG đo ARR/RCPR/Group Purity**; alert nguồn là **ngưỡng monitoring, KHÔNG phải log line WARNING** | **Không thể tái lập** trên RCAEval vì cần SOP 3–4 trang/alert mà RCAEval **không có SOP** (xem §4.3). Không có bằng chứng nào về hành vi ở mức WARNING. Đề tài dùng COLA làm **mốc so sánh khái niệm**, không phải baseline chạy được | [arXiv:2403.06485](https://arxiv.org/abs/2403.06485), [HTML v1](https://arxiv.org/html/2403.06485v1), [PDF proxy](https://r.jina.ai/https://arxiv.org/pdf/2403.06485v1) **[FACT]** |
| **AlertGuardian** (baseline đối chứng trung tâm #2) | **ASE 2025**, arXiv:2601.14912 (cs.DC, nộp 21/01/2026) | Vòng đời cảnh báo 3 pha: khử nhiễu + tóm tắt + tinh chỉnh rule | **Pha 1 – Denoise:** window **1 phút**; nhân bản alert theo `for` duration; **virtual noisy alert bắn mỗi phút**; ma trận đồng xuất hiện; **anonymize** thuộc tính cardinality cao thành `ANON_<ATTR>`; graph **node = alert**; model **GraphGuardian = LINE + Transformer**; similarity = **squared cosine distance**; loss = **MLE phân phối binomial**; Adam; ngưỡng **θ mặc định 0,7**. **Pha 2 – Summary:** **RAG + DeepSeek V3** (so sánh Qwen 2.5 72B). **Pha 3 – Rule Refinement:** multi-agent offline (Detect/Rule/Review Agent), 4 policy, ngưỡng nhiễu **5%**, tối đa **30 vòng lặp**, human-in-the-loop | 4 dataset production **Company-X (Tencent)**: A Game 12.960 rule/2.853.345 alert/138 incident; B Office 3.544/1.243.259/114; C Media 59.607/3.883.293/187; D Education 6.962/2.692.964/179. **KHÔNG PUBLIC** | **ARR: A 95,10% – B 93,82% – C 95,50% – D 95,00%**, trung bình **94,8%**, định nghĩa `(N−M)/N`. Baseline: Severity 83,92–85,04%; OAS 87–88%; UHAS 89–91%. **Chỉ trên Dataset A**: Action Acc **98,5%**, **RCA Acc 90,5%**. Rule refinement: đề xuất **1.174**, được chấp nhận **375**, tỷ lệ **32%**. Deployment System A: 300.000 → ~15.000 alert/ngày (−95%), critical F1 **0,92**; MTTR **156 phút → 21 phút (×7,4)**; loại >50.000 false positive/ngày | Chỉ phân **2 lớp noise/important** — **không có lớp WARNING riêng**; denoise **không dùng ngữ nghĩa** (nguyên văn: *"without considering semantics"*); graph là **đồng xuất hiện alert**, **không phải service call graph**; **"critical" lấy từ incident report của SRE, KHÔNG phải root-cause label** → không đo được RCPR; **KHÔNG có Pairwise F1 / Group Purity**; θ cần tune; giả định noise = alert lặp mỗi phút → **alert WARNING tiền sự cố xuất hiện 1 lần không khớp giả định**; dataset không public | Không có arm nào cho WARNING; **không tái lập được** trên RCAEval/LEMMA-RCA. Là **đối chứng mạnh nhất về ARR** (94,8%) mà đề tài phải nêu khi biện luận target ARR ≥ 60% là thận trọng và hợp lý | [arXiv:2601.14912](https://arxiv.org/abs/2601.14912), [HTML v1](https://arxiv.org/html/2601.14912v1), [PDF proxy](https://r.jina.ai/https://arxiv.org/pdf/2601.14912v1) **[FACT]** |
| **Drain3 + Sentence-BERT + HDBSCAN** (pipeline semantic-only, arm-2) | Drain: ICWS 2017; Drain3: LogPAI; SBERT: EMNLP-IJCNLP 2019; HDBSCAN: ACM TKDD 2015 | Parse log thành template → embedding → phân cụm cảnh báo tương tự ngữ nghĩa | Drain3 dùng **parse tree độ sâu cố định**; defaults `sim_th=0.4`, `depth=4`, `max_children=100`, `max_clusters=không giới hạn`, snapshot mỗi 1 phút; SBERT map câu → vector cố định; HDBSCAN phân cụm theo mật độ | Drain: 5 log set thật, **>10 triệu dòng**; SBERT: benchmark câu; **KHÔNG có paper nào công bố đúng tổ hợp này cho ALERT** | Drain được báo "highest accuracy" **[UNVERIFIED — snippet]**; bằng chứng gián tiếp: MDPI bỏ thành phần SBERT → F1 rơi **0,815 → 0,695**. **Không có số liệu F1 cho pipeline này trên alert** | ⚠️ **Drain3 README tự khuyến nghị BỎ severity trước khi parse**: *"template mining accuracy can be improved if you feed it with only the unstructured free-text portion … by first removing structured parts like timestamp, hostname, severity, etc."* → **mất tín hiệu WARNING vs ERROR nếu không giữ lại thủ công**; `sim_th` nhạy; mask bằng regex heuristic; **không dùng ngữ nghĩa ở tầng parse** | Đây là **arm-2 của đề tài**, và tổ hợp "Drain3 + SBERT + clustering **cho alert mức WARNING**" **chưa có tiền lệ công bố** (kết quả tìm kiếm phủ định, xem §3 Gap (a)). Điểm mù severity là luận cứ trực tiếp cho H4 | [Drain3 README](https://raw.githubusercontent.com/logpai/Drain3/master/README.md), [Drain ICWS 2017](https://www.computer.org/csdl/proceedings-article/icws/2017/0752a033/12OmNBInLkZ), HDBSCAN DOI 10.1145/2733381 **[FACT cho defaults; UNVERIFIED cho kết quả]** |
| **MDPI Electronics 2024 (Zha et al.)** — temporal-spatial gần nhất | *Electronics* **13(22):4425**, 11/11/2024, DOI **10.3390/electronics13224425** | Gom alert do **cùng một sự cố gốc** gây ra trong hệ thống online quy mô lớn | **Pha 1** (khung DBSCAN): gom theo temporal (ngưỡng **τ** trên creation time) → gom tiếp theo spatial (cosine của **node2vec** trên **Enterprise Topology Graph**) + textual (cosine của **Sentence-BERT**), trộn bằng trọng số **α**. **Pha 2**: map cluster lên **service dependency graph**, dùng **LLM truy vết cascading effect** | 3 dataset production ngành **điện lực** (State Grid Jiangsu), 01/09–31/12/2022, **>30 services**, **10 regions**, **~100.000 alerts**. I: 20.123 alert/21 storm; II: 33.424/42; III: 46.179/67. Storm dài **2–35 phút**, **370–6.248 alert/storm**. **KHÔNG PUBLIC** | **F1 Dataset I = 0,815** (cao nhất mọi dataset) so với FP-Growth 0,540; DBSCAN 0,248; AlertStorm 0,468. Ablation Dataset I: đầy đủ 0,815; bỏ temporal **0,540**; bỏ spatial **0,758**; bỏ textual **0,695**; bỏ Pha 2 **0,521** | Dataset **có nhãn severity 4 mức** (critical/high/medium/low) nhưng **kết quả báo cáo gộp, KHÔNG tách theo severity**; **không đo RCPR** — chỉ Precision/Recall/F1 ở **mức cặp alert**; **dataset không public, không có repo**; phụ thuộc service dependency graph; paper tự nêu yếu với *"rare or unseen alert scenarios"*; **alert nguồn là ngưỡng KPI monitoring, không phải log line WARNING**; chỉ 1 domain | Là công trình **gần đề tài nhất về mặt kỹ thuật** (temporal + spatial + textual), nhưng **không có bằng chứng nào cho mức WARNING** và **không tái lập được**. Đây là lý do đề tài cần arm-3 nhưng phải tự dựng topology từ repo public của 3 hệ thống RCAEval | [MDPI qua proxy](https://r.jina.ai/https://www.mdpi.com/2079-9292/13/22/4425) **[FACT]** |
| **LogST** | **ICSIP 2022**, pp.356–361, DOI 10.1109/icsip55141.2022.9886069 | Phát hiện bất thường log | Thay word-embedding + weighted aggregation bằng **SBERT** (giữ thứ tự ngữ nghĩa trong câu) + **GRU** | Public **HDFS** | Nguyên văn abstract: tốt hơn phương pháp khác khi đủ labeled normal log và ổn định khi ít label. **Abstract KHÔNG có con số cụ thể** | Full text closed access; chỉ 1 dataset HDFS; là **phát hiện bất thường**, **không phải gom nhóm alert**; không đo ARR/RCPR | Chỉ dùng làm **trích dẫn ủng hộ SBERT** (nguồn gốc kỹ thuật cho arm-2), **không dùng làm baseline so sánh**. Số liệu phải để trống, không được bịa | [OpenAlex W4296442240](https://api.openalex.org/works/doi:10.1109/icsip55141.2022.9886069) **[FACT metadata; số liệu UNVERIFIED]** |
| **SuperAgg** | **ISSRE 2024**, pp.25–36, DOI 10.1109/issre62328.2024.00014 | Gom alert cho **siêu máy tính (HPC)** | Phát hiện trạng thái không giám sát trên time series + phân tích chuyên gia → **hierarchical patterns** (4 nhóm mẫu tầng sensor; thống kê primary-secondary giữa các sensor → tương quan tầng hệ thống) + chiến lược spatiotemporal để giảm alert online | Alert từ một supercomputer production | **>98% aggregation rate**; accuracy cao hơn **83,8% và 43,2%** trên 2 dataset so với 3 baseline (nguyên văn abstract) | Domain **HPC/supercomputer**, **không phải microservices**; dựa quan hệ **vật lý giữa sensor**, không transfer trực tiếp sang service call graph; paper tự nêu phương pháp similarity-based hiện có là *"myopic"* | Chứng minh rằng **gom alert theo cấu trúc phân cấp** là hướng đã có tiền lệ, nhưng **chưa ai làm ở tầng log WARNING microservice**. Dùng để biện luận tính mới, không dùng làm baseline | [OpenAlex](https://api.openalex.org/works?filter=title.search:hierarchical%20patterns%20alert%20aggregation%20supercomputers), code [github.com/Txh-User/SuperAgg](https://github.com/Txh-User/SuperAgg) **[FACT abstract; chi tiết theo dataset UNVERIFIED]** |
| **Soldani & Brogi survey** | **ACM CSUR 55(3), Art. 59, 39 trang, 02/2022**, DOI 10.1145/3501297, arXiv:2105.12378 | Khảo sát **phát hiện bất thường + RCA** cho ứng dụng (micro)service | Phân loại theo **loại dữ liệu (KPI / log / trace)** × **mục tiêu (anomaly detection / RCA)**; dựa trên **46 nghiên cứu** | — (survey) | — | Là survey về **AD + RCA**, **KHÔNG có taxonomy cho gom nhóm/khử nhiễu alert**; taxonomy chi tiết **UNVERIFIED** do dl.acm.org trả 403 | Là **survey microservice đúng domain** để trích cho phần bối cảnh. Nhưng chính việc nó không có mục "alert aggregation" là **bằng chứng gián tiếp** cho thấy mảng này chưa được hệ thống hóa | [OpenAlex](https://api.openalex.org/works/doi:10.1145/3501297), [arXiv:2105.12378](https://arxiv.org/abs/2105.12378) **[FACT metadata; taxonomy UNVERIFIED]** |
| **Arif et al. survey** (khớp tiêu đề nhất) | **Springer Studies in Computational Intelligence, 2026, pp.314–331**, DOI **10.1007/978-3-032-00232-7_20**, OpenAlex W7118014343 | Survey **AIOps cho quản lý alert storm trong microservices** | Snippet: taxonomy **identification / characterization / summarization** (**UNVERIFIED**) | — (survey, **39 references**) | — | Full text **không truy cập được** (Springer yêu cầu đăng nhập); chỉ đọc được đầy đủ **danh sách 39 references** | ✅ **Bằng chứng gap mạnh nhất**: trong **39 reference** của survey microservices + alert storm mới nhất (2026), **KHÔNG có reference nào về WARNING-level / early-warning / pre-failure alert aggregation**. Tất cả đều post-failure, nhị phân noise/critical, hoặc xếp hạng alert | DOI 10.1007/978-3-032-00232-7_20 **[FACT metadata + 39 refs; thân bài UNVERIFIED]** |
| **Ndichu et al. survey** | 2026 (v2 18/05/2026), arXiv:2605.08316, đã nộp ACM CSUR, 34 trang, 12 bảng | Survey **sàng lọc cảnh báo bảo mật + giảm alert fatigue trong SOC** | Taxonomy **4 tầng: filtering, triage, correlation, generative augmentation**; tổng hợp **119 bản ghi, gồm 87 nghiên cứu lõi** | — (survey, bibliography **174 mục**) | — | Domain **SOC/cybersecurity**, KHÔNG phải microservices | Dùng được ở **một điểm duy nhất nhưng rất giá trị**: họ nêu gap *"evaluation practice"* (thực hành đánh giá) chưa chuẩn hóa → **luận cứ trực tiếp cho việc đề tài đề xuất bộ 4 metric ARR + RCPR + Pairwise F1 + Group Purity** | [arXiv:2605.08316](https://arxiv.org/abs/2605.08316) **[FACT abstract]** |
| **RCAEval** (dataset CHÍNH) | arXiv:2412.17015 (v5 03/02/2025); venue **WWW 2025 Companion, pp.777–780**; license paper **CC-BY-4.0**, code+data **MIT** | Benchmark **RCA** cho microservice (**KHÔNG phải gom nhóm alert**) | 9 dataset / 3 suite (**RE1, RE2, RE3**) × 3 hệ thống (**Online Boutique, Sock Shop, Train Ticket**); **735 ca lỗi**, **11 loại fault**; **15 baseline tái lập được** (README liệt kê 17 tên); metric `Avg@5`, `Chance@5`, `Lift@5` | 735 ca. RE1 = 375 ca (**chỉ metric, KHÔNG có log**); RE2 = 270 ca (metric + log + trace); RE3 = 90 ca (fault mức code F1–F5). Cấu trúc file: `metrics.json`, `inject_time.txt`, `logs.csv`, `traces.csv`; `cases.parquet` có `root_cause_service`, `fault`, `injection time` | Ví dụ BARO trên re2-tt: **Avg@5 — CPU 0,72 / MEM 0,99 / DISK 1,0 / SOCKET 0,83 / DELAY 0,63 / LOSS 0,64** | **KHÔNG có alert / alert instance / alert rule**; **KHÔNG có nhãn alert noise hay alert cluster**; **KHÔNG cung cấp service call graph**; **KHÔNG có runbook/SOP**; **KHÔNG document log level/severity (WARNING)**; **RE1 chiếm 375/735 = 51% ca không có log**; ground truth là **root cause service + root cause indicator**, **KHÔNG phải root-cause alert**; **KHÔNG có ARR/RCPR**; license baseline không đồng nhất (CausalRCA và RUN = *No License*) | ✅ Đây là **gap số 3**: **không dataset public nào có ground truth ở mức alert/alert group**. Hệ quả bắt buộc: đề tài phải **tự sinh alert WARNING từ `logs.csv` của RE2/RE3** và **tự gán nhãn bảo toàn root cause dựa trên `root_cause_service`**. Vừa là **đóng góp phương pháp**, vừa là **rủi ro validity lớn nhất** | [arXiv:2412.17015](https://arxiv.org/abs/2412.17015), [README](https://raw.githubusercontent.com/phamquiluan/RCAEval/main/README.md), [HuggingFace](https://huggingface.co/datasets/phamquiluan/RCAEval) **[FACT]** |
| **LEMMA-RCA** (dataset BACKUP) | arXiv:2406.05375 (v4 25/08/2026); **CIKM 2026**, DOI 10.1145/3799682.3840176; dataset DOI 10.5281/zenodo.20516735; site [lemmarca.info](https://www.lemmarca.info) | Benchmark **RCA đa phương thức, đa miền** | IT (Product Review + Cloud Computing) + OT (SWaT + WADI). Log → time series bằng **Drain (cửa sổ 10 phút, bước 30 giây)** + **golden-signal keywords** + **PCA của TF-IDF** → `X^L = [X1; X2; X3] ∈ R^(3×T)`. Metric **PR@K, MAP@K, MRR@K**; 6 baseline (PC, CIRCA, ε-Diagnosis, RCD, BARO, Nezha) | Product Review **765 GB**, 216 pod, 4 loại fault, trung bình **131.329 timestamp**/fault, tối đa **153 triệu log event**/fault. Cloud Computing **540 GB**, 167,71 entity, 6 loại fault. SWaT 51 sensor/16 fault; WADI 123 sensor/15 fault | BARO đa phương thức **PR@1 = 0,750**, MRR **0,775**, MAP@10 **0,775** (Product Review). BARO **chỉ-log PR@1 = 0**. CIRCA đa phương thức PR@10 = 1,000. SWaT tốt nhất CIRCA PR@1 = 0,188; WADI PC PR@1 = 0,071 | ⚠️ **Golden-signal keywords CHỈ gồm `'error'`, `'exception'`, `'critical'` → `warning`/`warn` KHÔNG được định nghĩa**: đây là **bằng chứng trực tiếp** cho gap WARNING. Log đã aggregate thành time series 3 chiều → **mất thông tin từng dòng log**; **KHÔNG có alert, KHÔNG có nhãn severity mức alert**; **KHÔNG có metric bảo toàn root cause**; 2/4 sub-dataset là **OT/xử lý nước**, không phải microservice; số baseline không nhất quán (abstract v4 ghi **6**, snippet cũ ghi **8**) | Dataset backup **cũng không có định nghĩa WARNING** → nếu RCAEval thất bại, phương án dự phòng **không giải quyết được gap**, chỉ đổi nguồn log. Ràng buộc pháp lý phải ghi rõ (xem §5, dòng 8) | [arXiv:2406.05375](https://arxiv.org/abs/2406.05375), [HTML v4 proxy](https://r.jina.ai/https://arxiv.org/html/2406.05375v4) **[FACT]** |
| **UHAS** (= Zhao et al.) — baseline của AlertGuardian | **ICSE-SEIP 2020**, pp.162–171, DOI 10.1145/3377813.3381363 | Xử lý alert storm: phát hiện + tóm tắt + đề xuất | **Extreme Value Theory (EVT)** + **Isolation Forest** để phân cụm, **chỉ giữ alert ở tâm cụm (cluster centroid)** | Dataset thật quy mô lớn của một ngân hàng (China EverBright Bank) | Abstract: *"high F1-score (larger than 0.9)"*; *"reduce the number of alerts need to be examined by more than 98%"* | **Nhị phân noise/critical, không có mức WARNING**; cơ chế **centroid-based → có bỏ alert**; AlertGuardian trích dẫn UHAS có *"low recall … discard some critical alerts"*; **không đo RCPR**; dataset không public; **F1 chính xác UNVERIFIED** (chỉ có abstract) | Là ví dụ điển hình của **"nén mạnh nhưng có thể nuốt mất tín hiệu"** — chính là rủi ro mà **RCPR của đề tài được thiết kế để phát hiện**. Dùng làm luận cứ cho sự cần thiết của metric RCPR | [OpenAlex](https://api.openalex.org/works/doi:10.1145/3377813.3381363) **[FACT abstract; số chính xác UNVERIFIED]** |

---

## 2. HAI BASELINE ĐỐI CHỨNG TRUNG TÂM — MÔ TẢ PHƯƠNG PHÁP CHI TIẾT

### 2.1 COLA — họ làm gì, từng bước, tham số quan trọng

**Vì sao phải hiểu kỹ COLA (FACT + INFERENCE):** đây là công trình **duy nhất kết hợp cả 3 thứ mà đề tài định dùng** (thống kê + topology + LLM reasoning) cho bài toán gom nhóm alert, và đạt F1 0,901–0,930 — cao nhất trong toàn bộ tài liệu đã khảo sát. Vì vậy mọi tuyên bố "tốt hơn SOTA" của đề tài đều phải đối chiếu với COLA. **INFERENCE**: nếu đề tài không nêu rõ COLA không chạy được trên RCAEval, hội đồng sẽ hỏi ngay "sao không so với COLA?".

**Bước 0 — Tiền xử lý (preprocessing):**
- Tách dữ liệu theo **region**: docs COLA lý luận các service ở region khác nhau "isolated and can be regarded as independent" → giảm khối lượng tính toán và tránh gom nhầm alert giữa các vùng không liên quan.
- Cửa sổ thời gian **Δ = 10 phút**, **sliding window** với bước trượt **s = ½ window**; công thức nguyên văn `[T0 + ksΔ, T0 + (ks+1)Δ]`, `k ∈ [1,2,3...]`.
- Chia train/test **theo thời gian**: train 01/01–31/05/2023, test 01/06–30/06/2023.

**Bước 1 — Correlation Mining Module (thống kê nhẹ, chạy online):**
- *(1a) Quan hệ thời gian bằng xác suất có điều kiện:*
  - `P(a1) = số window chứa a1 / tổng số window`; `P(a2)` tương tự.
  - `P(a1·a2) = số window chứa đồng thời a1 và a2 / tổng số window`.
  - `P(a2|a1) = P(a1·a2)/P(a1)`; `P(a1|a2) = P(a1·a2)/P(a2)`; ký hiệu `T_{a1|a2}`, `T_{a2|a1}`.
- *(1a') Khử nhiễu bằng Jaccard similarity:* `Jaccard = P(a1·a2) / (P(a1) + P(a2) − P(a1·a2))`. Lý luận của họ: alert nhiễu `a_N` xuất hiện đều đặn trong mọi window → `P(a_N·a_i) ≈ P(a_i)` và `P(a_N·a_i) ≪ P(a_N)` → Jaccard ≈ 0 → bị lọc. Nguyên văn: *"we filter out the alert pairs that have a small Jaccard similarity to perform denoising."*
- *(1b) Quan hệ không gian bằng service topology graph + node2vec:*
  - Node = **service**; cạnh nối 2 service nếu **trong lịch sử từng có cặp alert tương quan giữa 2 service đó**; hướng cạnh đi từ service có alert sớm hơn → service có alert muộn hơn.
  - ⚠️ **FACT quan trọng**: topology graph **xây từ lịch sử alert correlation**, **KHÔNG phải call graph / trace thật**. Đây là **vòng lặp logic (circular)**: cần biết cặp alert nào tương quan để dựng topology, rồi lại dùng topology để suy ra cặp alert tương quan.
  - Sampling: **alert-aware random walk** (node có nhiều alert thì random chọn 1 alert đưa vào sequence); hướng sampling "similar to DFS" để bắt đặc trưng lan truyền dài.
  - Embedding: **skip-gram** (Mikolov et al. 2013). Alert chưa từng thấy → lấy **trung bình embedding của service sở hữu nó**. Khoảng cách embedding mức 2 (distance 2) giữa 2 alert = `S_{a1a2}`.
- *(1c) Kết hợp 2 tín hiệu:*
  - `similarity score = max{T_{a1|a2}, T_{a2|a1}} − α · (S_{a1a2} − S_min)/(S_max − S_min)`
  - **α tìm bằng grid search từ 0 đến 10, bước 0,5 → α tối ưu = 3,5.**
  - Quyết định nguyên văn: *"if the similarity score is positive, we output the alert pairs as correlated. Otherwise, we input the pair to the next module."*

**Bước 2 — LLM Reasoning Module (chỉ xử lý các cặp "uncertain"):**
- **Knowledge Extraction (2 vòng CoT):** vòng 1 yêu cầu LLM **tóm tắt SOP** và nhấn vào các khía cạnh hữu ích cho suy luận (giải thích chi tiết, hậu quả lên hệ thống, các bước xử lý); vòng 2 suy luận trên cặp alert với SOP đã tóm tắt.
- **In-Context Learning (ICL):** embed title của alert + SOP bằng **FastText** thành **vector 750 chiều**; do giới hạn độ dài input, họ **chỉ lấy top-1 mẫu positive và top-1 mẫu negative**. Prompt gồm **3 phần: samples, query, rules**, với **3 rule định sẵn** (Rule 1 giải thích đặc trưng lan truyền của quan hệ nhân quả để LLM hiểu khái niệm root cause; Rule 2 và 3 định nghĩa thứ tự ưu tiên của các loại thông tin khi so sánh độ tương tự).
- **Supervised Fine-Tuning (SFT):** dùng **p-tuning v2** (Liu et al. 2021/2022), **train 1.800 steps**, đánh giá trên validation set, **lưu checkpoint mỗi 300 steps**, chọn checkpoint có validation loss nhỏ nhất.
- **Chia dữ liệu cho SFT:** train gốc 01–05/2023 chiếm ~**85,1%** toàn bộ dữ liệu; lấy ngẫu nhiên **80%** của train gốc làm train mới, **5,1%** còn lại làm validation.
- **Phần cứng:** server Windows, CPU Intel Core i7-10700 @ 2,90 GHz, 32 GB RAM; suy luận + fine-tune trên **4 GPU NVIDIA Tesla T4 12 GB**; tham số fine-tune mặc định **`PRE_SEQ_LEN = 128`**, **`LR = 2e-2`**.
- ⚠️ **Paper KHÔNG nêu tên LLM cụ thể** (chỉ nói "internal LLM" và so sánh với "commercial LLMs with over 100B parameters") → **INFERENCE: đây là lý do kỹ thuật khiến COLA không thể tái lập**, kể cả khi có SOP.

**Vai trò của SOP (kiến thức):** SOP = tài liệu mô tả alert do kỹ sư vận hành duy trì. Nội dung nguyên văn: *"SOPs contain the ID, title, severity, explanation of the alert, the impact on the system, possible cause, and recommended mitigation steps"*. Quy mô: *"spanning approximately 3 to 4 A4 pages"*; tổng **3.000 SOP**; cập nhật liên tục bởi kỹ sư tại chỗ.

**Trạng thái bằng chứng:** toàn bộ mục 2.1 là **[FACT]** — đọc trực tiếp từ [arXiv:2403.06485](https://arxiv.org/abs/2403.06485) (HTML v1 + PDF qua proxy). Riêng phần "vì sao không tái lập được" ở dòng cuối Bước 2 là **[INFERENCE]**.

### 2.2 AlertGuardian — họ làm gì, từng bước, tham số quan trọng

**Vì sao phải hiểu kỹ AlertGuardian (FACT + INFERENCE):** đây là baseline có **ARR cao nhất** (trung bình 94,8%) và là công trình duy nhất công bố **một dạng ràng buộc "bảo toàn cảnh báo quan trọng"** — gần nhất với khái niệm RCPR của đề tài. **INFERENCE**: nếu đề tài chỉ nêu "chúng tôi đạt RCPR ≥ 95%", người phản biện sẽ so với ràng buộc "no critical alerts suppressed" của họ và hỏi khác nhau ở đâu. Câu trả lời phải nằm sẵn trong CP2.

**Pha 1 — Alert Denoise (graph learning + virtual noise):**

*Tiền xử lý:*
- Chia thành **time window 1 phút**.
- Alert có `for` duration (ví dụ 5 phút) → **nhân bản alert sang 5 window kế tiếp** kể từ lần xuất hiện đầu.
- **Virtual noisy alert** (nguyên văn): *"we introduce a virtual noisy alert, fired every minute, to emulate persistent noise patterns. The core intent behind mandating the virtual noisy alert's presence each minute is to pinpoint real alerts exhibiting high co-occurrence frequencies with it. These alerts are likely indicative of persistent noise (e.g., false positives from heartbeat checks) that requires exclusion."*
- **Ma trận đồng xuất hiện:** `M_i[u,v] = 1` nếu alert u và v cùng xuất hiện trong window i, ngược lại 0; tổng hợp qua τ window → ma trận thống kê `M` (thưa).
- **Anonymize thuộc tính** (nguyên văn): *"certain attributes, such as Pod ID, possess extensive value spaces and primarily function as entity identifiers rather than indicators of anomalous behavior … we anonymize such identifier attributes by converting their values to a standardized format, `ANON_` appended with the attribute name (e.g., `ANON_POD_ID`)."*

*Mô hình graph:*
- **Node = alert**; thêm **virtual noisy node nối tới tất cả alert** để mô phỏng alert dai dẳng.
- **Thuộc tính cạnh:** mỗi cặp `(u,v)` có **tần suất đồng xuất hiện `k`** và **tổng số lần xuất hiện `c`** trên toàn bộ thời điểm.
- **Content correlation** (nguyên văn): *"we adopt a unique attribute-value encoding approach … Unlike traditional bag-of-words encoding, we assign a unique code to each attribute-value pair **without considering semantics**, focusing on identical pairs."* → **FACT: khâu khử nhiễu của họ cố tình KHÔNG dùng ngữ nghĩa.**
- **GraphGuardian** = **LINE** (mạng embedding quy mô lớn) + **Transformer**: LINE lấy cấu trúc cục bộ (first-order & second-order proximity); self-attention của Transformer lấy phụ thuộc bậc cao hơn cặp đồng xuất hiện đơn thuần.
- **Similarity — bình phương khoảng cách cosine:** `d(h_u, h_v) = (1 − (h_u · h_v^T) / (||h_u|| ||h_v||))²`.
  - ⚠️ **LỖI TRONG PAPER**: paper viết *"distance `d → 0` indicates high dissimilarity and `d → 1` indicates high similarity"* — **ngược với chính công thức** (bình phương khoảng cách cosine = 0 khi hai vector giống hệt nhau). Phần inference của họ lại nhất quán với công thức: *"The higher similarity indicates a higher likelihood of being a noise"* và *"Alerts with `d(h_u, h_v_noise) ≥ θ` are classified as noise"*. **INFERENCE: đây là lỗi diễn đạt của paper, không phải lỗi công thức.** Khi trích dẫn phải ghi chú rõ.
- **Loss — MLE với phân phối binomial:** `Binomial(k, c, p) = C(c,k) · p^k · (1−p)^(c−k)` với `p = d(h_u, h_v)`; `loss = −log(Binomial(k, c, p))`. Lý do chọn (nguyên văn): *"We chose the binomial distribution because it is less sensitive to low-frequency events, which is very important in our sparse data scenario."*
- **Optimizer:** Adam.

*Inference:*
- Ngưỡng `θ ∈ [0,1]`: alert có `d(h_u, h_v_noise) ≥ θ` → **noise**; ngược lại → **important**. Khuyến nghị **θ = 0,7**.
- Trade-off nguyên văn: *"A higher θ increases precision by filtering more alerts, but risks missing critical ones, while a lower θ improves recall at the cost of retaining more noise."*

**Pha 2 — Alert Summary (RAG + LLM):**
- Dùng **RAG** với tri thức nội bộ: *"system documents, alert rule explanations, incident tickets"*.
- LLM: **DeepSeek V3** (chính), **Qwen 2.5 72B** (đối chứng). Đầu ra: tóm tắt ngắn, có thể hành động (giải thích lỗi, định vị, cách khắc phục).
- **Lý do KHÔNG dùng LLM cho khâu khử nhiễu** (nguyên văn, 2 lý do): (1) *Cost Efficiency* — hệ thống sinh lượng alert khổng lồ mỗi ngày, dùng LLM sẽ tốn token không khả thi về kinh tế; (2) *Inference Speed* — độ trễ sinh token từng bước của LLM là nút cổ chai. → **FACT hữu ích cho arm-4 của đề tài**: cần fast filter trước LLM, đúng như H3 trong CP1.

**Pha 3 — Alert Rule Refinement (multi-agent, chạy offline):**
- *"an offline multi-agent workflow with iterative feedback optimizes rules through deduplication, threshold adjustments, and temporal analysis."*
- **4 policy:** Rule Deduplication, Rule Aggregation, Threshold Adjustment, Temporal Analysis. **3 agent:** Detect Agent, Rule Agent, Review Agent.
- **Điều kiện dừng (nguyên văn) — RẤT GẦN khái niệm RCPR:**
  - *"Preservation of Critical Alerts: Refined rules must retain all critical alerts, confirmed by the Review Agent's simulation tool, which tests rules against historical data to ensure no critical alerts are suppressed."*
  - *"Noise Reduction Threshold: The noise alert ratio (proportion of non-critical alerts) must fall below a predefined threshold (5% by default) … while maintaining full coverage of critical alerts."*
  - *"If the above conditions are not met after 30 iterations, the optimization process for the rule is terminated and the rule remains unoptimized."*
  - Rule tinh chỉnh xong được gửi cho SRE phê duyệt cuối — **human-in-the-loop**.
- ⚠️ **Giới hạn phạm vi (FACT):** đây là **ràng buộc của khâu tinh chỉnh rule**, **KHÔNG phải một metric đo trên kết quả gom nhóm alert**. Ngoài ra *"critical"* được định nghĩa từ **incident report của SRE**, **KHÔNG phải nhãn root cause**. → **INFERENCE: ràng buộc này không tương đương RCPR của đề tài**, vì RCPR đo "alert gốc có còn nằm trong nhóm chính không", còn họ đo "rule mới có làm mất alert critical theo incident report không".

**Trạng thái bằng chứng:** toàn bộ mục 2.2 là **[FACT]** — đọc trực tiếp từ [arXiv:2601.14912](https://arxiv.org/abs/2601.14912) (HTML v1 + PDF qua proxy). Phần so sánh với RCPR ở cuối là **[INFERENCE]**.

---

## 3. BA KHOẢNG TRỐNG NGHIÊN CỨU (RESEARCH GAPS)

### Gap (a) — Không công trình nào tách riêng mức WARNING / early-warning

**Phát biểu:** Trong toàn bộ phạm vi tìm kiếm được, **không có công trình nào gom nhóm cảnh báo riêng cho mức WARNING nhằm mục đích cảnh báo sớm (early warning) trong microservices**. Các công trình hiện có hoặc coi alert là một khối đồng nhất, hoặc chia nhị phân **noise / critical**, tức là **chỉ quan tâm hậu sự cố**.

**Bằng chứng trực tiếp — kết quả tìm kiếm phủ định có chủ đích (FACT, 16 truy vấn trên 3 engine độc lập: DuckDuckGo HTML/lite, arXiv API, OpenAlex API).** Các truy vấn arXiv API trả **0 kết quả**, trích nguyên văn:

| # | Truy vấn (nguyên văn) | Engine | Kết quả |
|---|---|---|---|
| 6 | `all:"warning level" AND all:"alert aggregation"` | arXiv API | **`opensearch:totalResults = 0`** |
| 9 | `abs:"alert severity" AND abs:"microservice"` | arXiv API | **`totalResults = 0`** |
| 10 | `abs:"alert fatigue" AND abs:"microservice"` | arXiv API | **`totalResults = 0`** |
| 11 | `abs:"alert aggregation" AND abs:"microservice"` | arXiv API | **`totalResults = 0`** |

Các truy vấn còn lại **có kết quả nhưng tất cả đều không liên quan**, trích nguyên văn:
- `abs:"early warning" AND abs:"microservice"` → **2 kết quả, cả 2 không liên quan**: (a) arXiv:2312.15323 *"Towards a Microservice-based Middleware for a Multi-hazard Early Warning System"* — cảnh báo sớm **thiên tai/môi trường**; (b) arXiv:2506.03830 về quản lý tài nguyên đô thị.
- `abs:"WARN" AND abs:"alert" AND abs:"microservice"` → **1 kết quả duy nhất, không liên quan**: arXiv:2111.05136 *"Using sequential drift detection to test the API economy"* (drift detection trên histogram + call graph, chữ "warning" chỉ là từ trong abstract).
- `abs:"pre-failure" AND abs:"log"` → **3 kết quả, không liên quan**: Varuna (RDMA failover), RODMAN (dự đoán hỏng đĩa, arXiv:1912.09722), Safe-CRL (học tăng cường).
- `all:"group purity" AND all:"alert"` → **`totalResults = 0`** (dùng cho cả Gap (b)).
- OpenAlex `title.search:AIOps alert storm management` → 1 kết quả (Arif et al.); OpenAlex `title.search:hierarchical patterns alert aggregation supercomputers` → 1 kết quả (SuperAgg). **Cả hai đều không phải WARNING-level.**

**Bằng chứng gián tiếp (FACT — mỗi dòng đều đọc trực tiếp từ nguồn đã dẫn ở §1):**
1. **COLA:** SOP có field `severity`, alert có severity, nhưng **toàn bộ Table 2/3/4 báo cáo gộp, không tách theo severity**.
2. **MDPI Electronics 2024:** dataset **có nhãn severity 4 mức** — nguyên văn *"The severity levels of these alerts are categorized as critical, high, medium, and low"* — nhưng kết quả **chỉ có 1 bảng gộp**.
3. **AlertGuardian:** chỉ phân **2 lớp noise vs critical**; `severity` xuất hiện **duy nhất như baseline heuristic yếu nhất** (ARR 83,92–85,04%). Không có arm nào cho WARNING.
4. **LEMMA-RCA (bằng chứng trực tiếp mạnh nhất):** log feature extraction dùng *"golden-signal keywords (e.g., `'error'`, `'exception'`, `'critical'`)"* → **`warning`/`warn` KHÔNG nằm trong golden signals**.
5. **AlertGuardian liệt kê 3 hạn chế của hệ thống alert hiện có** — **không có hạn chế nào về severity/WARNING**: (1) cơ chế khử nhiễu lỗi thời do bùng nổ tổ hợp thuộc tính, (2) thiếu quy trình tóm tắt alert, (3) thiếu quy trình tinh chỉnh alert rule.
6. **Survey Arif et al. 2026:** trong **39 reference**, **không có reference nào về WARNING-level / early-warning / pre-failure alert aggregation**. Tất cả đều post-failure, nhị phân noise/critical, hoặc xếp hạng alert.
7. **RCAEval (dataset chính của đề tài):** **không document log level/severity**, **không có alert ground truth**.

**Ranh giới của kết luận (bắt buộc ghi):** `[UNVERIFIED]` Đây là **tìm kiếm trên arXiv API + OpenAlex + DuckDuckGo**, **không phủ hết mọi venue** (ví dụ IEEE/ACM chỉ truy cập được abstract qua OpenAlex, dl.acm.org và link.springer.com trả 403). Vì vậy phát biểu đúng là **"không tìm thấy"**, không phải **"không tồn tại"**. Ngoài ra `UNVERIFIED` còn 2 ứng viên **gần nhất nhưng chưa kiểm chứng được full text**: preprint TechRxiv *"Deep Learning-Based Failure Detection and Log Classification in Cloud"* (DOI 10.36227/techrxiv.176369778.88172124 v1 — có tách **Error, Warning, Info**, nhưng là **log classification**, không phải alert aggregation, và **chưa peer-review**), và bài Springer *"Research on storage early warning and scheduling for cloud"* (DOI 10.1186/s13677-026-00983-6 — **early warning dự đoán**, không phải gom nhóm alert).

### Gap (b) — Không công trình nào đo khả năng bảo toàn nguyên nhân gốc (root cause preservation)

**Phát biểu:** Không có công trình nào định nghĩa và đo **khả năng giữ lại alert gốc sau khi gom nhóm**. Các metric hiện có chỉ là **Precision/Recall/F1 ở mức cặp alert** (pairwise) hoặc **ARR** — tức là đo *"nén được bao nhiêu"* và *"cặp gán đúng không"*, **không đo "có nuốt mất tín hiệu gốc không"**.

**Bằng chứng trực tiếp (FACT):**
- arXiv API `all:"root cause preservation"` → **`totalResults = 0`**.
- arXiv API `all:"group purity" AND all:"alert"` → **`totalResults = 0`**.
- **COLA:** chỉ có Precision/Recall/F1 mức cặp alert. Nguyên văn định nghĩa: *"TP stands for the correlated alerts in results which are also labeled as related in ground truth; True Negative (TN) are for those irrelevant alert pairs both in results and ground truth."* → **không có RCPR, không có ARR, không có Group Purity.**
- **MDPI Electronics 2024:** metric **chỉ precision/recall/F1 ở mức cặp alert**, **không đo root-cause preservation**.
- **AlertGuardian:** ground truth *"Critical alerts were derived from SRE-provided incident reports"* → **"critical" ≠ "root cause"**; con số gần nhất là *"critical alerts maintain an F1-score of 0.92"* trong câu chuyện triển khai System A, nhưng đây là **F1 phân loại critical/noise**, **không phải bảo toàn root cause**. **KHÔNG có ARR/recall tách theo severity.**
- **UHAS:** cơ chế **chỉ giữ alert ở tâm cụm** → về nguyên tắc **có bỏ alert**; AlertGuardian trích dẫn UHAS có *"low recall … discard some critical alerts"*. **Không có metric nào đo mức mất mát đó.**

**Hệ quả (INFERENCE):** đề tài phải **tự định nghĩa RCPR** và tự gán nhãn từ `root_cause_service` của RCAEval. Đây là **đóng góp phương pháp (methodological contribution)** của đề tài, đồng thời là **rủi ro validity lớn nhất** vì nhãn do chính tác giả sinh ra — phải khai báo rõ trong Threats to Validity.

### Gap (c) — Không dataset public nào có ground truth ở mức alert / alert group cho microservices

**Phát biểu:** Hai dataset public khả dụng cho đề tài **đều không có alert và không có nhãn ở mức alert**. Ba công trình gom nhóm alert tốt nhất (COLA, AlertGuardian, MDPI) **đều dùng dataset riêng và không public**.

**Bằng chứng trực tiếp (FACT):**

| Dataset | Có alert? | Có nhãn alert noise? | Có ground truth mức alert group? | Có SOP? | Có topology? | Public? |
|---|---|---|---|---|---|---|
| **RCAEval** (chính) | ❌ không | ❌ không | ❌ không (chỉ root cause **service** + **indicator**) | ❌ | ❌ không cung cấp artifact | ✅ HF / Figshare / Zenodo |
| **LEMMA-RCA** (backup) | ❌ không | ❌ không | ❌ không (chỉ root-cause entity) | ❌ | ❌ | ✅ lemmarca.info / Zenodo |
| **COLA** (Cloud X) | ⚠️ có alert hệ thống | ⚠️ có nhãn cặp tương quan | ⚠️ **pairwise**, không phải cluster | ✅ 3.000 SOP, 3–4 trang A4 | ⚠️ dựng từ lịch sử alert | ❌ **KHÔNG** |
| **AlertGuardian** (Company-X) | ✅ 10.672.861 alert | ⚠️ nhị phân noise/critical | ❌ không | ❌ (chỉ RAG cho summary) | ❌ (graph là đồng xuất hiện alert) | ❌ **KHÔNG** |
| **MDPI Zha et al.** | ✅ ~100.000 alert | ⚠️ nhãn theo incident report | ⚠️ **pairwise** | ❌ | ⚠️ Enterprise Topology Graph riêng | ❌ **KHÔNG** |

Ngoài ra, RCAEval còn có 2 hạn chế cấu trúc ảnh hưởng trực tiếp: **RE1 chiếm 375/735 = 51% số ca và KHÔNG có log**, và **README không document log level/severity**.

**Hệ quả (FACT → INFERENCE):** đề tài **bắt buộc phải tự định nghĩa và tự sinh alert WARNING từ `logs.csv` của RE2/RE3** (parse log level rồi sinh alert theo rule), và **tự gán nhãn bảo toàn root cause dựa trên `root_cause_service`**. Đây là **đóng góp mới** đồng thời là **rủi ro validity phải khai báo rõ trong Threats to Validity**. (LEMMA-RCA **không phải phương án dự phòng giải quyết gap**, vì log của nó đã bị aggregate thành time series 3 chiều → **mất thông tin ở mức từng dòng log**, và golden-signal keywords cũng không có `warning`.)

---

## 4. BASELINE VÀ METRIC ĐÃ CHỐT

### 4.1 Bốn nhánh thí nghiệm (4 arms)

| Arm | Công cụ / kỹ thuật | Đầu vào (input) | Chạy lại được trên RCAEval? | Khó khăn dự kiến |
|---|---|---|---|---|
| **Arm 1 — Rule-based** | Mô phỏng **Prometheus Alertmanager**: `group_by: service,alertname,severity`, `group_wait=30s`, `group_interval=5m` | Alert stream tự sinh từ `logs.csv` (RE2/RE3): `{alert_id, service, timestamp, message_template, severity="warning"}` | ✅ **Có** — không phụ thuộc dữ liệu ngoài, chỉ cần alert stream | Chỉ gom theo **label tĩnh**; **không đọc nội dung message**; **không dùng topology**; **không có ground truth** để đối chiếu ARR (chỉ so tương đối với các arm khác) |
| **Arm 2 — Semantic-only** | **Drain3** (`sim_th=0.4`, `depth=4`, `max_children=100`) → **Sentence-BERT** → **HDBSCAN** | `message_template` của alert + vector embedding SBERT | ⚠️ **Có, nhưng có điều kiện**: Drain3 **khuyến nghị bỏ severity trước khi parse** → phải **giữ severity riêng** và đưa lại làm feature, nếu không sẽ mất tín hiệu WARNING vs ERROR | Mất tín hiệu severity (điểm mù tự nêu của Drain3); phải tune `sim_th` và tham số HDBSCAN **không có nhãn để tune**; **không phân biệt được nhân quả** → kỳ vọng thấp trên cascading (H4) |
| **Arm 3 — Temporal-Spatial** | Service Call Graph + sliding window **Δt = 30/60/120 giây**; theo khung **DBSCAN** + node2vec của MDPI Electronics 2024 | Alert stream + **topology graph** (upstream/downstream) | ⚠️ **Có, nhưng phải tự dựng topology**: **RCAEval KHÔNG cung cấp service call graph như artifact** (README không document topology) → phải build thủ công từ repo public của Online Boutique / Sock Shop / Train Ticket. `[UNVERIFIED]` Việc "topology đã public" là ghi chú trong CP1, **chưa được kiểm chứng lại trong CP2** | Phụ thuộc chất lượng topology tự dựng; **τ / Δt nhạy** (MDPI tự nêu bỏ temporal → F1 rơi 0,815 → 0,540); công trình gốc dùng dataset **không public** nên **không so sánh số trực tiếp được** |
| **Arm 4 — LLM agent tool-calling** (**đề xuất chính**) | **Fast filter** (dedup + time-window) → **Agent** với tối đa 2 lần gọi tool/quyết định; 3 tool: `get_related_alerts(service, time_window)`, `get_service_dependency(service)`, `get_runbook(fault_type)` (runbook **tổng hợp**, không có thật trong dataset) | Alert stream đã lọc + topology + runbook tổng hợp | ✅ **Chạy được**, nhưng **toàn bộ ground truth phải tự sinh** → kết quả đo là **tự đối chiếu**, không so được với công trình nào | Latency + chi phí token; **tính không xác định** (cùng input có thể ra output khác); **rủi ro hallucination** (AlertGuardian tự nêu đã phải dùng RAG + vòng phản hồi để giảm, *"LLM hallucinations posed a risk"*); runbook **tổng hợp** → phải khai báo rõ là giả lập |

**Ghi chú về chi phí LLM (INFERENCE có bằng chứng):** AlertGuardian **cố tình không dùng LLM cho khâu khử nhiễu** vì 2 lý do đã nêu (chi phí token và độ trễ sinh token). Điều này **ủng hộ thiết kế fast filter ở H3** của CP1 và là luận cứ để arm-4 chỉ gọi LLM sau khi đã lọc thô.

### 4.2 Bốn metric đã chốt

| Metric | Tên đầy đủ / nghĩa | Công thức | Target | Ghi chú nguồn |
|---|---|---|---|---|
| **ARR** | Alert Reduction Ratio — tỷ lệ giảm cảnh báo | `ARR = 1 − N_after / N_before` (`N_before` = số alert WARNING trước gom nhóm; `N_after` = số nhóm/alert còn lại sau gom nhóm) | **≥ 60%** | Trùng dạng với định nghĩa của AlertGuardian: *"reduction ratio, defined as: (N − M)/N, where N is the initial number of alerts, and M is the number of alerts remaining after denoising"*. Mốc tham chiếu thực tế rất khác nhau: AlertGuardian **94,8%** (nhưng nhị phân noise/critical, ground truth từ incident report), SuperAgg **>98%** aggregation rate (domain HPC), UHAS **>98%** alert giảm (nhưng chấp nhận mất critical). `[INFERENCE]` Target 60% của đề tài là **thận trọng** vì bài toán khó hơn (giữ nguyên tín hiệu WARNING) |
| **RCPR** | Root Cause Preservation Rate — tỷ lệ bảo toàn nguyên nhân gốc | `RCPR = Σ I(root_cause_alert ∈ primary_group) / M` (`M` = số fault case; `I(·)` = 1 nếu alert gốc nằm trong nhóm chính) | **≥ 95%** | **Không có công trình nào định nghĩa metric này** (arXiv API `all:"root cause preservation"` → **0 kết quả**). Đây là **metric tự định nghĩa của đề tài** → phải mô tả rõ cách gán nhãn bằng `root_cause_service` của RCAEval |
| **Pairwise F1** | F1 trên các **cặp** alert cùng nhóm | `F1 = 2·P·R / (P + R)`, với `P/R` tính trên cặp alert được gom chung nhóm | **≥ 0,85** | Đây là metric **duy nhất so sánh được về mặt khái niệm với COLA** (COLA: F1 = A **0,908** / B **0,930** / C **0,901**) và MDPI (F1 Dataset I = **0,815**). ⚠️ So sánh chỉ mang tính **tham chiếu**, vì dataset của họ **không public** và alert nguồn **không phải log WARNING** |
| **Group Purity** | Độ "sạch" của nhóm — tỷ lệ alert trong nhóm thực sự cùng một nguyên nhân | `Purity = Σ (max_count_per_group) / N_total_alerts` | **≥ 0,80** | arXiv API `all:"group purity" AND all:"alert"` → **0 kết quả**. Cũng là **metric tự định nghĩa**. Dùng để chống lạm dụng ARR: gom tất cả vào 1 nhóm thì ARR rất cao nhưng Purity rất thấp |

### 4.3 Hai kết luận bắt buộc phải nêu rõ trong đề cương

1. **Baseline COLA KHÔNG tái lập được trên RCAEval.** Lý do cụ thể (FACT): COLA yêu cầu **SOP cho mỗi alert**, và nguyên văn paper ghi SOP *"spanning approximately 3 to 4 A4 pages"*, tổng **3.000 SOP**, do kỹ sư tại chỗ duy trì. **RCAEval không có runbook/SOP** (README không có mục nào về SOP). Ngoài ra COLA **không nêu tên LLM** dùng cho module suy luận, nên kể cả có SOP cũng **không tái lập được**. → COLA được dùng làm **mốc so sánh khái niệm** (conceptual reference), **không phải baseline chạy được**. Phải ghi điều này ngay trong phần Baseline, không để trong phần Limitations.
2. **COLA và AlertGuardian đều dùng dataset riêng KHÔNG public.**
   - COLA, nguyên văn (External validity): *"The three datasets are all from Cloud X, because there is no publicly available dataset containing such detailed and complete alert descriptions as SOPs."* → chính họ thừa nhận **không có benchmark public**.
   - AlertGuardian, nguyên văn (External Threats): *"The datasets, sourced exclusively from Company-X, may limit generalizability."*
   - MDPI Electronics 2024 cũng **không public, không có repo**.
   → **INFERENCE: mọi so sánh số với 3 công trình này chỉ là tham chiếu định hướng, không phải so sánh có kiểm soát (controlled comparison).** Không được viết trong paper rằng đề tài "tốt hơn COLA/AlertGuardian" — chỉ được viết "khác biệt ở mục tiêu và mức độ cảnh báo".

---

## 5. ĐÍNH CHÍNH CITATION (phải sửa trong đề cương hiện tại)

| # | Đề cương / ghi chú cũ ghi | Thực tế (đã xác minh) | Trạng thái | Nguồn xác minh |
|---|---|---|---|---|
| 1 | *"Zhu et al., **ICSE 2019**"* cho bài *"An Evaluation Study on Log Parsing"* | **Pinjia He, Jieming Zhu, Shilin He, Jian Li, Michael R. Lyu. DSN 2016, pp. 654–661**, DOI 10.1109/dsn.2016.66. Tác giả đầu là **Pinjia He** (không phải Zhu). **KHÔNG tìm thấy bài này ở ICSE 2019.** | **FACT** | [OpenAlex W2527994611](https://api.openalex.org/works/doi:10.1109/dsn.2016.66) |
| 2 | *"HDBSCAN — Campello et al. **2013**"* | Bản chính thức: **Campello, Moulavi, Zimek, Sander. ACM TKDD 10(1):1–51, 2015**, DOI 10.1145/2733381. (Bản PAKDD 2013 chỉ là **tiền thân**.) | **FACT** | Ref [35] của AlertGuardian |
| 3 | *"Jalalvand et al., ACM CSUR"* được trích như **survey alert correlation cho microservices** | Paper có thật nhưng là *"Alert Prioritisation in **Security Operations Centres**: A Systematic Survey on Criteria and Methods"* — **domain SOC/cybersecurity, KHÔNG phải microservices**. ACM CSUR **57(2), pp.1–36, 2024**, DOI 10.1145/3695462. | **FACT** | [OpenAlex](https://api.openalex.org/works/doi:10.1145/3695462) |
| 4 | *"Tariq et al., ACM CSUR"* được trích như **survey alert correlation cho microservices** | Paper có thật nhưng là *"Alert Fatigue in **Security Operations Centres**: Research Challenges and Opportunities"* — **domain SOC**. ACM CSUR **57(9), pp.1–38, 2025**, DOI 10.1145/3723158. | **FACT** | [OpenAlex](https://api.openalex.org/works/doi:10.1145/3723158) |
| 5 | AlertGuardian *"**diagnosis accuracy 90,5%**"* | Trong paper đây là **"RCA Accuracy"**, định nghĩa nguyên văn: *"accuracy in identifying root causes, assessed via heuristic matching with incident report annotations"*. Và nó: (i) **CHỈ đo trên Dataset A** (*"Due to the high cost of manual labeling, we focused solely on Dataset A"*), (ii) là metric của **module Alert Summary**, **KHÔNG phải metric của khâu gom nhóm/khử nhiễu**, (iii) đo bằng **heuristic matching**, không phải ground truth tuyệt đối. *(Con số 98,5% "Action Accuracy" là metric KHÁC — phân loại summary có cần SRE hành động hay không.)* | **FACT** | [AlertGuardian PDF proxy](https://r.jina.ai/https://arxiv.org/pdf/2601.14912v1), Table III |
| 6 | AlertGuardian *"**ARR 94,8%**"* (không nêu rõ đo trên dataset nào) | Là **trung bình của CẢ 4 dataset A/B/C/D**: 95,10 / 93,82 / 95,50 / 95,00. Kiểm chứng: (95,10+93,82+95,50+95,00)/4 = **94,855 ≈ 94,8** ✓. Định nghĩa: `(N − M)/N`. Ground truth "critical" lấy từ **SRE incident reports**. | **FACT** | AlertGuardian, Table II |
| 7 | COLA *"F1"* (ghi chung, không tách dataset) | F1: **A 0,908 / B 0,930 / C 0,901**; và bài toán là **pairwise ở mức CẶP ALERT**, **KHÔNG phải cluster-level**. Khớp abstract *"F1-scores from 0.901 to 0.930"* (min = Dataset C, max = Dataset B). | **FACT** | COLA, Table 2 |
| 8 | LEMMA-RCA *"license **CC BY-ND 4.0**"* (theo file raw) | ⚠️ **ĐÍNH CHÍNH do người viết tự kiểm chứng ngoài file raw**: license của LEMMA-RCA **trên HuggingFace** là **`cc-by-nc-4.0`** (NonCommercial), **KHÔNG phải CC BY-ND** (NoDerivatives). Ghi chú kỹ thuật: file raw ghi **CC BY-ND 4.0** cho bản dataset/paper (dòng 791, 820, 837), còn repo HF *Lemma-RCA-NEC/Product_Review_Original* ghi **CC-BY-NC-4.0**. **Hệ quả pháp lý khác nhau rõ rệt**: NC = **cấm dùng thương mại** nhưng **được phép tạo bản phái sinh**; ND = **cấm tạo bản phái sinh**. → Khi publish derived dataset phải **kiểm tra lại trực tiếp trên trang HF** trước khi khẳng định. | **FACT (tự kiểm chứng, ngoài file raw)** — cần chụp lại ảnh/ghi log kiểm chứng để đưa vào phụ lục | HF dataset card [Lemma-RCA-NEC/Product_Review_Original](https://huggingface.co/datasets/Lemma-RCA-NEC/Product_Review_Original) + ghi chú CP1 `cp1/huggingfaceListRepo.md` (dòng 50, 60, 205) |

**Lưu ý thêm khi trích dẫn (FACT, không phải lỗi của đề cương nhưng dễ sai):**
- AlertGuardian có **lỗi ký hiệu trong paper**: viết *"`d → 0` indicates high dissimilarity"* trong khi công thức là bình phương khoảng cách cosine. Khi trích phải mô tả **theo công thức**, không theo câu chữ.
- AlertGuardian có **typo `30,0000`** trong phần deployment (nhiều khả năng là `300,000`) — không dùng nguyên văn con số này mà không chú thích.
- Số **"11 datasets"** cho Drain (từ snippet Semantic Scholar) **mâu thuẫn** với abstract chính thức của He et al. DSN 2016 (*"five datasets"*) → **UNVERIFIED, KHÔNG dùng con số 11**.
- RCAEval: abstract ghi **"fifteen reproducible baselines"**, nhưng README liệt kê **17 tên**. Không tự ý chọn một con số — nêu cả hai kèm nguồn.

---

## 6. HỆ QUẢ CHO CP2 VÀ VIỆC CẦN LÀM TIẾP

**[FACT] Phát hiện làm thay đổi giả định của CP1:** RCAEval **không có cột severity** và **không document log level** (README chỉ ghi `logs.csv`: *"Log data"*).

> ### ✅ ĐÃ GIẢI QUYẾT — cập nhật 2026-09-28 (sau khi bản nháp này được viết)
> Câu hỏi Go/No-go ở trên **đã được kiểm chứng trực tiếp trên dữ liệu thật**. Kết quả đầy đủ nằm ở **`cp1/data_schema_notes.md`**. Tóm tắt:
>
> | Câu hỏi | Trả lời đã kiểm chứng |
> |---|---|
> | RCAEval có log `WARNING` không? | **CÓ**, nhưng rất hiếm: **9.738 dòng chứa `WARN` trên 49.652.771 dòng** (0,0196%) |
> | Có cột `severity`/`level` không? | **KHÔNG**. Log chỉ có 3 cột `timestamp`, `container_name`, `message`. Phải **parse mức từ `message`** |
> | Phân bố theo hệ thống? | **Sock Shop: 9.662 dòng** (99,2%) · Train Ticket: 74 dòng · **Online Boutique: 2 dòng trên 17,1 triệu dòng** |
> | Có bao nhiêu case dùng được? | **359/735 case có file log**; **376 case không có log** (375 thuộc suite RE1 + 1 case lỗi ở RE2) |
> | `root_cause_indicator` có ở mức alert không? | **Có, nhưng chỉ 8 case** — và chỉ **4 case** có indicator là dòng `WARNING` |
> | Loại nhiễu `Cascading` có đo được ở mức WARNING không? | **Gần như không**: Sock Shop chỉ 1 service phát WARN/case; Train Ticket có lan nhiều service nhưng chỉ 74 dòng |
>
> **Verdict cập nhật của CP1: CONDITIONAL GO (Go có điều kiện).** Ba phương án và khuyến nghị nằm ở §9 của `cp1/data_schema_notes.md`.

**Việc cần làm tiếp, theo thứ tự ưu tiên:**
1. **Gửi thầy Long xác nhận hướng đề tài.** Trong 3 lựa chọn ban đầu — (a) bỏ ràng buộc WARNING, (b) giữ WARNING nhưng tự định nghĩa mức và khai báo rõ là giả định của tác giả, (c) chuyển sang LEMMA-RCA — thì **(c) đã bị loại** (LEMMA-RCA cũng không có `warning`), và **đã chốt chọn (b)** theo Phương án B trong `cp1/data_schema_notes.md` §9. Việc cần thầy xác nhận nay thu hẹp còn: hướng **"early-warning level + agent tool-calling"** với quy trình gán mức 3 tầng có hợp lệ không, và có cho phép **mở rộng alert stream sang tier `ERROR`** để kiểm chứng H2 (cascading) hay không.
2. ~~**Kiểm tra thực nghiệm trên dữ liệu thật (việc của CP3):** tải `logs.csv` của RE2/RE3, kiểm tra xem **có dòng log nào chứa level/từ khóa WARNING/WARN hay không**.~~ → **ĐÃ LÀM XONG ngày 2026-09-28**, xem `cp1/data_schema_notes.md`. Kết quả: có `WARNING`, nhưng chỉ Sock Shop đủ mật độ để làm thực nghiệm.
3. **Chốt lại định nghĩa "alert" và "root-cause alert"** vì RCAEval chỉ có `root_cause_service` + `root_cause_indicator`, **không có root-cause alert** → cách ánh xạ phải được viết thành công thức, không để mô tả bằng lời.
4. **Dựng và lưu lại bằng chứng cho đính chính #8** (license HF) và cho **`UNVERIFIED` topology của 3 hệ thống RCAEval** — hai điểm này ảnh hưởng trực tiếp đến phần Threats to Validity.
5. **Cập nhật lại phần Baseline của đề cương**: ghi rõ COLA không chạy được (thiếu SOP 3–4 trang/alert) và COLA/AlertGuardian/MDPI đều dùng dataset không public → bỏ mọi phát biểu "so sánh trực tiếp với COLA/AlertGuardian".

---

## 7. DANH SÁCH ĐIỂM UNVERIFIED CÒN LẠI (không được dùng để kết luận)

| # | Nội dung | Lý do chưa xác minh | Ảnh hưởng tới CP2 |
|---|---|---|---|
| 1 | Tên cụ thể **4 nguyên nhân gây alert fatigue** trong Tariq et al. ACM CSUR 2025 | dl.acm.org và dlnext.acm.org đều trả **403/CAPTCHA** | Không ảnh hưởng — paper này chỉ dùng để đính chính citation, không dùng cho taxonomy |
| 2 | **Taxonomy chi tiết** của Soldani & Brogi ACM CSUR 2022 | dl.acm.org 403/CAPTCHA (chưa đọc bản arXiv:2105.12378) | Ảnh hưởng phần bối cảnh — hiện chỉ trích được metadata + mục tiêu survey |
| 3 | Con số **"11 datasets"** cho Drain trong He et al. DSN 2016 | Chỉ có snippet Semantic Scholar; abstract chính thức ghi **5 datasets** | **Không dùng con số 11.** Bảng §1 ghi rõ 5 dataset |
| 4 | **Taxonomy + toàn bộ thân bài** của Arif et al. Springer 2026 | Springer yêu cầu đăng nhập; chỉ lấy được **39 references** | Ảnh hưởng: bằng chứng gap (a) dựa trên **reference list**, không dựa trên phần thân bài của survey |
| 5 | **Taxonomy chi tiết** của He et al. ACM CSUR 2021 (log analysis) | Chỉ có snippet | Thấp — không phải nguồn chính |
| 6 | **Số liệu cụ thể của LogST** (SBERT + GRU) | Abstract không có số; full text closed access | Ảnh hưởng: **không được viết bất kỳ con số nào** cho LogST |
| 7 | **Nội dung** của Yang et al. DSN 2022 (alert anti-patterns) | Chỉ thấy trong reference list, chưa đọc full text | Thấp — hiện không dùng làm bằng chứng chính |
| 8 | **Kết quả SuperAgg chi tiết theo từng dataset** | Chỉ có abstract; full text closed access | Ảnh hưởng: chỉ được trích **">98%"** và **"83,8% và 43,2%"** nguyên văn từ abstract |
| 9 | **UHAS F1 chính xác** (abstract chỉ ghi *"larger than 0.9"*) | Paper closed access | Thấp — AlertGuardian đã cung cấp số ARR baseline của UHAS (89–91%) |
| 10 | Preprint TechRxiv *"Deep Learning-Based Failure Detection and Log Classification in Cloud"* — ứng viên **gần nhất cho WARNING-level** | Chỉ đọc được snippet; **chưa peer-review**; là log classification, không phải alert aggregation | **Quan trọng** — phải kiểm tra trước khi khẳng định gap (a), vì đây là công trình duy nhất tách Error/Warning/Info |
| 11 | Bài Springer *"Research on storage early warning and scheduling for cloud"* (DOI 10.1186/s13677-026-00983-6) | Chỉ đọc snippet | Trung bình — là early-warning dự đoán, khả năng không phải alert aggregation |
| 12 | **Topology (service call graph) của 3 hệ thống RCAEval** có thực sự "đã public" và build được như CP1 ghi | CP2 chưa kiểm chứng lại; RCAEval README **không document topology**. **Cập nhật 2026-09-28:** đã phát hiện RCAEval có `traces.parquet` cho **240 case** → có thể **tự dựng call graph thật** từ trace thay vì phải dựa vào repo public | **Quan trọng** — quyết định arm-3 có chạy được hay không. Hướng khả thi: dựng topology từ trace của chính dataset |
| 13 | ~~**`logs.csv` của RCAEval có chứa log level WARNING hay không**~~ → **ĐÃ GIẢI QUYẾT 2026-09-28** | Đã kiểm chứng trực tiếp: **CÓ 9.738 dòng `WARN`**, có cột `message` để parse mức, nhưng **KHÔNG có cột `severity`** | Xem `cp1/data_schema_notes.md`. Kết luận CP1: **CONDITIONAL GO** |
| 14 | **License LEMMA-RCA trên HuggingFace** | Tự kiểm chứng ngoài file raw (xem §5 dòng 8) nhưng **chưa lưu ảnh/log kiểm chứng** | Trung bình — ảnh hưởng phần pháp lý khi publish derived dataset |
| 15 | RCAEval: **15 baseline** (abstract) vs **17 baseline** (README liệt kê) | Chưa đối chiếu bản gốc | Thấp — nêu cả hai kèm nguồn |

---

**Ngày**: 2026-09-28 (thu thập dữ liệu raw; **cập nhật 2026-09-28** sau khi CP1 hoàn thành kiểm chứng dữ liệu)
**Trạng thái**: **nháp — scope đã chốt (Phương án B), chờ thầy Long xác nhận**. Câu hỏi Go/No-go về log `WARNING` **đã có câu trả lời** (xem khối ✅ ở §6).
**Nguồn dữ liệu**: `F:\study\NCKH\cp2\_research_raw.md` (908 dòng) + `F:\study\NCKH\cp1\data_schema_notes.md` (kết quả kiểm chứng trên RCAEval thật) — không có số liệu nào được thêm mới ngoài dòng đính chính #8 (đã ghi rõ là tự kiểm chứng).
