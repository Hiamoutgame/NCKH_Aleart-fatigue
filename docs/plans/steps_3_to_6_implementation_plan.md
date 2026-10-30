# Kế hoạch triển khai bước 3–6: cửa sổ trước/sau lỗi, gom nhóm, IncidentView/state, xếp hạng

Viết ngày 29/10/2026 cho agent triển khai (Gemini 3.8 Flash High). Người duyệt là chủ dự án.

Đọc trước khi code:
- [AGENTS.md](../../AGENTS.md)
- [baseline.md](../research/05_methodology/baseline.md)
- [ai_model_integration.md](../research/04_proposed_system/ai_model_integration.md)
- [data_flow.md](../research/04_proposed_system/data_flow.md)
- [pineline_training_model.md](../notes/pineline_training_model.md), Phụ lục B (công thức feature)

## 0. Hiện trạng (đã kiểm tra 29/10/2026)

| Bước | Trạng thái | Ở đâu |
| --- | --- | --- |
| 1. Chuẩn hóa | ✅ Xong, `verify` đạt | `data/normalized/{rcaeval,nezha}/`. `log_events.parquet` có cả `template_id` (regex, G1) và `drain_template_id` (Drain, G2); **mỗi incident là một row group** |
| 2. Split | ✅ Đã sinh, chưa có khóa chống ghi đè | `src/evaluation/split.py`, `splits.parquet`. RCAEval: train 254 / val 48 / test 57 incident (82 / 16 / 19 kịch bản). Nezha: 101 `external_test` |
| 3. Trước / sau lỗi | ❌ Chỉ có trong `scripts/pilot_relative_improvement.py` | — |
| 4. Gom nhóm | ⚠️ Có template mỗi log, chưa có bảng nhóm | — |
| 5. IncidentView + `state` | ❌ | — |
| 6. Xếp hạng | ⚠️ R1–R3 chỉ có trong script pilot | Metric và bootstrap đã có ở `src/evaluation/metrics.py` |

Số liệu dùng để tự kiểm tra:

| | RCAEval | Nezha |
| --- | --- | --- |
| Incident có log | 359 | 101 |
| Dòng trong `log_events` | 49,652,771 | 4,176,325 |
| Số nhóm `(service, template_id)` (G1) | 4,586,232 | 85,776 |
| Số nhóm `(service, drain_template_id)` (G2) | 103,560 | 16,755 |
| Coverage (service đáp án có log trong chính incident) | 92.8% (333/359) | 100% |

`.venv/bin/python -m pytest -q` hiện cho **56 passed**.

## 1. Luật bắt buộc (vi phạm là sai, kể cả khi test pass)

1. **Không sửa** `data/raw/`, `data/normalized/*/log_events.parquet`, `incidents.parquet`, `ground_truth.parquet`, `splits.parquet`. Không chạy lại `normalize` hay `split`.
2. **Rò rỉ đáp án:**
   - Tên case RCAEval chứa đáp án (`re2ob_currencyservice_delay_2`). `incident_id`, `log_id`, `source_case_id`, `source_file`, `raw_record_ref`, `scenario_id` đều chứa tên case.
   - `incidents.parquet` có `raw_label` và `fault_type`.
   - Không giá trị nào kể trên được vào feature, `state` hay danh sách ứng viên.
   - Code tạo feature/`state` **không được nhận** ground truth làm tham số.
   - **Cũng không truyền cả object `Incident`** vào các hàm đó, vì object này chứa `raw_label` và `fault_type`. Chỉ truyền đúng trường cần (`system_id`). Khi đọc `incidents.parquet`, luôn ghi rõ danh sách cột.
3. **Không dùng test để chọn gì cả:**
   - Học (LogReg, Kev fine-tune, danh sách ứng viên) chỉ trên `train`.
   - Chọn cấu hình chỉ trên `val`.
   - Lệnh chạy trên `test` hoặc `external_test` phải có cờ `--allow-test`.
4. **RAM máy chỉ 7 GB** (thường trống khoảng 2 GB). Xử lý theo 2 cấp:
   - **Cấp 1, theo incident:** không bao giờ đọc cả `log_events.parquet` một lần. Luôn đọc theo row group (= incident) và chỉ lấy cột cần.
   - **Cấp 2, theo batch trong incident:** khi quét log gốc (Task 3), dùng `ParquetFile.iter_batches(batch_size=20_000, row_groups=[i], columns=...)` thay vì nạp cả row group.
   - Số đo trên incident lớn nhất (314,211 dòng, đủ các cột text), peak RSS của cả tiến trình: `read_row_group` + `to_pandas` khoảng 1,300 MB; `iter_batches` khoảng 500 MB. Trung bình mỗi incident 138,308 dòng.
