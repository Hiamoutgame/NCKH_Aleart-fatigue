"""Expose exploration source when running the Resource test suite."""

import sys
from pathlib import Path


EXPLORATION_ROOT = Path(__file__).resolve().parent / "explore_datasets"
if str(EXPLORATION_ROOT) not in sys.path:
    sys.path.insert(0, str(EXPLORATION_ROOT))
