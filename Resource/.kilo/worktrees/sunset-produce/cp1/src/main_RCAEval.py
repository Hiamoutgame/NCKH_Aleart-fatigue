#!/usr/bin/env python3
"""Local-only CP1 workflow for the RCAEval dataset."""

from __future__ import annotations

import argparse

from cp1_core.analysis import scan_warnings, summary_lines, timing_table, verification_table
from cp1_core.dataset_io import inspect_local_source, list_case_log_paths, load_rcaeval_cases
from cp1_core.fetchers import fetch_source, require_local
from cp1_core.paths import artifact_dir
from cp1_core.reporting import write_table, write_text_report
from cp1_core.source_registry import get_source


def _warning_table_path():
    return artifact_dir("rcaeval") / "tables" / "warning_per_case.csv"


def _scan(rcaeval_dir):
    table = scan_warnings(rcaeval_dir)
    write_table(_warning_table_path(), table)
    write_text_report(artifact_dir("rcaeval") / "reports" / "scan_warnings.txt", summary_lines(table))
    print(f"Warning table: {_warning_table_path()}")
    return table


def _load_or_scan(rcaeval_dir):
    table_path = _warning_table_path()
    if table_path.exists():
        import pandas as pd
        return pd.read_csv(table_path)
    return _scan(rcaeval_dir)


def _inspect(rcaeval_dir):
    info = inspect_local_source(rcaeval_dir)
    info["cases_with_logs"] = len(list_case_log_paths(rcaeval_dir))
    try:
        cases = load_rcaeval_cases(rcaeval_dir)
        info["case_metadata_rows"] = len(cases)
        info["case_metadata_columns"] = ", ".join(cases.columns)
    except FileNotFoundError as error:
        info["case_metadata_error"] = str(error)
    report_path = artifact_dir("rcaeval") / "reports" / "inspect.txt"
    write_text_report(report_path, [f"{key}: {value}" for key, value in info.items()])
    print(f"Inspect report: {report_path}")


def _timing(rcaeval_dir):
    cases = load_rcaeval_cases(rcaeval_dir)
    table = timing_table(rcaeval_dir, cases, _load_or_scan(rcaeval_dir))
    output = artifact_dir("rcaeval") / "tables" / "warning_timing.csv"
    write_table(output, table)
    print(f"Timing table: {output}")


def _verify(rcaeval_dir):
    cases = load_rcaeval_cases(rcaeval_dir)
    table = verification_table(rcaeval_dir, cases, _load_or_scan(rcaeval_dir))
    output = artifact_dir("rcaeval") / "tables" / "warning_verification.csv"
    write_table(output, table)
    print(f"Verification table: {output}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CP1 RCAEval workflow")
    parser.add_argument(
        "command",
        nargs="?",
        choices=["fetch", "inspect", "scan-warnings", "timing", "verify", "all"],
        help="Task to run",
    )
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 0

    rcaeval_source = get_source("rcaeval")
    try:
        if args.command == "fetch":
            dataset_path = fetch_source(rcaeval_source)
            repository_path = fetch_source(get_source("rcaeval_github"))
            print(f"Dataset: {dataset_path}")
            print(f"Reference repository: {repository_path}")
            return 0

        if args.command == "all":
            fetch_source(rcaeval_source)
            fetch_source(get_source("rcaeval_github"))

        dataset_path = require_local(rcaeval_source)
        if args.command in {"inspect", "all"}:
            _inspect(dataset_path)
        if args.command in {"scan-warnings", "all"}:
            _scan(dataset_path)
        if args.command in {"timing", "all"}:
            _timing(dataset_path)
        if args.command in {"verify", "all"}:
            _verify(dataset_path)
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
