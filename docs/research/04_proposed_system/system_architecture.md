# System Architecture

Cập nhật 26/10/2026. **Đề xuất.** Tên module mới chỉ là chỗ giữ; nhóm có thể đổi khi viết code. Phần "đã có" đã được kiểm trong `src/` ngày 26/10/2026.

## 1. Overview

Hệ thống nhận log của một sự cố, gom thành cây `incident → service → nhóm template → log gốc`, rồi dùng Kev xếp hạng các service theo tỉ lệ nghi ngờ là nguyên nhân. Mỗi service trong kết quả có kèm nhóm log làm bằng chứng.

Có hai chế độ dùng chung một thư viện lõi:

- **Offline evaluation** (chính): chạy theo lô trên RCAEval / Nezha bằng CLI để đo kết quả.
- **Demo tương tác**: người dùng dán log qua giao diện web, nhận bảng service + tỉ lệ.

Chi tiết người dùng và chức năng ở [system_overview.md](system_overview.md).

## 2. Main Components

| Component | Description | Trạng thái |
|---|---|---|
| Frontend | Trang web demo: chọn hệ thống, dán log, xem bảng service + tỉ lệ, bấm vào service để xem nhóm log và log gốc. Đề xuất **Streamlit** (thư viện Python dựng web nhanh) để cả nhóm chỉ cần biết Python | Chưa có; làm sau cùng |
| Backend API | **FastAPI** (framework Python viết REST API), endpoint `POST /rank`. Chỉ gọi lại các hàm của thư viện lõi, nên demo và thực nghiệm chạy cùng code | Chưa có |
| Thư viện lõi (`src/`) | `datasets/` + `shared/` (đã có); thêm `windowing/`, `grouping/`, `ranking/`, `evaluation/`, `integrations/kev/` | Một phần |
| CLI | Chạy pipeline offline: chuẩn hóa, gom nhóm, xếp hạng, đánh giá | Có `datasets_cli.py` (list / inspect / normalize) |
| Database | **Không dùng database server.** Lưu file Parquet và JSON trong `data/` (raw, normalized, artifacts, runs). Nghiên cứu chạy offline theo lô, Parquet đã dùng trong repo, mỗi lần chạy tách riêng để tái lập. Có thể thêm SQLite nếu demo cần lưu lịch sử | `data/raw/` đã có |
| AI Service | **Kev server** (`python -m kev.serve --run <checkpoint> --port 8009`), API `POST /v1/systemone`. Chạy trên GPU local, Mac hoặc Colab/Kaggle | Chưa chạy trên dữ liệu dự án |
| Vector Database | **Không dùng.** Hệ thống không làm RAG hay tìm kiếm theo embedding. Gom nhóm dựa trên template (Drain), không dựa trên vector | Không áp dụng |
| External Services | Hugging Face (tải trọng số `jaredpalmer/kev-0.8b`, `kev-4b` và model nền Qwen3.5); Colab/Kaggle (GPU để fine-tune). Không gửi log ra API bên ngoài | — |

### Hai interface mới (bản phác)

```python
class LogGrouper(ABC):
    def group(self, events: list[LogEvent]) -> tuple[list[LogGroup], list[GroupMember]]: ...
    # Bảo đảm: mỗi log_id thuộc đúng một nhóm.

class ServiceRanker(ABC):
    def rank(self, view: IncidentView, candidates: list[str]) -> list[RankedService]: ...
    # Bảo đảm: chỉ trả service có trong candidates; không nhận ground truth.
```

Mọi ranker (đếm ERROR, Logistic Regression, Kev) đều cài `ServiceRanker`, nên module `evaluation/` chấm mọi phương pháp bằng cùng một hàm. Giữ quy tắc phụ thuộc trong [src/README.md](../../../src/README.md): module cùng cấp không import lẫn nhau; chỉ `integrations/kev/` biết Kev tồn tại.

## 3. Architecture Diagram

