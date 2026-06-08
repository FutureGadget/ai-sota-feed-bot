#!/usr/bin/env bash
# Smoke-test helper for the daily recap UI.
# Builds the input bundle, optionally seeds a PLACEHOLDER recap, then rebuilds
# the index. The real recap (step 2) is written by an agent, not this script.
#
# Usage:
#   bash run_daily.sh                 # build input + rebuild index only
#   bash run_daily.sh --seed          # also write a deterministic placeholder recap
#   bash run_daily.sh --seed --date 2026-06-07
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="${PYTHON:-python3}"

SEED=0
PASS_ARGS=()
for arg in "$@"; do
  if [[ "$arg" == "--seed" ]]; then SEED=1; else PASS_ARGS+=("$arg"); fi
done

"$PY" "$SCRIPT_DIR/build_daily_input.py" "${PASS_ARGS[@]}"
if [[ "$SEED" == "1" ]]; then
  "$PY" "$SCRIPT_DIR/seed_daily_sample.py"
fi
"$PY" "$SCRIPT_DIR/build_daily_index.py"
