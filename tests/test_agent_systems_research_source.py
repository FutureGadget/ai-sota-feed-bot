"""Regression coverage for the targeted agent-systems research source."""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))

import ranking  # noqa: E402


NOW = datetime(2026, 9, 3, 12, 0, 0, tzinfo=timezone.utc)
SOURCE = "arxiv_agent_systems_research"


def _source_config() -> dict:
    sources = yaml.safe_load((ROOT / "config" / "sources.yaml").read_text(encoding="utf-8"))["sources"]
    return next(source for source in sources if source["name"] == SOURCE)


def test_targeted_agent_systems_source_is_configured_and_mapped_to_research_watch():
    source = _source_config()
    assert source["type"] == "arxiv_api"
    assert "prompt optimization" in source["search_query"].lower()

    for path in (ROOT / "config" / "ranking.yaml", ROOT / "config" / "presets" / "balanced.yaml"):
        cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert SOURCE in cfg["slots"]["research_watch"]["sources"], path
        assert SOURCE in cfg["source_bias"], path


def test_fresh_agent_optimization_paper_can_reach_the_feed(monkeypatch):
    monkeypatch.setattr(ranking, "_now_utc", lambda: NOW)
    profile = yaml.safe_load((ROOT / "config" / "profile.yaml").read_text(encoding="utf-8"))
    paper = {
        "id": "gepa-fixture",
        "source": SOURCE,
        "title": "GEPA: Reflective Prompt Evolution for Agent Systems",
        "url": "https://arxiv.org/abs/2609.00001",
        "summary": "Prompt optimization improves agent trajectories, tool use, and evaluation efficiency.",
        "published": "2026-09-03T11:00:00+00:00",
    }

    top, _ = ranking.run_ranking([paper], profile, {"enabled": False}, {SOURCE: 1.0})

    assert len(top) == 1
    assert top[0]["source"] == SOURCE
    assert top[0]["slot"] == "research_watch"
