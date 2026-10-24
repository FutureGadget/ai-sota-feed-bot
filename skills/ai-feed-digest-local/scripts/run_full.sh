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

if [ "${AUTO_PUSH_RUNTIME:-1}" = "1" ]; then
  git rev-parse --is-inside-work-tree >/dev/null
fi

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

COLLECT_BYPASS_COOLDOWN=${FULL_RUN_BYPASS_COOLDOWN:-0} python collectors/collect.py
python pipeline/source_health.py update
python pipeline/source_alerts.py

# One edition builder. The collector writes raw, the builder applies the
# deterministic editorial policy + Jev gate, then ranks and publishes.
: "${TIER0_INCREMENTAL:=1}"
: "${TIER0_INCREMENTAL_SKIP_NO_DELTA:=1}"

DIGEST_LOG="$(mktemp -t build_digest.XXXXXX.log)"
TIER0_INCREMENTAL="$TIER0_INCREMENTAL" TIER0_INCREMENTAL_SKIP_NO_DELTA="$TIER0_INCREMENTAL_SKIP_NO_DELTA" \
  python pipeline/build_digest.py | tee "$DIGEST_LOG"

if grep -q "tier0_incremental_skip=true" "$DIGEST_LOG"; then
  echo "FULL_RUN_NO_DELTA_SKIP=true"
  exit 0
fi

# Sanity check: latest.json must be valid JSON before publishing.
python3 - <<'PY'
import json
from pathlib import Path
p = Path('data/processed/latest.json')
json.loads(p.read_text(encoding='utf-8'))
print('latest_json_valid=true')
PY

# Korean live-feed snapshots are optional and translation-provider gated.
# Missing credentials must never block the English hourly feed publish.
if [ "${STATIC_I18N_RECOVERY_BLOCKED:-0}" = "1" ]; then
  echo "localized_feed_step_skipped=true reason=unpersisted_static_usage_or_dry_run"
elif [ "${LOCALIZED_FEED_ENABLED:-1}" = "1" ]; then
  python pipeline/build_localized_feed.py --locale ko --label brief --limit 20 || echo "localized_feed_step_failed=1"
else
  LOCALIZED_FEED_ENABLED=0 python pipeline/build_localized_feed.py --locale ko --label brief --limit 20 || true
fi

# Capture this run's stories into the durable store and refresh static pages
# (/story/<sid>, recap pages, sitemap) before runtime snapshots get pruned.
# Storyline generation is intentionally owned by the Claude Code
# storyline-scout + storyline-editor routine, not this hourly workflow.
python pipeline/story_store.py sync
python pipeline/render_static_pages.py

# Processed snapshots are tiny and keep their archive; there is no Tier-1
# snapshot directory anymore.
: "${PROCESSED_RUN_RETENTION_DAYS:=45}"
: "${WEEKLY_ARCHIVE_AFTER_DAYS:=365}"
python pipeline/prune_runtime_data.py \
  --processed-days "$PROCESSED_RUN_RETENTION_DAYS" \
  --weekly-archive-after-days "$WEEKLY_ARCHIVE_AFTER_DAYS"

# Optional local->GitHub sync for Vercel auto-deploy (enabled by default)
if [ "${AUTO_PUSH_RUNTIME:-1}" = "1" ]; then
  git add data/ web/
  if git diff --cached --quiet; then
    echo "runtime_push_skipped=true reason=no_runtime_changes"
  else
    git commit -m "chore(data): refresh feed artifacts $(date +%F\ %H:%M)"
    git pull --rebase origin main
    if git push origin HEAD:main; then
      echo "runtime_commit_done=true"
    else
      echo "runtime_push_failed=true" >&2
      exit 1
    fi
  fi
fi

echo "FULL_RUN_OK"
