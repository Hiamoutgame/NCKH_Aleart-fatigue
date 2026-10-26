> **Đối chiếu V3 ngày 23/10/2026:** đây là thiết kế MVP để học/triển khai, chưa phải thuật toán chính thức được duyệt hoặc code đã có. [Master context](../../NCKH_MASTER_CONTEXT_2026-10-23.md), [implementation status](../status/implementation_status.md) và [protocol V3](../research/research_protocol_v3.md) bổ sung nguồn hiện hành.
>
> Tỷ lệ 70/15/15, seed/config/model và experiments bên dưới là **đề xuất trong tài liệu này**, chưa phải split run đã chốt; audit plan 20/10 có đề xuất 60/20/20 và validation cũ có 50/50. Các số coverage/annotation ghi trong note 19/10 là báo cáo lịch sử, chưa xác minh nội dung lại; footer Parquet chỉ xác nhận số rows. Default raw path CP1 không còn tồn tại; raw thật ở `data/raw/`. Nezha export/iteration và provenance (LEMMA đã bỏ khỏi dự án 26/10/2026) cần xử lý trước training. Không dùng nguyên Incident/raw_label hoặc heuristic root_cause trong exploration làm feature/GT log-level.

# Hướng dẫn hiểu và xây dựng pipeline training System One

> **Trạng thái:** tài liệu hướng dẫn thiết kế, cập nhật ngày 19/10/2026. Các phần System One bên dưới là công việc dự kiến; ví dụ code và tên lệnh chưa phải chương trình hoàn chỉnh có thể chạy ngay.
>
> Cách giải thích theo [OUTPUT.md](../../OUTPUT.md): nói vấn đề bằng tiếng Việt trước, giải thích thuật ngữ khi sử dụng, có ví dụ và cách kiểm tra. Tài liệu này không ghi nhận kết quả training mới.

## Cách đọc tài liệu

Nếu bạn muốn hiểu “từ một đống log và code làm sao có model”, hãy đọc mục 1–9 theo thứ tự. Mỗi bước sẽ nói rõ **nhận gì → làm gì → tạo ra gì → kiểm tra thế nào**.

Mục 10–12 nói về cách chia công việc và những điều còn chưa chắc chắn. Phụ lục A–D giữ các quy tắc kỹ thuật cần tra khi bắt đầu triển khai.

Các ví dụ dùng sự cố `A` và ba service `frontend`, `payment`, `cart`. **Tên và số liệu ví dụ là giả định**, không phải kết quả đo trên dataset.

## 1. Chúng ta đang muốn giải quyết vấn đề gì?

Giả sử một hệ thống bán hàng gặp lỗi thanh toán. Trong vài phút, `frontend`, `payment` và `cart` tạo hàng nghìn dòng log. Người điều tra cần biết:

1. Những dòng nào có thể xem chung thành một nhóm?
2. Service nào nên được kiểm tra trước?
3. Có thể mở lại những log nào để kiểm tra nghi vấn đó?

Hệ thống dự kiến làm hai việc nối tiếp:

```text
Hàng nghìn log
    ↓
Tổ chức log theo service và mẫu thông điệp
    ↓
Tính các con số mô tả từng service
    ↓
System One chấm điểm từng service
    ↓
Xếp hạng service + đưa ra nhóm log để kiểm tra
```

**Trong thiết kế MVP này, System One là tên dự kiến cho model xếp hạng service.** Phần gom log và chọn log để xem được viết bằng các quy tắc riêng trong phiên bản đầu.

Một vài từ sẽ được dùng xuyên suốt:

| Thuật ngữ | Hiểu đơn giản trong dự án này |
|---|---|
| **Incident** | Một sự cố hoặc một lần thí nghiệm gây lỗi, có mã riêng và khoảng thời gian quan sát |
| **Service** | Một thành phần của ứng dụng, chẳng hạn chức năng thanh toán `payment` |
| **Root cause** | Nguyên nhân gốc; ở bài toán này là service được dataset ghi nhận là nguyên nhân |
| **RCA — Root Cause Analysis** | Phân tích nguyên nhân gốc của sự cố |
| **Candidate** | Service có trong danh sách để model chấm điểm |
| **Pipeline** | Chuỗi bước xử lý, trong đó đầu ra bước trước được dùng cho bước sau |

MVP — phiên bản nhỏ đầu tiên đủ để kiểm chứng ý tưởng — dùng log trong **toàn bộ cửa sổ sự cố đã xác minh**. Đây là phân tích sau sự cố, chưa phải dự đoán lỗi trước khi nó xảy ra.

Mục tiêu nghiên cứu rộng hơn vẫn là tổ chức log để dễ điều tra. Model xếp hạng tốt và người dùng phải đọc ít mục hơn là hai kết quả cần đo riêng.

## 2. Code, model và training khác nhau như thế nào?

Bạn sẽ viết code để đọc file, đếm log, tạo bảng dữ liệu, gọi thuật toán học và lưu kết quả.

Model đầu tiên được đề xuất dùng **Logistic Regression** — thuật toán học trọng số cho các con số đầu vào để tạo một điểm đánh giá. Trong dự án, điểm này giúp sắp xếp thứ tự kiểm tra các service.

Ví dụ rút gọn chỉ có ba con số đầu vào:

```text
Điểm service = w1 × số log
             + w2 × số ERROR
             + w3 × số mẫu log
             + b
```

`w1`, `w2`, `w3` là trọng số: chúng quyết định mỗi con số ảnh hưởng đến điểm bao nhiêu. `b` là số cộng thêm, thường gọi là độ lệch. Trong triển khai thực tế, các con số sẽ được đổi về thang đo phù hợp trước khi tính điểm.

**Training — huấn luyện — là quá trình dùng các sự cố có đáp án để tìm những trọng số này.** Mình không tự đặt luật “nhiều ERROR nhất chắc chắn là nguyên nhân”. Model phải học từ nhiều ví dụ, và sau đó được kiểm tra trên những sự cố chưa dùng để học.

| Thời điểm | Có gì? |
|---|---|
| Viết code | Chương trình xử lý dữ liệu và điều khiển việc học |
| Khởi tạo model | Cấu trúc thuật toán và cấu hình cách học |
| Gọi `fit()` | Thư viện bắt đầu tìm các trọng số từ dữ liệu train |
| Lưu `model.joblib` | File chứa model đã học và bước chuẩn hóa số liệu đi kèm |
| Dùng model mới lưu | Đọc log của sự cố khác, tạo cùng loại đầu vào và tính điểm |

