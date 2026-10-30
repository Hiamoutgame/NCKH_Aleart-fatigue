#!/usr/bin/env python3
"""Run R1, R2, R3, R4, R5 ranking and evaluation on RCAEval validation split."""

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

EXTRA_PACKAGES_DIR = REPO_ROOT / ".cache" / "site-packages"
if EXTRA_PACKAGES_DIR.exists() and str(EXTRA_PACKAGES_DIR) not in sys.path:
    sys.path.insert(0, str(EXTRA_PACKAGES_DIR))

from src.interface.pipeline_cli import main


def execute_subcommand(args_list: list[str]) -> dict:
    print(f"Running command: {' '.join(args_list)}", flush=True)
    # Call main directly in-process
    exit_code = main(args_list)
    if exit_code != 0:
        raise RuntimeError(f"Command {' '.join(args_list)} failed with exit code {exit_code}")


def run():
    rankers = ["r1", "r2", "r3", "r4", "r5"]
    runs = {}

    for ranker in rankers:
        print(f"\n--- Ranking with {ranker} on val ---", flush=True)
        main(["rank", "rcaeval", "--ranker", ranker, "--method", "g2", "--split", "val"])


if __name__ == "__main__":
    run()