5. **Phụ thuộc giữa module:**
   - Module cùng cấp trong `src/` không import lẫn nhau, trừ khi kế hoạch này cho phép.
   - Chỉ `src/integrations/kev/` được biết Kev tồn tại.
   - Không sửa `third_party/kev/`; chỉ đọc để biết định dạng API.
6. **Cách viết code:** giống code hiện có, gồm type hints, docstring ngắn, `from __future__ import annotations`, đường dẫn lấy từ `src/shared/infrastructure/paths.py`. Mỗi task phải có test và chạy `pytest -q` đủ xanh trước khi sang task sau.
7. **Không commit, không push.** Để chủ dự án commit.
8. Thư viện mới duy nhất được thêm là `scikit-learn` (cho R4/R5), ghi vào `requirements.txt`. Gọi HTTP dùng `httpx`, đã cài sẵn.

## 2. Thư mục và file đầu ra

```text
src/
  shared/infrastructure/log_table.py   (+ hàm đọc theo incident, Task 1)
  windowing/        __init__.py, windows.py                    (Task 2)
  grouping/         __init__.py, groups.py                     (Task 3)
  views/            __init__.py, incident_view.py, state.py    (Task 5)
  ranking/          __init__.py, base.py, rules.py, candidates.py, features.py, logreg.py   (Task 4, 6, 7)
  integrations/kev/ __init__.py, client.py, ranker.py, export.py                        (Task 9)
  interface/pipeline_cli.py                                    (Task 8)
scripts/run_pipeline.py, run_pipeline.sh                       (Task 8, bắt chước run_datasets.*)

data/artifacts/<dataset>/
  groups_g1/groups.parquet + manifest.json
  groups_g2/groups.parquet + manifest.json
  candidates.json                    (chỉ RCAEval, học từ train)
  views_<g1|g2>.jsonl                (một IncidentView mỗi dòng, không có nhãn)
  models/r4/, models/r5/             (model.joblib + config.json)
  kev/train.jsonl, kev/val.jsonl     (Task 9)
data/runs/<run_id>/predictions.parquet, metrics.json, manifest.json
```

`manifest.json` dùng lại `src/shared/infrastructure/manifest.py` (`write_manifest`, `sha256_file`, `git_state`).

## 3. Các task, làm theo đúng thứ tự

### Task 0: khóa split

- Lệnh `split` trong [datasets_cli.py](../../src/interface/datasets_cli.py):
  - nếu `verify_splits(...)["passed"]` là False thì **không ghi file**, exit code 2;
  - nếu `splits.parquet` đã có thì từ chối ghi đè, trừ khi có cờ `--force`.
- Thêm `load_splits(normalized_dir) -> pd.DataFrame` vào `src/evaluation/split.py`. Hàm này kiểm tra sha256 của file khớp với `split_manifest.json`; không khớp thì raise.
- **Test:** chạy `split` hai lần, lần hai phải lỗi; sửa 1 byte trong `splits.parquet` thì `load_splits` raise.

### Task 1: đọc `log_events` theo incident

Thêm vào [log_table.py](../../src/shared/infrastructure/log_table.py):

```python
def incident_row_groups(path) -> dict[str, int]:
    """incident_id -> row group index, from column statistics (min == max); raise if a group mixes incidents."""
def read_incident(path, incident_id, columns) -> pd.DataFrame: ...
def iter_incident_ids(path) -> Iterator[tuple[str, int]]: ...   # (incident_id, row group index), không đọc dữ liệu log
def iter_incident_batches(path, row_group, columns, batch_size=20_000) -> Iterator[pd.DataFrame]: ...
```

- `read_incident` chỉ dùng khi cần ít dòng hoặc ít cột. Quét log gốc thì dùng `iter_incident_batches`.
- **Test:** dữ liệu giả 2 incident → đọc lại đúng từng incident; ghép các batch lại bằng đúng `read_incident`, đúng thứ tự dòng. Trên dữ liệu thật: `len(incident_row_groups(...)) == 359` (RCAEval) và `== 101` (Nezha).

### Task 2: cửa sổ trước / sau lỗi (`src/windowing/windows.py`)

