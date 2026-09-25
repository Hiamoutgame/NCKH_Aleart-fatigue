# 📖 Giải Thích Thuật Ngữ & Từ Khóa Nghiên Cứu (Literature Review)

> **Mục tiêu**: Bảng tra cứu thuật ngữ phục vụ viết Literature Review và tổng hợp kiến thức cho đề tài: *"Gom nhóm cảnh báo (Alert Aggregation) nhằm giảm cảnh báo nhiễu trong Microservices"*.  
> **Cấu trúc giải thích (theo chuẩn intern/fresher)**:
> 1. Vấn đề thực tế (Problem).
> 2. Nghĩa tiếng Việt & Thuật ngữ tiếng Anh (Definition).
> 3. Vai trò / Ứng dụng trong đề tài NCKH (Context & Application).

---

## 1. Cơ chế gom nhóm cảnh báo (Alert Grouping & Correlation Mechanisms)

### `alert aggregation`
- **Tiếng Anh**: Alert Aggregation
- **Nghĩa tiếng Việt**: Gom nhóm / Tổng hợp cảnh báo.
- **Vấn đề thực tế**: Khi hệ thống gặp trục trặc, hàng chục hoặc hàng trăm cảnh báo bắn về cùng lúc khiến kỹ sư trực bị ngợp thông tin.
- **Giải thích**: Kỹ thuật gộp nhiều cảnh báo đơn lẻ phát sinh trong cùng một khoảng thời gian lại thành các cụm (cluster/group) có ý nghĩa liên quan.
- **Ứng dụng trong đề tài**: Đây là kỹ thuật trọng tâm. Thay vì kỹ sư phải đọc 100 cảnh báo rời rạc, hệ thống dùng thuật toán (Rule-based, ML Clustering hoặc AI Agent) gom lại thành một số ít nhóm để xử lý nhanh hơn.

### `alert correlation`
- **Tiếng Anh**: Alert Correlation
- **Nghĩa tiếng Việt**: Phân tích tương quan cảnh báo.
- **Vấn đề thực tế**: Các cảnh báo có thể trông khác nhau (CPU cao ở Service A, thời gian phản hồi tăng ở Service B), nhưng thực chất liên quan mật thiết do Service B đang gọi Service A.
- **Giải thích**: Quá trình tìm và xác định mối quan hệ logic, quan hệ nhân - quả (cause-effect) hoặc quan hệ phụ thuộc (service dependency) giữa các cảnh báo.
- **Ứng dụng trong đề tài**: Là bước suy luận cốt lõi giúp hệ thống quyết định hai cảnh báo khác loại có nên được xếp chung vào một nhóm hay không.

### `alert deduplication`
- **Tiếng Anh**: Alert Deduplication
- **Nghĩa tiếng Việt**: Khử trùng lặp cảnh báo.
- **Vấn đề thực tế**: Một lỗi kéo dài 10 phút có thể kích hoạt cùng 1 cảnh báo lặp lại mỗi 30 giây (tạo ra 20 cảnh báo y hệt nhau).
- **Giải thích**: Hành động lọc bỏ hoặc gộp các cảnh báo giống hệt nhau về nguồn phát, mã lỗi và tính chất xảy ra trong cùng một khung thời gian ngắn.
- **Ứng dụng trong đề tài**: Bước tiền xử lý (pre-processing) cơ bản nhất trước khi thực hiện gom nhóm ngữ nghĩa phức tạp.

### `alert grouping`
- **Tiếng Anh**: Alert Grouping
- **Nghĩa tiếng Việt**: Phân nhóm cảnh báo.
- **Vấn đề thực tế**: Kỹ sư cần một "túi" gom tất cả thông tin liên quan đến một sự cố cụ thể để xử lý một lượt thay vì xử lý vụn vặt.
- **Giải thích**: Thường được dùng tương đương với *alert aggregation*, chỉ kết quả của việc phân chia tập cảnh báo thành các nhóm độc lập dựa trên quy tắc hoặc mô hình.
- **Ứng dụng trong đề tài**: Đầu ra (output) của các thuật toán phân cụm hoặc công cụ như Prometheus Alertmanager.