**Inference — suy luận — là bước dùng model đã học trên dữ liệu mới.** Bước này không cần đáp án thật và không gọi lại `fit()`.

## 3. Nhìn toàn bộ đường đi trước khi đi vào từng bước

```text
BƯỚC 1. Đọc và kiểm tra dữ liệu
Raw → ba bảng thống nhất → báo cáo sự cố nào dùng được

BƯỚC 2. Chia các sự cố thành ba tập riêng
Train: để học | Validation: để chọn cấu hình | Test: để chấm cuối

BƯỚC 3. Tổ chức log và tạo bảng số liệu cho từng tập
Log → nhóm theo service/mẫu → một dòng số liệu cho mỗi service

BƯỚC 4. Huấn luyện
Chỉ dữ liệu train → học cách chuẩn hóa số liệu + học trọng số model

BƯỚC 5. Chọn và kiểm tra model
Validation → chọn cấu hình → cố định model → chấm trên test

BƯỚC 6. Lưu và sử dụng
Model đã lưu + sự cố mới → xếp hạng service + log để kiểm tra
```

Ba tập dùng **cùng cách tạo số liệu**, nhưng không được gộp lại để học. Đây là ranh giới quan trọng nhất của pipeline.

## 4. Bước 1 — Biến dữ liệu gốc thành dữ liệu có thể tin tưởng

### Vấn đề cần giải quyết

Ba dataset có cách lưu khác nhau. Tên service, đơn vị thời gian và vị trí nhãn có thể khác. Nếu log của ngày này bị gán cho sự cố ngày khác thì model vẫn có thể chạy, nhưng nó học từ ví dụ sai.

**Adapter — bộ chuyển đổi dữ liệu —** là code đọc từng định dạng nguồn và đưa về cùng cấu trúc. Repo đã có adapter trong `src/`; phần này cần được kiểm tra và tái sử dụng.

### Đầu vào và đầu ra

| Nhận vào | Xử lý | Tạo ra |
|---|---|---|
| File gốc hiện ở `data/raw/` (default của code) | Đọc đúng nguồn, đổi thời gian đã xác minh về UTC, giữ tên service và nguồn bản ghi | Ba bảng Parquet theo cấu trúc chung |
| Ba bảng vừa tạo | Kiểm tra sự cố, log, nhãn và thời gian có khớp không | `incident_audit.parquet` và báo cáo dễ đọc |

**Parquet** là định dạng lưu bảng dữ liệu. Có thể hình dung nó lưu các hàng/cột giống một bảng tính, nhưng phù hợp để chương trình xử lý dữ liệu lớn.

| Bảng | Trả lời câu hỏi gì? | Ví dụ |
|---|---|---|
| `incidents.parquet` | Sự cố nào, quan sát từ lúc nào đến lúc nào? | Sự cố A, từ 10:00 đến 10:05 |
| `log_events.parquet` | Trong khoảng đó có những log nào, của service nào? | 10:01, payment, `ERROR connection timeout` |
| `ground_truth.parquet` | Dataset ghi nhận service nào là nguyên nhân? | Sự cố A → payment |

**Ground truth — nhãn đáp án đã được xác minh —** dùng để dạy và chấm model. Khi đưa vào thực tế, model không được nhận bảng đáp án này làm đầu vào dự đoán.

### Cách kiểm tra trước khi đi tiếp

Với sự cố A, cần trả lời được:

- Log có đúng nguồn và nằm trong khoảng quan sát không?
- Tên service có xác định được từ dữ liệu không?
- Nhãn `payment` có nguồn chứng minh không?
- `payment` có xuất hiện trong danh sách service quan sát được không?
- Có thể lần từ mỗi log đã xử lý về đúng file và bản ghi gốc không?

**Audit — kiểm tra chất lượng dữ liệu —** là bước thực hiện các câu hỏi này cho từng sự cố, rồi ghi kết quả và lý do loại.

Danh sách candidate trong MVP lấy từ service thực sự xuất hiện trong log hợp lệ. Nếu ground truth nói `database` là nguyên nhân nhưng log không có `database`, phải ghi nhận thiếu candidate. Không được chèn `database` vào danh sách chỉ vì đã xem đáp án.

Log thiếu service hoặc thời gian vẫn được giữ để tra lại nguồn. Nó không được tự điền giá trị giả cho đủ điều kiện học.

### Ba dataset được dùng thế nào?

- **RCAEval:** nguồn chính để học và chấm model đầu tiên.
- **Nezha:** giữ riêng để thử model đã chốt trên nguồn khác, khi dữ liệu đã được kiểm chứng.

Không cần hoàn tất mọi sửa chữa ở Nezha mới bắt đầu phần RCAEval hợp lệ. Các số liệu kiểm tra từ phiên trước nằm ở mục 12; cần chạy lại audit khi triển khai.

## 5. Bước 2 — Chia dữ liệu để model không được xem trước bài kiểm tra

### Vì sao cần chia?

Nếu model được học từ sự cố A rồi cũng được chấm trên A, điểm cao có thể chỉ cho thấy model nhớ dữ liệu đã học.

**Data leakage — rò rỉ thông tin —** xảy ra khi thông tin đáng lẽ chỉ dùng để chấm lại lọt vào quá trình học hoặc chọn model.

Ví dụ trong dự án: nếu `payment` của sự cố A nằm trong train còn `frontend` của cùng A nằm trong test, hai tập vẫn mang thông tin của cùng một sự cố. Vì vậy, phải chia theo **incident**, không chia ngẫu nhiên từng dòng log hoặc từng dòng service.

| Tập | Vai trò | Được dùng để cập nhật trọng số không? |
|---|---|---|
| Train | Những sự cố để model học | Có |
| Validation | Những sự cố để so sánh các cấu hình model | Không trong thiết kế dùng ba tập riêng |
| Test | Những sự cố giữ lại để chấm model sau khi đã chọn xong | Không |

Mục tiêu ban đầu là **70% / 15% / 15%**. Tỷ lệ thực tế phụ thuộc số sự cố hợp lệ và nhóm dữ liệu dùng chung; không tách một nhóm chỉ để đạt đúng tỷ lệ.

**Seed — số khởi tạo cho việc chia ngẫu nhiên —** dự kiến là `42`, giúp tái tạo cách chia khi dữ liệu, code và cấu hình giữ nguyên.

### Cần giữ những gì ở cùng một tập?

```text
Sự cố A → tất cả service và log của A cùng nằm trong train
Sự cố B → tất cả service và log của B cùng nằm trong validation
Sự cố C → tất cả service và log của C cùng nằm trong test
```

