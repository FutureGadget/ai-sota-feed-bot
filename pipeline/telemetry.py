"""Server-side PostHog operational telemetry for the collect->build pipeline.

The reader-facing site already emits product events (feed_view, page_view,
impression_batch, catchup_view). The pipeline, however, emits *no* operational
telemetry, so the feed-pipeline health scout has nothing to query: pipeline
cadence, build-skip rate, circuit-breaker trips, and source-failure clusters
are all invisible, and every scout run reads "healthy" when it actually means
"blind". This module closes that gap.

Design goals:
- No new dependency: capture events over PostHog's HTTP ingestion API with
  `requests` (already required), reusing the same host convention as the
  read-side helpers (feedback.py, north_star_metric.py).
- Optional + non-fatal: when the project API key is absent (local runs,
  secret-less CI) every call no-ops cleanly and NEVER raises, so telemetry can
  never break a pipeline run.

Credentials (from env, provisioned as CI secrets on the hourly runner):
- POSTHOG_PROJECT_API_KEY (or POSTHOG_API_KEY) — the project write/ingest key
  (``phc_...``). This is distinct from the POSTHOG_PERSONAL_API_KEY that the
  read-side HogQL helpers use.
- POSTHOG_API_HOST — optional, defaults to https://us.posthog.com.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Iterable

# Stable identity for pipeline (non-user) events. Overridable per-environment.
DEFAULT_DISTINCT_ID = "ai-sota-feed-bot-pipeline"


def _api_key() -> str:
    # Project write/ingest key (phc_...), NOT the personal API key used for reads.
    return (
        os.environ.get("POSTHOG_PROJECT_API_KEY", "").strip()
        or os.environ.get("POSTHOG_API_KEY", "").strip()
    )


def _host() -> str:
    return (os.environ.get("POSTHOG_API_HOST", "").strip() or "https://us.posthog.com").rstrip("/")


def _distinct_id() -> str:
    return os.environ.get("POSTHOG_PIPELINE_DISTINCT_ID", "").strip() or DEFAULT_DISTINCT_ID


def enabled() -> bool:
    """True when a project API key is configured (telemetry will be sent)."""
    return bool(_api_key())


def build_event(event: str, properties: dict[str, Any] | None, timestamp: str) -> dict[str, Any]:
    """Build a single PostHog capture payload. Pure — safe to unit-test."""
    props: dict[str, Any] = {"service": "feed-pipeline", "$lib": "ai-sota-feed-bot"}
    if properties:
        props.update({k: v for k, v in properties.items() if v is not None})
    return {
        "event": event,
        "distinct_id": _distinct_id(),
        "properties": props,
        "timestamp": timestamp,
    }


def capture_batch(events: Iterable[tuple[str, dict[str, Any] | None]]) -> bool:
    """Send a batch of (event, properties) tuples. No-ops and never raises."""
    events = list(events)
    if not events:
        return False

    api_key = _api_key()
    if not api_key:
        # Optional integration — stay silent-but-greppable and no-op.
        print(f"telemetry_skipped events={len(events)} reason=missing_credentials")
        return False

    try:
        import requests

        now = datetime.now(timezone.utc).isoformat()
        batch = [build_event(ev, props, now) for ev, props in events]
        resp = requests.post(
            f"{_host()}/batch/",
            json={"api_key": api_key, "batch": batch},
            timeout=5,
        )
        ok = 200 <= resp.status_code < 300
        names = ",".join(sorted({ev for ev, _ in events}))
        print(
            f"telemetry_capture events={len(batch)} names={names} "
            f"ok={str(ok).lower()} status={resp.status_code}"
        )
        return ok
    except Exception as e:  # never let telemetry break the pipeline
        print(f"telemetry_capture events={len(events)} ok=false error={type(e).__name__}")
        return False


def capture(event: str, properties: dict[str, Any] | None = None) -> bool:
    """Send a single event. No-ops and never raises."""
    return capture_batch([(event, properties)])
