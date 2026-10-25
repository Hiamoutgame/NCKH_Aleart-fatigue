# Đồng bộ docs V3 — 23/10/2026

## 1. Phạm vi và căn cứ

Đồng bộ theo bản handoff người dùng cung cấp ngày 23/10 và source local hiện hành. Giữ khung tài liệu sẵn có: proposal 11 mục, readme tóm tắt 8 mục, Resource/src maps, dataset READMEs, architecture/exploration guide, related-work notes và training handoff. [Master context](../../NCKH_MASTER_CONTEXT_2026-10-23.md) là lối vào chuẩn.

Không đổi thuật toán hoặc tự chốt open decisions; không tải dữ liệu, normalize lại, train model, chạy full raw audit hoặc thực hiện literature review ngoài repo.

## 2. Những gì được cập nhật

| Nhóm docs | Thay đổi |
| --- | --- |
| Root README + master context + AGENTS | Scope V3, thứ tự nguồn, invariants, lịch sử V1/V2, implementation boundaries và cách tiếp tục |
| Proposal + readme | Giữ cấu trúc cũ; thay WARNING/Agent/prediction bằng organization/provenance/service ranking; chưa chốt model/RQ/targets |
| Resource map + mindmap + src/architecture docs | Cây thư mục thật; CP1 active vắng mặt; raw đã ở NCKH_rawData; override path; schema dùng log_id |
| Dataset/shared READMEs | Export caps, labels/windows/service aliases/provenance assumptions; domain hiện có pandas; loại mô tả class chưa có |
| Audit + validation + implementation status | Tách footer mới, audit lịch sử, fixture checks và điều chưa kiểm chứng; bỏ claim sẵn sàng khoa học vô điều kiện |
| Research protocol | Output/gates/eligibility/split/metrics/ablation dưới nhãn đề xuất, chưa là modules tồn tại |
| Handoff/training note | Phân biệt MVP design với code đã có; tỷ lệ split khác nhau chưa tự khóa |
| Related work/glossary/requirement notes | Thêm scope/evidence status; giữ nguyên phần ghi chú lịch sử chưa xác minh lại |
| Report drafts | Thêm README và notice hiển thị trong LaTeX V1; DOCX/bibliography giữ nguyên |

## 3. Lưu lịch sử và thay đổi local có sẵn

Các bản README V1, proposal/readme V2, mindmap V1, audit 18/10 và validation 19/10 được sao chép **từ nội dung local trước khi sửa**, không lấy git HEAD để ghi đè những thay đổi của người dùng. [History index](history/README.md) liên kết các bản này. Ghi chú/literature/training cũ được giữ với banner hoặc chỉnh câu cụ thể để tránh mất nội dung.

Repo có nhiều thay đổi local từ trước lần làm việc này; không reset/revert, không commit. Snapshot/hash dùng kiểm tra lần đồng bộ được lưu ngoài repo trong thư mục tạm, không phải manifest khoa học của dataset hoặc gói handoff.

## 4. Kiểm chứng và giới hạn

- Đã đọc footer/schema 9 canonical Parquet; số rows khớp báo cáo 19/10 nhưng chưa kiểm nội dung, lineage hoặc eligible case count.
- CLI `--help`/`list` chạy được; xác nhận default path vẫn về CP1 cũ.
- Ba regression checks có sẵn dùng fixture/output tạm: **3 passed, 5 deselected**. Không chạy full suite cần raw paths/entrypoints đã vắng mặt.
- Fixture Nezha hai faults cùng bucket tái hiện inspect=2 nhưng loaded incidents/GT=1. Đây là lỗi source cần sửa tiếp, không thống kê dữ liệu thật.
- Rà 41 docs/phần bổ sung hiện hành: 187 liên kết local resolve được, Markdown fences cân bằng, proposal giữ 11 mục. Phần lịch sử nguyên văn có thể giữ link theo vị trí ban đầu và được ghi rõ tại history index.
- Đối chiếu hash 74 file source thực thi/config/artifacts/Parquet với snapshot trước sửa: không đổi, gồm cả 9 Parquet. Sáu bản sao lịch sử khớp byte với docs local trước sửa. Không dùng hash này để claim raw 400 GB đã kiểm toàn vẹn. Raw không có thao tác ghi trong phiên này.

[Validation report](validation_report.md) chứa lệnh và phạm vi checks chi tiết. Chưa có Top-k, Visible Log Reduction, full Raw Log Traceability hoặc user-study metric V3 mới. Paper claims/metadata/licenses vẫn cần nguồn gốc trước publication.

## 5. Bước tiếp theo còn được giữ mở

Case eligibility + labels/windows/inventory/provenance → sửa path/adapter gaps → chọn và khóa split/protocol → baseline grouping/hierarchy → ranker và held-out ablation. RQ/novelty/tên đề tài/model/targets/dataset mix/user study cần review tiếp với người hướng dẫn. Đồng bộ docs chưa đồng nghĩa hoàn thành các bước nghiên cứu đó.
