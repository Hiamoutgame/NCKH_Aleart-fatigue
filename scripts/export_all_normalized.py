"""Compatibility command: normalize all three datasets with canonical output names."""

import sys
from pathlib import Path

# Make the repository root importable so `src` resolves from any working directory.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.interface.datasets_cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main(["normalize", "all", *sys.argv[1:]]))