### `event correlation`
- **Tiếng Anh**: Event Correlation
- **Nghĩa tiếng Việt**: Tương quan sự kiện hệ thống.
- **Vấn đề thực tế**: Cảnh báo xuất hiện thường do một sự kiện nào đó vừa diễn ra (ví dụ: vừa triển khai bản code mới lúc 10:00 thì 10:01 hệ thống báo lỗi).
- **Giải thích**: Khái niệm rộng hơn *alert correlation*, mở rộng liên kết cảnh báo với các sự kiện hệ thống khác như: deploy, restart pod, thay đổi cấu hình, network flap.
- **Ứng dụng trong đề tài**: Dữ liệu ngữ cảnh phong phú giúp AI Agent hoặc mô hình hiểu nguyên nhân sâu xa phía sau chuỗi cảnh báo.

---

## 2. Vấn đề cảnh báo nhiễu (Alert Noise & Fatigue)

### `alert fatigue`
- **Tiếng Anh**: Alert Fatigue
- **Nghĩa tiếng Việt**: Tình trạng mệt mỏi / Quá tải vì cảnh báo.
- **Vấn đề thực tế**: Kỹ sư nhận 500 thông báo mỗi ngày, trong đó 90% là cảnh báo giả hoặc không cần làm gì. Lâu dần, kỹ sư sẽ tắt chuông hoặc bỏ qua thông báo theo phản xạ, dẫn tới bỏ lọt sự cố nghiêm trọng thật sự.
- **Giải thích**: Hiện tượng suy giảm độ nhạy bén và phản xạ của con người khi phải đối mặt với quá nhiều cảnh báo không giá trị trong thời gian dài.
- **Ứng dụng trong đề tài**: Động lực và bài toán thực tiễn quan trọng nhất mà đề tài NCKH này muốn giải quyết.

### `alert storm`
- **Tiếng Anh**: Alert Storm
- **Nghĩa tiếng Việt**: Cơn bão cảnh báo.
- **Vấn đề thực tế**: Một dịch vụ cơ sở dữ liệu (Database) bị nghẽn, kéo theo 50 microservices khác đồng loạt gửi hàng nghìn cảnh báo trong vòng vài phút do hiệu ứng lan truyền.
- **Giải thích**: Tình trạng hệ thống giám sát bắn ra một lượng khổng lồ cảnh báo dồn dập trong khoảng thời gian rất ngắn.
- **Ứng dụng trong đề tài**: Kịch bản kiểm thử (stress test / benchmark) để đánh giá khả năng nén và gom nhóm của thuật toán trong điều kiện khắc nghiệt.

### `alert flapping`
- **Tiếng Anh**: Alert Flapping
- **Nghĩa tiếng Việt**: Cảnh báo chập chờn / Bật-tắt liên tục.
- **Vấn đề thực tế**: Một chỉ số dao động quanh ngưỡng giới hạn (ví dụ CPU nhảy 79% -> 81% -> 79% -> 81%), làm cảnh báo liên tục reo chuông rồi tự hết trong vài giây.
- **Giải thích**: Hiện tượng cảnh báo liên tục chuyển đổi trạng thái giữa BÌNH THƯỜNG và BÁO ĐỘNG trong thời gian ngắn do ngưỡng đặt quá sát biến động tự nhiên.
- **Ứng dụng trong đề tài**: Một dạng nhiễu kinh điển cần được loại bỏ hoặc làm mịn trước khi thông báo cho kỹ sư.

### `noisy alerts`
- **Tiếng Anh**: Noisy Alerts / Alert Noise
- **Nghĩa tiếng Việt**: Cảnh báo nhiễu / Cảnh báo ồn ào.
- **Vấn đề thực tế**: Cảnh báo đúng theo công thức thiết lập (ví dụ RAM tăng vọt trong 5 giây do chạy tác vụ nền), nhưng dịch vụ vẫn chạy bình thường và khách hàng không bị ảnh hưởng.
- **Giải thích**: Các cảnh báo đúng về mặt kỹ thuật đo lường nhưng không đem lại giá trị vận hành thực tế (không chỉ ra sự cố cần can thiệp).
- **Ứng dụng trong đề tài**: Đối tượng chính cần giảm thiểu (đo qua chỉ số tỷ lệ giảm cảnh báo nhiễu).

### `actionable alerts`
- **Tiếng Anh**: Actionable Alerts
- **Nghĩa tiếng Việt**: Cảnh báo có thể hành động được / Cảnh báo có giá trị.
- **Vấn đề thực tế**: Một thông báo nêu rõ: "Ổ cứng Service Storage sắp đầy trong 30 phút, bấm vào đây để mở rộng dung lượng", kèm hướng dẫn xử lý cụ thể.
- **Giải thích**: Cảnh báo chỉ kích hoạt khi thực sự có vấn đề ảnh hưởng người dùng, yêu cầu con người can thiệp ngay lập tức và có các bước khắc phục rõ ràng.
- **Ứng dụng trong đề tài**: Mục tiêu chất lượng đầu ra sau khi qua khâu gom nhóm và lọc nhiễu.

