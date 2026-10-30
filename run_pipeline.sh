#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
for candidate in \
    "$SCRIPT_DIR/.venv/bin/python"; do
    if [ -x "$candidate" ]; then
        exec "$candidate" "$SCRIPT_DIR/scripts/run_pipeline.py" "$@"
    fi
done
exec python3 "$SCRIPT_DIR/scripts/run_pipeline.py" "$@"
