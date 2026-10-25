#!/usr/bin/env python3
"""Convenient entrypoint to run and explore LEMMA-RCA dataset.

Usage:
  python run_lemma_rca.py fetch [--dry-run] [--mode {sample,full}]
  python run_lemma_rca.py profile [--limit 10000]
  python run_lemma_rca.py list-incidents
  python run_lemma_rca.py show-incident --id <incident_id>
  python run_lemma_rca.py logs [--service <service>] [--level <level>] [--query <keyword>] [--limit 20]
  python run_lemma_rca.py export --output <file.csv> [--format {csv,json}] [--service <service>] [--level <level>] [--limit 1000]
"""

import sys
from pathlib import Path

# Make the repository root importable so `src` resolves from any working directory.
root_dir = Path(__file__).resolve().parents[1]
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.datasets.lemma_rca.interface.cli import main

if __name__ == "__main__":
    sys.exit(main())
