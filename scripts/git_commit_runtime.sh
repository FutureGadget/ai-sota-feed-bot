#!/usr/bin/env bash
set -euo pipefail

msg=${1:-"chore(data): refresh runtime artifacts"}

# Stage generated runtime artifacts only
git add data web/models-data.json web/models-top.json 2>/dev/null || true

if git diff --cached --quiet; then
  echo "No runtime data changes to commit"
  exit 0
fi

git commit -m "$msg"

branch=$(git rev-parse --abbrev-ref HEAD)
if [ "$branch" = "HEAD" ]; then
  branch="main"
fi

if ! git remote get-url origin >/dev/null 2>&1; then
  git push
  echo "runtime_commit_done=true"
  exit 0
fi

# main is busy with automated bot commits — rebase and retry on push.
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
  echo "Runtime commit push failed after retries" >&2
  exit 1
fi

echo "runtime_commit_done=true"