Nếu A và B dùng chung bản ghi nguồn hoặc thực chất là hai bản sao của cùng lần chạy, chúng cũng phải đi cùng nhau. Các nhóm liên kết theo chuỗi cũng được giữ chung: A chia sẻ với B, B chia sẻ với C thì cả ba cùng một tập.

**Kiểm tra:** không có incident hoặc nhóm bản ghi nguồn dùng chung giữa các tập. Lưu cách chia vào `splits.parquet`, không chia lại tùy ý mỗi khi kết quả chưa tốt.

### Những bước nào chỉ được học trên train?

Đếm số log trong một incident là phép tính cố định; nó không học quy luật từ các incident khác.

Nhưng **StandardScaler — bước đổi các cột số về thang đo phù hợp —** phải tính trung bình và độ lệch chuẩn từ train. Sau đó giữ nguyên các giá trị đó khi xử lý validation/test. Nếu tính từ cả test, model đã gián tiếp thấy thông tin của bài kiểm tra.

Quy tắc chung: mọi bước phải học thông số từ dữ liệu đều chỉ học trên train. Các chi tiết chia nhóm và phương án khi validation quá ít nằm ở Phụ lục A.

## 6. Bước 3 — Từ log thành một dòng số liệu cho mỗi service

### 6.1. Gom những dòng có cùng mẫu

Xét hai log giả định của `payment`:

```text
ERROR request 101 failed: connection timeout
ERROR request 102 failed: connection timeout
```

Hai dòng khác mã request nhưng có cùng nội dung chính. Có thể đưa về:

```text
ERROR request <ID> failed: connection timeout
```

**Template — mẫu thông điệp log —** là phần cấu trúc chung này. **Grouping — gom nhóm —** đặt các dòng cùng mẫu vào chung nhóm trong một service và incident.

```text
Sự cố A
└── payment
    └── Nhóm: ERROR request <ID> failed: connection timeout
        ├── log_001 → dòng gốc có request 101
        └── log_002 → dòng gốc có request 102
```

Hai log gốc vẫn còn. Tài liệu hiển thị có thể trình bày một nhóm trước, rồi cho mở các dòng bên trong.

| File tạo ra | Chứa gì? |
|---|---|
| `groups.parquet` | Mỗi nhóm gồm service nào, mẫu gì, bao nhiêu log, xuất hiện từ lúc nào đến lúc nào |
| `group_members.parquet` | Danh sách log thuộc từng nhóm, để mở lại đúng dòng gốc |

**Kiểm tra:** mọi log trong phạm vi gom nhóm có thể lần ngược về nguồn. Quy tắc bỏ mã request phải phân biệt với mã lỗi: không được vô tình xóa mất thông tin cần điều tra. Quy tắc này có version — số phiên bản — để biết lần chạy dùng cách gom nào.

### 6.2. Tạo feature: những con số model sẽ đọc

**Feature — đặc trưng đầu vào —** là một con số mô tả service. Model đầu tiên đọc các con số này, chưa đọc và hiểu câu log như một mô hình ngôn ngữ.

Ví dụ giả định sau khi xử lý toàn bộ log trong cửa sổ 300 giây của A, `payment` có:

| Feature | Ý nghĩa | Giá trị ví dụ |
|---|---|---:|
| `log_count` | Có bao nhiêu log? | 180 |
| `error_count` | Có bao nhiêu dòng được xác định là ERROR? | 45 |
| `error_ratio` | ERROR chiếm bao nhiêu trong log của service? | 45 / 180 = 0,25 |
| `unique_template_count` | Có bao nhiêu mẫu log khác nhau? | 8 |
| `log_rate` | Trung bình bao nhiêu log mỗi giây trong cửa sổ? | 180 / 300 = 0,6 |

Đây là thống kê minh họa cho cả cửa sổ, không phải phép đếm từ hai dòng log ở ví dụ trên.

Số ERROR cao chưa chắc chỉ đúng nguyên nhân: `frontend` có thể sinh nhiều lỗi vì `payment` gặp trục trặc. Vì vậy, cần đo xem model học từ các feature có tốt hơn cách chỉ đếm ERROR không.

Ba nhóm feature dự kiến:

- **Basic — thống kê cơ bản:** số log, số/tỷ lệ ERROR và WARN, tỷ lệ chưa biết mức log, tỷ trọng log của service.
- **Template — thống kê mẫu log:** số mẫu và tỷ trọng mẫu xuất hiện nhiều nhất.
- **Temporal — thống kê theo thời gian:** log xuất hiện sớm hay muộn, kéo dài bao lâu, lượng log thay đổi giữa đầu và cuối cửa sổ.

Công thức cụ thể ở Phụ lục B. Chưa xác minh được khoảng hoạt động bình thường thì không tạo feature “tăng bất thường so với bình thường”. Nửa đầu cửa sổ không mặc nhiên là thời gian hệ thống khỏe mạnh.

### 6.3. Ghép nhãn để tạo dữ liệu học

Ví dụ giả định:

| Incident | Service | log_count | error_count | unique_template_count | Nhãn `y` |
|---|---|---:|---:|---:|---:|
| A | frontend | 500 | 20 | 12 | 0 |
| A | payment | 180 | 45 | 8 | 1 |
| A | cart | 300 | 5 | 10 | 0 |

Tách bảng thành ba phần:

```text
X = các cột số liệu đã chọn cho experiment
    Ví dụ: log_count, error_count, unique_template_count

y = nhãn để học
    1: service thuộc tập nguyên nhân đã xác minh
    0: service không thuộc tập nguyên nhân được ghi nhận

metadata = thông tin đi kèm để tra cứu
    incident_id, service_id, nguồn file, liên kết nhóm log
```

`metadata` không đưa vào model. Tên file, fault type — loại lỗi được tiêm trong thí nghiệm — hoặc ID có thể chứa đáp án và làm model học nhầm cách đoán từ tên.

Nhãn `0` không đồng nghĩa service không có lỗi. `frontend` có thể bị ảnh hưởng bởi lỗi của `payment`. Với một sự cố nhiều nguyên nhân, có thể có nhiều service mang nhãn `1`.

**Đầu ra:** `service_features.parquet` chứa feature, `service_labels.parquet` chứa nhãn và `splits.parquet` chỉ rõ dòng thuộc sự cố ở tập nào.

**Kiểm tra:** ghép đúng theo incident/service, không nhân bản dòng khi có nhiều nhãn. Đổi đáp án thật không được làm thay đổi feature hoặc danh sách candidate của cùng incident đầu vào.

