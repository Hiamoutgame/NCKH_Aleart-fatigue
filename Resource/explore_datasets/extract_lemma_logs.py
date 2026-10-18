"""Script tien ich doc, trich xuat va phan tich Log LEMMA-RCA nhanh bang Python / Pandas.

Cach dung tu dong lenh (CLI):
  python extract_lemma_logs.py --summary
  python extract_lemma_logs.py --service productpage --limit 20
  python extract_lemma_logs.py --level ERROR --export errors.csv
  python extract_lemma_logs.py --query "503" --limit 10

Cach dung trong Python / Jupyter Notebook:
  from extract_lemma_logs import get_lemma_logs_df
  df = get_lemma_logs_df(level="WARN")
  print(df[['timestamp', 'service', 'level', 'message']].head())
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

# Dam bao import duoc src.datasets.lemma_rca
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

from src.datasets.lemma_rca.application.use_cases import (
    describe_lemma_use_case,
    export_lemma_logs_use_case,
    inspect_lemma_logs_use_case,
    list_lemma_incidents_use_case,
)
from src.datasets.lemma_rca.infrastructure.loader import LemmaLoader


def get_lemma_logs_df(
    service: Optional[str] = None,
    level: Optional[str] = None,
    query: Optional[str] = None,
    limit: Optional[int] = None,
    data_root: Optional[str | Path] = None,
):
    """Tra ve DataFrame chua toan bo hoac tap con log da duoc chuan hoa cua LEMMA-RCA."""
    if not HAS_PANDAS:
        raise RuntimeError("Yeu cau cai dat pandas: pip install pandas")

    loader = LemmaLoader(data_root=data_root)
    rows = loader.load_canonical_rows(
        limit=limit,
        service=service,
        level=level,
        query=query,
    )
    return pd.DataFrame(rows)


def print_summary(data_root: Optional[str | Path] = None, limit: int = 10000):
    """In tong quan thong ke log theo dung 4 tieu chi explore_datasets."""
    res = describe_lemma_use_case(data_root=data_root, sample_limit=limit)
    if res["n_rows"] == 0:
        print("[!] Chua tim thay du lieu log nao. Hay chay './run_lemma.sh fetch' truoc.")
        return

    print("=" * 70)
    print("           TONG QUAN DU LIEU LOG LEMMA-RCA (ELASTICSEARCH)")
    print("=" * 70)
    print(f"Dataset:            {res['name']}")
    print(f"So file tim thay:   {len(res['files'])} ({', '.join(res['files'])})")
    print(f"Shape:              ({res['n_rows']}, {res['n_cols']}){' [lay mau ' + str(limit) + ']' if res.get('sampled') else ''}")
    print(f"Cac cot canonical:  {', '.join(res['columns'])}")

    print("\n--- Top Microservices & Infrastructure Services ---")
    for svc, count in list(res["value_counts"].get("service", {}).items())[:8]:
        pct = (count / res["n_rows"]) * 100
        print(f"  * {svc:<25}: {count:>6} dong ({pct:5.1f}%)")

    print("\n--- Phan bo muc do nghiem trong (Log Level) ---")
    for lvl, count in res["value_counts"].get("level", {}).items():
        pct = (count / res["n_rows"]) * 100
        print(f"  * {lvl:<25}: {count:>6} dong ({pct:5.1f}%)")

    print("\n--- Phan loai (Log Type) ---")
    for lt, count in res["value_counts"].get("log_type", {}).items():
        pct = (count / res["n_rows"]) * 100
        print(f"  * {lt:<25}: {count:>6} dong ({pct:5.1f}%)")

    print("\n--- Mau 3 dong log dau tien (Head) ---")
    for idx, row in enumerate(res["head"][:3], start=1):
        print(f"[{idx}] {row.get('timestamp')} | {row.get('service')} | {row.get('level')}")
        print(f"    Message: {row.get('message')[:100]}...")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Trich xuat va phan tich nhanh Log LEMMA-RCA")
    parser.add_argument("--summary", action="store_true", help="In tong quan thong ke dataset")
    parser.add_argument("--service", default=None, help="Loc theo ten service (productpage, reviews, dispatch...)")
    parser.add_argument("--level", default=None, help="Loc theo level (DEBUG, INFO, WARN, ERROR)")
    parser.add_argument("--query", default=None, help="Loc theo tu khoa trong message")
    parser.add_argument("--limit", type=int, default=15, help="So dong log hien thi / xuat")
    parser.add_argument("--export", default=None, help="Xuat ket qua ra file CSV (vi du: errors.csv)")
    parser.add_argument("--format", choices=["csv", "json"], default="csv", help="Dinh dang xuat")

    args = parser.parse_args()

    if args.summary or (len(sys.argv) == 1):
        print_summary()
        if len(sys.argv) == 1:
            print("\nGoi y cac lenh tiep theo:")
            print("  python extract_lemma_logs.py --level ERROR --limit 10")
            print("  python extract_lemma_logs.py --service productpage --limit 10")
            print("  python extract_lemma_logs.py --level ERROR --export errors.csv")
        return 0

    if args.export:
        print(f"Dang xuat log theo bo loc vao: {args.export}...")
        res = export_lemma_logs_use_case(
            output_path=args.export,
            format=args.format,
            service=args.service,
            level=args.level,
            query=args.query,
            limit=args.limit,
        )
        print(f"[Thanh cong] Da xuat {res['total_exported']} dong vao {res['output_path']}.")
        return 0

    records = inspect_lemma_logs_use_case(
        service=args.service,
        level=args.level,
        query=args.query,
        limit=args.limit,
    )
    print(f"Tim thay {len(records)} ban ghi log:")
    for idx, r in enumerate(records, start=1):
        print(f"\n[{idx}] {r.timestamp_str} | {r.service} | {r.level} | Pod: {r.pod_name or '-'} | Host: {r.host or '-'}")
        print(f"    Message: {r.message}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
