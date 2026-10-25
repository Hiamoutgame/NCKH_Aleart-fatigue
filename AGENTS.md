# Hướng dẫn làm việc với dự án NCKH

Đọc [master context V3](NCKH_MASTER_CONTEXT_2026-10-23.md), [implementation status](Resource/docs/implementation_status.md) và [Resource map](Resource/README.md) trước khi đề xuất hoặc cập nhật nghiên cứu.

- Working scope: nghiên cứu offline về evidence-preserving hierarchical log organization và service-level root-cause candidate ranking. RQ/novelty/tên đề tài chưa được người hướng dẫn duyệt.
- V1 WARNING-only/LLM Agent và V2 failure prediction là lịch sử, không tự đưa lại vào scope V3.
- Giữ raw logs, ID và provenance. Code hiện dùng `log_id`; `event_id`/`raw_log_id` trong ý tưởng là khái niệm tương ứng, chưa phải cột mới.
- Không coi correlation là causation hoặc nhãn service là ground-truth log/edge/group label. Không tự sinh service ngoài inventory có nguồn.
- Phân biệt SOURCE FACT, HISTORICAL REPORT, PROPOSAL, INFERENCE, UNVERIFIED; không bịa metric, paper claim hoặc implementation.
- Split theo incident/nhóm case lặp; preprocessing có fit chỉ học trên train. Test labels không dùng làm feature, inventory hoặc tuning.
- Source active ở `Resource/explore_datasets/`; raw ở `NCKH_rawData/raw_data/`. `paths.py` còn mặc định về CP1 cũ: kiểm tra và dùng `--data-root` từng dataset. Không coi `.kilo/worktrees/` là source active.
- Tài liệu lịch sử trong `Resource/docs/history/` và `01_topic_proposal/history/` không phải specification hiện tại. Không sửa raw/Parquet chỉ để đồng bộ docs.
- Giải thích bằng tiếng Việt đơn giản theo [OUTPUT.md](OUTPUT.md). Mô tả phần đã làm và giới hạn kiểm chứng rõ ràng.
