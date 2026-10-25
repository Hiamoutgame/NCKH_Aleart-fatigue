# Dataset modules — registry hiện hành

**23/10/2026.** Ba module tham gia CLI; vai trò nghiên cứu là dự kiến sau audit, không tự chứng nhận external ranking eligibility.

| Slug | Vai trò dự kiến | Đơn vị code hiện tại | README |
| --- | --- | --- | --- |
| `rcaeval` | Primary candidate | Case | [RCAEval](rcaeval/README.md) |
| `lemma_rca` | External/backup candidate | Scenario hard-code | [LEMMA-RCA](lemma_rca/README.md) |
| `nezha` | Secondary/external candidate | Fault window | [Nezha](nezha/README.md) |

Thư mục này chứa code, không chứa raw. Raw thật tại `data/raw/` (default của code); `--data-root` override từng dataset. `_template/` chỉ là sườn, không có trong registry.

Không import chéo giữa datasets; shared chứa canonical schema/ports/helpers. CLI composition ở `src/interface/datasets_cli.py`, runtime paths ở `src/shared/infrastructure/paths.py`. `dataset.yaml` chưa được loader đọc làm runtime config. CP1/archive được nhắc ở docs cũ không hiện diện trong checkout active.

[Implementation status](../../docs/status/implementation_status.md) chỉ rõ export caps, mapping và metadata gaps. [Thêm dataset](../../docs/code/src_docs/ADD_A_DATASET.md) mô tả bước mở rộng; không lấy số rows hoặc nhãn code gán để chứng minh khoa học.
