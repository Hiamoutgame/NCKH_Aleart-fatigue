# Literature Review Matrix

Cập nhật 26/10/2026. Bảng tổng hợp các bài nhóm đã đọc hoặc đã trích dẫn trong repo (`paper_summaries/`, `paper_list.md`, `requirement/Why.md`, `paper/report/references.bib`, `docs/references/*.pdf`). Chưa tìm thêm bài mới ngoài repo.

Mục tiêu: biết các bài trước làm gì, dùng model gì, dataset nào, metric nào, và tìm khoảng trống cho đề tài (tổ chức log phân cấp giữ bằng chứng + xếp hạng service nghi ngờ). Ô ghi "chưa đọc" nghĩa là repo chưa có thông tin đáng tin cho ô đó, không có nghĩa bài không có.

## Matrix

| No | Paper Title | Year | Venue | Domain | AI Method | Dataset | Metrics | Main Contribution | Limitation | Relevance to Our Topic |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Nezha: Interpretable Fine-Grained Root Causes Analysis for Microservices on Multi-modal Observability Data (Yu et al.) | 2023 | ESEC/FSE | Microservices RCA (metric + log + trace) | Không học có giám sát. Đổi metric/log/trace thành event (log parse bằng Drain, metric alert theo k-σ), dựng event graph theo trace/span ID, so tần suất pattern giữa giai đoạn bình thường và giai đoạn lỗi (Score_min = 0.67) | Tự tạo bằng tiêm lỗi: OnlineBoutique 56 lỗi (42 tài nguyên, 14 code), TrainTicket 45 lỗi (20/25), mỗi lỗi 3 phút (tr. 560). Public trên Zenodo/GitHub | AS@1/3/5 (service), AIS@1/3/5 (code region / resource type), ablation, thời gian chẩn đoán | AS@1 92.86% (OB), 86.67% (TT), hơn các baseline unsupervised (Bảng 3, tr. 561). Kết quả kèm cặp "đáng lẽ chạy gì → thực tế chạy gì" để giải thích | Bắt buộc log có trace/span ID (tr. 562). Phụ thuộc bộ phát hiện bất thường và dữ liệu bình thường. Chỉ 2 hệ thống | **Cao.** Dataset Nezha trong `data/raw/nezha/` chính là dữ liệu của bài này. Ý tưởng so trước/sau lỗi gần với flow của nhóm |
| 2 | MRCA: Metric-level Root Cause Analysis for Microservices via Multi-Modal Data (Wang et al.) | 2024 | ASE | Microservices RCA mức metric | Drain + tần suất template theo service + latency trace → VAE xếp hạng service theo reconstruction probability; Granger causality + Q-learning để dừng mở rộng đồ thị; pruning | Dataset của Nezha: OB 3,907,981 log, TT 1,352,335 log; train/test 60/40 (tr. 1063–1064) | P/R/F1 (phát hiện bất thường), PR@1/3/5, MRR (service và metric level), thời gian | Service level PR@1 0.589 / 0.622, PR@3 0.804 / 0.822, MRR 0.691 / 0.735 (OB/TT, Bảng 4, tr. 1065) | Lỗi code chỉ định vị tới service. ~50% ca sai do service ít hoạt động, ~40% do lỗi code chỉ thấy qua call chain (tr. 1066–1067). Baseline tự cài lại. 1 dataset | **Cao.** Bỏ log làm PR@1 OB giảm 0.589 → 0.482 (Bảng 6). Bảng 1: log không phản ánh CPU contention và network jam |
| 3 | RCAEval: A Benchmark for Root Cause Analysis of Microservice Systems with Telemetry Data (Pham et al.) | 2025 | WWW Companion | Benchmark RCA microservices | Benchmark + 15 baseline tái lập được (theo abstract) | 735 case, 3 hệ thống (Online Boutique, Sock Shop, Train Ticket). Kiểm trên raw: 359 case có log, mỗi case 1 service đáp án, 18 service, 11 loại lỗi | Chưa đọc phần metric của paper | Benchmark public có log + nhãn service lớn nhất trong danh sách | Log chỉ có `timestamp`, `container_name`, `message`; không có severity, không có trace ID. Tên case chứa đáp án. 26/359 case service lỗi không có log | **Rất cao.** Dataset chính của dự án |
| 4 | Drain: An Online Log Parsing Approach with Fixed Depth Tree (He, Zhu, Zheng, Lyu) | 2017 | ICWS (tr. 33–40) | Log parsing | Parse online: vài regex thay biến → cây độ sâu cố định (nhánh theo số token, rồi theo vài token đầu) → so độ giống theo vị trí token với ngưỡng `st` → gộp, token khác thành `*`. Mỗi nhóm lưu template + danh sách log ID | 5 bộ log thật (không phải microservices): BGL, HPC, HDFS (11,175,629 dòng), Zookeeper, Proxifier (Bảng I) | F-measure trên cặp log so với template chuẩn; thời gian chạy; case study phát hiện bất thường | Accuracy cao nhất 4/5 bộ (0.99 / 0.84 / 0.99 / 0.99 / 0.86, Bảng III); nhanh hơn Spell 51.85%–81.47% (Bảng IV); nhóm không giao nhau (tr. 34) | Giả định cùng template thì cùng số token. `depth`, `st` chỉnh riêng từng bộ. Parse đúng chưa chắc bước sau tốt (SHISO, Bảng VI) | **Cao.** Thay regex + MD5 hiện tại; Nezha và MRCA đều dùng. Nhóm giữ log ID, khớp tầng lá của cây phân cấp |
| 5 | Knowledge-aware Alert Aggregation in Large-scale Cloud Systems: A Hybrid Approach — COLA (Kuang et al.) | 2024 | ICSE-SEIP | Gom alert trong cloud | Tương quan thống kê + LLM dùng tri thức vận hành | Dữ liệu cloud công nghiệp; ghi chú cũ nói không public (chưa kiểm) | Pairwise F1 0.901–0.930 | Chỉ ra semantic similarity bỏ qua lý do nhân quả, thống kê khó với alert hiếm | Đơn vị là alert, không phải log; cần tri thức riêng; khó tái lập (chưa kiểm) | **Trung bình.** Gần phần gom nhóm, nhưng pairwise F1 cần nhãn nhóm mà dataset của dự án không có |
| 6 | AlertGuardian: Intelligent Alert Life-Cycle Management for Large-scale Cloud Systems (Yu et al.) | 2025 | ASE | Quản lý vòng đời alert | Graph learning + LLM reasoning | Ghi chú cũ nói private (chưa kiểm) | Alert Reduction Ratio 94.8%, diagnosis accuracy 90.5% | Vừa giảm alert vừa hỗ trợ chẩn đoán trong cùng một hệ | Chưa đọc toàn văn | **Trung bình–Cao.** Cùng mục tiêu "giảm số mục mà vẫn chẩn đoán đúng" |
| 7 | Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks (Reimers & Gurevych) | 2019 | EMNLP | Biểu diễn câu | BERT siamese tạo vector câu để so cosine | chưa đọc | chưa đọc | Ứng viên gom nhóm theo nghĩa | Chưa có bằng chứng giúp được log; tốn tài nguyên hơn template | **Trung bình** |
| 8 | HDBSCAN: Hierarchical Density-Based Clustering (McInnes et al.) | 2017 | JOSS | Phân cụm | Phân cụm theo mật độ, không cần định trước số cụm | chưa đọc | chưa đọc | Thư viện cài đặt thuật toán HDBSCAN | Là bài về phần mềm; trích thuật toán cần thêm bài gốc của Campello et al. | **Thấp–Trung bình** |
| 9 | Log Severity Levels Matter: A Multivocal Mapping (Mendes & Petrillo) | 2021 | arXiv:2109.01192 | Thực hành ghi log | Multivocal mapping (tổng hợp tài liệu học thuật + công nghiệp) | 27 nghiên cứu, 40 thư viện logging | Không áp dụng (khảo sát) | 19 mức severity, có dư thừa và trùng nghĩa | Preprint | **Trung bình.** Lý do không tin severity suy ra bằng regex |
| 10 | Intelligent Logging and Monitoring Strategies (Bellundagi) | 2026 | IJSTC | Logging/monitoring Java microservices | Structured logging (Log4j) + clustering, classification, chuỗi thời gian | Không nêu dataset | Nhắc anomaly accuracy, MTTR nhưng không có số liệu | Chiến lược tổng quan | Không số liệu, không baseline, chưa rõ chất lượng venue | **Thấp** |
| 11 | Alert Prioritisation in Security Operations Centres: A Systematic Survey on Criteria and Methods (Jalalvand et al.) | 2024 | ACM CSUR | Cảnh báo trong SOC | Survey | Không áp dụng | Không áp dụng | Bối cảnh ưu tiên cảnh báo | Lĩnh vực security | **Thấp.** Chỉ cho phần mở đầu |
| 12 | Alert Fatigue in Security Operations Centres: Research Challenges and Opportunities (Tariq et al.) | 2025 | ACM CSUR | Alert fatigue trong SOC | Survey | Không áp dụng | Không áp dụng | Bối cảnh alert fatigue | Lĩnh vực security; câu trích trong Why.md chưa kiểm nguyên văn | **Thấp.** Chỉ cho phần mở đầu |
| 13 | Site Reliability Engineering (Beyer et al., eds.) — ch. 10, ch. 11; Site Reliability Workbook — ch. 5 | 2016 / 2018 | O'Reilly (sách) | Vận hành SRE | Không áp dụng | Không áp dụng | Không áp dụng | Cảnh báo phải dẫn tới hành động; tối đa 2 sự cố mỗi ca trực 12 giờ (ch. 11) | Sách thực hành, không phải nghiên cứu thực nghiệm | **Thấp.** Bối cảnh |
| 14 | LEMMA-RCA: A Large Multi-modal Multi-domain Dataset for Root Cause Analysis (Zheng et al.) | chưa rõ | chưa rõ | Dataset RCA đa phương thức | chưa đọc | chưa đọc | chưa đọc | chưa đọc | Metadata mâu thuẫn (xem cuối file) | **Thấp.** Dự án đã bỏ dataset này ngày 26/10/2026 |

