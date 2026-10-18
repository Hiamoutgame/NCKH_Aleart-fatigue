"""CP1 helpers using the shared utilities inside explore_datasets."""

import sys
from pathlib import Path


EXPLORATION_ROOT = Path(__file__).resolve().parents[3] / "explore_datasets"
if str(EXPLORATION_ROOT) not in sys.path:
    sys.path.insert(0, str(EXPLORATION_ROOT))
