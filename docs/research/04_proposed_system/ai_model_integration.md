# AI model integration

Cập nhật 26/10/2026. Thông tin về Kev lấy từ `third_party/kev/README.md` (bản vendored, commit `2074cc4`). Cách dùng Kev cho bài toán này là **đề xuất**, chưa chạy thử.

## 1. Tóm tắt

| Câu hỏi | Trả lời |
| --- | --- |
| Model dùng là gì? | **Kev**: model quyết định nhỏ (decision model). LoRA + pointer head trên nền Qwen3.5. Bắt đầu với Kev-0.8B, chuyển sang Kev-4B nếu đủ GPU |
| Vì sao chọn? | Trả **xác suất cho từng phương án** trong một câu hỏi chọn một, nên ra thẳng bảng xếp hạng service; chỉ chọn trong danh sách cho trước; fine-tune được trên dữ liệu nhỏ; chạy local |
| Lấy từ đâu? | GitHub `jaredpalmer/kev` (vendored tại `third_party/kev/`), trọng số trên Hugging Face `jaredpalmer/kev-0.8b`, `jaredpalmer/kev-4b` (tag `v1.0`). License Apache-2.0 |
| Input? | Text: bản tóm tắt nhóm log của một incident + câu hỏi chọn một với các phương án là service ứng viên |
| Output? | Xác suất đã hiệu chỉnh cho từng service → sắp xếp thành bảng xếp hạng |
| Tích hợp thế nào? | Kev chạy thành server HTTP; class `KevRanker` trong `src/integrations/kev/` gửi request và đổi kết quả thành `RankedService`. Dùng chung cho batch job đánh giá và API demo |
| Có baseline không? | Có: ngẫu nhiên, nhiều log nhất, nhiều ERROR nhất, Logistic Regression, Kev chưa fine-tune. Xem [baseline.md](../05_methodology/baseline.md) |

## 2. Kev là gì, nói đơn giản

Kev đọc một đoạn văn bản (gọi là `state`) và trả lời các câu hỏi về nó. Nó không viết ra câu trả lời mà **chấm điểm từng phương án có sẵn**, rồi đổi điểm thành xác suất. Ba loại câu hỏi:

| Loại | Nghĩa | Dùng trong dự án |
| --- | --- | --- |
| `choice` | Chọn một trong nhiều phương án | **Chính:** service nào là nguyên nhân? |
| `noul` | Có / không | Phụ, tùy chọn: hai nhóm log này có nên gộp không? |
| `score` | Cho điểm theo mức | Không dùng |

Thuật ngữ:
- **LoRA**: cách fine-tune chỉ học thêm vài ma trận nhỏ, giữ nguyên phần lớn trọng số của model nền. Nhờ vậy fine-tune rẻ hơn.
- **Pointer head**: phần nhỏ phía trên model nền, chấm điểm từng phương án.
- **Calibrated probability** (xác suất đã hiệu chỉnh): mỗi checkpoint có một hệ số `temperature` để xác suất gần với tần suất đúng thật. Ví dụ, khi model nói 0.7 thì khoảng 70% số lần nó đúng. Điều này quan trọng vì demo sẽ hiện tỉ lệ cho người dùng xem.

## 3. Vì sao Kev hợp với bài toán

1. **Đầu ra khớp với bài toán.** Một câu `choice` với các phương án là service ứng viên trả về xác suất cho từng service. Sắp xếp theo xác suất là ra bảng xếp hạng.
2. **Không bịa service.** Kev chỉ chọn trong các phương án được đưa vào, nên mọi service trong kết quả đều thuộc danh sách quan sát được. Điều này khớp với quy tắc của dự án.
3. **Fine-tune được trên dữ liệu riêng.** README của Kev có lệnh `kev.train --init_from` để học tiếp từ checkpoint có sẵn.
4. **Chạy local, mã nguồn mở.** Không gửi log ra API bên ngoài, tái lập được.

So với Logistic Regression: LogReg chỉ đọc các con số (số log, số ERROR...). Kev đọc được cả nội dung template, ví dụ "connection refused to redis". Thí nghiệm sẽ cho biết điều đó có giúp ích không (RQ2, RQ3).

## 4. Input: cách xây `state`

`state` là bản tóm tắt nhóm log của **một incident**, tạo từ cây phân cấp. Ví dụ minh họa (dữ liệu giả định):

```text
System: ob. Window: 12 minutes after alert, compared with 12 minutes before.
Service cartservice: 1,240 logs after (before: 310). ERROR 412, WARN 0.
  New templates after alert:
    [412] "Can't access cart storage. StackExchange.Redis.RedisTimeoutException <*>"
  Most frequent templates:
    [620] "GetCartAsync called with userId=<*>"
Service frontend: 5,930 logs after (before: 5,700). ERROR 1,930.
  New templates after alert:
    [1930] "request error ... rpc error: code = Unavailable <*>"
...
```

Câu hỏi:

```json
{
  "type": "choice",
  "instructions": "Which service is the most likely root cause of this incident?",
  "criteria": { "adservice": null, "cartservice": null, "frontend": null, "...": null }
}
```

**Quy tắc khi xây `state`:**