Không còn dùng: Chain-of-Thought Prompting (Wei et al., NeurIPS 2022), chỉ phục vụ nhánh LLM Agent của phiên bản cũ.

## Mức kiểm chứng

| Mức | Nghĩa | Bài |
| --- | --- | --- |
| **PDF** | Đã đọc toàn văn PDF trong `docs/references/` ngày 26/10/2026; số liệu kèm số trang in trên bài | 1, 2, 4 |
| **ABS** | Số liệu khớp abstract theo [Why_FactCheck.md](../requirement/Why_FactCheck.md); chưa đọc toàn văn | 3, 5, 6, 9, 13 |
| **REPO** | Đã kiểm trực tiếp trên `data/raw/` ngày 26/10/2026 | Phần dataset của 3 |
| **META** | Chỉ có thông tin trích dẫn hoặc ghi chú cũ | 7, 8, 10, 11, 12, 14 |

## Model dùng trong hệ thống (không phải bài báo)

| Model | Nguồn | Phương pháp | Dữ liệu train | Metric công bố | Hạn chế | Vai trò |
| --- | --- | --- | --- | --- | --- | --- |
| Kev 1.0 | GitHub `jaredpalmer/kev`, vendored tại `third_party/kev/` (commit `2074cc4`), Apache-2.0 | LoRA + pointer head trên Qwen3.5 (0.8B/4B/9B); trả xác suất đã hiệu chỉnh cho câu hỏi có/không, chọn một, cho điểm; không sinh văn bản | `decision-v7`: 10,000 ví dụ từ 10 dataset công khai + dữ liệu sinh | Kev-4B trên nguồn chưa thấy: accuracy 0.817 (dev) / 0.838 (test) | Không train trên log; kiểm chứng tới 8,192 token (bản ≤ 9B); đổi thứ tự phương án có thể đổi kết quả; không có bài báo peer-review | Ranker chính, bọc sau interface `ServiceRanker`. Xem [ai_model_integration.md](../04_proposed_system/ai_model_integration.md) |

