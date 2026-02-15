#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../../.."

source .venv/bin/activate
python collectors/collect.py
python pipeline/source_health.py update
python pipeline/source_alerts.py
python pipeline/build_digest.py
python publish/publish_issue.py --repo FutureGadget/ai-sota-feed-bot --date "$(date +%F)"
python publish/publish_telegram.py

echo "FULL_RUN_OK"
