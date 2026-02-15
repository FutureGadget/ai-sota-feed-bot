#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p data/llm

PROVIDER="${1:-anthropic}"

echo "Starting OAuth login for provider: ${PROVIDER}"
npx @mariozechner/pi-ai login "${PROVIDER}"

# npx saves auth.json in cwd
if [ -f auth.json ]; then
  mv auth.json data/llm/auth.json
fi

echo "OAuth credentials saved to data/llm/auth.json"