```python
@dataclass(frozen=True)
class WindowConfig:
    before_seconds: float | None = None   # None = lấy hết log trước lỗi
    after_seconds: float | None = None    # None = lấy hết log sau lỗi

def assign_windows(timestamps: pd.Series, inject_time: pd.Timestamp, config: WindowConfig) -> pd.Series:
    """'before' nếu ts < inject_time (và trong before_seconds), 'after' nếu ts >= inject_time
    (và trong after_seconds), còn lại 'outside' (gồm NaT)."""
def offset_seconds(timestamps, inject_time) -> pd.Series   # ts - inject_time, tính bằng giây
```

- `inject_time` chỉ dùng để chia cửa sổ và tính độ lệch tương đối. Không bao giờ đưa giờ tuyệt đối vào feature hay `state`.
- Không ghi file `windows.parquet`: tính lại khi cần, vì nhanh, và ghi `WindowConfig` vào manifest của bước dùng nó.
- **Test:**
  - đúng thời điểm lỗi tính là `after`;
  - NaT là `outside`;
  - có giới hạn giây thì phần vượt giới hạn là `outside`;
  - case RCAEval không có log trước lỗi vẫn chạy được.

### Task 3: bảng nhóm (`src/grouping/groups.py`)

**Khóa nhóm:** `(incident_id, service_id, template_key)` với `method ∈ {"g1", "g2"}`.
- `template_key` = `template_id` (g1) hoặc `drain_template_id` (g2).
- Nếu template rỗng mà `raw_message` khác rỗng: khóa = `"raw:" + md5(raw_message)[:12]`.
- Nếu `raw_message` rỗng: khóa = `"log:" + log_id`, tức mỗi log một nhóm riêng (Phụ lục B: không gom mọi giá trị thiếu vào một nhóm).
- `service_id` null giữ là null. Đây là nhóm "chưa rõ service" và **không bao giờ** là ứng viên.

`group_id = f"{method}:" + md5(f"{incident_id}|{service_id}|{template_key}")[:16]`. Giá trị này cố định qua các lần chạy.

**Cột của `groups.parquet`** (mỗi incident một row group):

| Cột | Ý nghĩa |
| --- | --- |
| `group_id`, `method`, `incident_id`, `service_id`, `template_key` | Khóa |
| `template_text` | g2: `drain_template`; g1: `parsed_message` của dòng đầu tiên; nếu không có thì `raw_message` cắt còn 300 ký tự |
| `n_logs`, `n_before`, `n_after`, `n_outside` | Số log theo cửa sổ |
| `n_error`, `n_warn`, `n_unknown_severity` | Đếm trên **toàn nhóm**. ERROR = `severity ∈ {"ERROR", "FATAL"}`, WARN = `"WARN"`, unknown = null |
| `n_error_after`, `n_warn_after`, `n_unknown_after` | Như trên, chỉ trong cửa sổ `after` |
| `first_offset_s`, `last_offset_s`, `first_after_offset_s` | Giây so với thời điểm lỗi, có thể âm |
| `is_new_after` | `n_before == 0 and n_after > 0` |
| `example_log_ids` | Tối đa 3 `log_id` đầu tiên theo thời gian, dùng làm bằng chứng mở lại dòng gốc |

**Cách tính: cộng dồn qua các batch.** Với mỗi incident, duyệt `iter_incident_batches`. Trong từng batch, `groupby` theo khóa rồi gộp kết quả vào một dict `{template khóa → thống kê}`. Kết quả phải giống hệt khi tính trên cả incident một lượt. Quy tắc gộp:

| Trường | Cách gộp qua batch |
| --- | --- |
| Mọi cột `n_*` | Cộng |
| `first_offset_s`, `first_after_offset_s` | `min`. `first_after_offset_s` chỉ xét dòng thuộc cửa sổ `after`; chưa có dòng nào thì để `None`, không để 0 |
| `last_offset_s` | `max` |
| `example_log_ids` | Giữ tối đa 3 `log_id` gặp đầu tiên. Đúng theo thời gian vì `log_events` đã sắp theo thời gian trong từng incident (NaT ở cuối) |
| `template_text` | Giữ giá trị gặp đầu tiên |

Hai bẫy cần tránh:
- `is_new_after` **chỉ tính sau khi đã gộp xong cả incident**. Tính trong từng batch sẽ sai: một nhóm có thể chưa thấy log `before` trong batch này nhưng có ở batch khác.
- Không gộp bằng vòng lặp Python trên từng dòng log (49.6 triệu dòng). Gộp trên kết quả `groupby` của từng batch.