---

## 3. Nền tảng SRE (Site Reliability Engineering Principles)

### `symptom-based alerting`
- **Tiếng Anh**: Symptom-based Alerting
- **Nghĩa tiếng Việt**: Cảnh báo dựa trên triệu chứng người dùng.
- **Vấn đề thực tế**: Báo động khi người dùng thấy trang web bị chậm hoặc trả về lỗi 500, thay vì báo động mỗi khi CPU máy chủ tăng nhẹ.
- **Giải thích**: Triết lý thiết lập cảnh báo tập trung vào những biểu hiện trực tiếp ảnh hưởng đến người dùng (triệu chứng như latency, error rate) thay vì đoán các nguyên nhân ngầm bên dưới.
- **Ứng dụng trong đề tài**: Giúp phân biệt giữa cảnh báo triệu chứng (symptom alert) và cảnh báo nguyên nhân gốc (root cause alert).

### `alerting philosophy`
- **Tiếng Anh**: Alerting Philosophy
- **Nghĩa tiếng Việt**: Triết lý thiết kế cảnh báo.
- **Vấn đề thực tế**: Đội ngũ không có quy định chung, ai thích gì cũng đặt cảnh báo khiến hệ thống giám sát tràn ngập thông báo vô nghĩa.
- **Giải thích**: Bộ nguyên tắc chuẩn xác định khi nào thì ĐƯỢC PHÉP gửi cảnh báo (chỉ cảnh báo khi khẩn cấp, có thể hành động được, và có ảnh hưởng dịch vụ).
- **Ứng dụng trong đề tài**: Dựa trên triết lý từ Google SRE Book (Chương 6 & 10) làm nền móng lý thuyết để lập luận cho bài báo.

### `paging policy`
- **Tiếng Anh**: Paging Policy
- **Nghĩa tiếng Việt**: Chính sách phân cấp gọi trực / Báo động khẩn cấp.
- **Vấn đề thực tế**: Lỗi không nghiêm trọng nhưng lại reo chuông đánh thức kỹ sư trực lúc nửa đêm.
- **Giải thích**: Quy định phân luồng mức độ cảnh báo: loại nào cần đánh thức kỹ sư ngay (Page/PagerDuty), loại nào chỉ cần gửi email hoặc đưa vào dashboard xem sau (Ticket/Log).
- **Ứng dụng trong đề tài**: Định vị phạm vi xử lý: tập trung xử lý các cảnh báo mức WARNING (sớm, chưa sập) và tối ưu hóa luồng Paging.

### `SLO-based alerting`
- **Tiếng Anh**: SLO-based Alerting (Service Level Objective Alerting)
- **Nghĩa tiếng Việt**: Cảnh báo dựa trên mục tiêu mức dịch vụ.
- **Vấn đề thực tế**: Ngưỡng cố định (Static threshold) rất dễ báo giả. Nếu dựa vào tốc độ tiêu hao ngân sách lỗi (Error Budget Burn Rate) của SLO, cảnh báo sẽ chính xác hơn nhiều.
- **Giải thích**: Cơ chế phát cảnh báo khi hệ thống có nguy cơ phá vỡ cam kết chất lượng dịch vụ (SLO) đã thỏa thuận với người dùng.
- **Ứng dụng trong đề tài**: Tiêu chuẩn hiện đại trong SRE để đo lường và đánh giá tính cấp thiết của cảnh báo.

---

## 4. Microservices & Quan sát hệ thống (Observability)

### `microservice failure diagnosis`
- **Tiếng Anh**: Microservice Failure Diagnosis
- **Nghĩa tiếng Việt**: Chẩn đoán sự cố trong kiến trúc vi dịch vụ.
- **Vấn đề thực tế**: Hệ thống gồm 50 dịch vụ nhỏ gọi chéo nhau. Khi có lỗi, dịch vụ ở tầng sâu bị nghẽn làm tê liệt cả chuỗi, rất khó tìm ra lỗi phát sinh từ đâu.
- **Giải thích**: Toàn bộ quy trình phát hiện, phân tích và giải thích nguyên nhân gốc rễ gây ra lỗi trong hệ thống microservices.
- **Ứng dụng trong đề tài**: Miền bài toán (Domain) chính mà nghiên cứu nhắm tới.

