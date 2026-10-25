# Bắt đầu với Kev: hiểu code và chạy thử bằng Colab/Kaggle

Ngày 24/10/2026. Đây là hướng dẫn học và thử kỹ thuật, không phải thay đổi scope V3, chốt model nghiên cứu hoặc báo cáo kết quả RCA.

Notebook đi kèm: [kev_01_colab_kaggle.ipynb](../notebooks/kev_01_colab_kaggle.ipynb).

## 1. Hiểu bài toán bằng một ví dụ

Giả sử một sự cố có ba service. Những tên `S1`, `S2`, `S3` dưới đây chỉ là ví dụ giả định:

```text
S1: không kết nối được database
S2: gọi S1 bị timeout
S3: trả lỗi cho người dùng khi gọi S2
```

Ta đưa thông tin này và danh sách ba service vào Kev, hỏi: “Nên điều tra service nào trước?” Kev trả điểm cho các lựa chọn. Chương trình của nhóm sắp điểm từ cao xuống thấp và giữ liên kết về log đã dùng.

Chưa có lý do khẳng định Kev sẽ chọn đúng trên dữ liệu thật. Một service có nhiều ERROR có thể chỉ đang chịu ảnh hưởng từ service khác.

Ba việc cần phân biệt:

| Việc | Hiểu đơn giản | Có cần GPU? |
| --- | --- | --- |
| Chuẩn bị dữ liệu | Đọc log, kiểm tra nhãn, gom nhóm và giữ nguồn | Bản baseline theo quy tắc có thể làm trên CPU local |
| Inference — dùng model | Cho model có sẵn đọc một đầu vào và trả điểm | Notebook dùng GPU cloud; chưa cập nhật trọng số |
| Fine-tuning — học tiếp | Cho model có sẵn xem ví dụ kèm đáp án để điều chỉnh một phần trọng số | Đây là phần đưa lên GPU cloud |

“System One” trong note cũ là vai trò model chấm điểm. Kev là một ứng viên để thực hiện vai trò đó. Logistic Regression là baseline khác để so sánh.

## 2. Máy yếu thì phân chia công việc thế nào?

```text
Máy cá nhân: raw → audit → chia incident → nhóm log → JSONL gọn
                                      ↓
Colab/Kaggle: tải JSONL + Kev → chạy thử → fine-tune → lưu model
                                      ↓
Máy cá nhân: lưu model, cấu hình, dự đoán và báo cáo
```

Không cần chuyển cả raw corpus lên cloud để học thao tác. Notebook đầu dùng dữ liệu minh họa nhỏ, không đọc hay sửa raw/Parquet của dự án.

**Đề xuất:** học thao tác trên Colab trước; dùng Kaggle như lựa chọn thứ hai tùy GPU và quota tài khoản. Bắt đầu với **Kev-0.8B**, vì model nhỏ phù hợp hơn để kiểm tra môi trường. Đây là lựa chọn cho bài học; model cuối của nghiên cứu chưa chốt.

Nguồn chính thức đã đối chiếu ngày 24/10/2026:

- [Colab FAQ](https://research.google.com/colaboratory/faq.html): GPU và giới hạn sử dụng thay đổi; free runtime có thể chạy tối đa 12 giờ tùy tài nguyên và cách sử dụng, không bảo đảm một phiên đủ 12 giờ.
- [Kaggle GPU usage](https://www.kaggle.com/docs/efficient-gpu-usage): GPU có quota theo tuần; xem số còn lại trong tài khoản/Notebook Settings. Không coi một con số giờ cố định là cam kết cho mọi tài khoản.
- [Kaggle announcement](https://www.kaggle.com/discussions/product-announcements/735239): P100 được thông báo ngừng từ 15/09/2026; hướng dẫn này không yêu cầu chọn P100.
- [Kev README](../../modals/kev/README.md): phần “Runs on” là khả năng chạy model, không tự chứng minh lượng VRAM cần cho training.

Kaggle có thể hiện nhiều GPU. Hai GPU T4 không tự trở thành một GPU có bộ nhớ gấp đôi; lệnh bài học dùng một GPU.

## 3. Vì sao không copy nguyên lệnh Modal?

`skills/kev-finetune/scripts/kev_modal.py` điều khiển máy GPU của dịch vụ Modal. Chạy lệnh đó bên trong Colab vẫn có thể tạo công việc trên Modal và tính phí bên đó.

Để dùng GPU được Colab/Kaggle cấp, notebook gọi trực tiếp:

```text
python -m kev.train ... --device cuda
```

`cuda` ở đây nghĩa là dùng GPU NVIDIA của chính runtime hiện tại.

Một điểm cần kiểm tra trước khi chạy:

- Code training hiện có `--dtype fp32` hoặc `--dtype bf16`, chưa có `--dtype fp16`.
- GPU T4 không có hỗ trợ BF16 native. FP32/BF16 là các cách máy lưu và tính số; BF16 thường tiết kiệm tài nguyên hơn nhưng phụ thuộc GPU và code.
- Bài học dùng **FP32, model 0.8B, đầu vào ngắn, batch 1, tối đa 2 bước cập nhật** để thử kỹ thuật. Chưa có phép đo xác nhận thời gian hoặc VRAM trên tài khoản cloud của bạn.
- Notebook không cài thêm các kernel FLA/fused. Model Qwen3.5 có thể dùng đường PyTorch chậm hơn; bước chạy dự đoán đầu tiên giúp phát hiện vấn đề trước training.

Nếu lỗi xảy ra, đọc cell kiểm tra GPU và lỗi đầu tiên. Đừng đổi thành `fp16` trong lệnh training: parser hiện tại sẽ từ chối.

## 4. Đọc code từ đâu và vì sao?

Lượt đầu chỉ cần hiểu **đầu vào, đầu ra và một lần cập nhật model**. Các file dưới đây nằm trong `modals/kev/` của repo dự án.

### Bước A — README: biết chương trình làm gì

Đọc [README](../../modals/kev/README.md), các phần **Quick Start**, **Fine-Tune on Your Own Data**, **How It Works**.

Mục tiêu: trả lời “Kev nhận gì và trả gì?”. Chưa cần đọc bảng benchmark dài hoặc toàn bộ lịch sử nghiên cứu.

### Bước B — api.py: hiểu dữ liệu mình gửi vào

Đọc [api.py](../../modals/kev/kev/api.py), tìm theo thứ tự:

1. `SystemOneRequest`: một lần gọi cần `state` và `questions`.
2. `Choice`, `Noul`, `Score`: ba dạng câu hỏi.
3. `render`: object/list được chuyển thành văn bản như thế nào.
4. `to_record`: request chuyển thành cấu trúc model đọc ra sao.
5. `to_answers`: điểm của model chuyển lại thành kết quả trả về thế nào.

Ví dụ minh họa:

```json
{
  "state": "S1: database connection refused. S2: requests to S1 time out.",
  "questions": {
    "investigate": {
      "type": "choice",
      "instructions": "Which service should be investigated first?",
      "criteria": {"S1": null, "S2": null}
    }
  }
}
```

`state` là thông tin cho model xem. `questions` là điều mình muốn hỏi. `criteria` là các lựa chọn được phép trả về. JSON này chưa có đáp án vì đây là ví dụ gọi dự đoán.

### Bước C — data.py: hiểu ví dụ có đáp án đi vào training

Trong [data.py](../../modals/kev/kev/data.py), tìm `load_records`, `api_request`, `materialize`.

- `load_records`: đọc JSONL, tức file mỗi dòng là một JSON record.
- `api_request`: lấy phần đầu vào, bỏ nhãn và metadata khỏi request gửi model.
- `materialize`: đưa đầu vào qua `api.to_record`, rồi gắn nhãn riêng để tính mức sai.

Ví dụ khi học, câu hỏi trên có thêm `"label": "S1"`. Nhãn dùng để so với dự đoán, không đưa vào nội dung `state` để model nhìn thấy đáp án.

### Bước D — checkpoint.py: hiểu model có sẵn được nạp thế nào

Trong [checkpoint.py](../../modals/kev/kev/checkpoint.py), tìm `Meta`, `Checkpoint.load`, `warm_start`.

**Checkpoint — bộ file lưu trạng thái model —** của bản LoRA gồm adapter, `head.pt` và thông tin base model. Base model là phần mô hình nền; adapter là phần trọng số bổ sung học tiếp.

- `load`: dùng checkpoint để dự đoán.
- `warm_start`: nạp adapter và phần chấm điểm đã học để tiếp tục training; kiểm tra cấu hình có tương thích không.

Trong bài học, lấy cấu hình từ checkpoint để tránh ghép nhầm model nền hoặc kích thước adapter.

### Bước E — train.py: hiểu model thực sự học ở đâu

Trong [train.py](../../modals/kev/kev/train.py), đọc theo **tên hàm**, chưa đọc tuần tự toàn file:

1. `parse_args`: các cờ trong lệnh có nghĩa gì, cờ nào hợp lệ.
2. `training_requests`: dữ liệu nào được dùng để học; record quá dài có thể bị loại.
3. `main`: tạo model và nạp checkpoint ban đầu.
4. `question_loss`: so điểm dự đoán với nhãn để tính mức sai, gọi là **loss**.
5. Trong `main`, tìm `.backward()`, `opt.step()`, `opt.zero_grad()`.
6. Cuối `main`, tìm `save_pretrained` và `finish_checkpoint` để xem file được lưu ở đâu.

Ba lệnh chính có thể hiểu như sau:

```python
loss.backward()  # tính mỗi trọng số cần điều chỉnh theo hướng nào
opt.step()      # thực hiện điều chỉnh các trọng số được phép học
opt.zero_grad() # xóa phần tính toán cập nhật vừa dùng để sang bước mới
```

Code thực tế chia loss cho số record trong nhóm trước `backward()`. Đó là cách gom đóng góp của nhiều lượt nhỏ trước một lần cập nhật.

**LoRA — học các ma trận bổ sung nhỏ và giữ cố định phần lớn trọng số nền —** giúp giảm lượng trọng số cần cập nhật. Nó vẫn cần bộ nhớ để chứa model nền và dữ liệu trung gian; không bảo đảm model nào cũng vừa GPU miễn phí.

### Bước F — model.py: hiểu cơ chế bên trong sau khi đã thấy đầu ra

Trong [model.py](../../modals/kev/kev/model.py), lần đầu tìm:

- `encode`: chuyển văn bản thành token, tức các đơn vị số model xử lý.
- `DecisionModel.__init__`: nạp model nền, gắn LoRA và phần chấm điểm.
- `PointerHead.forward`: tạo điểm cho các lựa chọn.
- `DecisionModel.forward`, `probs`: tính điểm rồi chuyển sang xác suất.

Đọc phần này sau vì mask, cache và tensor khó hiểu nếu chưa biết một request trông như thế nào. Lượt đầu có thể để phần tối ưu cache/CUDA graphs cho sau.

### Bước G — benchmark.py: hiểu cách so với đáp án

Trong [benchmark.py](../../modals/kev/kev/benchmark.py), tìm `prediction_rows`, `evaluate_records`, `summarize`.

Benchmark này chấm các câu hỏi. Với dữ liệu RCA thật, nhóm vẫn cần bước gom điểm thành ranking và chấm theo incident. Nếu dùng câu hỏi Yes/No cho từng service, đúng nhiều câu “No” chưa có nghĩa tìm đúng service nguyên nhân.

## 5. Thao tác trên Colab

1. Mở [Google Colab](https://colab.research.google.com/).
2. Chọn **File → Upload notebook**, tải notebook đi kèm lên.
3. Chọn **Runtime → Change runtime type → GPU**; tên GPU tùy tài khoản và thời điểm.
4. Chạy từng cell từ trên xuống bằng nút ▶ hoặc Shift+Enter. Lần đầu không dùng Run all để có thời gian đọc đầu ra.
5. Cell đầu báo GPU; cell cài đặt tải code, Python và dependencies nên có thể mất thời gian.
6. Cell dữ liệu tạo sáu mẫu học và ba mẫu kiểm tra **giả định**, có đánh dấu rõ.
7. Cell dự đoán ban đầu cho thấy model hiện chọn service nào.
8. Cell training chạy tối đa hai lần cập nhật. Hoàn thành kỹ thuật khi có `head.pt`, adapter và `training_metrics.json`.
9. Cell dự đoán sau training cho xem lại điểm. Điểm đổi hoặc loss giảm chưa chứng minh RCA tốt hơn.
10. Cell cuối tạo file ZIP và tải về máy. `/content` là nơi làm việc tạm; giữ notebook không đồng nghĩa đã giữ checkpoint.

Notebook chạy Python 3.13 trong môi trường riêng. Kernel notebook có thể dùng phiên bản Python khác; các lệnh model vẫn gọi đúng Python trong môi trường đó.

## 6. Thao tác trên Kaggle

1. Mở [Kaggle Code](https://www.kaggle.com/code), tạo Notebook và dùng chức năng import/upload notebook.
2. Trong **Settings/Session options**, bật **Internet** và chọn GPU đang được cung cấp.
3. Nếu GPU bị khóa, kiểm tra thông báo xác minh tài khoản hoặc quota trong giao diện Kaggle.
4. Chạy các cell như Colab. Notebook tự dùng `/kaggle/working/kev_lab`.
5. Cuối phiên, tải ZIP ở đường dẫn notebook in ra. Nếu lưu phiên bản chạy bằng **Save Version**, kiểm tra file ZIP thực sự xuất hiện trong Output của phiên bản đã chạy.

Không chọn TPU cho bài học này: lệnh đang dùng PyTorch CUDA.

## 7. Bài tập hoàn thành khi hiểu được gì?

- Chỉ ra `state`, `questions`, `criteria`, `label` trong một record.
- Giải thích vì sao lúc dự đoán không cần nhãn.
- Chỉ ra code đọc dữ liệu, code tính mức sai, code cập nhật và code lưu model.
- Nhìn tên GPU và đường dẫn output để biết tính toán đang diễn ra ở đâu.
- Tải được checkpoint và notebook về máy.

## 8. Khi chuyển sang dữ liệu nghiên cứu thật

Thay dữ liệu bài học bằng JSONL sau audit. Chia incident/nhóm nguồn trước khi sinh record. Giữ mapping về group và `log_id` ở metadata/artifact riêng; chặn fault label, path chứa đáp án và ground truth khỏi đầu vào.

Notebook bài học **chưa có** split nghiên cứu độc lập, calibration, Top-k RCA evaluator hoặc kiểm chứng provenance raw. Các mẫu giả định được dựng từ cùng một quy tắc để học thao tác; chúng không tạo thêm incident nghiên cứu độc lập.

Code LoRA hiện lưu checkpoint cuối khi chạy xong. Các cờ resume định kỳ trong `kev.train` hiện dành cho full-weight training. Vì vậy bắt đầu bằng các run ngắn hoàn thành được trong một phiên; khởi tạo từ checkpoint đã lưu là học tiếp, không phải khôi phục chính xác optimizer của run bị ngắt.

## 9. Giới hạn kiểm chứng hướng dẫn

Đã đối chiếu chữ ký hàm/cờ với source local ở commit `2074cc44256200bb37540103fa4572901faa10f3`, kiểm tra cấu trúc notebook, cú pháp các cell/script và dữ liệu minh họa bằng CPU. Chưa chạy tải model, inference hoặc training trên GPU Colab/Kaggle. Thời gian, VRAM và tương thích driver/kernel trên tài khoản của bạn còn cần bước chạy thử.

Tài liệu chuẩn của dự án: [master context](../../NCKH_MASTER_CONTEXT_2026-10-23.md), [implementation status](../docs/implementation_status.md), [protocol V3](../docs/research_protocol_v3.md). Tài liệu chuẩn của Kev: [data format](../../modals/kev/skills/kev-finetune/references/data-format.md) và [model card 0.8B](../../modals/kev/docs/model-cards/kev-0.8b.md).