```text
 ┌────────────────────────────┐      ┌──────────────────────────────┐
 │ CLI (offline evaluation)   │      │ Frontend demo (Streamlit)    │
 │ src/interface/*_cli.py     │      │ dán log → bảng service       │
 └─────────────┬──────────────┘      └──────────────┬───────────────┘
               │                                    │ HTTP
               │                     ┌──────────────▼───────────────┐
               │                     │ Backend API (FastAPI)        │
               │                     │ POST /rank                   │
               │                     └──────────────┬───────────────┘
               ▼                                    ▼
 ┌──────────────────────────────────────────────────────────────────┐
 │ Thư viện lõi trong src/ (Python)                                 │
 │  datasets/     adapters RCAEval, Nezha                [đã có]    │
 │  shared/       schema, normalize_message, paths       [đã có]    │
 │  windowing/    chia trước/sau lỗi                     [mới]      │
 │  grouping/     LogGrouper: regex, Drain               [mới]      │
 │  ranking/      ServiceRanker: luật, LogReg, Kev       [mới]      │
 │  evaluation/   split, leakage check, metrics          [mới]      │
 │  integrations/kev/  chỗ DUY NHẤT gọi Kev              [mới]      │
 └───────────────┬─────────────────────────────┬────────────────────┘
                 │ đọc/ghi file                │ HTTP (System One API)
 ┌───────────────▼──────────────┐  ┌───────────▼──────────────────────┐
 │ Lưu trữ: Parquet + JSON      │  │ AI Service: Kev server           │
 │ data/raw, data/normalized,   │  │ cổng 8009; trọng số tải từ       │
 │ data/artifacts, data/runs    │  │ Hugging Face                     │
 └──────────────────────────────┘  └──────────────────────────────────┘
```

Có thể vẽ lại sơ đồ này thành hình (draw.io, Figma) khi đưa vào bài báo.

## 4. Data Flow

Luồng demo, theo thứ tự của mẫu:

1. Người dùng chọn hệ thống (ví dụ `ob`) và dán các dòng log ERROR/WARN tại thời điểm lỗi.
2. Backend tạo các `LogEvent` tạm, mỗi dòng có `log_id` riêng; giữ nguyên chuỗi gốc.
3. Backend gom nhóm theo template và tạo bản tóm tắt (`state`), rồi gửi tới AI Service cùng danh sách service của hệ thống.
4. Kev chấm điểm từng service và trả xác suất.
5. Backend sắp xếp, gắn nhóm log bằng chứng cho từng service, trả kết quả.
6. Người dùng xem bảng service + tỉ lệ, bấm vào service để xem nhóm log và dòng log gốc.

Luồng offline (7 bước, kèm file đầu ra từng bước và chỗ dùng nhãn) ở [data_flow.md](data_flow.md).

## 5. AI Integration

Kev được tích hợp ở **bước xếp hạng** (bước 3–4 ở trên, bước 6 trong luồng offline):

- `KevRanker` (trong `src/integrations/kev/`) cài interface `ServiceRanker`.
- Đầu vào: bản tóm tắt nhóm log của incident + câu hỏi `choice` có các phương án là service ứng viên.
- Đầu ra: xác suất từng service → sắp thành bảng xếp hạng.
- Gọi Kev qua HTTP, nên Kev có thể chạy ở máy khác (GPU, Colab) mà không phải sửa code lõi.

Tùy chọn: Kev hỗ trợ quyết định gộp các cặp nhóm Drain gần ngưỡng (câu hỏi có/không). Chi tiết lý do chọn model, fine-tune, phần cứng và trích dẫn ở [ai_model_integration.md](ai_model_integration.md).

## 6. Triển khai

| Thành phần | Chạy ở đâu | Ghi chú |
| --- | --- | --- |
| Chuẩn hóa, gom nhóm, baseline, đánh giá | Máy local, CPU | Không cần GPU |
| Kev inference | GPU local, Mac, hoặc Colab/Kaggle | Kev-0.8B chạy được trên GPU 4 GB; Kev-4B cần L40S/H100 hoặc Mac 32 GB (theo README Kev) |
| Kev fine-tune | Colab/Kaggle GPU | Notebook có sẵn: `notebooks/kev_01_colab_kaggle.ipynb` |
| Demo | Máy local | Gọi Kev server qua HTTP |

[architecture_proposal_v3.md](../../status/architecture_proposal_v3.md) từng đề xuất đổi package thành `src/nckh/`. Tài liệu này giữ package `src` và chỉ thêm module mới, để không phải sửa import đang chạy (18 test đang pass).