Bộ nhớ của dict tỉ lệ với số nhóm: g2 tối đa 1,526 nhóm mỗi incident, g1 tối đa 29,682 nhóm.

- **Không tạo `group_members.parquet`** (49.6 triệu dòng). Thành viên của nhóm lấy lại bằng `members(log_events_path, group) -> pd.DataFrame`: đọc row group của incident theo batch rồi lọc theo cùng khóa. Ghi chú quyết định này vào `data_flow.md`.
- Chạy `build_groups(dataset, method, window_config)`, ghi vào `data/artifacts/<dataset>/groups_<method>/`. Đọc `incidents.parquet` chỉ với 2 cột `incident_id`, `inject_time`.
- **Kiểm tra lúc build** (sai thì raise):
  - trong mỗi incident, tổng `n_logs` = số dòng của incident;
  - `n_before + n_after + n_outside == n_logs`;
  - `group_id` không trùng.
- **Test:**
  - dữ liệu giả có log thiếu service, message rỗng, template rỗng;
  - `members()` trả đúng `n_logs` dòng;
  - **không phụ thuộc cỡ batch:** cùng dữ liệu với `batch_size` = 1, 7 và 20,000 cho ra bảng nhóm giống hệt, gồm cả trường hợp log `before` và `after` của một nhóm nằm ở hai batch khác nhau (`is_new_after` phải là False);
  - trên dữ liệu thật, tổng số nhóm g1 / g2 khớp bảng ở mục 0, **với điều kiện** khóa thiếu-template không đổi số nhóm. Nếu lệch, ghi rõ lệch bao nhiêu và vì sao.

### Task 4: danh sách ứng viên (`src/ranking/candidates.py`)

```python
def train_inventory(groups_path, splits) -> dict[str, list[str]]   # system_id -> service sắp tăng dần
def observed_candidates(view) -> list[str]                          # service có ≥1 log trong incident
```

- `train_inventory`: hợp các `service_id` khác null xuất hiện trong nhóm của **các incident train** của từng hệ thống. Lưu vào `data/artifacts/rcaeval/candidates.json`, kèm số incident train dùng để học.
- Chế độ ứng viên dùng cho mỗi dataset:
  - RCAEval: `train_inventory`;
  - Nezha (không có train) và demo: `observed_candidates`.

  Ghi chế độ đã dùng vào manifest của mỗi lần chạy.
- Báo coverage (đáp án nằm trong danh sách ứng viên) riêng cho train, val và test. Coverage tính trong lúc đánh giá, ở Task 8, không phải trong hàm này.
- **Test:** đổi ground truth của một incident thì danh sách ứng viên không đổi (hàm không nhận ground truth); incident val/test không làm thay đổi `train_inventory`.

### Task 5: IncidentView và `state` (`src/views/`)

```python
@dataclass(frozen=True)
class GroupSummary: group_id, template_text, n_before, n_after, n_error_after, n_warn_after, is_new_after, first_after_offset_s
@dataclass(frozen=True)
class ServiceView: service_id, n_before, n_after, n_error_after, n_warn_after, n_unknown_after, n_templates_after, groups: tuple[GroupSummary, ...]
@dataclass(frozen=True)
class IncidentView: incident_id, system_id, method, before_seconds, after_seconds, services: tuple[ServiceView, ...]
def build_view(incident_id: str, system_id: str, groups_frame: pd.DataFrame) -> IncidentView
```

- `build_view` chỉ nhận đúng các tham số trên. **Không nhận** object `Incident`, `raw_label`, `fault_type`, ground truth. Offset so với thời điểm lỗi đã có sẵn trong bảng nhóm, nên không cần `inject_time`.
- Service sắp theo tên. Nhóm "chưa rõ service" để riêng, không nằm trong `services`.
- `before_seconds` / `after_seconds` = độ dài thực tế của log có trong cửa sổ, tính từ offset.
- `IncidentView` ghi ra `views_<method>.jsonl` có kèm `incident_id`, để join với split. `state` thì không chứa `incident_id`.

`render_state(view, candidates, config: StateConfig) -> str`:

```python
@dataclass(frozen=True)
class StateConfig:
    include_before: bool = True          # False = ablation A1
    include_template_text: bool = True   # False = ablation A2
    include_severity: bool = True        # False = ablation A3
    max_new_templates: int = 3
    max_frequent_templates: int = 2
    max_template_chars: int = 160
    max_chars: int = 12_000              # khoảng 3–4k token; đo token thật sau ở môi trường Kev
```