## 7. Bước 4 — Tạo model và thực sự huấn luyện nó

### 7.1. Những gì cần có trước khi gọi `fit()`

- `X_train`: bảng feature của các service thuộc những sự cố được phép học.
- `y_train`: nhãn tương ứng, có cả 0 và 1.
- `X_valid`: feature của các sự cố để chọn cấu hình; nhãn validation dùng để chấm riêng.
- Danh sách cột và thứ tự cột cố định cho mọi tập.

Mỗi sự cố dùng để training phải có nhãn đầy đủ đã xác minh, mọi service nguyên nhân nằm trong candidate và có ít nhất một candidate không phải nguyên nhân. Thiếu điều kiện thì báo lý do, không biến sự cố thành một nhóm toàn nhãn 0.

Baseline này có thể chạy trên CPU. Thời gian đọc/chuẩn hóa hàng triệu log và thời gian fit bảng feature cần đo riêng; chưa có số đo để cam kết thời lượng.

### 7.2. Đoạn code quan trọng nhất làm gì?

Đây là ví dụ giải thích, **chưa phải script hoàn chỉnh của repo**. Các biến `X_train`, `y_train`, `X_valid` phải được tạo bởi những bước trước.

```python
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression

pipeline = Pipeline([
    ("scaler", StandardScaler()),
    ("model", LogisticRegression(
        C=1.0,
        solver="lbfgs",
        class_weight=None,
        max_iter=2000,
        random_state=42,
    )),
])

pipeline.fit(X_train, y_train)
valid_scores = pipeline.decision_function(X_valid)
```

Đọc theo thứ tự thực thi:

1. `Pipeline(...)` nối bước đổi thang đo và model thành một khối, để khi sử dụng lại vẫn xử lý giống lúc học.
2. `StandardScaler()` tạo bộ đổi thang đo. Nó chưa học gì cho đến khi `fit()` được gọi.
3. `LogisticRegression(...)` tạo model và cấu hình cách học.
4. `fit(X_train, y_train)` học các thông số đổi thang đo từ train, rồi học trọng số model từ dữ liệu đã đổi thang đo và nhãn.
5. `decision_function(X_valid)` dùng thông số đã học để trả điểm cho từng dòng validation. Lệnh này không học lại.

**Loss — mức sai cần giảm —** cho biết dự đoán đang lệch nhãn đến đâu. Bên trong `fit()`, thư viện lặp quá trình:

```text
Dùng trọng số hiện tại để tính điểm
    ↓
So với nhãn, tính loss
    ↓
Điều chỉnh trọng số
    ↓
Lặp cho đến khi đạt điều kiện dừng
```

Thư viện lo phần tính toán này; mình không cần tự viết vòng cập nhật trọng số cho Logistic Regression.

### 7.3. Các cấu hình trong code có nghĩa gì?

| Cấu hình | Giải thích trong lần học này |
|---|---|
| `C` | Điều chỉnh mức hạn chế trọng số lớn; `C` nhỏ nghĩa là hạn chế mạnh hơn |
| `solver="lbfgs"` | Chọn phương pháp tính toán để tìm trọng số; giữ cố định trong baseline |
| `class_weight` | Quy định mức coi trọng nhãn 0/1; thử `balanced` để xét trường hợp hai nhãn xuất hiện chênh lệch |
| `max_iter=2000` | Cho phép tối đa 2.000 vòng tối ưu; không có nghĩa chắc chắn phải chạy đủ |
| `random_state=42` | Ghi cấu hình số ngẫu nhiên khi thuật toán dùng đến; với solver này không thay thế seed của bước chia dữ liệu |

**Regularization — hạn chế trọng số quá lớn —** là cơ chế liên quan tới `C`, nhằm tránh model bám quá sát các ví dụ train. Giá trị nào phù hợp phải được chọn bằng validation.

Nếu thư viện báo chưa hội tụ — chưa đạt điều kiện dừng tối ưu trong số vòng cho phép — cần kiểm tra dữ liệu và thang đo, rồi mới quyết định điều chỉnh giới hạn. Tạo được file model chưa đủ để coi training hợp lệ.

## 8. Bước 5 — Chọn model và chấm kết quả

### 8.1. Chọn cấu hình bằng validation

**Tuning — thử và chọn cấu hình —** dự kiến bắt đầu nhỏ:

```text
C:             0.1, 1.0, 10.0
class_weight:  None hoặc balanced
→ tổng cộng 6 tổ hợp cho một bộ feature
```

Với mỗi tổ hợp: tạo pipeline mới → học trên train → tính điểm trên validation → xếp service trong từng incident → chấm ranking.

**Ranking — xếp hạng —** nghĩa là sắp service theo điểm giảm dần. Không so điểm của service ở sự cố A với service ở sự cố B để tạo một bảng xếp hạng chung.

Ví dụ điểm giả định của sự cố mới:

```text
payment  →  1.8 → hạng 1
frontend →  0.4 → hạng 2
cart     → -0.7 → hạng 3
```

Điểm `1.8` không phải xác suất 180%. Đây là điểm từ `decision_function`; số lớn hơn được xếp trước. Không cần đặt ngưỡng 0.5 cho bài toán này.

### 8.2. Chấm đúng đơn vị: sự cố

| Chỉ số | Câu hỏi nó trả lời |
|---|---|
| Top-1 | Service đứng đầu có thuộc nguyên nhân thật không? |
| Top-3 | Ba service đứng đầu có chứa ít nhất một nguyên nhân thật không? |
| MRR — Mean Reciprocal Rank | Nguyên nhân thật thường xuất hiện sớm đến đâu trong danh sách? Hạng 1 nhận 1 điểm, hạng 2 nhận 1/2, hạng 4 nhận 1/4 |
| Recall@K | Nếu có nhiều nguyên nhân, K vị trí đầu tìm được bao nhiêu phần trong số đó? |

Không chọn model bằng tỷ lệ đúng từng dòng service. Nếu có rất nhiều nhãn 0, model luôn trả 0 có thể đạt tỷ lệ đúng cao mà không tìm được service nguyên nhân nào.

### 8.3. Không giấu những sự cố thiếu candidate đúng

**Candidate coverage — mức bao phủ ứng viên —** cho biết bao nhiêu sự cố có đáp án thật xuất hiện trong danh sách candidate.

Ví dụ giả định:

```text
100 sự cố có nguồn/cửa sổ và nhãn hợp lệ để đánh giá
 80 sự cố có ít nhất một service nguyên nhân trong candidate
 60 sự cố được xếp đúng Top-1
```

