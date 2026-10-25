# src — kiến trúc dataset hiện có và ranh giới V3

Scope chuẩn: [master context](../../../NCKH_MASTER_CONTEXT_2026-10-23.md). Code ở đây phục vụ đọc/khám phá/chuẩn hóa; grouping/hierarchy/ranking V3 chưa được triển khai trong source active.

## Cây thư mục thật

```text
src/
├── interface/datasets_cli.py      # Registry/composition 3 adapters, list/inspect/normalize
├── shared/
│   ├── domain/                   # Canonical entities, ports, profile models
│   ├── application/              # Profiling use case
│   ├── infrastructure/           # Loaders, paths, normalization, severity
│   └── interface/                # File profiler CLI
├── datasets/
│   ├── rcaeval/                  # Runtime ở infrastructure/adapter.py; layer khác là sườn
│   ├── nezha/                    # Runtime ở infrastructure/adapter.py; layer khác là sườn
│   ├── lemma_rca/                # Domain, use cases, loader/downloader/adapter, CLI/notebook
│   └── _template/                # Sườn thêm dataset, không thuộc registry
├── docs/                         # Architecture, exploration protocol, add dataset
└── legacy/                       # Code cũ để đối chiếu
```

## Dependency rule và hiện trạng

```text
interface/datasets_cli → datasets/{rcaeval,lemma_rca,nezha} → shared
shared không import dataset cụ thể; adapters không import chéo dataset
```

Định hướng layer: domain ← application ← infrastructure/interface. Đây là mục tiêu thiết kế, không phải khẳng định đã tuân thủ hoàn toàn: `shared/domain/canonical.py` import pandas và chứa DataFrame conversion; LEMMA use cases gọi concrete loader. CP1 từng dùng helpers shared nhưng source CP1 không có trong checkout active.

| Layer | Hiện có | Quy tắc khi mở rộng |
| --- | --- | --- |
| domain | Canonical Incident/LogEvent/GroundTruth, ports, profile models | Tách đối tượng/quy tắc khỏi I/O khi có thể; ghi rõ dependency hiện hữu |
| application | Profiling và LEMMA exploration use cases | Điều phối công việc; không đưa nhãn vào inference |
| infrastructure | Source adapters/loaders, paths, regex | Mapping có provenance; không tự chứng nhận labels |
| interface | CLI và notebook | Entry point mỏng, không lẫn proposed command với command đã có |
| dataset.yaml | Nguồn/mapping mô tả | Không được coi là runtime config tự động |

## Contract dữ liệu đang chạy

[canonical.py](shared/domain/canonical.py) định nghĩa:

- `Incident`: identity, dataset/system/source case, start/end/inject time, fault type, raw label.
- `LogEvent`: **log_id**, incident, raw/parsed message, template key, time/service/entity/severity/trace/span, source file/row/ref.
- `GroundTruth`: label level, original/canonical target, fault type, label source, mapping status.

`event_id`/`raw_log_id` trong research handoff tương ứng khái niệm `log_id`, chưa là cột trong code. Không có Group/Edge/Ranking schema hiện hành; [output contracts V3](../../docs/research_protocol_v3.md) là đề xuất.

Tách ground truth thành bảng riêng chưa loại leakage: Incident còn chứa đáp án/metadata lỗi. `template_id` hiện là MD5 chuỗi regex-normalized, không chứng minh đã tích hợp Drain3/Spell. `raw_message` Nezha là extracted message, muốn phục hồi full record phải resolve file/ref.

## Path, lệnh và trạng thái

[paths.py](shared/infrastructure/paths.py) neo theo source nhưng default raw vẫn ở CP1 cũ. Raw thật đã ở `NCKH_rawData/raw_data/`; dùng `--data-root` theo [exploration README](../README.md). Từ root chạy `bash run_datasets.sh --help` để xem lệnh có thật.

Profiler từ `Resource/explore_datasets/`:

```bash
PYTHONPATH=. .venv/bin/python -m src.shared.interface.profile_cli <file> --name <name> --value-cols service message
```

Profiler có thể nạp bảng; tự giới hạn input phù hợp, không mặc định chạy toàn raw. [Implementation status](../../docs/implementation_status.md) ghi limits/lỗi adapter và [validation](../../docs/validation_report.md) ghi kiểm tra đã chạy. Không claim full V3 pipeline hoặc 100% tests từ schema/source tồn tại.
