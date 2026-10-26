# Evaluation Plan

Cập nhật 26/10/2026. Định nghĩa đầy đủ về mẫu số nằm ở [research protocol](../research_protocol_v3.md) mục 5. Chưa có kết quả thực nghiệm nào.

## 1. Evaluation Objectives

Đánh giá trả lời bốn câu hỏi trong [research_questions.md](../03_problem_and_gap/research_questions.md):

| Mục tiêu | Câu hỏi |
| --- | --- |
| Gom nhóm giảm được bao nhiêu mục cần đọc mà vẫn mở lại được mọi log gốc | RQ1 |
| Kev xếp hạng service đúng đến đâu so với baseline, và tỉ lệ nó đưa ra có đáng tin không | RQ2 |
| Thành phần nào của bằng chứng giúp xếp hạng: template, severity, so sánh trước/sau lỗi | RQ3 |
| Kết quả thay đổi thế nào theo loại lỗi, hệ thống, và trên dataset ngoài | RQ4 |

## 2. Dataset

- **RCAEval:** 359 case có log (ob 120, ss 120, tt 119), mỗi case một service đáp án. Chia 70/15/15 theo 117 kịch bản lỗi, phân tầng theo suite × hệ thống, seed 42.
- **Nezha:** 101 lần tiêm lỗi (OnlineBoutique 56, TrainTicket 45). Chỉ dùng làm test ngoài sau khi đã khóa model; cần sửa adapter trước.

Chi tiết, rủi ro rò rỉ đáp án và các lỗi adapter ở [dataset.md](dataset.md).

## 3. Baseline

- **Gom nhóm:** G0 không gom, G1 regex + MD5 (đã có), G2 Drain, G3 Drain + Kev hỗ trợ gộp (tùy chọn).
- **Xếp hạng:** R0 ngẫu nhiên, R1 nhiều log nhất, R2 nhiều ERROR nhất, R3 tăng nhiều nhất so với trước lỗi, R4–R5 Logistic Regression, R6 Kev chưa fine-tune, **P Kev đã fine-tune**.
- **Ablation:** A1 bỏ phần "trước lỗi", A2 bỏ nội dung template, A3 bỏ severity, A4 gom bằng G1 thay vì G2.

Chi tiết ở [baseline.md](baseline.md).

## 4. Metrics

| Metric | Meaning | Why Used |
|---|---|---|
| Top-1 / Top-3 / Top-5 | Tỉ lệ incident có service đáp án nằm trong k service đầu | Metric chính của bài toán gợi ý / xếp hạng; Nezha và MRCA đều dùng, dễ đặt cạnh |
| MRR (Mean Reciprocal Rank) | Trung bình `1 / hạng của đáp án`; không có thì 0 | Thưởng cho việc đặt đáp án sớm, không chỉ đúng/sai ở một ngưỡng k |
| Candidate coverage | Tỉ lệ incident có đáp án nằm trong danh sách service ứng viên | Giới hạn trên của mọi phương pháp; tránh thổi phồng kết quả khi lọc bỏ case khó |
| Conditional vs end-to-end Top-k | Conditional: chia cho số incident có coverage. End-to-end: chia cho toàn bộ incident | Bài học từ chênh lệch Nezha / MRCA do khác mẫu số |
| Brier score | Trung bình bình phương sai lệch giữa xác suất và kết quả thật; càng nhỏ càng tốt | Demo hiện tỉ lệ cho người dùng, cần biết tỉ lệ có đáng tin không |
| ECE (Expected Calibration Error) | Chênh lệch giữa mức tự tin của model và tỉ lệ đúng thật, tính theo từng khoảng tự tin | Như trên; kiểm tra temperature của Kev |
| Visible Log Reduction | `1 - số nhóm / số log`, tính ở cùng một tầng của cây | Đo mức giảm số mục phải đọc (RQ1) |
| Raw Log Traceability | Số log mở lại đúng dòng gốc / tổng số log | Bảo đảm gom nhóm không làm mất bằng chứng; mục tiêu 100% |
| Response Time | Thời gian từng bước (chuẩn hóa, gom nhóm, tạo `state`, xếp hạng) cho mỗi incident | Biết hệ thống có dùng được trong lúc trực sự cố không |
| Độ dài `state` (token) | Số token Kev phải đọc mỗi incident | Kev bản ≤ 9B chỉ kiểm chứng tới 8,192 token |
| Accuracy / F1 theo từng dòng service | — | **Không dùng.** Mỗi incident có khoảng 11 ứng viên và 1 đáp án; luôn đoán "không phải" vẫn đạt khoảng 90% |
| Expert Rating, User Satisfaction (SUS), Time to Locate | Đánh giá của người dùng | **Chỉ dùng khi có user study** với protocol rõ ràng. Hiện chưa có kế hoạch |

Ghi chú:

- Với `k` lớn hơn số ứng viên, dùng `k' = min(k, số ứng viên)`. Hòa điểm thì xếp theo `service_id` tăng dần.
- RCAEval và Nezha mỗi incident có một đáp án, nên Recall@k trùng với Top-k.
- Visible Log Reduction không tính bằng cách chỉ đếm 3 nhóm bằng chứng được hiển thị, và không tự chứng minh người dùng tìm nhanh hơn.
- Parse accuracy kiểu Drain (F-measure trên cặp log) chỉ đo được nếu tự gán template cho một mẫu nhỏ có protocol.

### Mức cải thiện (Relative Improvement)

Gọi `M` là một metric trung bình trên các incident (Top-1, Top-3 hoặc MRR), `B` là baseline, `P` là phương pháp được so.