Cần báo đủ:

- Coverage: `80/100 = 80%`.
- **Conditional Top-1 — độ đúng trên phần có candidate đúng:** `60/80 = 75%`.
- **End-to-end success — tỷ lệ thành công trên toàn bộ phạm vi đánh giá:** `60/100 = 60%`.

Tài liệu báo 75% mà không nói mẫu số sẽ khiến người đọc hiểu quá cao về khả năng hệ thống. Công thức nhiều nguyên nhân và trường hợp không có dữ liệu nằm ở Phụ lục C.

### 8.4. Khi nào mới dùng test?

Sau khi chọn cấu hình trên validation, cố định model, feature và cách chấm rồi mới xem kết quả test. Không sửa model dựa vào test rồi vẫn gọi đó là kết quả độc lập.

Với cách chia ba tập riêng, baseline đầu lưu model đã fit trên train của cấu hình thắng; không tự train lại bằng train + validation. Phương án dữ liệu ít được mô tả riêng ở Phụ lục A.

### 8.5. Làm sao biết grouping có ích?

**Baseline — cách làm đơn giản để đối chiếu —** đầu tiên chỉ xếp service theo số ERROR. Sau đó so các thí nghiệm dùng cùng sự cố, candidate và cách chia:

| Mã | Cách làm | Điều muốn kiểm tra |
|---|---|---|
| E1 | Xếp theo ERROR count | Một quy tắc đơn giản làm được đến đâu? |
| E2 | Logistic Regression + Basic | Model học có tốt hơn quy tắc đếm ERROR không? |
| E3 | Logistic Regression + Basic + Template | Thêm thống kê từ nhóm log có giúp hơn E2 không? |
| E4 | Logistic Regression + Basic + Temporal | Thông tin thời gian có giúp hơn E2 không? |
| E5 | Logistic Regression + cả ba bộ feature | Kết hợp có giúp hơn từng bộ riêng không? |

Làm E1–E3 trước. So E3 với E2 là **ablation — so sánh khi thêm/bớt một thành phần** — để kiểm tra đóng góp của thống kê template. Không thêm cả template và thời gian cùng lúc rồi kết luận cải thiện chỉ nhờ grouping.

Đo thêm số nhóm hiển thị và khả năng mở lại log gốc. Ví dụ giả định 1.000 log được biểu diễn bằng 100 nhóm thì giảm 90% số mục ở cấp hiển thị nhóm. Nó chưa chứng minh người dùng điều tra nhanh hơn 90%.

## 9. Bước 6 — Lưu model và sử dụng trên sự cố mới

### 9.1. Một lần training cần lưu những gì?

**Artifact — sản phẩm file sinh ra sau một lần chạy —** giúp sử dụng lại hoặc kiểm tra kết quả. Không chỉ lưu riêng trọng số rồi quên cách tạo đầu vào.

```text
runs/<run_id>/
├── model.joblib              # Bộ đổi thang đo + model đã học
├── feature_schema.json      # Tên, thứ tự, kiểu và cách tính feature
├── training_config.json     # Bộ feature, tham số và cách chọn model
├── metrics.json             # Điểm đánh giá kèm số lượng sự cố được chấm
├── predictions.parquet      # Điểm và thứ hạng của từng service
└── manifest.json            # Nguồn dữ liệu, phiên bản code/thư viện, split đã dùng
```

**Schema — cấu trúc dữ liệu được thống nhất —** trong `feature_schema.json` giúp tránh đưa nhầm cột. Ví dụ model từng học `[log_count, error_count]` mà nhận `[error_count, log_count]` thì ý nghĩa số liệu bị đảo.

**Manifest — bản kê thông tin của lần chạy —** giúp biết model nào được tạo từ dữ liệu và cấu hình nào. Mỗi lần thử có mã riêng; không ghi đè model cũ.

### 9.2. Đường đi khi dùng model

```text
Log sự cố mới + thời gian bắt đầu/kết thúc quan sát
    ↓
Chuẩn hóa và tạo candidate như lúc training
    ↓
Gom log và tạo đúng các feature đã chốt
    ↓
Load model.joblib
    ↓
Tính điểm và xếp hạng service
    ↓
Gắn các nhóm/log nên kiểm tra
```

Không cần `ground_truth.parquet` cho luồng này. Nếu không có candidate thì trả trạng thái thiếu dữ liệu. Nếu feature sai cấu trúc hoặc phiên bản không tương thích thì báo lỗi rõ, không lặng lẽ điền số 0.

### 9.3. Vì sao một log được đưa ra để xem?

**Evidence — log hỗ trợ điều tra —** là những bản ghi được chọn để người dùng kiểm tra nghi vấn. Model chỉ nhìn số liệu tổng hợp nên không tự xác nhận log nào là nguyên nhân.

MVP dùng **heuristic — quy tắc chọn đơn giản do mình quy định**:

1. Trong mỗi service, ưu tiên nhóm có nhiều ERROR, tiếp đến WARN, rồi số log; dùng thời gian xuất hiện sớm và ID để xử lý hòa.
2. Lấy tối đa 3 nhóm. Mỗi nhóm lấy tối đa 3 log: ERROR đầu tiên nếu có, log đầu và log cuối; bỏ ID trùng.
3. Ghi lý do chọn và giữ liên kết để mở toàn bộ log của nhóm.

Nếu không biết mức severity — mức độ log như ERROR/WARN — thì chọn nhóm đại diện theo số lượng và nói rõ điều đó.

Hai câu hỏi giải thích khác nhau:

- **Vì sao model chấm service cao?** Xem feature nào góp nhiều vào điểm.
- **Người điều tra nên xem log nào?** Xem các log được quy tắc evidence chọn ra.

Log được chọn chưa phải log nguyên nhân đã xác nhận. Ví dụ output giả định:

```json
{
  "service_id": "payment",
  "score": 1.8,
  "score_type": "decision_function",
  "rank": 1,
  "supporting_group_ids": ["group_01"],
  "supporting_log_ids": ["log_001", "log_002"],
  "evidence_method": "severity_volume_representatives_v1",
  "evidence_status": "investigation_support"
}
```

**Kiểm tra:** nạp lại model phải cho cùng điểm với cùng input; mọi log trả về phải mở lại đúng nguồn; luồng dự đoán không cần nhãn thật và không học lại.

## 10. Code dự kiến được chia thành những phần nào?

Phần đọc dataset tiếp tục tái sử dụng trong `explore_datasets`. Phần System One dự kiến:

