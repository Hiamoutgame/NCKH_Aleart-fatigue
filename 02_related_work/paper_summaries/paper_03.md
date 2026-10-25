> **Ghi chú paper lịch sử — bổ sung 23/10/2026.** Nội dung/metadata/claim dưới đây chưa được đối chiếu paper gốc trong lần đồng bộ docs V3. Khi dùng cho Related Work, xác minh source/page và phân biệt paper fact với inference. [Matrix V3](../literature_review_matrix.md) quy định vai trò hiện tại; không lấy scope WARNING/Agent/prediction cũ làm yêu cầu V3.

# Paper 03 Summary

## Citation

- **Tên bài:** MRCA: Metric-level Root Cause Analysis for Microservices via Multi-Modal Data
- **Tác giả:** Yidan Wang, Zhouruixing Zhu, Qiuai Fu, Yuchi Ma, Pinjia He
- **Năm:** 2024
- **Nguồn:** ASE 2024 (39th IEEE/ACM International Conference on Automated Software Engineering), ACM
- **DOI/Link:** https://doi.org/10.1145/3691620.3695485

## Problem

**Root Cause Analysis — RCA** (phân tích nguyên nhân gốc) thủ công trong hệ thống **microservices** lớn tốn thời gian và không khả thi, nên cần tự động hóa. Paper chỉ ra 3 hạn chế của các phương pháp trước:

1. **Chưa khai thác tốt multi-modal data** (dữ liệu đa phương thức — metrics, traces, logs): không một loại dữ liệu nào phủ hết các loại lỗi. Bảng 1 của paper cho thấy log **không** phản ánh **CPU contention** và **network jam**, còn metric **không** phản ánh **code logic error** và **configuration error**. Các phương pháp đa phương thức có sẵn cũng còn hạn chế: Eadro không xử lý được lỗi logic chương trình, Nezha dựa vào **pattern mining** nên tốn thời gian.
2. **Xem nhẹ bước anomaly detection** (phát hiện bất thường): phần lớn phương pháp tách phát hiện và định vị thành hai giai đoạn độc lập, và dùng kỹ thuật quá đơn giản như **N-sigma** dù dữ liệu không theo phân phối chuẩn. Phát hiện sai kéo theo định vị sai. Ngoài ra khi có cảnh báo thì **mọi service** (cả bình thường lẫn bất thường) đều được đưa vào bước định vị, gây nhiễu và tốn tài nguyên.
3. **Root cause còn coarse-grained** (thô — chỉ ở mức service): SRE vẫn phải tự tìm loại bất thường. Các phương pháp **metric-level** có sẵn thì phải dựng **causal graph** (đồ thị nhân quả) cho từng metric nên chậm.

## Method

MRCA là phương pháp RCA ở **metric level** (mức metric — chỉ ra cặp service–metric gây lỗi, từ đó suy ra loại bất thường), dùng dữ liệu đa phương thức và **reinforcement learning** (học tăng cường) để dừng phân tích nhân quả sớm. Pipeline gồm 3 giai đoạn:

1. **Feature extraction** (trích đặc trưng) từ log và trace:
   - **Traces:** lấy **latency** (độ trễ) của các lời gọi, coi là đặc trưng của service **được gọi**; lấy trung bình theo cửa sổ 5 giây.
   - **Logs:** parse bằng **Drain** để lấy **log template**, rồi đếm **tần suất** từng template theo thời gian.
   - Mỗi service có `m` đặc trưng template và 1 đặc trưng latency, gộp theo timestamp thành một **chuỗi thời gian** thống nhất.
