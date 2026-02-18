#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "usage: $0 <anon_user_id>"
  exit 1
fi

ANON_ID="$1"
APP_URL="https://ai-sota-feed-bot.vercel.app"

set_env_all() {
  local key="$1"
  local val="$2"
  for env in production preview development; do
    vercel env rm "$key" "$env" -y >/dev/null 2>&1 || true
    printf '%s' "$val" | vercel env add "$key" "$env" >/dev/null
  done
}

echo "[1/4] setting test env knobs"
set_env_all PERSONALIZATION_MODE active
set_env_all PERSONALIZATION_MIN_CLICKS 1
set_env_all PERSONALIZATION_MIN_IMPRESSIONS 20

echo "[2/4] deploying prod"
vercel --prod --yes >/dev/null

echo "[3/4] querying debug feed"
RESP=$(curl -sS "${APP_URL}/api/feed?limit=10&anon_user_id=${ANON_ID}&debug_personalization=1")
echo "$RESP" | jq '.personalization'
echo "$RESP" | jq '.items[0] | {source, _source_boost, _topic_boost, _personal_boost, _final_score}'

echo "[4/4] current event totals"
turso db shell ai-sota-feed-bot "select event_type, count(*) as cnt from feed_events group by event_type order by cnt desc;"

echo "done"
