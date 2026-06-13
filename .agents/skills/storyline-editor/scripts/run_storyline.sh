#!/usr/bin/env bash
# Smoke-test helper for the storyline-editor routine.
# Builds the input bundle, optionally seeds PLACEHOLDER narratives, validates,
# then overlays them onto the served storyline files via the pipeline. The real
# narratives (the editorial work) are written by an agent, not this script.
#
# Usage:
#   bash run_storyline.sh                 # build input + validate + overlay
#   bash run_storyline.sh --seed          # also write deterministic placeholders
#   bash run_storyline.sh --seed --all
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
PY="${PYTHON:-python3}"

SEED=0
PASS_ARGS=()
for arg in "$@"; do
  if [[ "$arg" == "--seed" ]]; then SEED=1; else PASS_ARGS+=("$arg"); fi
done

"$PY" "$SCRIPT_DIR/build_storyline_input.py" ${PASS_ARGS[@]+"${PASS_ARGS[@]}"}
if [[ "$SEED" == "1" ]]; then
  "$PY" "$SCRIPT_DIR/seed_storyline_sample.py"
fi
"$PY" "$SCRIPT_DIR/validate_narratives.py" --check
# Overlay sidecars onto data/storylines/<slug>.json + index.json (deterministic).
"$PY" "$REPO_ROOT/pipeline/build_storylines.py"
