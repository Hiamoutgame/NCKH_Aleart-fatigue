# Paper List — Alert Aggregation / LLM Agent / Microservices RCA

> **Trạng thái: BẢN NHÁP** — Chỉ liệt kê seed papers từ README.
> Cậu cần tự research thêm bằng từ khóa trong `search_keywords.md`, rồi bổ sung vào đây.

---

## Yêu cầu tối thiểu

| Loại | Min | Hiện có | Ghi chú |
|------|-----|---------|---------|
| Liên quan trực tiếp (alert aggregation, RCA, log clustering) | 5 | 4 | Cần ≥ 1 bài nữa |
| Model AI / phương pháp AI (LLM, SBERT, HDBSCAN, agent) | 3 | ~1 | Cần ≥ 2 bài nữa |
| Domain ứng dụng (AIOps, observability, SRE) | 2 | 1 | Cần ≥ 1 bài nữa |

---

## A. Bài liên quan trực tiếp

| # | Tiêu đề | Tác giả chính | Venue / Năm | arXiv / DOI | Đọc? | Ghi chú tóm tắt |
|---|---------|---------------|-------------|-------------|------|------------------|
| A1 | COLA: Cross-system Online Log-based Alert Aggregation | — | ICSE-SEIP 2024 | arXiv:2403.06485 | ☐ | Pairwise F1 0.901–0.930; cần 3,000 SOPs; không reproducible trên RCAEval |
| A2 | AlertGuardian: LLM-powered Alert Aggregation | — | ASE 2025 | arXiv:2601.14912 | ☐ | ARR 94.8%; dataset không public; binary noise/critical |
| A3 | RCAEval: A Benchmark for Root Cause Analysis in Microservices | Phạm Quí Luân et al. | WWW 2025 Companion | arXiv:2412.17015 | ☐ | 735 cases, MIT; không có alert ground truth |
| A4 | LEMMA-RCA | — | CIKM 2026 | arXiv:2406.05375 | ☐ | Backup dataset; không có WARNING signal |
| A5 | *(cần tìm thêm)* | — | — | — | ☐ | — |

## B. Bài về Model AI / Phương pháp AI

| # | Tiêu đề | Tác giả chính | Venue / Năm | arXiv / DOI | Đọc? | Ghi chú tóm tắt |
|---|---------|---------------|-------------|-------------|------|------------------|
| B1 | *(cần tìm — ví dụ: Drain3 original paper, SBERT paper, HDBSCAN paper, hoặc LLM tool-calling paper)* | — | — | — | ☐ | — |
| B2 | *(cần tìm)* | — | — | — | ☐ | — |
| B3 | *(cần tìm)* | — | — | — | ☐ | — |

> **Gợi ý tìm cho nhóm B:**
> - He et al. "Drain: An Online Log Parsing Approach..." (ICWS 2017)
> - Reimers & Gurevych "Sentence-BERT" (EMNLP 2019)
> - Campello et al. "HDBSCAN" (TODS 2015 / KDD 2013)
> - Schick et al. "Toolformer" (NeurIPS 2023) hoặc ReAct (Yao et al. ICLR 2023)

## C. Bài về Domain ứng dụng (AIOps / Observability / SRE)

| # | Tiêu đề | Tác giả chính | Venue / Năm | arXiv / DOI | Đọc? | Ghi chú tóm tắt |
|---|---------|---------------|-------------|-------------|------|------------------|
| C1 | Intelligent Logging and Monitoring Strategies | — | IJSTC (IJCDRA) | [link](https://ijcdra.us/index.php/IJSTC/article/view/69) | ☐ | Đang đọc — logging/monitoring domain |
| C2 | *(cần tìm)* | — | — | — | ☐ | — |

> **Gợi ý tìm cho nhóm C:**
> - Notaro et al. "A Survey of AIOps Methods for Failure Management" (TIST 2021)
> - Chen et al. "Outage analysis of microservices" (ATC/OSDI domain)
> - Dang et al. "AIOps: Real-World Challenges and Research Innovations" (ICSE-SEIP 2019)

---

## Hướng dẫn ghi bài mới

Khi tìm được bài mới, thêm 1 row vào bảng phù hợp (A/B/C) với format:

```markdown
| A5 | Tên bài | Tác giả | Venue Năm | DOI/arXiv | ☐ | Ghi chú ngắn |
```

Đánh ☑ cột "Đọc?" khi đã đọc xong. Sau đó cập nhật `literature_review_matrix.md`.
