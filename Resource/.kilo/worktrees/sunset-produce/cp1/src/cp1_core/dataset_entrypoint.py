"""Shared CLI behaviour for reference datasets without CP1 analysis yet."""

from __future__ import annotations

import argparse
from pathlib import Path

from .dataset_io import inspect_local_source
from .fetchers import fetch_source, require_local
from .paths import artifact_dir
from .reporting import write_text_report
from .source_registry import get_source


def run_dataset_cli(source_id: str, display_name: str, argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=f"CP1 entrypoint for {display_name}")
    parser.add_argument("command", nargs="?", choices=["fetch", "inspect", "all"], help="Task to run")
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 0

    source = get_source(source_id)
    try:
        if args.command in {"fetch", "all"}:
            path = fetch_source(source)
            print(f"Fetched {source_id}: {path}")
        if args.command in {"inspect", "all"}:
            path = require_local(source)
            info = inspect_local_source(path)
            report_path = artifact_dir(source_id) / "reports" / "inspect.txt"
            write_text_report(report_path, [f"{key}: {value}" for key, value in info.items()])
            print(f"Inspect report: {report_path}")
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        parser.error(str(error))
    return 0
