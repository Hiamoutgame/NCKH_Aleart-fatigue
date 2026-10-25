# Handoff — V3 Log Organization & Service RCA

**Đồng bộ 23/10/2026.** Bản đầy đủ và nguồn scope chuẩn: [NCKH_MASTER_CONTEXT_2026-10-23.md](../../NCKH_MASTER_CONTEXT_2026-10-23.md). Không dùng bản handoff ngắn này thay bằng chứng source/audit.

## 1. Bài toán và working decisions

Nghiên cứu offline: incident → service → log groups → raw references, có thể bổ sung evidence links và xếp hạng service để ưu tiên điều tra. Giữ toàn bộ raw events, không coi correlation là causation, không biến service labels thành log-level ground truth. Trusted inventory, split theo incident/source groups, không dùng test labels làm features/tuning.

V1 WARNING-only/LLM Agent và V2 failure prediction là lịch sử. Tên/RQ/novelty chưa được Prof. Long duyệt; parser/model/features/targets/split tỷ lệ chưa chốt. Timeline 8 tuần là kế hoạch gốc, không phải tiến độ hiện tại.

## 2. Repo thực tế

- Source active: `src/`, có adapters RCAEval/LEMMA-RCA/Nezha, schema, regex normalization và CLI.
- Raw thật: `data/raw/`; metadata audit L0/L1: `scripts/audit/` (script) + `data/audit/` (artifact).
- `paths.py` mặc định đọc raw ở `data/raw/` (sửa ngày 25/10/2026); `Resource/cp1/` không có active. Không lấy `.kilo/worktrees/` làm source hiện hành.
- Canonical outputs: `data/normalized/<slug>/`. Footer 23/10: RCAEval 735/735/5,272,618; LEMMA 4/4/200,000; Nezha 21/21/71,173, theo thứ tự incident/GT/log rows. Counts không chứng minh eligible coverage.

## 3. Khoảng trống phải biết

[Implementation status](../status/implementation_status.md): RCAEval cap 30 case mặc định; LEMMA 50,000 logs/scenario, hard-code labels và rút multi-target; Nezha metadata loop tạo item cuối mỗi bucket và export logs incident đầu. Mapping/time/provenance còn cần kiểm chứng. `log_id` là event ID hiện có; template key là regex-normalized MD5, chưa phải Drain3/semantic clustering.

Chưa có group/tree/evidence graph/ranker/training/held-out evaluation V3 trong source active. Training note System One là phương án MVP, chưa phải code đã chạy. Chưa có metric hoặc novelty V3 xác nhận.

## 4. Làm tiếp theo thứ tự

Reconcile paths → case eligibility/labels/windows/inventory → canonical provenance và split groups → template baseline/hierarchy → optional links → service scores/ranker → held-out metrics/ablation/error analysis → paper. [Protocol V3](../research/research_protocol_v3.md) giữ các lựa chọn ở trạng thái đề xuất.

Thiếu labels/join đáng tin thì chưa hứa service RCA; có thể tiếp tục grouping/exploration. Thiếu edge labels thì không claim causal graph accuracy. User-study benefit chưa có bằng chứng từ reduction đơn thuần.

## 5. Cách làm việc

Tiếng Việt dễ hiểu theo [OUTPUT.md](../../OUTPUT.md). Phân biệt SOURCE FACT / HISTORICAL REPORT / PROPOSAL / INFERENCE / UNVERIFIED. Không bịa tên service, paper result, số đo hoặc implementation. [Validation](../status/validation_report.md) ghi chính xác kiểm tra mới; [history](../history/resource_docs/README.md) giữ V1/V2 và báo cáo cũ.
