"""Unit tests for multi-feed `rss` sources (collectors/collect.py).

Covers the `urls:` fan-in used by cloudflare_blog, where several tag-scoped
feeds carve an on-topic slice out of a broader blog and overlap each other.
The HTTP fetch itself is exercised by validate_source.py runs, not CI.
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "collectors"))

import collect  # noqa: E402

NOW = datetime(2026, 8, 5, 12, 0, 0, tzinfo=timezone.utc)


class _Entry(dict):
    """feedparser entries expose keys as attributes."""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc


class _Parsed:
    def __init__(self, entries):
        self.entries = entries


def _entry(title, url, published="Wed, 05 Aug 2026 13:00:00 GMT"):
    return _Entry(title=title, link=url, summary=f"<p>{title}</p>", published=published)


def _fake_parse(feeds):
    def parse(url):
        return _Parsed(feeds.get(url, []))

    return parse


def test_urls_list_resolves_all_feeds():
    source = {"name": "multi", "type": "rss", "urls": ["https://a/rss/", "https://b/rss/"]}
    assert collect.rss_source_urls(source) == ["https://a/rss/", "https://b/rss/"]


def test_single_url_key_still_works():
    assert collect.rss_source_urls({"name": "one", "url": "https://a/rss/"}) == ["https://a/rss/"]


def test_missing_url_yields_no_feeds():
    assert collect.rss_source_urls({"name": "none", "type": "rss"}) == []


def test_blank_entries_are_dropped_from_urls_list():
    source = {"urls": ["https://a/rss/", "  ", ""]}
    assert collect.rss_source_urls(source) == ["https://a/rss/"]


def test_collects_union_of_feeds(monkeypatch):
    feeds = {
        "https://a/rss/": [_entry("Alpha", "https://blog/alpha/")],
        "https://b/rss/": [_entry("Beta", "https://blog/beta/")],
    }
    monkeypatch.setattr(collect.feedparser, "parse", _fake_parse(feeds))
    entries = collect.collect_from_rss({"urls": list(feeds)}, NOW)
    assert [e["title"] for e in entries] == ["Alpha", "Beta"]


def test_overlapping_feeds_yield_one_item_per_article(monkeypatch):
    # A post tagged both "ai" and "agents" appears in both tag feeds.
    shared = _entry("Shared", "https://blog/shared/")
    feeds = {
        "https://a/rss/": [shared, _entry("OnlyA", "https://blog/only-a/")],
        "https://b/rss/": [_entry("Shared", "https://blog/shared/"), _entry("OnlyB", "https://blog/only-b/")],
    }
    monkeypatch.setattr(collect.feedparser, "parse", _fake_parse(feeds))
    entries = collect.collect_from_rss({"urls": list(feeds)}, NOW)
    assert [e["title"] for e in entries] == ["Shared", "OnlyA", "OnlyB"]


def test_dedupe_ignores_trailing_slash_case_and_query(monkeypatch):
    feeds = {
        "https://a/rss/": [_entry("Post", "https://blog/Post/")],
        "https://b/rss/": [_entry("Post", "https://blog/post?utm_source=rss")],
    }
    monkeypatch.setattr(collect.feedparser, "parse", _fake_parse(feeds))
    entries = collect.collect_from_rss({"urls": list(feeds)}, NOW)
    assert len(entries) == 1


def test_entries_missing_title_or_link_are_skipped(monkeypatch):
    feeds = {
        "https://a/rss/": [
            _entry("", "https://blog/no-title/"),
            _entry("No link", ""),
            _entry("Good", "https://blog/good/"),
        ]
    }
    monkeypatch.setattr(collect.feedparser, "parse", _fake_parse(feeds))
    entries = collect.collect_from_rss({"urls": list(feeds)}, NOW)
    assert [e["title"] for e in entries] == ["Good"]


def test_published_falls_back_to_now(monkeypatch):
    entry = _Entry(title="No date", link="https://blog/no-date/", summary="")
    monkeypatch.setattr(collect.feedparser, "parse", _fake_parse({"https://a/rss/": [entry]}))
    entries = collect.collect_from_rss({"urls": ["https://a/rss/"]}, NOW)
    assert entries[0]["published"] == NOW.isoformat()


def test_cloudflare_source_is_configured_as_tag_scoped_feeds():
    import yaml

    root = Path(__file__).resolve().parents[1]
    sources = yaml.safe_load((root / "config" / "sources.yaml").read_text())["sources"]
    cf = next(s for s in sources if s["name"] == "cloudflare_blog")
    urls = collect.rss_source_urls(cf)
    assert len(urls) == 3
    # The main blog feed mixes in CDN/network/billing posts — tag feeds only.
    assert all("/tag/" in u for u in urls)
    assert all(u.startswith("https://blog.cloudflare.com/") for u in urls)


def test_cloudflare_source_is_mapped_to_a_ranking_slot():
    import yaml

    root = Path(__file__).resolve().parents[1]
    for path in (root / "config" / "ranking.yaml", root / "config" / "presets" / "balanced.yaml"):
        slots = yaml.safe_load(path.read_text())["slots"]
        owning = [name for name, cfg in slots.items() if "cloudflare_blog" in (cfg.get("sources") or [])]
        assert owning == ["cloud_platform_updates"], path
        # One seat per platform, so an Agents Week burst cannot take the slot.
        assert slots["cloud_platform_updates"]["max_per_source"] == 1, path
