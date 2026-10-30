"""One local inspect/normalize/verify/split CLI for RCAEval and Nezha."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

from src.evaluation.split import (
    create_nezha_splits,
    save_splits,
    stratified_scenario_split,
    verify_splits,
)
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
    for command in ("inspect", "normalize", "verify", "split"):
        task = commands.add_parser(command)
        task.add_argument("dataset", choices=[*ADAPTERS, "all"])
        task.add_argument("--data-root", type=Path, help="Override raw path for one dataset")
        if command in ("normalize", "verify", "split"):
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
        if command == "split":
            task.add_argument("--seed", type=int, default=42, help="Seed for reproducible scenario splitting")
            task.add_argument("--train-ratio", type=float, default=0.70, help="Train ratio (RCAEval default 0.70)")
            task.add_argument("--val-ratio", type=float, default=0.15, help="Validation ratio (RCAEval default 0.15)")
            task.add_argument("--test-ratio", type=float, default=0.15, help="Test ratio (RCAEval default 0.15)")
            task.add_argument("--force", action="store_true", help="Overwrite existing splits.parquet and split_manifest.json")

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
            if args.command == "split":
                output_splits_file = output_dir / "splits.parquet"
                if output_splits_file.exists() and not getattr(args, "force", False):
                    raise FileExistsError(
                        f"Splits file already exists at {output_splits_file}. Pass --force to overwrite."
                    )
                incidents_parquet_path = output_dir / "incidents.parquet"
                if not incidents_parquet_path.exists():
                    raise FileNotFoundError(
                        f"Cannot split {slug}: {incidents_parquet_path} does not exist. Run normalize first."
                    )
                incidents_frame = pd.read_parquet(incidents_parquet_path)
                manifest_path = output_dir / "manifest.json"
                incidents_with_logs = None
                if manifest_path.exists():
                    manifest_data = json.loads(manifest_path.read_text())
                    incidents_with_logs = manifest_data.get("outputs", {}).get("incidents_with_logs")

                split_settings = {"seed": args.seed}
                if slug == "rcaeval":
                    split_settings.update({
                        "train_ratio": args.train_ratio,
                        "val_ratio": args.val_ratio,
                        "test_ratio": args.test_ratio,
                    })
                    splits_frame = stratified_scenario_split(
                        incidents_frame=incidents_frame,
                        incidents_with_logs=incidents_with_logs,
                        train_ratio=args.train_ratio,
                        validation_ratio=args.val_ratio,
                        test_ratio=args.test_ratio,
                        random_seed=args.seed,
                    )
                else:
                    splits_frame = create_nezha_splits(incidents_frame, incidents_with_logs)

                verification_report = verify_splits(splits_frame, incidents_frame)
                if not verification_report["passed"]:
                    results[slug] = {
                        "error": "Splits verification failed; files not saved.",
                        "verification": verification_report,
                    }
                    exit_code = 2
                    continue
                splits_file, manifest_file = save_splits(output_dir, splits_frame, split_settings)
                results[slug] = {"splits_file": str(splits_file), "manifest_file": str(manifest_file),
                                 "verification": verification_report}
                continue
            drain_config = DrainConfig(args.drain_depth, args.drain_st, args.drain_max_child)
            adapter = ADAPTERS[slug](data_root=args.data_root, drain_config=drain_config)
            result = adapter.normalize(output_dir, max_cases=args.max_cases)
            result["table_rows"] = {
                name: pq.ParquetFile(output_dir / name).metadata.num_rows
                for name in TABLES
            }
            results[slug] = result
    except (FileNotFoundError, ValueError, FileExistsError) as error:
        parser.exit(1, f"Dataset error: {error}\n")
    print(json.dumps(results, indent=2, ensure_ascii=False, default=str))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
