"""One local inspect/normalize/verify CLI for RCAEval and Nezha."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pyarrow.parquet as pq

from src.shared.application.verify_normalized import REPORT_NAME, verify_normalized
from src.shared.infrastructure.drain import DrainConfig
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
    for command in ("inspect", "normalize", "verify"):
        task = commands.add_parser(command)
        task.add_argument("dataset", choices=[*ADAPTERS, "all"])
        task.add_argument("--data-root", type=Path, help="Override raw path for one dataset")
        if command in ("normalize", "verify"):
            task.add_argument(
                "--output-root", type=Path, default=NORMALIZED_DIR,
                help="Parent directory; each dataset is written under its canonical slug",
            )
        if command == "normalize":
            defaults = DrainConfig()
            task.add_argument("--drain-depth", type=int, default=defaults.depth, help="Drain parse tree depth")
            task.add_argument("--drain-st", type=float, default=defaults.st, help="Drain similarity threshold")
            task.add_argument("--drain-max-child", type=int, default=defaults.max_child, help="Drain max children per node")
            task.add_argument("--max-cases", type=int, help="Normalize only N incidents (smoke test); default all")
        if command == "verify":
            task.add_argument("--sample-per-incident", type=int, default=20, help="Rows re-read from raw per incident")
            task.add_argument("--seed", type=int, default=42)

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
    exit_code = 0
    try:
        for slug in selected:
            if args.command == "inspect":
                results[slug] = ADAPTERS[slug](data_root=args.data_root).inspect()
                continue
            output_dir = args.output_root / slug
            if args.command == "verify":
                report = verify_normalized(
                    ADAPTERS[slug](data_root=args.data_root), output_dir, args.sample_per_incident, args.seed
                )
                failed = [check for check in report["checks"] if not check["passed"]]
                results[slug] = {"passed": report["passed"], "failed_checks": failed,
                                 "report": str(output_dir / REPORT_NAME)}
                exit_code = exit_code or (0 if report["passed"] else 2)
                continue
            drain_config = DrainConfig(args.drain_depth, args.drain_st, args.drain_max_child)
            adapter = ADAPTERS[slug](data_root=args.data_root, drain_config=drain_config)
            result = adapter.normalize(output_dir, max_cases=args.max_cases)
            result["table_rows"] = {
                name: pq.ParquetFile(output_dir / name).metadata.num_rows
                for name in TABLES
            }
            results[slug] = result
    except (FileNotFoundError, ValueError) as error:
        parser.exit(1, f"Dataset error: {error}\n")
    print(json.dumps(results, indent=2, ensure_ascii=False, default=str))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
