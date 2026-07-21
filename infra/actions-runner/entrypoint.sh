#!/usr/bin/env bash
set -euo pipefail

RUNNER_HOME=/home/runner
cd "$RUNNER_HOME"

require_env() {
  local name="$1"
  if [ -z "${!name:-}" ]; then
    echo "runner_configuration_error=missing_${name}" >&2
    exit 1
  fi
}

if [ ! -f "$RUNNER_HOME/.runner" ]; then
  require_env "RUNNER_URL"
  require_env "RUNNER_TOKEN"

  ./config.sh \
    --unattended \
    --replace \
    --url "$RUNNER_URL" \
    --token "$RUNNER_TOKEN" \
    --name "${RUNNER_NAME:-llm-digest-docker-arm64}" \
    --labels "${RUNNER_LABELS:-llm-digest}" \
    --work "${RUNNER_WORK:-_work}"
fi

# The one-hour registration token is not needed after config.sh exchanges it
# for the runner's persistent credentials in the named volume.
unset RUNNER_TOKEN

exec ./run.sh
