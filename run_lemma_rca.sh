#!/usr/bin/env bash
# Root wrapper script for LEMMA-RCA dataset exploration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/scripts/run_lemma.sh" "$@"
