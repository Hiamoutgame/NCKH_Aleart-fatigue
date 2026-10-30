"""Expose the repository root so tests can import `src`."""

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

EXTRA_PACKAGES_DIR = REPO_ROOT / ".cache" / "site-packages"
if EXTRA_PACKAGES_DIR.exists() and str(EXTRA_PACKAGES_DIR) not in sys.path:
    sys.path.insert(0, str(EXTRA_PACKAGES_DIR))