Định dạng cố định (tiếng Anh, vì Kev được train chủ yếu bằng tiếng Anh):

```text
System: ob. Logs after the alert: 1,240 over 12 min. Logs before: 310 over 12 min.
Service cartservice: 1,240 logs after (before: 310). ERROR 412, WARN 0, unknown level 828.
  New after alert: [412] "Can't access cart storage. StackExchange.Redis.RedisTimeoutException <*>"
  Most frequent after alert: [620] "GetCartAsync called with userId=<*>"
Service emailservice: no logs.
```

- Liệt kê **mọi** ứng viên theo thứ tự tên, kể cả service không có log.
- **Xóa mảnh thời gian trong template trước khi đưa vào `state`.** `normalize_message` chỉ che một phần ngày giờ, nên template vẫn còn ngày và giờ thật, ví dụ `{"t":{"$date":"<N>-<N>-18T16:<N>:<N>+<N>:<N>"}` và `created_time:"<N>-<N>-15T18:...`.
  - Đo trên `drain_template` của RCAEval: 887 template (đếm theo từng incident) trong **217/359 incident**. Template còn có tên tháng (`Jan <N>`).
  - Vì các kịch bản được chạy nối tiếp nhau, model có thể học "ngày 18 lúc 16 giờ → service X" thay vì học từ nội dung log (suy luận, chưa đo).
  - Viết `scrub_time(text) -> str` trong `state.py`, thay các mẫu sau bằng `<TIME>`:

    ```python
    TIME_FRAGMENT_RE = re.compile(
        r"(?:<N>|\d+)-(?:<N>|\d+)-(?:<N>|\d{1,2})[T ](?:<N>|\d{1,2})[:-](?:<N>|\d{1,2})(?:[:-](?:<N>|\d{1,2}))?"
        r"(?:[.,](?:<N>|<HEX>|\d+))?(?:Z|[+-](?:<N>|\d{1,2})(?::?(?:<N>|\d{2}))?)?"
    )
    MONTH_DAY_RE = re.compile(r"\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)?\s*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(?:<N>|\d{1,2})(?!\d)")
    # Áp dụng TIME_FRAGMENT_RE trước, MONTH_DAY_RE sau.
    ```

  - Đã thử hai regex này trên toàn bộ `drain_template` và `parsed_message` của RCAEval và Nezha: sau khi thay, 3 mẫu thời gian ở test 1 bên dưới còn **0** kết quả.
  - Chỉ áp dụng khi render `state`. Không sửa `groups.parquet` hay `log_events`.
- Nếu quá `max_chars`: giảm số template mỗi service theo thứ tự 3→2→1→0, rồi cắt ngắn `template_text`. Không bao giờ bỏ dòng `Service ...`.
- Trả kèm thông tin `state_chars` và `truncated`.
- Các cờ ablation chỉ ẩn đúng phần của mình:
  - `include_before=False` ẩn mọi số "before" và dòng "New after alert" (vì "new" cần biết phần before);
  - `include_template_text=False` ẩn mọi dòng template;
  - `include_severity=False` ẩn phần ERROR/WARN/unknown.