### `telemetry data`
- **Tiếng Anh**: Telemetry Data
- **Nghĩa tiếng Việt**: Dữ liệu viễn trắc / Dữ liệu giám sát vận hành.
- **Vấn đề thực tế**: Để hiểu được hệ thống phân tán đang hoạt động thế nào, cần liên tục thu thập số liệu đo từ xa.
- **Giải thích**: Toàn bộ dữ liệu đo đạc phát ra từ các dịch vụ, gồm 3 trụ cột (Observability Pillars): Metrics (chỉ số đo), Logs (nhật ký) và Traces (dấu vết phân tán).
- **Ứng dụng trong đề tài**: Dữ liệu đầu vào (Input) từ các tập benchmark như RCAEval hoặc LEMMA-RCA.

### `root cause localization`
- **Tiếng Anh**: Root Cause Localization
- **Nghĩa tiếng Việt**: Định vị nguyên nhân gốc rễ.
- **Vấn đề thực tế**: 10 microservices đồng loạt báo lỗi, nhưng chỉ có đúng 1 microservice là thủ phạm gây ra vấn đề.
- **Giải thích**: Quá trình khoanh vùng và xác định chính xác dịch vụ hoặc thành phần cụ thể chịu trách nhiệm cho toàn bộ sự cố.
- **Ứng dụng trong đề tài**: Tiêu chí đánh giá xem nhóm cảnh báo sau khi gom có bảo toàn và chỉ đúng dịch vụ gốc (Root cause service) hay không.

---

## 5. Đánh giá & Phân tích (Evaluation Metrics & Methods)

### `alert reduction ratio` (ARR)
- **Tiếng Anh**: Alert Reduction Ratio
- **Nghĩa tiếng Việt**: Tỷ lệ cắt giảm cảnh báo.
- **Vấn đề thực tế**: Cần một thước đo định lượng để chứng minh thuật toán gom nhóm đã giúp kỹ sư bớt phải đọc bao nhiêu thông báo.
- **Công thức**:
  $$\text{ARR} = 1 - \frac{N_{\text{sau gom nhóm}}}{N_{\text{trước gom nhóm}}}$$
- **Ứng dụng trong đề tài**: Chỉ số hiệu năng chính (Primary Metric), mục tiêu thường đặt ra là $\ge 50\%$.

### `precision-recall alert grouping`
- **Tiếng Anh**: Precision & Recall in Alert Grouping
- **Nghĩa tiếng Việt**: Độ chính xác và độ bao phủ trong gom nhóm cảnh báo.
- **Vấn đề thực tế**: Gom ẩu tất cả cảnh báo vào 1 nhóm thì tỷ lệ giảm rất cao nhưng sai bản chất (Low Precision); chia quá vụn thì sót cảnh báo cùng sự cố (Low Recall).
- **Giải thích**:
  - **Precision (Độ chính xác)**: Tỷ lệ các cảnh báo trong cùng 1 nhóm thực sự thuộc về cùng một nguyên nhân gốc.
  - **Recall (Độ bao phủ)**: Tỷ lệ cảnh báo của cùng 1 nguyên nhân gốc được gom trọn vẹn vào nhóm mà không bị văng ra ngoài.
- **Ứng dụng trong đề tài**: Thước đo chất lượng phân cụm để tránh việc mô hình gom nhóm bừa bãi chỉ để đạt ARR cao.

### `clustering-based alert triage`
- **Tiếng Anh**: Clustering-based Alert Triage
- **Nghĩa tiếng Việt**: Sàng lọc và phân loại cảnh báo dựa trên kỹ thuật phân cụm.
- **Vấn đề thực tế**: Khi cảnh báo đổ về liên tục, cần tự động phân loại mức độ ưu tiên theo từng cụm lỗi để kỹ sư biết xử lý cụm nào trước.
- **Giải thích**: Phương pháp áp dụng các thuật toán học máy không giám sát (như DBSCAN, K-Means, hoặc LLM Clustering) để gom nhóm và sắp xếp thứ tự xử lý cảnh báo.
- **Ứng dụng trong đề tài**: Phương pháp luận (Methodology) nền tảng trong các nghiên cứu liên quan (Literature) dùng để so sánh đối chứng (Baseline).
