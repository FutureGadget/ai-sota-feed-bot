#!/usr/bin/env bash
# Smoke-test helper for the storyline-scout routine.
# Generates candidates, optionally seeds a PLACEHOLDER link, validates, then
# rebuilds storylines so the link is applied through the floor gate. The real
# links (the judgment) are written by an agent, not this script.
#
# Usage:
#   bash run_scout.sh                 # candidates + validate + build
#   bash run_scout.sh --seed          # also seed a deterministic placeholder link
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
PY="${PYTHON:-python3}"

SEED=0
for arg in "$@"; do
  if [[ "$arg" == "--seed" ]]; then SEED=1; fi
done

# Candidates are derived from the current storylines, so build first.
"$PY" "$REPO_ROOT/pipeline/build_storylines.py" >/dev/null
"$PY" "$REPO_ROOT/pipeline/scout_candidates.py"
if [[ "$SEED" == "1" ]]; then
  "$PY" "$SCRIPT_DIR/seed_scout_sample.py"
fi
"$PY" "$SCRIPT_DIR/validate_links.py" --check
# Apply confirmed links through the deterministic floor gate.
"$PY" "$REPO_ROOT/pipeline/build_storylines.py"