| Tên | Công thức | Đọc là |
| --- | --- | --- |
| Chênh lệch tuyệt đối | `Δ = M(P) − M(B)` | Tăng bao nhiêu điểm phần trăm. **Số chính khi báo kết quả** |
| Relative Improvement | `RI = (M(P) − M(B)) / M(B)` | Tăng bao nhiêu % so với baseline. Không xác định khi `M(B) = 0` |
| Error Reduction | `ER = (M(P) − M(B)) / (1 − M(B))` | Sửa được bao nhiêu phần trong số ca baseline làm sai. Không xác định khi `M(B) = 1` |

**Khoảng tin cậy:** bootstrap paired theo kịch bản lỗi. Mỗi lần lặp bốc lại các kịch bản (có hoàn lại), tính `M(P)` và `M(B)` trên **cùng** các incident đó, rồi tính Δ, RI, ER. Lặp 1,000 lần, lấy phân vị 2.5% và 97.5%. Các lần lặp có `M(B) = 0` được đếm riêng, không bỏ qua âm thầm.

**Quy tắc quyết định** (ghi trước khi chạy test): chỉ nói "P cải thiện so với B" khi **cận dưới khoảng tin cậy 95% của Δ lớn hơn 0**.

**Vì sao không báo RI một mình:** RI phóng to khi baseline thấp. Ví dụ, baseline 0.10 lên 0.20 cho RI = +100%, trong khi chỉ thêm 10 điểm %. MRCA ghi "improve PR@1 by 74.72% ~ 367.67%" (tr. 1064) vì baseline yếu nhất chỉ khoảng 0.13. Luôn báo kèm Δ và giá trị gốc của B và P.

Cài đặt: `src/evaluation/metrics.py` (`relative_improvement`, `error_reduction`, `paired_bootstrap`), kiểm bằng ví dụ tính tay trong `tests/test_evaluation_metrics.py`.

## 5. Evaluation Procedure

1. Sửa adapter Nezha, sinh `data/normalized/` cho RCAEval và Nezha.
2. Chạy audit, tạo `splits.parquet` theo kịch bản và **khóa split** trước khi chạy bất kỳ model nào.
3. Lập danh sách service ứng viên cho mỗi hệ thống từ log tập train; đo candidate coverage trên validation và test.
4. Chạy G0, G1, G2 trên mọi incident; đo Visible Log Reduction, Raw Log Traceability và kiểm tra mỗi `log_id` đúng một nhóm (RQ1).
5. Chạy R0–R5 trên validation. Huấn luyện R4, R5 chỉ trên train.
6. Chạy R6 (Kev chưa fine-tune) trên validation. Fine-tune Kev trên train, chọn checkpoint theo MRR validation, fit temperature trên validation.
7. Ghi quy tắc chọn cấu hình trước khi xem test: theo MRR validation, hòa thì chọn cấu hình đơn giản hơn.
8. Khóa toàn bộ model và cấu hình. Chạy **một lần** trên test RCAEval cho mọi phương pháp và ablation A1–A4.
9. Chạy một lần trên Nezha (test ngoài) với cùng cấu hình.
10. Tính khoảng tin cậy bằng bootstrap 1,000 lần, lấy mẫu theo **kịch bản lỗi**, dùng cùng mẫu cho các phương pháp được so (paired).
11. Chia nhỏ kết quả theo hệ thống (ob, ss, tt), loại lỗi (RE2 tài nguyên/mạng, RE3 code) và từng fault type nếu đủ mẫu.
12. Phân tích lỗi: với mỗi incident sai, ghi đáp án đứng hạng mấy, service đứng đầu là gì, đáp án có log hay không.
13. Lưu `manifest.json` cho mỗi lần chạy: dữ liệu, split, cấu hình, checkpoint, commit code, phiên bản thư viện, cấu hình máy.

## 6. Expected Results

Đây là **giả thuyết** để kiểm, không phải kết quả. Không đặt con số mục tiêu trước khi chạy.

| Giả thuyết | Cơ sở | Nếu sai thì sao |
| --- | --- | --- |
| H1. G2 (Drain) giảm số mục nhiều hơn G1 mà vẫn giữ Traceability 100% | Drain được thiết kế để gom log khác nhau ở biến; tầng lá giữ danh sách log ID | Báo đúng như vậy; regex hiện có có thể đã đủ cho RCAEval |
| H2. P xếp hạng tốt hơn R2 (đếm ERROR) | Kev đọc được nội dung template, không chỉ con số | Kết quả quan trọng: model nhỏ không hơn quy tắc đơn giản trên dữ liệu này |
| H3. P tốt hơn R6, nhưng mức chênh có thể nhỏ | Tập train chỉ khoảng 250 incident; README Kev ghi fine-tune với 400 bản ghi từng cho cải thiện trong nhiễu | Báo kèm khoảng tin cậy; không khẳng định fine-tune giúp nếu khoảng tin cậy chứa 0 |
| H4. Mọi phương pháp chỉ dùng log yếu hơn trên lỗi tài nguyên (RE2) so với lỗi code (RE3) | MRCA Bảng 1: log không phản ánh CPU contention và network jam | Nếu ngược lại, cần xem log RE2 có dấu hiệu gián tiếp (timeout ở service khác) |
| H5. A1 (bỏ phần trước lỗi) làm giảm Top-1 | So trước/sau là ý tưởng cốt lõi của Nezha và R3 | Nếu không giảm, demo dán log không cần log trước lỗi |

Kết quả sẽ được báo đầy đủ dù có ủng hộ giả thuyết hay không.
