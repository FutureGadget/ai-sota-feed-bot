#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../../.."

LOCK_DIR=".run_tier1.lock"
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  echo "TIER1_RUN_SKIPPED: another run_tier1_fast.sh execution is already in progress"
  exit 0
fi
cleanup() { rmdir "$LOCK_DIR" 2>/dev/null || true; }
trap cleanup EXIT

source .venv/bin/activate

python collectors/collect.py
python pipeline/source_health.py update
python pipeline/build_tier1.py

echo "TIER1_RUN_OK"
