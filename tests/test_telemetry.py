"""Unit tests for server-side pipeline telemetry (pipeline/telemetry.py).

Covers the pure payload builder and the credential-gated no-op path. The
actual HTTP POST to PostHog is exercised manually against real credentials,
not in CI (same posture as test_north_star_metric.py).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))

import telemetry  # noqa: E402


def test_build_event_shape_and_defaults():
    ev = telemetry.build_event("collect_run_completed", {"items_collected": 42}, "2026-07-02T00:00:00+00:00")
    assert ev["event"] == "collect_run_completed"
    assert ev["timestamp"] == "2026-07-02T00:00:00+00:00"
    assert ev["distinct_id"] == telemetry.DEFAULT_DISTINCT_ID
    assert ev["properties"]["items_collected"] == 42
    # Baseline tagging is always present.
    assert ev["properties"]["service"] == "feed-pipeline"
    assert ev["properties"]["$lib"] == "ai-sota-feed-bot"


def test_build_event_drops_none_properties():
    ev = telemetry.build_event("circuit_breaker_opened", {"source": "acme", "reliability": None}, "t")
    assert ev["properties"]["source"] == "acme"
    assert "reliability" not in ev["properties"]


def test_build_event_honours_distinct_id_override(monkeypatch):
    monkeypatch.setenv("POSTHOG_PIPELINE_DISTINCT_ID", "staging-pipeline")
    ev = telemetry.build_event("feed_build_completed", None, "t")
    assert ev["distinct_id"] == "staging-pipeline"


def test_enabled_reflects_project_key(monkeypatch):
    monkeypatch.delenv("POSTHOG_PROJECT_API_KEY", raising=False)
    monkeypatch.delenv("POSTHOG_API_KEY", raising=False)
    assert telemetry.enabled() is False
    monkeypatch.setenv("POSTHOG_API_KEY", "phc_test")
    assert telemetry.enabled() is True


def test_capture_noops_without_credentials(monkeypatch, capsys):
    monkeypatch.delenv("POSTHOG_PROJECT_API_KEY", raising=False)
    monkeypatch.delenv("POSTHOG_API_KEY", raising=False)
    # Must not raise and must not attempt any network call.
    assert telemetry.capture("collect_run_completed", {"items_collected": 1}) is False
    assert "telemetry_skipped" in capsys.readouterr().out


def test_capture_batch_empty_is_false():
    assert telemetry.capture_batch([]) is False


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-v"]))
