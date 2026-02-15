#!/usr/bin/env bash
set -euo pipefail

msg=${1:-"chore(data): refresh runtime artifacts"}

# Stage generated runtime artifacts only
git add data || true

if git diff --cached --quiet; then
  echo "No runtime data changes to commit"
  exit 0
fi

git commit -m "$msg"
git push

echo "runtime_commit_done=true"
