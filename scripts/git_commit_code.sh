#!/usr/bin/env bash
set -euo pipefail

msg=${1:-"chore: update code"}

# Stage code/config/docs/workflow changes only
git add AGENTS.md README.md || true
git add collectors pipeline publish config docs scripts .github/workflows || true

if git diff --cached --quiet; then
  echo "No code/config/docs changes to commit"
  exit 0
fi

git commit -m "$msg"
git push

echo "code_commit_done=true"
