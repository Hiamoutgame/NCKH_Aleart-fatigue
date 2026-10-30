# Bản đồ repo và tài liệu

Cấu trúc này có từ ngày 25/10/2026 (branch `restructure`). Đợt này **chỉ di chuyển file và sửa đường dẫn**, không refactor code: package vẫn tên `src`, các lệnh `from src...` giữ nguyên. Kiến trúc tách core/grouping/ranking là đề xuất riêng ở [architecture_proposal_v3.md](status/architecture_proposal_v3.md).

## Cây thư mục

```text
.
├── README.md, AGENTS.md, OUTPUT.md        # lối vào, quy tắc làm việc, cách giải thích
├── NCKH_MASTER_CONTEXT_2026-10-23.md      # context chuẩn V3
├── requirements.txt, pytest.ini, conftest.py
├── run_datasets.sh                        # wrapper gọi scripts/
├── src/                                   # code: adapters, canonical schema, normalization, CLI
├── scripts/                               # entry scripts, export; audit/ = audit L0/L1; legacy/ = setup CP1 cũ
├── tests/                                 # test chung (test riêng dataset nằm trong src/datasets/*/tests)
├── notebooks/                             # khám phá dữ liệu, bài học Kev trên Colab
├── docs/
│   ├── context/                           # mindmap, handoff
│   ├── research/                          # 01 proposal, 02 related work, 03 problem/gap/RQ, 04 hệ thống đề xuất, 05 phương pháp; protocol, requirement (Why)
│   ├── status/                            # implementation status, audit, validation, kiến trúc đề xuất
│   ├── plans/                             # kế hoạch triển khai giao cho agent (bước 3–6)
│   ├── data/                              # dataset plan, README raw, explore_cards/ (data card)
│   ├── notes/                             # ghi chú làm việc, hướng dẫn Kev/Colab, thiết kế training
│   ├── code/                              # hướng dẫn CLI, src_docs/ (clean architecture, add dataset…)
│   ├── history/                           # V1/V2 và bản đồ Resource cũ: không phải specification
│   └── references/                        # PDF paper tham khảo (MRCA, Nezha)
├── paper/                                 # report/ (LaTeX, DOCX), IEEE_template/
├── third_party/kev/                       # Kev vendored, xem UPSTREAM.md
├── data/        (không lên git)           # raw/, normalized/, audit/, output/
└── _personal/   (không lên git)           # tài liệu học tập cá nhân, slide môn học
```

## Đặt file mới ở đâu

| Loại file | Nơi đặt |
| --- | --- |
| Code Python dùng lại được | `src/` |
| Script chạy một lần (audit, export, convert) | `scripts/` |
| Test | `tests/` hoặc `src/datasets/<tên>/tests/` |
| Notebook | `notebooks/` |
| Raw, Parquet, JSONL, checkpoint, output | `data/` (không commit; chia sẻ qua Drive) |
| Tài liệu đang dùng | `docs/<nhóm>/` theo bảng cây thư mục |
| Tài liệu hết hiệu lực | `docs/history/` (giữ nguyên nội dung, thêm nhãn lịch sử) |
| Báo cáo, bài báo | `paper/` |
| Sửa/mở rộng Kev | `third_party/kev/`, ghi thay đổi vào `third_party/kev/UPSTREAM.md` |

## Đường dẫn cũ → mới

| Cũ | Mới |
| --- | --- |
| `Resource/explore_datasets/src/` | `src/` |
| `Resource/explore_datasets/src/docs/` | `docs/code/src_docs/` |
| `Resource/explore_datasets/tests/` | `tests/` |
| `Resource/explore_datasets/*.py`, `run_lemma.sh` | `scripts/` |
| `Resource/explore_datasets/README.md` | `docs/code/datasets_cli.md` |
| `Resource/explore_datasets/requirements.txt` | `requirements.txt` (root) |
| `Resource/explore_datasets/.venv` | `.venv` |
| `Resource/explore_datasets/output/` | `data/output/` |
| `Resource/conftest.py`, `Resource/pytest.ini` | `conftest.py`, `pytest.ini` |
| `Resource/setup.ps1`, `Resource/requirements.txt` (CP1) | `scripts/legacy/` |
| `Resource/datasets/normalized/` | `data/normalized/` |
| `Resource/notebooks/` | `notebooks/` |
| `Resource/docs/research_protocol_v3.md` | `docs/research/` |
| `Resource/docs/history/` | `docs/history/resource_docs/` |
| `Resource/docs/*` (còn lại) | `docs/status/` |
| `Resource/note/HANDOFF_NCKH.md`, `Resource/PROJECT_MINDMAP.md` | `docs/context/` |
| `Resource/note/*` | `docs/notes/` |
| `Resource/requirement/` | `docs/research/requirement/` |
| `Resource/README.md` | `docs/history/resource_map_2026-10-23.md` |
| `Resource/README`, `Resource/explore_datasets/README` | `docs/history/` |
| `Resource/report/`, `IEEE_template/` | `paper/report/`, `paper/IEEE_template/` |
| `01_topic_proposal/`, `02_related_work/` | `docs/research/` |
| `PDF_NCKH/` (paper MRCA, Nezha) | `docs/references/` |
| `PDF_NCKH/Chương 1–5`, `introductions/`, `academicWords.md`, `*-tutor.md` | `_personal/` |
| `NCKH_rawData/raw_data/` | `data/raw/` |
| `NCKH_rawData/spec/audit_metadata.py`, test, requirements | `scripts/audit/` |
| `NCKH_rawData/spec/*.md`, `NCKH_rawData/README.md` | `docs/data/` |
| `NCKH_rawData/spec/` (JSON/CSV artifact, `.audit_deps`) | `data/audit/` |
| `models/kev/` | `third_party/kev/` |

## Giới hạn

- Thư mục `data/` không có trong git. Máy mới (hoặc Colab) phải copy raw vào `data/raw/` hoặc dùng `--data-root`.
- Cột `source_file` trong Parquet đã sinh trước ngày 25/10 ghi đường dẫn **CP1 cũ** (ví dụ `Resource/cp1/raw_data/huggingface/rcaeval/<case>/logs.parquet`, kiểm tra 25/10 trên row group đầu của cả ba bảng). Đổi prefix `Resource/cp1/raw_data/` → `data/raw/` khi resolve; nội dung Parquet không bị sửa.
- Tài liệu lịch sử và biên bản có ngày (`validation_report.md`, `docs_reconciliation_2026-10-23.md`, `refactor_preservation.json`, note 28-09) giữ nguyên đường dẫn cũ như ghi nhận tại thời điểm đó.
