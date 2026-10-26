# Data flow

Cập nhật 26/10/2026. Tên file artifact là **đề xuất**, trừ ba bảng chuẩn hóa đã có trong code.

## 1. Luồng offline: từ dữ liệu gốc tới kết quả đánh giá

```text
data/raw/  (RCAEval: cases.parquet + <case>/logs.parquet;  Nezha: fault_list.json + CSV)
   │
   │ (1) Adapter chuẩn hóa                                   [đã có: src/datasets/]
   ▼
data/normalized/<dataset>/  incidents.parquet │ log_events.parquet │ ground_truth.parquet
   │
   │ (2) Audit + chia tập theo kịch bản lỗi                  ← ground truth chỉ dùng để
   ▼                                                            kiểm tra case hợp lệ
incident_audit.parquet   splits.parquet   service_inventory.parquet (từ log tập train)
   │
   │ (3) Chia cửa sổ trước / sau thời điểm lỗi
   ▼
windows.parquet   (log_id → "before" | "after" | "outside")
   │
   │ (4) Gom nhóm: service + template (regex, rồi Drain)
   ▼
groups.parquet   group_members.parquet   (mỗi log_id đúng 1 nhóm)
   │
   │ (5) Dựng cây + tóm tắt incident
   ▼
hierarchy (incident → service → group → log_id)    incident_views.jsonl (state cho Kev / feature cho LogReg)
   │
   │ (6) Xếp hạng: baseline luật │ LogReg │ Kev             ← nhãn chỉ dùng khi TRAIN
   ▼
data/runs/<run_id>/predictions.parquet
   │
   │ (7) Đánh giá                                            ← nhãn chỉ dùng khi CHẤM
   ▼
data/runs/<run_id>/metrics.json   manifest.json
```

## 2. Chi tiết từng bước

| Bước | Đầu vào | Xử lý | Đầu ra | Kiểm tra |
| --- | --- | --- | --- | --- |
| 1 | File raw | Đọc theo từng dataset, đổi timestamp sang UTC, giữ `raw_message`, `source_file`, `source_row_id` | 3 bảng chuẩn | Số dòng khớp raw; không mất incident |
| 2 | 3 bảng chuẩn | Đánh dấu case dùng được và lý do loại; chia train/validation/test theo kịch bản (tên case bỏ hậu tố `_1`, `_2`...); lập danh sách service mỗi hệ thống từ log tập train | Audit, split, inventory | Không kịch bản nào nằm ở hai tập; coverage của đáp án trong inventory được báo riêng |
| 3 | `log_events`, thời điểm lỗi | Log trước thời điểm lỗi là "before", từ thời điểm lỗi trở đi là "after" | Nhãn cửa sổ cho từng log | Log thiếu timestamp vẫn giữ, gắn "outside" |
| 4 | Log của từng incident | Nhóm theo `(incident, service, template)`. Log thiếu service vào nhóm "chưa rõ service" | `groups`, `group_members` | Tổng số thành viên = số log; mỗi `log_id` đúng một nhóm |
| 5 | Nhóm + cửa sổ | Đếm theo nhóm/service/cửa sổ, tìm template mới xuất hiện sau lỗi, viết `state` | Cây + tóm tắt | Không có tên case, nhãn, giờ tuyệt đối trong tóm tắt |
| 6 | Tóm tắt + inventory | Mỗi ranker trả danh sách service có điểm và bằng chứng | `predictions` | Chỉ có service trong inventory; thứ tự hòa cố định |
| 7 | `predictions` + `ground_truth` | Tính metric theo [evaluation_metrics.md](../05_methodology/evaluation_metrics.md) | Metric + manifest | Báo đủ mẫu số và số case bị loại |

**Thời điểm lỗi ở bước 3:** dùng `inject_time` của dataset làm mốc. Giả định là thời điểm người vận hành nhận cảnh báo xấp xỉ thời điểm tiêm lỗi. Đây là giả định cần ghi ở phần threats to validity. `inject_time` chỉ dùng để cắt cửa sổ, không bao giờ đưa vào feature hay `state`.

RCAEval có đủ dữ liệu cho cách chia này: trung vị khoảng 12 phút log trước và 12 phút sau `inject_time`. Có 1/359 case không có log trước thời điểm lỗi.

## 3. Ground truth đi vào ở đâu

| Bước | Có dùng nhãn không | Dùng để làm gì |
| --- | --- | --- |
| 1, 3, 4, 5 | Không | — |
| 2 | Có | Chỉ để đánh dấu case có nhãn hợp lệ và đo coverage. Không dùng để thêm service vào inventory |
| 6 | Chỉ ở tập train | Dạy LogReg và fine-tune Kev; fit temperature trên validation |
| 7 | Có | Chấm điểm |

Kiểm tra tự động nên có: đổi nhãn của một incident thì `state`, feature và danh sách ứng viên của incident đó không được đổi.

## 4. Luồng demo: người dùng dán log

```text
Người dùng: chọn hệ thống "ob", dán 200 dòng log ERROR/WARN
   │
   ▼ POST /rank
Backend: tạo LogEvent tạm (log_id = vị trí dòng), service lấy từ trường trong log nếu có
   │
   ▼ cùng hàm bước (4) và (5)
Nhóm template + state
   │
   ▼ KevRanker → Kev server (/v1/systemone)
Xác suất cho từng service trong inventory của "ob"
   │
   ▼
UI: bảng service + tỉ lệ; bấm vào service → nhóm log → dòng log gốc
```

Khác với luồng offline: demo không có giai đoạn "trước lỗi", trừ khi người dùng dán thêm log trước đó. Vì vậy cần đánh giá thêm một biến thể chỉ dùng log "after" (RQ3), để biết demo kém đi bao nhiêu khi thiếu phần so sánh trước/sau.

## 5. Lưu lại để tái lập

Mỗi lần chạy, `manifest.json` ghi: phiên bản dữ liệu và hash, danh sách incident và lý do loại, split và seed, cấu hình gom nhóm (regex/Drain, `depth`, `st`), ranker và checkpoint, temperature, commit code, phiên bản thư viện, thời gian chạy từng bước.