- **Bốn test chống rò rỉ, bắt buộc** (trong `tests/test_leakage.py`):
  1. **Quét chuỗi cấm:** với `state` của **mọi** incident RCAEval và Nezha (g1 và g2), và mọi dòng JSONL ở Task 9, không có chuỗi nào sau đây:
     - `incident_id`, `source_case_id`, `scenario_id` của **chính** incident đó, so **nguyên chuỗi**;
     - `data/`, `.parquet`, `.csv`;
     - mảnh thời gian: `\d{4}-\d{2}-\d{2}`, `\b\d{1,2}T\d{1,2}\b`, `\b\d{2}:\d{2}:\d{2}\b`.

     Không dùng riêng mẫu `\d{4}-\d{2}-\d{2}`: mẫu này có **0** kết quả trên template thật vì số đã bị đổi thành `<N>`, nên test luôn đạt mà không kiểm được gì.
  2. **Đổi nhãn không đổi đầu ra (metamorphic / invariance test):** test phải chạy **cả chuỗi xử lý**, không chỉ gọi một hàm. Vì hàm không nhận nhãn thì test ở mức hàm luôn đạt.
     - Trên bộ dữ liệu giả ghi ra đĩa: chạy `group` → `views` → `render_state` → feature của Task 7;
     - sửa `ground_truth.parquet` và cả `raw_label`, `fault_type` trong `incidents.parquet` thành giá trị giả;
     - chạy lại, so sánh: `state`, bảng feature và `candidates.json` phải **giống hệt từng byte**.
  3. **Tên service trùng trong tên case:** tên case `re2ob_cartservice_cpu_1` chứa `cartservice`. Bộ quét chỉ cấm nguyên tên case và mã kịch bản. Test: `cartservice` vẫn nằm trong ứng viên, trong `criteria`, và trong dòng `Service cartservice:` của chính incident đó. Không viết bộ lọc xóa từng phần của tên case.
  4. **Chữ ký hàm:** dùng `inspect.signature` kiểm tra `build_view`, `render_state`, hàm tạo feature, `train_inventory`: không có tham số tên `ground_truth`, `label`, `raw_label`, `fault_type`, và không có tham số kiểu `Incident`.

  Giới hạn cần nhớ: bốn test này không chứng minh hết mọi kiểu rò rỉ. Nội dung log vẫn có thể chứa dấu vết của lỗi; đó là tín hiệu hợp lệ khi log do hệ thống tự ghi. Quét `drain_template` RCAEval cho thấy tên case xuất hiện 0 lần. Từ khóa `chaos`, `stress`, `inject`, `kill`, `fault`, `oom` chỉ xuất hiện ở 4 template trong 2 incident (`re2ss_orders_disk_1`, `_2`): `Killed` và thông báo tín hiệu của MongoDB là log hệ thống, còn `javax.inject.Inject` là tên annotation Java.
- **Test `scrub_time`:** hai ví dụ thật ở trên đều biến thành `<TIME>`; chuỗi không có thời gian giữ nguyên.
- **Test định dạng:** dữ liệu giả cho ra đúng từng ký tự như mẫu trên; cùng input thì cùng output.

### Task 6: interface xếp hạng và baseline luật (`src/ranking/base.py`, `rules.py`)

```python
@dataclass(frozen=True)
class RankedService: service_id: str; score: float; rank: int; supporting_group_ids: tuple[str, ...]; method: str
class ServiceRanker(ABC):
    name: str
    def rank(self, view: IncidentView, candidates: Sequence[str]) -> list[RankedService]: ...
```

**Hợp đồng chung:**
- trả **đúng một lần** mỗi ứng viên, không trả service ngoài danh sách (raise nếu vi phạm);
- sắp theo `(-score, service_id)`, giống hệt `order_by_score` trong `src/evaluation/metrics.py`. Không import chéo: viết lại hàm sắp trong `ranking`, và thêm một test so hai hàm cho cùng kết quả;
- `rank` bắt đầu từ 1.

**Ba baseline luật:**
- R1 `MostLogsAfter`: score = `n_after`.
- R2 `MostErrorsAfter`: score = `n_error_after`.
- R3 `GrowthAfter`: score = `n_after / (n_before + 1)`.

**Bằng chứng** `supporting_group_ids`: tối đa 3 nhóm của service đó, chọn theo quy tắc cố định: `is_new_after` trước, rồi `n_error_after`, rồi `n_after` giảm dần, rồi `group_id`. Ghi tên quy tắc vào `method`, ví dụ `"r2|evidence:new>error>count"`.

R0 (ngẫu nhiên) **không** là ranker. Khi đánh giá, tính bằng `expected_random_hit` và `expected_random_reciprocal_rank` có sẵn.

**Test hồi quy bắt buộc**, so với kết quả pilot đã chạy:
- Dùng `observed_candidates`, nhóm g1 hoặc g2 (đếm theo service nên không phụ thuộc cách gom), `WindowConfig()` mặc định.
- Top-1, Top-3 và 1/hạng của R1/R2/R3 phải **trùng từng case** với `data/runs/pilot_relative_improvement_2026-10-26/per_case.csv`, cột `R1_top1` … `R3_rr`, trên cả 359 case.
- Nếu lệch, dừng lại và báo; không chỉnh test cho khớp.
- Lý do phải khớp: pilot dùng cùng quy tắc ERROR (`extract_explicit_severity ∈ {ERROR, FATAL}`), cùng mốc `timestamp >= inject_time`, cùng cách bỏ `container_name` null, cùng cách phá hòa theo tên.

### Task 7: Logistic Regression R4 / R5 (`src/ranking/features.py`, `logreg.py`)

