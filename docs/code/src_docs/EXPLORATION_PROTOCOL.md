# EXPLORATION PROTOCOL — Đọc một dataset và một incident

> **V3, cập nhật 23/10/2026.** [Master context](../../../NCKH_MASTER_CONTEXT_2026-10-23.md) quy định scope; [dataset audit](../../status/dataset_audit.md) phân biệt artifact cũ với footer mới. Profiler/sample không chứng minh eligibility hoặc nhãn causal/log-level.

## 0. Nguyên tắc
- Mục tiêu: trả lời được "dataset này có gì?" và "incident này có nội dung gì?" bằng bằng chứng tái lập được.
- Không kết luận nhân quả từ tần suất.
- Mọi kết luận nên ghi rõ FACT (đọc trực tiếp) hay INFERENCE (suy luận).

## 1. Bốn tiêu chí bắt buộc
### 1.1 shape
- Lấy df.shape, ghi rõ (số dòng, số cột).
- Ghi rõ một dòng đại diện cho cái gì (một log line, một alert, một case, một window).

### 1.2 columns
- Liệt kê tên cột, dtype, số non-null, số null, số unique, một giá trị ví dụ.
- Chỉ ra cột nào map sang canonical: timestamp, service, message, severity, root_cause.
- Nếu thiếu cột (ví dụ severity), ghi rõ là dataset không có, không được bịa.

### 1.3 head(10)
- In 10 dòng đầu tiên.
- Dùng để nhận diện format timestamp, ngôn ngữ log, mẫu message, mức nhiễu.

### 1.4 value_counts()
- Đếm tần suất cho service và message; thêm severity nếu có.
- In top N kèm số lượng và phần trăm.
- Với dataset lớn, lấy mẫu hoặc lọc theo cửa sổ thời gian trước khi đếm.

## 2. Checklist đọc một incident
Cần trả lời được các câu hỏi sau:
1. Định danh incident: id, hệ thống (system), suite, độ lặp (repetition).
2. Dịch vụ bị ảnh hưởng và fault type (nếu có nhãn).
3. Cửa sổ thời gian: time_start, inject_time, time_end.
4. Incident có log không? Bao nhiêu dòng log?
5. Những service nào xuất hiện trong log? Service nào nhiều nhất?
6. Những message nào xuất hiện nhiều? Có mẫu WARN/ERROR nào không?
7. Dấu hiệu bất thường so với baseline (trước inject_time) là gì?
8. Nhãn root cause (nếu có) và bằng chứng nào trong log ủng hộ nó?

## 3. Cảnh báo diễn giải (BẮT BUỘC)
- message xuất hiện nhiều KHÔNG nhất thiết là lỗi: có thể là log INFO lặp, health check, retry thành công.
- service có nhiều log KHÔNG nhất thiết là service gây ra sự cố: có thể do service verbose, hoặc là nạn nhân của lỗi lan truyền.
- Tần suất = độ phổ biến, không phải mức nghiêm trọng.
- Các tín hiệu thời gian/dependency/baseline hỗ trợ xếp hạng nghi vấn; chúng chưa chứng minh causation. Đối chiếu service labels để chấm ranking, không dùng labels tạo feature hoặc kết luận log nào là nguyên nhân.

## 4. Output chuẩn của một lần explore
- profile.json: shape, columns, head, value_counts.
- report.md: nhận xét, nghi vấn, việc cần kiểm chứng tiếp.
- Ghi lại cảnh báo diễn giải ở mục 3 trong report.

## 5. Gate cho V3 trước thực nghiệm

- Ghi snapshot/source path, sampling scope/caps, timestamp units/timezone/missingness và raw provenance. Raw mặc định ở `data/raw/`.
- Tách grouping pool khỏi RCA-eligible pool; ground truth service không cung cấp log-group/noise/causal-edge labels.
- Kiểm tra label source/multiplicity, service aliases và inventory coverage; không loại case thiếu candidate đáp án âm thầm.
- Giữ `log_id`/raw strings/source record references; kiểm tra duplicate IDs, incident overlap và repeated-run groups trước split.
- Không feed raw_label/fault_type/inject annotation hoặc heuristic root_cause từ exploration vào model.
- [Research protocol](../../research/research_protocol_v3.md) mô tả output/gate đề xuất; profile.json/report.md ở mục 4 là format mong muốn, không phải mọi CLI hiện tự xuất được hai file này.
