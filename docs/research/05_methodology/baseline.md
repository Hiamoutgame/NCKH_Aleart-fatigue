# Baseline

Cập nhật 26/10/2026. Mọi phương pháp dưới đây chạy trên **cùng split, cùng danh sách ứng viên, cùng incident**. Chưa có kết quả nào.

**Baseline** là cách làm đơn giản dùng làm mốc so sánh. Nếu phương pháp đề xuất không hơn baseline thì không có lý do dùng nó.

## 1. Baseline cho gom nhóm (RQ1)

| ID | Cách làm | Ghi chú |
| --- | --- | --- |
| G0 | Không gom: mỗi dòng log là một mục | Mốc để tính mức giảm |
| G1 | `(service, template_id)` với `template_id` = MD5 của chuỗi đã qua `normalize_message` | Đã có trong code. Đổi mọi số thành `<N>` nên có thể gộp nhầm `error 404` và `error 500` |
| G2 | `(service, drain_template_id)` | Đề xuất chính. Đã có trong code (26/10/2026): Drain tự viết, một cây mỗi incident, tách header trước. `depth` và `st` đang để mặc định 4 / 0.4, sẽ chỉnh trên tập train |
| G3 (tùy chọn) | G2 + Kev quyết định gộp các cặp nhóm gần ngưỡng | Xem [ai_model_integration.md](../04_proposed_system/ai_model_integration.md) mục 7 |

Khi so G1, G2, G3 cho RQ2, giữ ranker cố định và chỉ đổi cách gom nhóm.

## 2. Baseline cho xếp hạng service (RQ2)

| ID | Cách làm | Học từ dữ liệu? | Cần GPU? |
| --- | --- | --- | --- |
| R0 | Ngẫu nhiên đều | Không | Không |
| R1 | Nhiều log nhất sau thời điểm lỗi | Không | Không |
| R2 | Nhiều log ERROR nhất sau thời điểm lỗi (E1 trong training note) | Không | Không |
| R3 | Tăng nhiều nhất so với trước lỗi: số log "after" / ("before" + 1) | Không | Không |
| R4 | Logistic Regression + feature cơ bản: số log, ERROR, WARN, tỉ lệ severity không rõ (E2) | Có | Không |
| R5 | R4 + feature template và thời gian: số template, template mới sau lỗi, tỉ trọng template lớn nhất, thời điểm xuất hiện (E3–E5) | Có | Không |
| R6 | Kev chưa fine-tune (zero-shot), cùng `state` với P | Không | Có |
| **P** | **Kev fine-tune trên tập train** | Có | Có |

Ghi chú:

- R0 có thể tính chính xác bằng công thức: Top-k kỳ vọng = `min(k, n) / n` với `n` là số ứng viên. Không cần chạy.
- R3 mượn ý tưởng so giai đoạn bình thường với giai đoạn lỗi của Nezha, nhưng chỉ đếm log, không dùng pattern hay trace.
- Feature của R4/R5 theo Phụ lục B của [training note](../../notes/pineline_training_model.md). Không dùng tên service, tên case, loại lỗi hay giờ tuyệt đối làm feature.
- Hòa điểm thì xếp theo `service_id` tăng dần; báo tỉ lệ hòa (R2 dễ hòa khi nhiều service có 0 ERROR).

**So sánh quan trọng nhất:**

- P so với R2: model có hơn quy tắc đếm ERROR không?
- P so với R5: đọc nội dung template có hơn chỉ đọc con số không?
- P so với R6: fine-tune có giúp không, với chỉ khoảng 250 incident train?

## 3. Ablation cho RQ3

**Ablation** là bỏ từng thành phần khỏi phương pháp đầy đủ để xem nó đóng góp bao nhiêu. Giữ nguyên split, ứng viên, model và cách huấn luyện.

| ID | Bỏ gì khỏi `state` của P | Trả lời câu hỏi |
| --- | --- | --- |
| A1 | Phần "before" (chỉ giữ log sau lỗi) | So sánh trước/sau có giúp không? Cũng là điều kiện của demo |
| A2 | Nội dung template (chỉ giữ con số) | Nội dung log có giúp không? |
| A3 | Thông tin severity | ERROR/WARN có giúp không, khi severity được suy ra bằng regex? |
| A4 | Gom bằng G1 thay vì G2 | Drain có giúp xếp hạng không? |

## 4. Kết quả của các bài báo khác

| Bài | Kết quả trên dữ liệu Nezha | Vì sao không đặt cạnh trực tiếp |
| --- | --- | --- |
| Nezha | AS@1 92.86% (OB), 86.67% (TT) (Bảng 3, tr. 561) | Dùng metric + log + trace; báo theo xác suất có điều kiện (theo MRCA tr. 1064) |
| MRCA | PR@1 0.589 (OB), 0.622 (TT) (Bảng 4, tr. 1065) | Dùng log + trace + metric; train/test 60/40 khác split của nhóm |

Chỉ dùng các con số này để định vị trong phần thảo luận, kèm điều kiện khác nhau. Không viết "phương pháp của nhóm tốt hơn Nezha" khi không chạy cùng điều kiện.

## 5. Đối chiếu với tên cũ

| Tài liệu cũ | Tương ứng ở đây |
| --- | --- |
| B0 (proposal V3) | G0 |
| B2 template + frequency | G1/G2 + R1/R2 |
| B3 semantic clustering | Chưa đưa vào; có thể thêm sau G2 |
| E1 / E2 / E3–E5 (training note) | R2 / R4 / R5 |
| P (proposal V3) | P |
