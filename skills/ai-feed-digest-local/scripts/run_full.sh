#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../../.."

source .venv/bin/activate

if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

python collectors/collect.py
python pipeline/source_health.py update
python pipeline/source_alerts.py
python pipeline/build_digest.py

# Optional local->GitHub sync for Vercel auto-deploy (enabled by default)
if [ "${AUTO_PUSH_RUNTIME:-1}" = "1" ]; then
  git pull --rebase --autostash
  ./scripts/git_commit_runtime.sh "chore(data): refresh feed artifacts $(date +%F\ %H:%M)"
fi

python publish/publish_issue.py --repo FutureGadget/ai-sota-feed-bot --date "$(date +%F)"

if [ -z "${TELEGRAM_BOT_TOKEN:-}" ] || [ -z "${TELEGRAM_CHAT_ID:-}" ]; then
  echo "FULL_RUN_PARTIAL: missing TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID (issue published, telegram skipped)"
else
  python publish/publish_telegram.py
  echo "FULL_RUN_OK"
fi
