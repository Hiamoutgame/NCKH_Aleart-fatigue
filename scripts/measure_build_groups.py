#!/usr/bin/env python3
"""Run build_groups for RCAEval and Nezha, reporting timing, group counts, and peak RSS."""

import json
import resource
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.grouping.groups import build_groups


def run():
    dataset = sys.argv[1] if len(sys.argv) > 1 else "rcaeval"
    method = sys.argv[2] if len(sys.argv) > 2 else "g2"

    start_time = time.time()
    out_parquet, out_manifest = build_groups(dataset, method)
    elapsed_seconds = time.time() - start_time

    manifest_data = json.loads(Path(out_manifest).read_text())
    max_rss_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0

    report = {
        "dataset": dataset,
        "method": method,
        "elapsed_seconds": round(elapsed_seconds, 2),
        "peak_rss_mb": round(max_rss_mb, 2),
        "total_groups": manifest_data.get("total_groups"),
        "total_logs": manifest_data.get("total_logs"),
        "total_incidents": manifest_data.get("total_incidents"),
    }
    print("RESULT_JSON:" + json.dumps(report))


if __name__ == "__main__":
    run()
