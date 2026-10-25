# Literature review V3 — bảng cần kiểm chứng

**Đồng bộ scope ngày 23/10/2026, chưa thực hiện literature search mới.** [Master context](../NCKH_MASTER_CONTEXT_2026-10-23.md) là nguồn định hướng. Các paper/claims phía dưới từ ghi chú cũ không trở thành bằng chứng đã xác minh chỉ vì xuất hiện trong matrix.

## Matrix làm việc hiện tại

| Nhóm candidate đã được nhắc | Vai trò có thể có trong V3 | Cần đọc/kiểm chứng trước khi dùng |
| --- | --- | --- |
| RCAEval, LEMMA-RCA, Nezha | Dataset/benchmark và service-level diagnosis | Modality, label level/multiplicity, case eligibility, protocol và source revision |
| Drain/Spell | Template parsing baseline | Parser assumptions, accuracy/coverage, fitting protocol; phân biệt Drain paper và implementation Drain3 |
| Sentence-BERT, HDBSCAN | Semantic grouping candidates | Input granularity, grouping labels, parameters, runtime, relation với service ranking |
| COLA, AlertGuardian | Related alert organization/correlation | Log vs alert unit, data availability, knowledge sources, evidence preservation và scope metric |
| SRE/domain materials | Problem framing, operational concepts | Source/claim thực tế; không dùng background làm bằng chứng novelty |
| Intelligent Logging and Monitoring Strategies | Candidate background từ V2 | Metadata/chất lượng nguồn/nội dung thực; chưa xác nhận phù hợp |

Mỗi paper record cần: exact source/revision, inspected section/page, task/input/output, label granularity, raw provenance, hierarchy/relationships/ranking, dataset/split/leakage controls, metrics denominator, reproducibility, limitations và evidence status. Paper score chỉ ghi khi có vị trí nguồn cụ thể.

## Những giả thuyết cần literature và thí nghiệm

- Hierarchy có provenance có hỗ trợ khám phá log tốt hơn flat grouping không?
- Grouping/temporal features có lợi gì cho service ranking khi giữ candidates và split cố định?
- Có trade-off giữa số mục hiển thị, raw reconstruction và RCA accuracy không?

Đây là **câu hỏi cần trả lời**, chưa phải research gaps đã xác nhận. Không dùng “WARNING gap”, RCPR target, first hybrid topology+semantic+agent hoặc việc suy alert labels từ service GT làm novelty V3.

## Ghi chú matrix V1/V2 được giữ để đối chiếu

**Toàn bộ phần cũ bên dưới là lịch sử/UNVERIFIED cho lần đồng bộ này.** Không dùng gap map/claim method/metric của nó như kết luận hiện tại. IDs trong các file cũ chưa thống nhất với nhau; khi review phải đối chiếu paper identity, không chỉ ID A1/A2.

# Literature Review Matrix — Alert Aggregation / LLM Agent / Microservices RCA

> **Trạng thái: BẢN NHÁP** — Chưa điền sâu vì cần cậu research bài trước từ `search_keywords.md`.
> Matrix này dùng để so sánh paper sau khi đã có danh sách bài thật trong `paper_list.md`.

---

## 1. Matrix chính

| ID | Paper | Problem | Domain | Data | Method | AI/LLM? | Metrics | Strength | Limitation | Liên quan tới đề tài |
|----|-------|---------|--------|------|--------|---------|---------|----------|------------|----------------------|
| A1 | COLA | Alert aggregation / alert correlation | AIOps / SRE | SOP + alerts | Log/alert correlation | Có | Pairwise F1 | Metric rõ, kết quả cao | Cần 3,000 SOPs; khó tái lập trên RCAEval | Baseline trực tiếp cho grouping quality |
| A2 | AlertGuardian | Alert noise reduction | AIOps / incident management | Private dataset | LLM-based aggregation | Có | ARR | ARR cao | Dataset không public; binary noise/critical, không tập trung WARNING | So sánh ARR và LLM aggregation |
| A3 | RCAEval | Benchmark RCA | Microservices | 735 cases | Dataset benchmark | Không chính | RCA metrics | Public, MIT, dùng được làm primary dataset | Không có alert ground truth; no severity column | Dataset chính của đề tài |
| A4 | LEMMA-RCA | RCA benchmark | Microservices | Benchmark dataset | Dataset / RCA | Không chính | RCA metrics | Có thể làm backup | Không giải quyết WARNING gap | Backup dataset |
| C1 | Intelligent Logging and Monitoring Strategies | Logging / monitoring strategy | System monitoring | Literature / conceptual | Monitoring strategy | Có thể có | — | Phù hợp domain logging/monitoring | Cần đọc kỹ để xác định đóng góp cụ thể | Domain background |
| B1 | *(cần tìm)* | — | — | — | — | — | — | — | — | — |
| B2 | *(cần tìm)* | — | — | — | — | — | — | — | — | — |
| B3 | *(cần tìm)* | — | — | — | — | — | — | — | — | — |

---

## 2. Các cột cần điền khi đọc paper

| Cột | Cách điền |
|-----|-----------|
| Problem | Bài giải quyết vấn đề gì: alert fatigue, RCA, anomaly detection, log parsing... |
| Domain | Microservices, SRE, AIOps, cloud system, distributed system... |
| Data | Public/private, synthetic/production, có log/metric/trace/alert không |
| Method | Rule-based, ML, clustering, LLM, agent, topology-based... |
| AI/LLM? | Không / ML truyền thống / LLM / Agent / Tool-calling |
| Metrics | ARR, precision/recall/F1, RCA accuracy, latency, cost... |
| Strength | Điểm mạnh có thể học theo |
| Limitation | Điểm yếu/gap để đề tài mình khai thác |
| Liên quan tới đề tài | Trực tiếp / nền tảng / baseline / domain background |

---

## 3. Gap map tạm thời

| Gap từ literature | Dẫn chứng dự kiến | Cách đề tài mình xử lý |
|-------------------|------------------|--------------------------|
| Ít nghiên cứu tập trung vào `WARNING` / early-warning logs | Cần tìm thêm paper | Tập trung vào WARNING-level logs trước failure |
| Nhiều nghiên cứu đo compression nhưng chưa bảo toàn root-cause signal rõ ràng | AlertGuardian / alert aggregation papers | Đề xuất RCPR làm metric chính |
| LLM-all tốn cost và latency | Cần tìm paper LLM AIOps | Chỉ gọi LLM cho difficult/ambiguous cases |
| Public alert-level benchmark thiếu | RCAEval có log nhưng không có alert ground truth | Tạo alert stream + label từ RCAEval |
| Semantic-only không hiểu topology/service dependency | Cần paper log clustering | Kết hợp semantic + temporal + topology |

---

## 4. Checklist trước khi viết Related Work

- [ ] Đủ ≥ 5 bài liên quan trực tiếp.
- [ ] Đủ ≥ 3 bài về model AI / phương pháp AI.
- [ ] Đủ ≥ 2 bài về domain ứng dụng.
- [ ] Mỗi bài có ít nhất 3 dòng note: problem, method, limitation.
- [ ] Matrix có cột limitation rõ để sinh research gap.
- [ ] Không claim metric/chỉ số nếu chưa đọc paper gốc.

---

## 5. Template note nhanh cho mỗi paper

```markdown
### ID — Paper title

- **Problem:**
- **Method:**
- **Data:**
- **Metrics:**
- **Key result:**
- **Limitation:**
- **Use in our project:**
```
