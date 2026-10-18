"""Compatibility command: normalize all three datasets with canonical output names."""

import sys

from src.interface.datasets_cli import main


if __name__ == "__main__":
    raise SystemExit(main(["normalize", "all", *sys.argv[1:]]))