2. **Anomaly detection** bằng **VAE — Variational Autoencoder** (bộ tự mã hóa biến phân — học nén rồi dựng lại dữ liệu):
   - **Huấn luyện offline** chỉ trên dữ liệu **fault-free** (bình thường), nên VAE dựng lại tốt dữ liệu bình thường.
   - **Chạy online:** tính **reconstruction probability** (xác suất dựng lại). Dữ liệu bất thường khó dựng lại nên xác suất giảm mạnh. Xác suất của service nào thấp hơn ngưỡng `ε` thì phát cảnh báo.
   - **Xếp hạng:** xác suất càng thấp thì anomaly score càng cao. Service có xác suất cao hơn ngưỡng `ξ` bị loại. Kết quả là danh sách `List_initial` gồm các service nghi ngờ.
   - Có thêm **attention mechanism** (cơ chế chú ý) đặt vào log, để chú ý các template chưa từng xuất hiện lúc bình thường hoặc đột ngột giảm tần suất.
3. **Root cause localization** (định vị nguyên nhân gốc) trên dữ liệu **metric**:
   - **Granger causality test** (kiểm định nhân quả Granger — X "gây ra" Y nếu giá trị quá khứ của X giúp dự đoán Y tốt hơn): xét từng cặp service–metric trong cửa sổ `T_causal` sau khi phát hiện bất thường, mở rộng đồ thị bắt đầu từ các node xếp hạng cao nhất trong `List_initial`.
   - **Q-learning** quyết định mở rộng node nào tiếp theo hoặc **dừng**. **State** là số node, cạnh, tầng và service của đồ thị hiện tại. **Reward** là `α · r_com + β · r_rca`, trong đó `r_com` phạt độ phức tạp của đồ thị và `r_rca` thưởng theo độ chính xác RCA.
   - **Pruning** (cắt tỉa): nguyên nhân phải xảy ra trước kết quả, nên loại các node có node cha, chỉ giữ node gốc và node mồ côi.
4. **Output:** danh sách `List_final` gồm các cặp (service, loại bất thường), chuyển từ kết quả mức service sang mức metric.

## Dataset

Paper **không tự thu thập dữ liệu** mà dùng dataset công khai của **Nezha**, thu trên 2 hệ thống:

- **OnlineBoutique (OB):** 56 lỗi, 3,907,981 log, 80,934 trace.
- **TrainTicket (TT):** 45 lỗi (20 resource, 25 code), 1,352,335 log, 51,604 trace.

Ba loại lỗi được tiêm: **CPU contention**, **network congestion** (nghẽn mạng) và **code defect** (lỗi code). Tỷ lệ train/test là 60%/40%.

> **Lưu ý:** Bảng 2 của paper ghi OB có 42 resource fault và 24 code fault, tổng là 66 chứ không phải 56. Paper Nezha gốc ghi 14 code defect (42 + 14 = 56), nên con số 24 nhiều khả năng là lỗi đánh máy.

## Evaluation

Paper đánh giá theo 4 câu hỏi:

- **RQ1:** anomaly detection được lợi bao nhiêu từ dữ liệu đa phương thức.
- **RQ2:** hiệu quả RCA ở **metric level** và **service level**.
- **RQ3:** đóng góp của từng nguồn dữ liệu và của module cắt tỉa (ablation).
- **RQ4:** module cắt tỉa có giảm thời gian RCA không.

**Metric:**

- **Precision, Recall, F1** cho anomaly detection (bài toán phân loại nhị phân).
- **PR@K** (Precision@K): trong top-K kết quả có root cause thật không.
- **MRR** (Mean Reciprocal Rank): trung bình nghịch đảo thứ hạng của đáp án đúng đầu tiên.

**Baseline:**

- Dựa trên metrics: **CloudRanger**, **MicroCause**, **ε-Diagnosis**.
- Dựa trên traces + reinforcement learning: **TraceDiag**.
- Đa phương thức: **Nezha**.
- Ở metric level chỉ so với MicroCause, ε-Diagnosis và Nezha.

**Ablation:** **MRCA w/o L** (bỏ log), **w/o T** (bỏ latency của trace), **w/o A** (bỏ attention), **w/ A in T** (chuyển attention từ log sang trace).

**Cài đặt:** cửa sổ trượt dài 20, bước trượt 5; VAE huấn luyện 1000 epoch, batch size 64, learning rate 10⁻³. Paper không nêu giá trị cụ thể của `ε` và `ξ`, chỉ nói ngưỡng chọn theo reconstruction error trên tập train.