**Feature** tính từ `ServiceView` cho mỗi cặp (incident, ứng viên), theo Phụ lục B nhưng **chỉ trên cửa sổ `after`**, vì demo chỉ có log sau cảnh báo:

| Bộ | Feature |
| --- | --- |
| R4 basic | `has_logs`, `log_count`, `log_rate` (= `n_after / after_seconds`), `service_log_share`, `error_count`, `warn_count`, `error_ratio`, `warn_ratio`, `unknown_severity_ratio` |
| R5 = R4 + | `unique_template_count`, `dominant_template_share`, `new_template_count` (số nhóm `is_new_after`), `new_template_log_share`, `first_seen_offset_ratio` (offset đầu tiên sau lỗi / `after_seconds`), `growth_ratio` (= `n_after / (n_before + 1)`) |

- Ứng viên không có log: mọi số đếm và tỉ lệ bằng 0, `has_logs = 0`. Không cần imputer. Chia cho 0 thì ra 0.
- **Feature không được có:** tên service, `system_id`, ID, giờ tuyệt đối, `fault_type`. Có test kiểm danh sách cột đúng tên và thứ tự, và mọi giá trị hữu hạn.
- **Model:** `Pipeline(StandardScaler(), LogisticRegression(class_weight="balanced", max_iter=1000))`.
  - Fit **chỉ trên train**, với nhãn `y = 1` nếu ứng viên là service đáp án.
  - Chọn `C ∈ {0.01, 0.1, 1, 10}` theo MRR trên val; hòa thì lấy `C` nhỏ hơn.
  - Score khi xếp hạng = `predict_proba[:, 1]`.
  - Incident có đáp án không nằm trong ứng viên vẫn đưa vào train (toàn nhãn 0), và ghi lại số lượng.
- Lưu `model.joblib` + `config.json` (feature list, C đã chọn, MRR val của từng C, số incident và số dòng train) vào `data/artifacts/rcaeval/models/r4|r5/`.
- **Test:** dữ liệu giả tách rõ thì R4 xếp đúng; đổi nhãn val không làm đổi model đã fit; hàm fit báo lỗi nếu nhận incident không thuộc train.
- **Kiểm tra xáo nhãn, chạy một lần trên dữ liệu thật:** fit lại với nhãn train bị xáo ngẫu nhiên (seed 42), giữ nguyên feature. Top-1 trên val phải gần R0 (khoảng tin cậy của Δ so với R0 chứa 0). Nếu vẫn cao rõ rệt, nghĩa là feature hoặc cách đánh giá đang lộ đáp án: dừng lại và báo.

### Task 8: CLI và chạy đánh giá (`src/interface/pipeline_cli.py`)

```bash
bash run_pipeline.sh group rcaeval --method g2            # Task 3
bash run_pipeline.sh candidates rcaeval                   # Task 4
bash run_pipeline.sh views rcaeval --method g2            # Task 5
bash run_pipeline.sh train-logreg rcaeval --features r4   # Task 7
bash run_pipeline.sh rank rcaeval --ranker r2 --method g2 --split val [--allow-test]
bash run_pipeline.sh evaluate --run <run_id> [--baseline <run_id>|r0]
```

**`rank`** ghi `data/runs/<run_id>/predictions.parquet`:
- cột: `incident_id`, `service_id`, `score`, `rank`, `supporting_group_ids`, `method`;
- `run_id = <dataset>_<ranker>_<method>_<split>_<yyyymmdd-hhmmss>`;
- kèm `manifest.json`: ranker, method, split, chế độ ứng viên, `WindowConfig`, `StateConfig`, sha256 của `splits.parquet` và `groups.parquet`, `git_state()`.

**`evaluate`:**
- đọc predictions và ground truth, tạo `IncidentRanking` cho từng incident, gọi `summarize(ks=(1, 3, 5))`;
- nếu có baseline thì gọi `paired_bootstrap` với `groups = scenario_id` lấy từ `splits.parquet`, 1000 lần lặp, seed 42, cho Top-1, Top-3 và MRR. `r0` nghĩa là baseline ngẫu nhiên tính theo công thức;
- báo cả **end-to-end** lẫn **conditional**, coverage, tỉ lệ hòa ở hạng 1, và chia theo `stratum` (RE2/RE3 × hệ thống);
- ghi ra `metrics.json`.

Lệnh `rank` / `evaluate` với `--split test` hoặc `external_test` mà không có `--allow-test` phải thoát với lỗi. **Agent không chạy test.**

