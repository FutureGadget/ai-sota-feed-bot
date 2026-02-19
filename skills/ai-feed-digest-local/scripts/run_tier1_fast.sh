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

COLLECT_DEFAULT_POLL_MINUTES=${COLLECT_DEFAULT_POLL_MINUTES:-30} python collectors/collect.py
python pipeline/source_health.py update
python pipeline/build_tier1.py

# Commit and push runtime data so Vercel serves fresh content
if git diff --quiet && git diff --cached --quiet; then
  echo "runtime_push_skipped=true reason=no_changes"
else
  git add data/ || true
  if git diff --cached --quiet; then
    echo "runtime_push_skipped=true reason=no_staged_changes"
  else
    git commit -m "chore(data): tier1 fast refresh $(date +%F\ %H:%M)" || true
    git pull --rebase origin main 2>/dev/null || true
    git push origin main 2>/dev/null && echo "runtime_commit_done=true" || echo "runtime_push_failed=true"
  fi
fi

echo "TIER1_RUN_OK"