## Results

- **Anomaly detection:** F1 = 0.893, Precision = 0.875, Recall = 0.913. Baseline tốt nhất là TraceDiag (F1 = 0.571); Nezha chỉ đạt F1 = 0.400.
- **Service level:** PR@1 là 0.589 (OB) và 0.622 (TT); PR@3 là 0.804 và 0.822; PR@5 là 0.875 và 0.889; MRR là 0.691 và 0.735. Trung bình PR@3 = 81.3%.
- **Metric level** (chỉ tính trên **lỗi tài nguyên**, vì lỗi code thường không hiện trong metric): PR@1 là 0.738 (OB) và 0.700 (TT); trung bình PR@1 = 71.9%, PR@3 = 85.4%, PR@5 = 90.3%.
- **Ablation:** bản đầy đủ tốt nhất. Bỏ log giảm mạnh nhất (PR@1 ở OB từ 0.589 xuống 0.482), bỏ trace giảm ít nhất (0.554). Paper giải thích là phần lớn lỗi được tiêm liên quan đến code, vốn lộ ra ở tần suất log chứ không ở latency. Đặt attention vào trace còn kém hơn bỏ hẳn trace.
- **Độ nhạy:** tỷ lệ `α/β` tăng thì cả độ chính xác và thời gian đều giảm (dừng sớm hơn). Giá trị cân bằng tốt nhất là 0.05.
- **Thời gian:** paper kết luận MRCA định vị một lỗi nhanh hơn các baseline và chênh lệch giữa hai hệ thống nhỏ. Số liệu cụ thể nằm trong Hình 6, bản tóm tắt này chưa đọc được giá trị từ hình.

> **Lưu ý khi trích dẫn:**
>
> - **Kết quả của Nezha thấp hơn nhiều so với paper gốc** (PR@1 service level 0.321–0.378 so với AS@1 khoảng 90%). MRCA giải thích là họ tính trên toàn bộ mẫu, còn Nezha báo cáo theo xác suất có điều kiện. Không nên đặt hai bộ số này cạnh nhau như cùng một phép đo.
> - **Các baseline trừ Nezha do nhóm tác giả tự cài lại** vì không có code công khai; paper tự nêu đây là mối đe dọa nội tại.
> - **PR@1 trung bình ở service level** paper ghi 60.1%, trong khi trung bình của 0.589 và 0.622 là 60.6%.
> - **Các khoảng cải thiện** (F1 tăng 56.4%–115.7%, top-3 hơn 25.0%–117.5%) khớp khi so với TraceDiag và CloudRanger. Nếu tính cả Nezha (F1 = 0.400, PR@3 ở OB = 0.357) thì cận trên phải cao hơn. Nên trích số tuyệt đối thay vì các khoảng này.

## Limitations

- Chỉ phát hiện được lỗi **để lại dấu vết trong dữ liệu quan sát**; không xử lý được tấn công từ bên ngoài hay gián đoạn nội bộ không sinh dữ liệu.
- **Lỗi code chỉ định vị được ở mức service**, không tới mức metric, vì lỗi code thường không làm metric thay đổi rõ.
- **Service ít hoạt động** cung cấp ít dữ liệu bình thường nên khó phát hiện; chiếm khoảng 50% ca thất bại.
- Khoảng 40% ca thất bại là **lỗi code gây network timeout chỉ lộ ra trong call chain**; MRCA bỏ sót vì không khai thác **service dependency** (quan hệ phụ thuộc giữa các service) cho lỗi code.
- Loại bất thường được suy ra từ **một metric đại diện**, trong khi lỗi phức tạp có thể lộ ra ở nhiều metric, hoặc một metric bất thường có thể do nhiều nguyên nhân.
- Chỉ đánh giá trên **một dataset mô phỏng** (của Nezha) với số lỗi tiêm hạn chế.
- **Không bàn về concept drift** *(nhận xét của nhóm, không phải của paper)*: VAE học "bình thường" một lần ở giai đoạn offline; paper không đề cập huấn luyện lại khi hệ thống deploy bản mới hoặc traffic thay đổi.
- **Mất execution context** *(nhận xét của nhóm)*: gộp log thành tần suất theo cửa sổ thời gian thì không còn biết log nào thuộc request nào — đúng điểm Nezha đã phê bình ở PDiagnose.
- **Granger không phải nhân quả thật** *(nhận xét của nhóm)*: nó chỉ kiểm tra X xảy ra trước và giúp dự đoán Y.
- MRCA không phải bài toán giảm cảnh báo, nên paper **không đánh giá** các metric của alert aggregation như **ARR**, **RCPR**, **Pairwise F1** và **Group Purity**.

