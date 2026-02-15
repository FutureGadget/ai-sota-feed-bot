#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p data/llm
npx @mariozechner/pi-ai login openai-codex
# npx saves auth.json in cwd
if [ -f auth.json ]; then
  mv auth.json data/llm/auth.json
fi
echo "OAuth credentials saved to data/llm/auth.json"
