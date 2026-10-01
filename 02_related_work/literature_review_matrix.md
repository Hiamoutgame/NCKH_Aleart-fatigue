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
