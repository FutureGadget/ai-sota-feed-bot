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

branch=$(git rev-parse --abbrev-ref HEAD)
if [ "$branch" = "HEAD" ]; then
  branch="main"
fi

if ! git remote get-url origin >/dev/null 2>&1; then
  git push
  echo "code_commit_done=true"
  exit 0
fi

pushed=false
for i in 1 2 3 4; do
  if git pull --rebase origin "$branch" && git push origin "HEAD:$branch"; then
    pushed=true
    break
  else
    git rebase --abort 2>/dev/null || true
  fi
  sleep $((2 ** i))
done

if [ "$pushed" = false ]; then
  echo "Code commit push failed after retries" >&2
  exit 1
fi

echo "code_commit_done=true"

