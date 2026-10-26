# Clean architecture — định hướng và source thực tế

**Cập nhật 23/10/2026.** [src map](../../../src/README.md) mô tả code hiện có; các layer còn là sườn không được ghi thành chức năng hoàn chỉnh.

## 1. Dependency rule đề xuất

```text
interface/datasets_cli → datasets/{rcaeval,nezha}
datasets/<x> → shared
datasets/<x> không import datasets/<y>
shared không import dataset cụ thể
```

Trong module, ưu tiên domain ← application ← infrastructure/interface. Quy tắc này là hướng thiết kế; source hiện có `canonical.py` import pandas/chuyển DataFrame. CP1 từng dùng shared helpers nhưng không có source CP1 active trong checkout này.

## 2. Vai trò layer

| Layer | Hiện trạng | Hướng mở rộng |
| --- | --- | --- |
| Domain | Incident/LogEvent/GroundTruth, profile entities, ports | Tách I/O/conversion khi phù hợp; không mặc định đã thuần Python |
| Application | Profiling use cases | Điều phối; không feed label metadata vào inference |
| Infrastructure | Raw readers, canonical adapters, paths, regex | Mapping/time/provenance có evidence và validation |
| Interface | CLI/notebook, registry composition | Entry points rõ scope/limits |
| dataset.yaml | Metadata mô tả | Chưa được runtime loader dùng làm cấu hình |

## 3. Shared và pipeline V3

Shared giữ contract/helper thực sự dùng chung; không thêm logic riêng của một dataset. Canonical schema chưa có Group/Edge/Ranking. Khi triển khai, dùng `LogEvent.log_id` liên kết group members và provenance; không tự đổi tên schema theo sơ đồ.

Grouping, hierarchy, evidence relationships và service ranking là các bước riêng trong [research protocol](../../research/research_protocol_v3.md), **chưa phải modules tồn tại**. Tách feature allowlist khỏi Incident/GT vì `raw_label` có thể chứa đáp án. Dependency tốt không tự chứng minh dữ liệu không leakage hoặc mapping đúng.

## 4. Những giới hạn cần đối chiếu

Default raw path là `data/raw/`; `--data-root` override từng dataset. Export caps/Nezha iteration, raw payload và timestamp assumptions được liệt kê ở [implementation status](../../status/implementation_status.md). Không mô tả chúng đã được sửa trong lần cập nhật docs.