```text
Resource/system_one/
├── configs/                     # Cấu hình các lần thử
├── src/system_one/
│   ├── audit.py                 # Kiểm tra log, sự cố và nhãn có khớp
│   ├── dataset.py               # Candidate, nhãn, chia tập và bản kê dữ liệu
│   ├── grouping.py              # Gom log và giữ liên kết về nguồn
│   ├── features.py              # Tính các cột số liệu cho mỗi service
│   ├── train.py                 # Tạo model, fit và chọn cấu hình
│   ├── predict.py               # Nạp model, tính điểm, xếp hạng
│   ├── evidence.py              # Chọn nhóm và log để xem
│   └── evaluate.py              # Chấm kết quả và xuất báo cáo
├── tests/                       # Kiểm thử hành vi cần bảo đảm
├── artifacts/<dataset_version>/ # Dữ liệu đã xử lý và split
├── runs/<run_id>/                # Model và kết quả từng lần training
└── README.md                    # Hướng dẫn chạy sau khi đã triển khai
```

Tên file mô tả trách nhiệm dự kiến, chưa phải cam kết các file đã tồn tại.

Đường gọi chính khi triển khai sẽ là:

```text
Adapter hiện có
    → audit.py → dataset.py → grouping.py → features.py
    → train.py → evaluate.py

Khi sử dụng model:
    predict.py → cùng cách grouping/features → model → evidence.py
```

`predict.py` dùng lại cách tạo feature lúc train để tránh hai luồng tính khác nhau. Các chức năng dự kiến là `audit`, `split`, `group`, `prepare`, `train`, `evaluate`, `predict`; chưa phải các command có thể copy chạy ngay.

## 11. Nên triển khai theo thứ tự nào?

| Mốc | Làm gì? | Khi nào coi là hoàn thành? |
|---|---|---|
| M1 — Kiểm chứng dữ liệu | Tái sử dụng adapter, đọc đủ dữ liệu, kiểm tra từng incident và xác định split | Biết case nào dùng được, case nào bị loại và vì sao |
| M2 — Tạo dữ liệu học | Gom log, tạo feature/nhãn, lưu split | Có X/y tái tạo được, log tra về nguồn được, các tập độc lập |
| M3 — Model đầu tiên | Chạy E1–E3, chọn model, chấm test, lưu và nạp lại model | Có ranking, evidence và báo cáo theo cùng quy trình |
| M4 — Thực nghiệm nghiên cứu | Thêm feature thời gian, thử hệ thống/nguồn khác khi đủ dữ liệu | Có so sánh để trả lời thành phần nào giúp và giới hạn ở đâu |

**Mốc kế tiếp được đề xuất là M1–M2: kiểm chứng dữ liệu trước khi train.** M3–M4 được mô tả để thấy toàn bộ đường đi.

Các bước kiểm thử cần có khi bắt đầu viết code:

- Log đúng nguồn, đúng thời gian; các lỗi thiếu dữ liệu không bị che bằng giá trị giả.
- Nhãn không làm thay đổi candidate hoặc feature; candidate thiếu đáp án được báo riêng.
- Mỗi log đã gom truy ngược được nguồn, ID ổn định khi đọc theo các đợt khác nhau.
- Những sự cố dùng chung nguồn không nằm ở nhiều tập.
- Thay dữ liệu test không làm đổi scaler hoặc model đã học khi split cố định.
- Điểm/ranking không đổi sau lưu và nạp model; thứ tự khi bằng điểm có quy tắc cố định.
- Top-K/MRR/Recall@K đúng trên ví dụ nhỏ có thể tính tay, kể cả candidate rỗng và nhiều nguyên nhân.
- Train không đủ điều kiện thì báo lý do; không tạo kết quả giả.

## 12. Điều đã biết, điều đang đề xuất và điều chưa kiểm chứng

| Loại thông tin | Nội dung |
|---|---|
| **FACT — đã quan sát** | Repo có adapter, canonical schema và các file Parquet; phiên trước đã kiểm tra một số giới hạn dữ liệu local |
| **PROPOSAL — thiết kế dự kiến** | Dùng RCAEval chính, Logistic Regression, các bộ feature và protocol đánh giá trong tài liệu |
| **INFERENCE — suy luận cần kiểm tra** | Feature về template/thời gian có thể bổ sung thông tin mà số ERROR không thể hiện |
| **UNVERIFIED — chưa kiểm chứng** | Bao nhiêu incident đạt chuẩn sau audit đầy đủ; model chính xác đến đâu; grouping có giúp điều tra hiệu quả hơn không |

Số liệu dưới đây là **snapshot từ phiên kiểm tra trước**, không phải kết quả vừa đo lại khi sửa cách trình bày:

| Dataset | Đã ghi nhận trong phiên trước | Cần xác minh/xử lý khi triển khai |
|---|---|---|
| RCAEval | 359 file log raw; normalized có log của 30 case | Mở rộng xử lý đầy đủ và audit từng case; chưa coi 359 là số mẫu train hợp lệ |
| Nezha | 101 bản ghi tiêm lỗi; adapter tạo 21 incident; normalized có log cho 1 incident | Sửa vòng lặp và đọc log cho mọi incident; kiểm tra lỗi đồng thời |

Giới hạn cần nhớ: service không phát log có thể không vào candidate; nhãn có thể khác cấp service; model giỏi trên hệ thống đã thấy chưa chắc giỏi trên hệ thống mới. Chưa có kết quả accuracy hoặc runtime thực nghiệm trong tài liệu.

---

## Phụ lục A — Quy tắc dữ liệu và chia tập khi triển khai

Phần này dùng để tra cứu sau khi đã hiểu luồng chính.

### A1. Lưu dữ liệu và nguồn gốc

- Giữ nguyên raw. Kết quả mới có version riêng; không ghi đè dữ liệu đang đối chiếu.
- Giữ tên cột hiện có như `timestamp_utc`, `canonical_target`, `raw_record_ref` để dùng lại adapter.
- Mỗi log có ID ổn định từ nguồn/vị trí bản ghi. Log thuộc nhiều cửa sổ vẫn giữ cùng định danh nguồn; cặp `(incident_id, log_id)` chỉ việc log thuộc incident nào.
- Giữ payload — nội dung bản ghi nguồn đầy đủ — hoặc tham chiếu khôi phục chính xác. Nội dung đã parse — tách thành trường dễ xử lý — lưu riêng.
- Đọc theo batch — từng đợt vừa bộ nhớ — thay vì nạp toàn bộ log vào RAM. Chế độ sample xử lý mẫu để kiểm tra; chế độ full xử lý đầy đủ và phải được ghi rõ trong bản kê.
- Cửa sổ dùng `start <= timestamp <= end`, với `start < end`. Chưa xác minh timezone thì không tự gán UTC. Log ngoài cửa sổ/thiếu timestamp vẫn được giữ riêng để tra lại.
- Nhãn nhiều service lưu nhiều target đã xác minh; không cắt lấy tên đầu tiên. Nhãn node hoặc storage chưa có bằng chứng ánh xạ thì không chuyển thành service.

