#!/usr/bin/env python3
"""Evaluate val runs for R1-R5 against R0 and R5 against R2."""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.interface.pipeline_cli import main

RUN_IDS = {
    "R1": "rcaeval_r1_g2_val_20261030-173436",
    "R2": "rcaeval_r2_g2_val_20261030-173453",
    "R3": "rcaeval_r3_g2_val_20261030-173505",
    "R4": "rcaeval_r4_g2_val_20261030-173510",
    "R5": "rcaeval_r5_g2_val_20261030-173516",
}


def run():
    # Evaluate each against r0
    for ranker_name, run_id in RUN_IDS.items():
        print(f"\n================ Evaluating {ranker_name} vs r0 ================", flush=True)
        main(["evaluate", "--run", run_id, "--baseline", "r0"])

    # Evaluate R5 vs R2
    print(f"\n================ Evaluating R5 vs R2 ================", flush=True)
    main(["evaluate", "--run", RUN_IDS["R5"], "--baseline", RUN_IDS["R2"]])


if __name__ == "__main__":
    run()
