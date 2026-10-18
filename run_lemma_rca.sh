#!/usr/bin/env bash
# Root wrapper script for LEMMA-RCA dataset exploration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/Resource/explore_datasets/run_lemma.sh" "$@"
