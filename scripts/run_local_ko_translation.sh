#!/usr/bin/env bash
# ==============================================================================
# Script: scripts/run_local_ko_translation.sh
# Purpose: Orchestrates the hourly/scheduled translation pipeline for the
#          Korean (/ko/) live feed and static pages using a local LLM.
#
# Usage:
#   chmod +x scripts/run_local_ko_translation.sh
#   ./scripts/run_local_ko_translation.sh
#
# Prerequisites:
#   1. LM Studio must be running locally with the model (default: google/gemma-4-e4b) loaded.
#   2. Local git repository configured with write access to origin/main.
# ==============================================================================

set -euo pipefail

# Set paths relative to script location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Configurable options
LM_STUDIO_URL="http://localhost:1234/v1"
MODEL_NAME="google/gemma-4-e4b"
BASE_URL="https://www.llm-digest.com"

echo "=== [1/5] Checking Prerequisites & Updating Repository ==="
# Verify LM Studio is reachable
if ! curl -s -f -o /dev/null "${LM_STUDIO_URL}/models"; then
  echo "Error: LM Studio is not running or not reachable at ${LM_STUDIO_URL}"
  echo "Please start LM Studio, load your model, and try again."
  exit 1
fi
echo "LM Studio is active."

# Ensure we are on main and up to date to prevent push conflicts
cd "${ROOT_DIR}"
echo "Pulling latest changes from remote..."
git checkout main
git pull origin main

echo -e "\n=== [2/5] Translating Live Feed Snapshot ==="
# Translates the top 20 ranked Brief snapshot items.
# Outputs: data/i18n/ko/feed/latest.json & data/i18n/ko/feed/status.json
python3 pipeline/build_localized_feed.py \
  --locale ko \
  --label brief \
  --limit 20 \
  --model "${MODEL_NAME}" \
  --base-url "${LM_STUDIO_URL}"

echo -e "\n=== [3/5] Translating Static Pages ==="
# Scans the workspace and translates all missing/stale static pages
# (daily/weekly recaps, storylines, wiki topics, foundations concepts).
# Uses a large limit to translate everything in the queue.
python3 scripts/translate_local.py \
  --locale ko \
  --limit 1000 \
  --days 1 \
  --model "${MODEL_NAME}" \
  --base-url "${LM_STUDIO_URL}"

echo -e "\n=== [4/5] Re-rendering Static HTML Pages & Sitemap ==="
# Compiles the newly translated JSON/Markdown sidecars under data/i18n/ko/
# into static HTML files under web/ko/ and regenerates the search sitemap.
python3 pipeline/render_static_pages.py --base-url "${BASE_URL}"

echo -e "\n=== [5/5] Committing & Publishing to Remote Main ==="
# Check if there are changes to publish
if [[ -z "$(git status --porcelain data/i18n/ko/ web/ko/ web/sitemap.xml)" ]]; then
  echo "No translation updates or rendered pages changed. Nothing to commit."
else
  echo "Translation updates detected. Staging and committing..."
  git add data/i18n/ko/ web/ko/ web/sitemap.xml
  git commit -m "chore(data): refresh Korean feed snapshots and static pages"
  
  echo "Pushing commits to remote repository..."
  git push origin main
  echo "Korean feed and pages successfully updated & pushed to main!"
fi

echo -e "\n=== Execution Complete! ==="