### A2. Phân biệt đủ điều kiện chấm và đủ điều kiện học

| Cờ | Ý nghĩa |
|---|---|
| `evaluation_eligible` | Nguồn, cửa sổ và nhãn service đã xác minh; vẫn có thể thiếu candidate đúng |
| `training_eligible` | Đạt điều kiện trên, toàn bộ root cause có trong candidate và có ít nhất một candidate nhãn 0 |

Chia các incident `evaluation_eligible` của RCAEval trước. Trong phần train, chỉ dùng các incident `training_eligible` để fit. Nhờ đó test vẫn giữ những sự cố candidate không chứa đáp án.

Báo cáo audit ghi `valid` (hợp lệ), `invalid` (sai), `unverified` (chưa xác minh), `missing_information` (thiếu thông tin), cùng lý do cụ thể. Incident không vào phạm vi chấm vẫn phải xuất hiện trong báo cáo loại.

### A3. Protocol — quy trình thực nghiệm cần giữ cố định

- Chia theo nhóm nguồn độc lập, seed 42, mục tiêu 70/15/15; kiểm tra cân bằng hệ thống rồi loại lỗi. Ghi tỷ lệ thực tế và các loại lỗi hiếm.
- `GroupShuffleSplit` là công cụ chia theo nhóm. Nó không tự cân bằng hệ thống/loại lỗi, và tỷ lệ của công cụ tính theo số nhóm; phải kiểm tra kết quả thực tế.
- Nếu validation quá ít để dùng, giữ test cố định và dùng **group cross-validation — luân phiên các nhóm trong phần dữ liệu còn lại để học và kiểm tra**. Mỗi lượt gọi là một fold; scaler/model phải được fit mới trên phần học của lượt đó.
- Chọn số fold lớn nhất từ 5 xuống 2 sao cho mỗi phần học có cả hai nhãn. Nếu không thể, dừng tuning và báo giới hạn. Điều này là điều kiện kỹ thuật, chưa tự chứng minh mẫu đủ lớn về khoa học.
- Chốt phương án trước khi xem model score. Với cross-validation, chọn cấu hình theo điểm ranking trung bình giữa các lượt, sau đó fit trên toàn bộ phần ngoài test.
- Thử cấu hình bằng conditional Top-1, hòa thì MRR; vẫn hòa thì chọn `C` nhỏ hơn rồi `class_weight=None`. Với MRR dùng để phá hòa, giữ mẫu số như Phụ lục C trên tập validation tương ứng.
- `class_weight="balanced"` cân bằng mức coi trọng các nhãn theo tần suất, không tự cho mọi incident trọng số bằng nhau. Ghi số candidate để thấy khác biệt này.
- Nếu sau này thử **cross-system — kiểm tra trên hệ thống chưa dùng để học**, giữ trọn một hệ thống làm test; chọn cấu hình chỉ trên các hệ thống còn lại.
- Nezha chỉ là **external evaluation — đánh giá bằng nguồn ngoài** nếu chưa dùng để chọn feature/cấu hình. Nếu đã dùng nó để điều chỉnh, cần nguồn độc lập khác cho kết luận cuối.

## Phụ lục B — Công thức feature và kiểm tra input

Gọi `N_s` là số log hợp lệ của service, `N` là tổng số log hợp lệ của mọi candidate trong incident, `D` là độ dài cửa sổ tính bằng giây. Candidate có `N_s > 0`, cửa sổ có `D > 0`. Log chưa rõ service báo riêng, không vào `N`.

| Bộ | Feature | Cách tính |
|---|---|---|
| Basic | `log_count` | `N_s` |
| Basic | `log_rate` | `N_s / D` |
| Basic | `service_log_share` | `N_s / N` |
| Basic | `error_count`, `warn_count` | Số log có mức ERROR/WARN được xác định tường minh |
| Basic | `error_ratio`, `warn_ratio` | Count tương ứng chia `N_s` |
| Basic | `unknown_severity_ratio` | Số log chưa xác định mức chia `N_s` |
| Template | `unique_template_count` | Số nhóm template của service |
| Template | `dominant_template_share` | Số log trong nhóm lớn nhất chia `N_s` |
| Temporal | `first_seen_offset_ratio` | `(thời điểm log đầu - start) / D` |
| Temporal | `active_span_ratio` | `(thời điểm log cuối - thời điểm log đầu) / D`; một log thì bằng 0 |
| Temporal | `late_early_log_rate_delta` | Rate nửa sau trừ rate nửa đầu; log ở đúng giữa cửa sổ thuộc nửa sau |

ERROR count bằng 0 chỉ nói không quan sát được log nhận diện là ERROR. Luôn giữ tỷ lệ severity chưa biết; không dùng nhãn root cause để suy ra severity.

Template chưa tạo được dùng khóa theo raw message; không gom mọi giá trị thiếu vào một mẫu. Không học danh sách template từ toàn train/test rồi dùng làm input. Template ID dùng tổ chức, không đưa làm cột phân loại cho model MVP.

Các cột được đưa vào model phải hữu hạn, đúng tên/thứ tự và kiểu dữ liệu. Không dùng ID, tên file, tên service, hệ thống, fault type hoặc thời điểm tiêm lỗi làm feature. Feature thời gian dùng khoảng lệch trong cửa sổ, không dùng ngày/giờ tuyệt đối để model nhớ lịch thí nghiệm.

MVP không cần **imputer — bộ điền giá trị thiếu —** cho các feature trên: dữ liệu vi phạm điều kiện phải bị báo. Nếu bổ sung feature cho phép thiếu, phải định nghĩa cách xử lý và học thông số điền chỉ từ train.

Chỉ thêm **anomaly feature — số liệu mô tả độ bất thường so với mức tham chiếu —** khi mức tham chiếu có nguồn đáng tin. Nếu học mức tham chiếu chung từ dataset thì chỉ dùng train; nếu dùng khoảng trước sự cố của từng case thì khoảng đó phải có sẵn tại thời điểm dự đoán và không bị lỗi khác làm nhiễu. Thiếu bằng chứng thì bỏ feature này.

