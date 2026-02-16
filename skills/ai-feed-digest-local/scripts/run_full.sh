#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../../.."

LOCK_DIR=".run_full.lock"
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  echo "FULL_RUN_SKIPPED: another run_full.sh execution is already in progress"
  exit 0
fi
cleanup() { rmdir "$LOCK_DIR" 2>/dev/null || true; }
trap cleanup EXIT

source .venv/bin/activate

PREEXISTING_DIRTY=0
if ! git diff --quiet || ! git diff --cached --quiet; then
  PREEXISTING_DIRTY=1
fi

if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

# Sync first while worktree is still clean to avoid data-file rebase conflicts later.
if [ "${AUTO_PUSH_RUNTIME:-1}" = "1" ] && [ "$PREEXISTING_DIRTY" = "0" ]; then
  git pull --rebase
fi

python collectors/collect.py
python pipeline/source_health.py update
python pipeline/source_alerts.py
python pipeline/build_digest.py

# Sanity check: latest.json must be valid JSON before publishing.
python3 - <<'PY'
import json
from pathlib import Path
p = Path('data/processed/latest.json')
json.loads(p.read_text(encoding='utf-8'))
print('latest_json_valid=true')
PY

# Optional local->GitHub sync for Vercel auto-deploy (enabled by default)
if [ "${AUTO_PUSH_RUNTIME:-1}" = "1" ]; then
  if [ "$PREEXISTING_DIRTY" = "1" ]; then
    echo "runtime_push_skipped=true reason=preexisting_dirty_worktree"
  else
    git add data || true
    if git diff --cached --quiet; then
      echo "runtime_push_skipped=true reason=no_runtime_changes"
    else
      git commit -m "chore(data): refresh feed artifacts $(date +%F\ %H:%M)"
      git push
      echo "runtime_commit_done=true"
    fi
  fi
fi

python publish/publish_issue.py --repo FutureGadget/ai-sota-feed-bot --date "$(date +%F)"

if [ -z "${TELEGRAM_BOT_TOKEN:-}" ] || [ -z "${TELEGRAM_CHAT_ID:-}" ]; then
  echo "FULL_RUN_PARTIAL: missing TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID (issue published, telegram skipped)"
else
  python publish/publish_telegram.py
  echo "FULL_RUN_OK"
fi