- Không chứa tên case, `raw_label`, `fault_type`, giờ tuyệt đối, đường dẫn file. Tên case RCAEval chứa luôn đáp án (ví dụ `re2ob_currencyservice_delay_2`).
- Danh sách phương án lấy từ service quan sát được của hệ thống trong tập train, sắp xếp theo thứ tự cố định (theo tên), không theo đáp án.
- Giới hạn độ dài: Kev bản ≤ 9B được kiểm chứng tới 8,192 token, và chủ yếu được train trên đoạn ngắn hơn nhiều. Mục tiêu ban đầu là dưới 4,096 token, giữ vài template mỗi service. Con số cụ thể sẽ chốt sau khi đo trên dữ liệu.
- Hàm tạo `state` dùng chung cho train, đánh giá và demo.

## 5. Output và cách đổi thành bảng xếp hạng

Kev trả `probabilities` cho từng phương án. `KevRanker` làm như sau:

1. Sắp service theo xác suất giảm dần. Nếu bằng nhau, xếp theo `service_id` để kết quả cố định.
2. Gắn bằng chứng: với mỗi service, chọn tối đa 3 nhóm theo quy tắc cố định (nhóm mới xuất hiện sau lỗi, nhiều ERROR, nhiều dòng). Kev **không** chọn bằng chứng; bằng chứng do quy tắc chọn và có ghi tên quy tắc.
3. Trả danh sách `RankedService(service_id, score, rank, supporting_group_ids, supporting_log_ids, method="kev-<version>")`.

**Ảnh hưởng của thứ tự phương án:** README của Kev ghi rằng đổi thứ tự phương án có thể đổi câu trả lời. Kev server có endpoint `/v1/systemone/permute` chạy một câu `choice` với nhiều thứ tự khác nhau. Đề xuất: lấy trung bình xác suất qua vài thứ tự, và báo mức chênh lệch.

## 6. Fine-tune

| Bước | Cách làm |
| --- | --- |
| Dữ liệu | Mỗi incident trong tập train thành một dòng JSONL: `state` + câu `choice` + `label` = service đáp án |
| Lệnh | `kev.train --data train.jsonl --init_from jaredpalmer/kev-0.8b --lr 2e-5 ...` (README khuyên lr ≤ 2e-5 khi học tiếp) |
| Hiệu chỉnh xác suất | Fit `temperature` trên tập validation, không dùng test |
| Chọn checkpoint | Theo MRR trên validation |
| Test | Chạy một lần sau khi đã khóa model |

**Rủi ro dữ liệu ít:** RCAEval có 359 case. Chia 70/15/15 theo kịch bản thì tập train còn khoảng 250 incident. README của Kev ghi rằng trên một workload mẫu, fine-tune với 400 bản ghi cho mức cải thiện nằm trong nhiễu. Cách xử lý:

- Luôn báo kết quả Kev chưa fine-tune bên cạnh Kev đã fine-tune.
- Có thể tạo nhiều `state` cho một incident (ví dụ các khoảng thời gian con, hoặc các tập con nhóm ERROR/WARN giống đoạn log người dùng dán). Các bản này phải nằm cùng tập với incident gốc.
- Báo khoảng tin cậy bootstrap theo incident.

## 7. Phần phụ, tùy chọn: Kev hỗ trợ gom nhóm

Với các cặp nhóm Drain có độ giống gần ngưỡng `st`, hỏi Kev một câu `noul`: *"Do these two log templates describe the same kind of event?"*. Nếu xác suất cao thì gộp.

Hạn chế: dataset không có nhãn nhóm, nên không đo trực tiếp được độ đúng. Chỉ báo ảnh hưởng tới mức giảm số mục và tới Top-k, hoặc tự gán nhãn một mẫu nhỏ có protocol. Làm phần này sau khi phần xếp hạng đã có kết quả.

## 8. Phần cứng

| Model | Inference | Ghi chú |
| --- | --- | --- |
| Kev-0.8B | GPU 4 GB, mọi Mac Apple Silicon (README) | Dùng để phát triển và thử pipeline; Colab T4 dùng FP32 vì T4 không hỗ trợ BF16 (xem `docs/notes/kev_bat_dau_colab_kaggle.md`) |
| Kev-4B | L40S / H100, hoặc Mac 32 GB (README) | Dùng nếu đủ tài nguyên. Mọi so sánh trong một bảng kết quả phải dùng cùng một size |

Chưa đo thời gian và VRAM khi chạy trên dữ liệu của dự án.

## 9. Trích dẫn và license

Bọc Kev sau interface của dự án là thiết kế phần mềm, không thay đổi nguồn gốc model. Khi viết báo cáo phải:

- Trích repo Kev và model nền Qwen3.5.
- Giữ file `third_party/kev/LICENSE` (Apache-2.0); ghi mọi file Kev bị sửa vào `third_party/kev/UPSTREAM.md`.
- Mô tả đúng: "Kev-0.8B fine-tuned on ...", không gọi là model của nhóm.

Phần đóng góp của nhóm nằm ở cách tổ chức log, cách xây `state`, dữ liệu fine-tune và protocol đánh giá.
