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
python publish/publish_issue.py --repo FutureGadget/ai-sota-feed-bot --date "$(date +%F)"

if [ -z "${TELEGRAM_BOT_TOKEN:-}" ] || [ -z "${TELEGRAM_CHAT_ID:-}" ]; then
  echo "FULL_RUN_PARTIAL: missing TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID (issue published, telegram skipped)"
else
  python publish/publish_telegram.py
  echo "FULL_RUN_OK"
fi