## Tổng hợp

### Model / phương pháp đã được dùng

- **Parse log:** Drain là lựa chọn chung của Nezha và MRCA. Dự án hiện dùng regex + MD5. Bài Drain so với LKE, IPLoM (offline) và SHISO, Spell (online).
- **Xếp hạng RCA không cần nhãn:** so pattern trước/sau lỗi (Nezha), phát hiện bất thường bằng VAE (MRCA), PageRank / spectrum ở các baseline mà Nezha so sánh.
- **Có LLM:** COLA, AlertGuardian. Cả hai làm trên alert và dữ liệu công nghiệp.
- **Học có giám sát để xếp hạng service:** chưa có bài nào trong danh sách. Nezha (tr. 556) chủ động bỏ qua cách có giám sát vì khó có dữ liệu gán nhãn.

### Dataset phù hợp

| Dataset | Public | Có log | Nhãn | Ghi chú |
| --- | --- | --- | --- | --- |
| RCAEval | Có | 359/735 case | Service, 1 nhãn/case | Dataset chính. Log không có trace ID |
| Nezha | Có (Zenodo/GitHub) | Có, kèm trace/span ID | Pod (ánh xạ sang service) | 101 lỗi: OB 56 (raw ngày 2022-08-22/23) + TT 45 (raw ngày 2023-01-29/30, pod `ts-*`). Nezha và MRCA đều báo kết quả trên dữ liệu này, nhưng dùng đa phương thức |
| Dữ liệu của COLA, AlertGuardian | Chưa kiểm, ghi chú cũ nói không | — | — | Không dùng làm thực nghiệm được |