## Phụ lục C — Công thức đánh giá và giải thích kết quả

Gọi `E` là tập test có nguồn/cửa sổ và nhãn service hợp lệ, trước khi lọc coverage. Với mỗi sự cố: có tập nguyên nhân thật, tập candidate và danh sách xếp hạng. Các công thức sau tính trung bình theo **incident**, không theo từng dòng service.

| Metric — chỉ số đo | Cách tính |
|---|---|
| Any-candidate coverage | Số incident có ít nhất một nguyên nhân thật trong candidate / số incident thuộc `E` |
| Full-candidate coverage | Số incident có đủ mọi nguyên nhân thật trong candidate / số incident thuộc `E` |
| Conditional Hit@K | Số incident có ít nhất một nguyên nhân thật trong Top-K / số incident có any coverage |
| End-to-end Hit@K | Cùng số incident đúng Top-K / số incident thuộc `E` |
| MRR | Với mỗi incident: `1 / hạng của nguyên nhân thật đầu tiên`; không tìm thấy thì 0; lấy trung bình trên `E` |
| Recall@K | Với mỗi incident: số nguyên nhân thật trong Top-K / tổng số nguyên nhân thật; lấy trung bình trên `E` |

Không có candidate hoặc không trả được ranking được tính 0 cho end-to-end trong phạm vi `E`. Không có incident để làm mẫu số thì ghi `N/A` — không tính được — chứ không gán 0. Nhãn chưa biết nằm ngoài `E`, nhưng số lượng và lý do loại vẫn phải báo.

Service bằng điểm được sắp theo service ID tăng dần để tái lập. Báo tỷ lệ bằng điểm, nhất là E1 khi mọi ERROR count bằng 0. Nếu K lớn hơn số candidate, dùng mọi candidate hiện có.

Đánh giá việc tổ chức log riêng:

- **Visible Log Reduction — mức giảm số mục hiển thị:** `1 - số nhóm / số log đã nhóm`, tính khi mỗi nhóm hiển thị thành một mục. Không dùng việc chỉ chọn 3 evidence groups để thổi phồng mức giảm.
- **Raw Log Traceability — khả năng tra về log gốc:** số log đã xử lý có tham chiếu đúng nguồn / tổng số log đã xử lý; mục tiêu kỹ thuật 100%.
- Kiểm tra mọi log trong phạm vi grouping có đúng liên kết nhóm, kể cả nhóm chưa rõ service. Không có log thì tỷ lệ là `N/A`.
- **Runtime — thời gian chạy:** đo riêng đọc/kiểm tra dữ liệu, grouping, tạo feature, fit và inference; ghi số log, incident, CPU/RAM đi kèm.

Các experiment phải dùng cùng dữ liệu, candidate, split và số cấu hình được thử. Nếu một bộ feature chỉ tính được trên một phần case, chạy các phương pháp đối chiếu trên cùng phần đó và báo phạm vi giảm.

E3 hơn E2 chỉ cho thấy bộ feature từ template trong thiết kế này hữu ích; chưa chứng minh mọi cách grouping đều tốt. Nếu ước lượng độ bất định bằng cách lấy mẫu lặp lại, lấy theo nhóm incident độc lập và dùng cùng nhóm cho các phương pháp được so, không coi dòng service là mẫu độc lập. Báo riêng kết quả từng hệ thống và các trường hợp sai.

## Phụ lục D — Tra cứu thuật toán, dữ liệu và hồ sơ lần chạy

### D1. Chi tiết model khi cần đọc sâu hơn

Với các feature đã đổi thang đo, Logistic Regression tính:

```text
z = tổng(w_j × x_j) + b
p = 1 / (1 + exp(-z))
```

Hàm biến `z` thành `p` gọi là **sigmoid**, đưa giá trị về khoảng 0–1. Training dùng **binary cross-entropy — cách tính mức sai khi nhãn là 0 hoặc 1 —** cùng regularization để tìm trọng số. Giá trị `p` chưa mặc nhiên là xác suất root cause đáng tin; muốn diễn giải như xác suất cần đánh giá hiệu chuẩn riêng. MVP dùng `z` để xếp hạng.

Model học điểm từng candidate độc lập rồi sắp theo incident; nó chưa tối ưu trực tiếp thứ hạng Top-K. Muốn giải thích điểm có thể xem `w_j × feature_đã_đổi_thang_đo` cùng `b`; đó là đóng góp của feature, không phải xác nhận log nguyên nhân.

### D2. Bản kê cần ghi gì để chạy lại?

Lưu nguồn/phiên bản dữ liệu, danh sách input, phiên bản code và thay đổi local, phiên bản thư viện, cấu hình feature, split, seed, tiêu chí chọn model và thời gian chạy. Dùng hash — mã kiểm tra nội dung — để phát hiện input/config/split đã thay đổi. Chỉ dùng lại kết quả xử lý khi thông tin tương ứng còn khớp.

Giữ code/config/test trong quản lý phiên bản; model và dữ liệu lớn được quản lý theo lần chạy và bản kê. Kiểm tra khả năng lưu/nạp ở đúng phiên bản thư viện đã dùng thay vì mặc định mọi phiên bản tương thích.

### D3. Các tài liệu để đối chiếu

- [OUTPUT.md — cách giải thích dành cho intern/fresher](../../OUTPUT.md).
- [repo map](../README.md) và [hướng dẫn adapter/CLI](../code/datasets_cli.md).
- [Đối chiếu schema dataset](../status/dataset_audit.md) và [báo cáo validation hiện có](../status/validation_report.md). Dùng audit mới để đối chiếu khi chạy thực nghiệm.
- [RCAEval trên Hugging Face](https://huggingface.co/datasets/phamquiluan/RCAEval): tham khảo định dạng nguồn. Adapter local đã được ghi nhận đọc `cases.parquet`/`logs.parquet`; kiểm tra version/schema trước khi quyết định sửa hoặc tải lại. Tên split `train` trên nguồn không thay thế cách chia của dự án.
- [scikit-learn: tránh rò rỉ dữ liệu](https://scikit-learn.org/stable/common_pitfalls.html).
- [scikit-learn: LogisticRegression](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html).
- [scikit-learn: GroupShuffleSplit](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.GroupShuffleSplit.html).

Các phương án trong tài liệu là thiết kế để triển khai và đo kiểm. Chưa đặt accuracy mục tiêu, chưa có kết quả chứng minh grouping hoặc các feature đề xuất chắc chắn cải thiện RCA.
