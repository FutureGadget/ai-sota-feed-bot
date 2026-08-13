"""Unit tests for per-source title exclusion (collectors/collect.py).

Covers `exclude_title_regex:` in config/sources.yaml, used by databricks_blog:
Databricks publishes no category-scoped feed, so the site-wide feed is the only
option and it carries a recurring SEO glossary series alongside the engineering
posts. Also pins the databricks_blog ranking wiring, since a source that is not
mapped to a slot never reaches the feed.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "collectors"))

import collect  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def _excluded(source, title):
    return any(pat.search(title) for pat in collect.compile_title_excludes(source))


def test_source_without_the_key_excludes_nothing():
    assert collect.compile_title_excludes({"name": "plain", "type": "rss"}) == []


def test_patterns_are_compiled_in_order():
    pats = collect.compile_title_excludes({"exclude_title_regex": ["^a", "b$"]})
    assert [p.pattern for p in pats] == ["^a", "b$"]


def test_invalid_pattern_raises_so_the_source_is_recorded_as_error():
    # Silently ignoring it would collect exactly the titles it was meant to drop.
    try:
        collect.compile_title_excludes({"exclude_title_regex": ["(unclosed"]})
    except re.error:
        return
    raise AssertionError("invalid regex should raise")


def _databricks_source():
    import yaml

    sources = yaml.safe_load((ROOT / "config" / "sources.yaml").read_text())["sources"]
    return next(s for s in sources if s["name"] == "databricks_blog")


def test_databricks_uses_the_site_wide_feed():
    src = _databricks_source()
    assert src["type"] == "rss"
    # No category-scoped feed exists (/blog/category/<x>/feed and
    # /blog/rss.xml both 404), so the AI slice cannot be taken at the source.
    assert src["url"] == "https://www.databricks.com/feed"


def test_databricks_drops_the_data_ai_foundations_glossary_series():
    src = _databricks_source()
    for title in ("What is an AI Assistant?", "What is Tool Calling?", "What are Agentic Workflows?"):
        assert _excluded(src, title), title


def test_databricks_keeps_engineering_posts():
    src = _databricks_source()
    for title in (
        "Benchmarking Coding Agents on Databricks' Multi-Million Line Codebase",
        "Managing AI Coding Costs at Scale",
        "Introducing OfficeQA Pro V2: A New Benchmark for Enterprise Grounded-Reasoning",
        "Unity AI Gateway is Generally Available",
    ):
        assert not _excluded(src, title), title


def test_glossary_pattern_is_anchored_at_the_title_start():
    # A mid-title question is analysis, not a glossary entry.
    src = _databricks_source()
    assert not _excluded(src, "Agent evals: what is worth measuring?")


def test_databricks_is_mapped_to_a_ranking_slot():
    import yaml

    for path in (ROOT / "config" / "ranking.yaml", ROOT / "config" / "presets" / "balanced.yaml"):
        slots = yaml.safe_load(path.read_text())["slots"]
        owning = [name for name, cfg in slots.items() if "databricks_blog" in (cfg.get("sources") or [])]
        assert owning == ["cloud_platform_updates"], path
        slot = slots["cloud_platform_updates"]
        # One seat per platform: max_items tracks the source count, and
        # max_per_source keeps a single platform from taking the whole slot.
        assert slot["max_per_source"] == 1, path
        assert slot["max_items"] == len(slot["sources"]), path
