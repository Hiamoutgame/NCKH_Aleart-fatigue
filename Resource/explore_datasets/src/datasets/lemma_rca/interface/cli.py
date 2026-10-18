"""CLI interface for LEMMA-RCA dataset.

Ho tro cac lenh:
- fetch: Tai dataset (ho tro --dry-run va che do selective 'sample' khuyen dung)
- profile: Hien thi profile 4 tieu chi (shape, columns, head, value_counts)
- list-incidents: Liet ke cac ca su co va ground truth
- show-incident: Xem chi tiet mot ca su co
- logs: Tra cuu va xem chi tiet noi dung cac dong log thuc te
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ..application.use_cases import (
    describe_lemma_use_case,
    export_lemma_logs_use_case,
    fetch_lemma_use_case,
    get_lemma_incident_use_case,
    inspect_lemma_logs_use_case,
    list_lemma_incidents_use_case,
)


def _cmd_fetch(args: argparse.Namespace) -> int:
    print(f"=== LEMMA-RCA FETCH [{args.mode.upper()}] ===")
    plan = fetch_lemma_use_case(
        mode=args.mode,
        target_dir=args.target_dir,
        dry_run=args.dry_run,
    )
    if args.dry_run:
        print("\n[Luu y] Ban dang chay voi co --dry-run (chi xem ke hoach).")
        print("De thuc su tai ve may, hay bo co --dry-run.")
    else:
        print("\n[Thanh cong] Hoan tat tai du lieu.")
    return 0


def _cmd_profile(args: argparse.Namespace) -> int:
    print("=== LEMMA-RCA PROFILE (4 TIEU CHI) ===")
    res = describe_lemma_use_case(
        data_root=args.data_root,
        sample_limit=args.limit,
    )

    if res["n_rows"] == 0:
        print("[Thong bao] Chua co file log nao trong thu muc local.")
        print("Goi y: Chay lenh fetch truoc: python -m src.datasets.lemma_rca.interface.cli fetch")
        return 1

    print(f"Dataset: {res['name']}")
    print(f"Files found: {len(res['files'])} ({', '.join(res['files'][:3])}{'...' if len(res['files']) > 3 else ''})")
    print(f"Shape: ({res['n_rows']}, {res['n_cols']}){' [sampled]' if res.get('sampled') else ''}")

    print("\n1. Columns:")
    for c in res["columns"]:
        print(f"  - {c}")

    print(f"\n2. First {len(res['head'])} rows (Head):")
    for i, r in enumerate(res["head"], start=1):
        ts = r.get("timestamp") or "-"
        svc = r.get("service") or "-"
        lvl = r.get("level") or "-"
        msg = (r.get("message") or "")[:85]
        print(f"  [{i:>2}] {ts:<28} | {svc:<16} | {lvl:<5} | {msg}...")

    print("\n3. Value Counts (Top phan bo):")
    for col, counts in res["value_counts"].items():
        print(f"  [{col}]:")
        total = sum(counts.values()) or 1
        for val, cnt in counts.items():
            pct = round(100.0 * cnt / total, 2)
            print(f"    - {val:<20}: {cnt:>6} ({pct}%)")

    print("\n[Luu y dien giai]: Tan suat xuat hien cao khong dong nghia voi nguyen nhan gay su co (RCA).")
    return 0


def _cmd_list_incidents(args: argparse.Namespace) -> int:
    print("=== LEMMA-RCA DOCUMENTED INCIDENTS (GROUND TRUTH) ===")
    incidents = list_lemma_incidents_use_case()
    print(f"Tong so su co duoc ghi nhan: {len(incidents)}")
    print(f"{'ID':<30} | {'DATE':<10} | {'SYSTEM':<20} | {'FAULT TYPE'}")
    print("-" * 95)
    for inc in incidents:
        print(f"{inc.incident_id:<30} | {inc.date:<10} | {inc.system:<20} | {inc.fault_type}")
    print("\nXem chi tiet tung ca bang lenh: python -m src.datasets.lemma_rca.interface.cli show-incident --id <ID>")
    return 0


def _cmd_show_incident(args: argparse.Namespace) -> int:
    inc = get_lemma_incident_use_case(args.id)
    if not inc:
        print(f"Khong tim thay su co co ID: {args.id}")
        print("Dung lenh 'list-incidents' de xem danh sach ID co san.")
        return 1

    print(f"=== CHI TIET SU CO: {inc.incident_id} ===")
    print(f"System:             {inc.system}")
    print(f"Date:               {inc.date}")
    print(f"Fault Type:         {inc.fault_type}")
    print(f"Root Cause Service: {inc.root_cause_service}")
    print(f"Impacted Services:  {', '.join(inc.impacted_services)}")
    print(f"Start Time:         {inc.start_time}")
    print(f"Injection Time:     {inc.inject_time}")
    print(f"End Time:           {inc.end_time}")
    print(f"\nDescription:")
    print(f"  {inc.description}")
    print(f"\nSymptoms:")
    print(f"  {inc.symptoms}")
    return 0


def _cmd_logs(args: argparse.Namespace) -> int:
    print(f"=== LEMMA-RCA LOGS (Limit: {args.limit}) ===")
    records = inspect_lemma_logs_use_case(
        data_root=args.data_root,
        service=args.service,
        level=args.level,
        query=args.query,
        limit=args.limit,
    )
    if not records:
        print("Khong tim thay ban ghi log nao phu hop voi bo loc.")
        return 0

    print(f"Tim thay {len(records)} ban ghi:")
    for idx, r in enumerate(records, start=1):
        print(f"\n[{idx}] {r.timestamp_str} | {r.service} | {r.level} | Pod: {r.pod_name or '-'} | Host: {r.host or '-'}")
        print(f"    Message: {r.message}")
    return 0


def _cmd_export(args: argparse.Namespace) -> int:
    print(f"=== LEMMA-RCA EXPORT LOGS [{args.format.upper()}] ===")
    res = export_lemma_logs_use_case(
        output_path=args.output,
        format=args.format,
        data_root=args.data_root,
        service=args.service,
        level=args.level,
        query=args.query,
        limit=args.limit,
    )
    print(f"[Thanh cong] Da xuat {res['total_exported']} ban ghi vao: {res['output_path']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CLI explore dataset LEMMA-RCA")
    subparsers = parser.add_subparsers(dest="command")

    # Subcommand fetch
    p_fetch = subparsers.add_parser("fetch", help="Tai du lieu tu Hugging Face")
    p_fetch.add_argument(
        "--mode",
        choices=["sample", "full"],
        default="sample",
        help="Che do tai: 'sample' (khuyen dung, nhanh ~30MB) hoac 'full' (~51GB)",
    )
    p_fetch.add_argument("--dry-run", action="store_true", help="Xem ke hoach tai truoc ma khong tai that")
    p_fetch.add_argument("--target-dir", default=None, help="Thu muc luu file tai ve")
    p_fetch.set_defaults(func=_cmd_fetch)

    # Subcommand profile
    p_prof = subparsers.add_parser("profile", help="Xuat profile 4 tieu chi")
    p_prof.add_argument("--data-root", default=None, help="Thu muc du lieu local")
    p_prof.add_argument("--limit", type=int, default=10000, help="Gioi han so dong mau de profile")
    p_prof.set_defaults(func=_cmd_profile)

    # Subcommand list-incidents
    p_list = subparsers.add_parser("list-incidents", help="Liet ke cac ca su co (Ground Truth)")
    p_list.set_defaults(func=_cmd_list_incidents)

    # Subcommand show-incident
    p_show = subparsers.add_parser("show-incident", help="Xem chi tiet mot ca su co")
    p_show.add_argument("--id", required=True, help="Incident ID")
    p_show.set_defaults(func=_cmd_show_incident)

    # Subcommand logs
    p_logs = subparsers.add_parser("logs", help="Xem va loc cac dong log")
    p_logs.add_argument("--data-root", default=None, help="Thu muc du lieu local")
    p_logs.add_argument("--service", default=None, help="Loc theo ten service / container")
    p_logs.add_argument("--level", default=None, help="Loc theo level (DEBUG, INFO, WARN, ERROR)")
    p_logs.add_argument("--query", default=None, help="Loc theo tu khoa trong message")
    p_logs.add_argument("--limit", type=int, default=20, help="So dong log toi da")
    p_logs.set_defaults(func=_cmd_logs)

    # Subcommand export
    p_exp = subparsers.add_parser("export", help="Xuat du lieu log canonical ra file CSV hoac JSON")
    p_exp.add_argument("--output", "-o", required=True, help="Duong dan file dau ra (vi du: logs.csv hoac logs.json)")
    p_exp.add_argument("--format", choices=["csv", "json"], default="csv", help="Dinh dang xuat: csv hoac json")
    p_exp.add_argument("--data-root", default=None, help="Thu muc du lieu local")
    p_exp.add_argument("--service", default=None, help="Loc theo ten service / container")
    p_exp.add_argument("--level", default=None, help="Loc theo level (DEBUG, INFO, WARN, ERROR)")
    p_exp.add_argument("--query", default=None, help="Loc theo tu khoa trong message")
    p_exp.add_argument("--limit", type=int, default=None, help="So dong log toi da de xuat (mac dinh: tat ca)")
    p_exp.set_defaults(func=_cmd_export)

    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