## Relevance to our topic

- **Liên quan cao về domain:** cùng nghiên cứu **microservices**, **observability** và **RCA**, cùng dùng hai hệ thống OnlineBoutique và TrainTicket.
- **Dẫn chứng trực tiếp cho giới hạn của log:** Bảng 1 cho thấy log chỉ có tín hiệu **Error/Warning** với code logic error, network interruption và configuration error, còn **CPU contention** và **network jam** thì log không có gì. Đề tài tập trung vào log mức WARNING nên cần nêu rõ đây là giới hạn phạm vi: RCPR trên các lỗi tài nguyên có thể thấp vì root-cause signal không nằm trong log.
- **Tương đồng về ý tưởng lọc nhiễu:** MRCA loại các service bình thường trước khi phân tích để giảm nhiễu và chi phí (Motivation 3). Đây là cùng tinh thần với việc giảm số alert trước khi SRE xử lý, nhưng MRCA lọc **service** còn đề tài gom **alert**.
- **Tương đồng về xử lý log:** MRCA dùng **Drain + tần suất template theo service**, **không cần trace ID/span ID trong log** như Nezha. Cách này khả thi hơn trên bảng log RCAEval (`timestamp`, `container_name`, `message`). Tuy nhiên MRCA còn cần latency từ trace và metric, nên cần kiểm tra RCAEval có đủ hai nguồn này trước khi coi là tái hiện được.
- **Tín hiệu thời gian để phân biệt gốc với lan truyền:** bước Granger + pruning dựa trên nguyên tắc "nguyên nhân xảy ra trước kết quả", liên quan trực tiếp tới việc tách alert của root cause khỏi **cascading alerts**.
- **Khác nhau về mục tiêu và output:** MRCA trả về cặp service–metric; đề tài trả về alert group và phải giữ **root-cause signal**.
- **Gợi ý cho thiết kế** *(suy luận của nhóm)*: ablation cho thấy log đóng góp nhiều nhất trên dataset này, là cơ sở để lập luận rằng pipeline dựa trên log có giá trị, miễn là thừa nhận giới hạn với lỗi tài nguyên.

## Possible improvement

- Dùng **xếp hạng mức bất thường theo service** (kiểu reconstruction probability) làm tín hiệu ưu tiên khi gom nhóm: alert từ service có anomaly score cao không được gộp mất.
- Thêm **thứ tự thời gian** giữa các alert (ý tưởng của Granger + pruning) vào Arm temporal-spatial để nhận diện alert gốc và alert lan truyền.
- Khai thác **service dependency** cho lỗi code, là điểm MRCA thừa nhận còn thiếu (40% ca thất bại).
- Xử lý **service ít hoạt động**: với nhóm này nên dựa vào ngữ nghĩa của log thay vì thống kê tần suất.
- Xét cơ chế **cập nhật baseline định kỳ** để tránh concept drift, thay vì huấn luyện offline một lần.
- Đánh giá **trade-off** giữa **ARR** và **RCPR** tách riêng theo loại lỗi (resource và code), vì Bảng 1 của MRCA cho thấy hai nhóm này lộ ra ở các nguồn dữ liệu khác nhau.
