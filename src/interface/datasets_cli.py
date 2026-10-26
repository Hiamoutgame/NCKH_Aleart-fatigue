"""One local inspect/normalization CLI for RCAEval and Nezha."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pyarrow.parquet as pq

from src.shared.infrastructure.paths import DATASET_PATHS, NORMALIZED_DIR
from src.datasets.nezha import NezhaAdapter
from src.datasets.rcaeval import RCAEvalAdapter


ADAPTERS = {
    "rcaeval": RCAEvalAdapter,
    "nezha": NezhaAdapter,
}
TABLES = ("incidents.parquet", "log_events.parquet", "ground_truth.parquet")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command")
    commands.add_parser("list", help="List supported datasets and their local paths")
    for command in ("inspect", "normalize"):
        task = commands.add_parser(command)
        task.add_argument("dataset", choices=[*ADAPTERS, "all"])
        task.add_argument("--data-root", type=Path, help="Override raw path for one dataset")
        if command == "normalize":
            task.add_argument(
                "--output-root", type=Path, default=NORMALIZED_DIR,
                help="Parent directory; each dataset is written under its canonical slug",
            )

    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    if args.command == "list":
        print(json.dumps({slug: str(path) for slug, path in DATASET_PATHS.items()}, indent=2))
        return 0
    if args.dataset == "all" and args.data_root is not None:
        parser.error("--data-root requires one dataset, not 'all'")

    selected = ADAPTERS if args.dataset == "all" else [args.dataset]
    results = {}
    try:
        for slug in selected:
            adapter = ADAPTERS[slug](data_root=args.data_root)
            if args.command == "inspect":
                results[slug] = adapter.inspect()
                continue
            output_dir = args.output_root / slug
            result = adapter.normalize(output_dir)
            result["table_rows"] = {
                name: pq.ParquetFile(output_dir / name).metadata.num_rows
                for name in TABLES
            }
            results[slug] = result
    except (FileNotFoundError, ValueError) as error:
        parser.exit(1, f"Dataset error: {error}\n")
    print(json.dumps(results, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
