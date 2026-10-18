#!/usr/bin/env python3
"""Inspect Nezha inputs already available locally (no automatic fetch)."""

from cp1_core.dataset_entrypoint import run_dataset_cli


if __name__ == "__main__":
    raise SystemExit(run_dataset_cli("nezha", "Nezha"))
