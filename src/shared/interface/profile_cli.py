"""CLI dung chung: doc mot file va in profile 4 tieu chi."""

from __future__ import annotations

import argparse

from src.shared.application.profiling import format_profile, profile_dataframe
from src.shared.infrastructure.loaders import load_table


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Profile mot dataset: shape, columns, head, value_counts"
    )
    parser.add_argument("path", help="duong dan file csv/tsv/json/jsonl/parquet")
    parser.add_argument("--name", default=None, help="ten hien thi")
    parser.add_argument("--head", type=int, default=10, help="so dong head, mac dinh 10")
    parser.add_argument(
        "--value-cols",
        nargs="*",
        default=["service", "message"],
        help="cac cot can value_counts",
    )
    args = parser.parse_args(argv)

    df = load_table(args.path)
    name = args.name or args.path
    profile = profile_dataframe(
        df, name=name, head_n=args.head, value_count_columns=args.value_cols
    )
    print(format_profile(profile))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