### Metric thường dùng

- **Xếp hạng:** Top-k (AS@k, PR@k), MRR. Metric chung của Nezha, MRCA và kế hoạch của nhóm.
- **Gom nhóm:** Pairwise F1 (COLA), Alert Reduction Ratio (AlertGuardian). Cả hai cần nhãn nhóm hoặc định nghĩa alert. Dataset của dự án không có nhãn nhóm, nên nhóm dùng Visible Log Reduction và Raw Log Traceability.
- **Parse log:** F-measure trên cặp log so với template chuẩn (Drain). Muốn đo trên RCAEval phải tự gán template cho một mẫu nhỏ.
- **Khác:** P/R/F1 cho phát hiện bất thường (MRCA), thời gian chạy (Drain, Nezha, MRCA).

**Lưu ý về mẫu số:** MRCA báo Nezha chỉ đạt PR@1 0.321–0.378 ở service level, trong khi bài Nezha báo AS@1 khoảng 90%. MRCA giải thích là hai bài tính trên mẫu số khác nhau (tr. 1064). Đây là lý do nhóm báo riêng candidate coverage, conditional Top-k và end-to-end Top-k.

### Khoảng trống

Chi tiết ở [research_gap.md](../03_problem_and_gap/research_gap.md). Danh sách nguồn mới có 14 bài và chưa tìm kiếm có hệ thống, nên các gap là giả thuyết cần kiểm; không viết "chưa ai làm" dựa trên bảng này.

## Sai lệch phát hiện khi đối chiếu

| Vị trí | Vấn đề | Bằng chứng |
| --- | --- | --- |
| `paper/report/references.bib`, mục `drain3` | Ghi venue là ICSE 2017, doi `10.1109/ICSE.2017.11`. Đúng phải là ICWS 2017, tr. 33–40, doi `10.1109/ICWS.2017.13` | Trang đầu bài Drain (`docs/references/phe_icws2017_drain.pdf`). Nezha [19] và MRCA [16] cũng trích như vậy |
| `references.bib` và `paper_list.md`, LEMMA-RCA | Hai số arXiv khác nhau | 2401.12345 và 2406.05375 |
| MRCA Bảng 2 | OB ghi 42 lỗi tài nguyên + 24 lỗi code, trong khi tổng là 56 | Bài Nezha ghi 14 lỗi code (tr. 560) |
| MRCA, phần chữ | PR@1 service level ghi 60.1%, trong khi trung bình của 0.589 và 0.622 là 60.55% | Bảng 4, tr. 1065 |
| Nezha, abstract | 89.77% được gắn với mức code region / resource type, nhưng đó cũng là trung bình AS@1 ở mức service (hai bảng có cùng số top-1) | Bảng 3 và Bảng 4, tr. 561 |

## Nên đọc tiếp

Các bài được Nezha hoặc MRCA trích dẫn, liên quan trực tiếp tới RCA dựa trên log hoặc tới dataset của dự án:

- **SBLD** — Rosenberg & Moonen, ESEM 2020 (Nezha [55]): chẩn đoán dựa trên log.
- **LogFaultFlagger** — Amar & Rigby, ICSE 2019 (Nezha [1]): chẩn đoán dựa trên log.
- **LogCluster** — Lin et al., ICSE Companion 2016 (Nezha [36]): gom cụm log để xác định sự cố.
- **PDiagnose** — Hou et al., 2021 (Nezha [21]): đa phương thức, đổi log thành chuỗi thời gian.
- **Eadro** — Lee et al., ICSE 2023 (MRCA [22]).
- **BARO** — Pham et al., FSE 2024 (MRCA [35]): cùng nhóm tác giả RCAEval.
- Toàn văn **RCAEval**, **COLA**, **AlertGuardian**: ba bài gần đề tài nhất nhưng mới kiểm abstract.

Lịch sử của bảng này (bản về WARNING-only và LLM Agent) còn trong git history.
