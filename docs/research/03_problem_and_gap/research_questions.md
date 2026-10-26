# Research Questions

Cập nhật 26/10/2026. Bốn câu hỏi, mỗi câu gắn với một gap trong [research_gap.md](research_gap.md) và một cách đo trong [evaluation_metrics.md](../05_methodology/evaluation_metrics.md).

## Main Research Question

> Can evidence-preserving hierarchical log organization reduce information overload while maintaining accurate service-level root cause localization in microservice systems?

Tạm dịch: tổ chức log phân cấp có giữ bằng chứng gốc có giảm được lượng thông tin phải đọc, mà vẫn định vị đúng service gây lỗi không?

## Sub Research Questions

**RQ1. How much can template-based grouping reduce the number of items an engineer must read, while keeping every raw log traceable?**

Gom log theo template giảm được bao nhiêu mục cần đọc, trong khi mọi dòng log vẫn mở lại được?

- So sánh: log thô, nhóm theo regex hiện có, nhóm theo Drain.
- Đo: Visible Log Reduction ở mức nhóm, Raw Log Traceability, số nhóm mỗi service.
- Gap: G2.

**RQ2. How accurately can a fine-tuned small decision model rank root-cause services from grouped log summaries, compared with rule-based and statistical baselines?**

Kev sau khi fine-tune xếp hạng service gây lỗi chính xác đến đâu so với cách đếm ERROR và Logistic Regression?

- So sánh: các baseline trong [baseline.md](../05_methodology/baseline.md), Kev chưa fine-tune, Kev đã fine-tune.
- Đo: Top-1, Top-3, MRR, candidate coverage, conditional và end-to-end; độ hiệu chỉnh xác suất (Brier, ECE).
- Gap: G1, G4.

**RQ3. Which parts of the organized evidence contribute to ranking accuracy: template groups, severity, or the contrast between the before-fault and after-fault windows?**

Phần nào của bằng chứng giúp xếp hạng đúng hơn: nhóm template, mức severity, hay so sánh log trước và sau lỗi?

- Cách làm: ablation, tức là giữ nguyên ranker và split, mỗi lần bỏ một thành phần khỏi input.
- Đo: thay đổi Top-1 / MRR so với bản đầy đủ, kèm khoảng tin cậy bootstrap theo incident.
- Gap: G1, G2.

**RQ4. How does ranking accuracy vary across fault types and systems, and does it hold on a dataset not used for training or tuning?**

Độ chính xác thay đổi thế nào theo loại lỗi và hệ thống, và có giữ được trên dataset không dùng để huấn luyện hay chỉnh tham số không?

- Chia kết quả: lỗi tài nguyên/mạng (RE2) và lỗi code (RE3); ba hệ thống ob, ss, tt.
- Dataset ngoài: Nezha (OnlineBoutique + TrainTicket), sau khi sửa adapter, chỉ dùng để đánh giá cuối.
- Gap: G1, G3.

## Ngoài phạm vi

- **Time to Locate** (thời gian người dùng tìm ra service đúng): chỉ đo nếu có user study với protocol rõ ràng. Mức giảm số mục không tự chứng minh người dùng nhanh hơn.
- **Độ đúng của quan hệ nhân quả** giữa các nhóm: dataset không có nhãn quan hệ.
