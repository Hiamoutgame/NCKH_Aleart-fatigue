# Project Mindmap — V3 Log Organization & Service RCA

**23/10/2026, working direction chưa được người hướng dẫn duyệt.** [Master context](../../NCKH_MASTER_CONTEXT_2026-10-23.md) là nguồn scope chuẩn. [Mindmap V1](../history/resource_docs/PROJECT_MINDMAP_V1.md) được giữ để đối chiếu.

```mermaid
mindmap
  root((V3: log organization + service ranking))
    Problem
      Log rời rạc và lặp lại
      Cần ưu tiên service điều tra
    Invariants
      Giữ raw và log_id
      Truy nhóm về raw records
      Candidate từ trusted inventory
      Correlation khác causation
    Hiện có
      Adapters và CLI ba dataset
      Canonical schema và Parquet
      Audit raw L0/L1 ngày 20/10
      Regex normalization và template hash
    Cần triển khai và kiểm chứng
      Case eligibility và clock/service mapping
      Template grouping baseline
      Incident/service/group hierarchy
      Evidence links tùy chọn
      Service ranker
    Evaluation đề xuất
      Visible items tại cùng tree level
      Raw log traceability
      Candidate coverage và Top-k
      Runtime và memory
      User study nếu khả thi
    Quyết định còn mở
      RQ và novelty với thầy
      Parser và grouping algorithm
      Ranker và features
      Split protocol và dataset mix
```

Luồng dự kiến: **audit → canonical data → parsing/grouping → hierarchy → optional relationships → ranking → held-out evaluation**. Có adapter chưa có nghĩa grouping/ranker đã hoàn thành.

Raw thật: `data/raw/`, cũng là default của code từ 25/10. [repo map](../README.md) và [implementation status](../status/implementation_status.md) ghi hướng dùng `--data-root` và giới hạn export.

Không mặc định WARNING-only, LLM Agent, failure prediction hoặc target lịch sử. Chưa có kết quả Top-k/Traceability/Visible Log Reduction V3; không dùng sơ đồ này như báo cáo tiến độ thực nghiệm.