**Chạy để nghiệm thu (chỉ trên val):**
- `group` g1 và g2 cho cả hai dataset;
- `candidates`, `views`;
- R1, R2, R3, R4, R5 trên `val` của RCAEval;
- `evaluate` từng run so với `r0` và so R5 với R2.

Dán bảng kết quả val vào báo cáo cuối.

### Task 9: Kev (`src/integrations/kev/`), chỉ code và test với server giả

Agent **không** tải model và không chạy GPU. Chạy thật sẽ làm sau trên Colab/Kaggle, theo [kev_bat_dau_colab_kaggle.md](../notes/kev_bat_dau_colab_kaggle.md).

- `client.py`, `KevClient(base_url="http://127.0.0.1:8009", timeout=120, api_key=os.environ.get("KEV_API_KEY"))`:
  - `choice(state, options, instructions) -> dict[str, float]` gửi `POST /v1/systemone`:

    ```json
    {"state": "...", "model": "kev-latest",
     "questions": {"root_cause": {"type": "choice",
       "instructions": "Which service is the most likely root cause of this incident?",
       "criteria": {"adservice": null, "cartservice": null}}}}
    ```

  - đọc `response["answers"]["root_cause"]["probabilities"]`;
  - kiểm tra key đúng bằng tập options và tổng xác suất ≈ 1, sai thì raise;
  - lỗi 422 (state quá dài) thì raise kèm nội dung lỗi; không tự cắt `state`.
- Trước khi viết `permute(...)` (endpoint `/v1/systemone/permute`), đọc `third_party/kev/kev/serve.py` (khoảng dòng 262) để lấy đúng định dạng request/response. Đây là phần tùy chọn: nếu không chắc định dạng thì để `NotImplementedError` và ghi chú lại.
- `ranker.py`, `KevRanker(ServiceRanker)`: `render_state` → `choice` (options theo tên) → `RankedService` (score = xác suất), bằng chứng theo cùng quy tắc của Task 6. `name = "kev-<model>"`, trong đó model đọc từ `GET /v1/models` nếu có.
- `export.py`, `export_jsonl(split, ...)`: ghi `data/artifacts/rcaeval/kev/{train,val}.jsonl`, theo định dạng fine-tune của README Kev, mỗi dòng là:

  ```json
  {"state": "...", "questions": {"root_cause": {"type": "choice", "instructions": "...", "criteria": {...}, "label": "cartservice"}}}
  ```

  - Bỏ incident có đáp án không nằm trong ứng viên, và ghi số lượng vào `export_manifest.json`.
  - Từ chối `split="test"`.
- **Test** dùng `httpx.MockTransport`:
  - parse đúng xác suất;
  - option thừa hoặc thiếu thì raise;
  - lỗi 422 được báo rõ;
  - file JSONL đúng schema, không chứa ID hay tên case;
  - `label` luôn nằm trong `criteria`.

## 4. Báo cáo cuối của agent

Gửi lại cho chủ dự án:

1. Danh sách file đã tạo hoặc sửa.
2. Số test trước (56) và sau.
3. Kết quả test hồi quy so với pilot (Task 6): khớp bao nhiêu / 359.
4. Số nhóm g1 / g2 thực tế so với mục 0.
5. Coverage của danh sách ứng viên theo train / val.
6. Bảng metric trên **val**: R1–R5 so với R0, so R5 với R2. Mỗi dòng ghi Δ kèm khoảng tin cậy, RI và kết luận `improved`.
7. Độ dài `state` trên val: trung vị và lớn nhất (số ký tự), và số incident bị `truncated`.
8. Kết quả 4 test chống rò rỉ, số template đã bị `scrub_time` sửa, và kết quả kiểm tra xáo nhãn.
9. Peak RSS khi chạy `group` trên RCAEval, và thời gian chạy.
10. Mọi chỗ làm khác kế hoạch, kèm lý do.

Không ghi kết quả test. Không viết "Kev tốt hơn" khi chưa chạy Kev.

## 5. Ngoài phạm vi

- Chạy Kev thật hoặc fine-tune.
- G3 (Kev hỗ trợ gộp nhóm).
- Demo FastAPI / Streamlit.
- Chạy trên test hoặc Nezha.
- Chỉnh `st` / `depth` của Drain. Khi làm sau này, chọn trên val theo MRR, vì không có nhãn nhóm để chỉnh trực tiếp. (`baseline.md` đang ghi "chỉnh trên tập train"; chủ dự án sẽ chốt.)
- Sửa split.
