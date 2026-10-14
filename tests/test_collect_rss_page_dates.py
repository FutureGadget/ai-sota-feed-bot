"""RSS sources with `extract_published_from_page: true` (collectors/collect.py).

LangChain's Webflow feed re-stamps every item's pubDate on each site republish,
so a months-old post resurfaces as new. The page's own datePublished wins.
"""
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "collectors"))

import collect  # noqa: E402

NOW = datetime(2026, 10, 14, 12, 0, 0, tzinfo=timezone.utc)
FEED_DATE = "Tue, 13 Oct 2026 19:56:07 GMT"


class _Entry(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc


class _Parsed:
    def __init__(self, entries):
        self.entries = entries


def _feed(*urls):
    entries = [_Entry(title=u.rsplit("/", 1)[-1], link=u, summary="", published=FEED_DATE) for u in urls]
    return lambda url: _Parsed(entries)


def _source(**extra):
    return {"name": "webflow", "type": "rss", "url": "https://a/rss/",
            "extract_published_from_page": True, **extra}


class PagePublishedDateTest(unittest.TestCase):
    def setUp(self):
        self.cache = {}
        patches = [
            mock.patch.object(collect, "_load_sitemap_meta_cache", lambda: self.cache),
            mock.patch.object(collect, "_save_sitemap_meta_cache", lambda c: None),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def _collect(self, feed, fetch, source=None):
        with mock.patch.object(collect.feedparser, "parse", feed), \
                mock.patch.object(collect, "_fetch_page_meta", fetch):
            return collect.collect_from_rss(source or _source(), NOW)

    def test_page_date_replaces_restamped_feed_date_and_is_cached(self):
        calls = []

        def fetch(url):
            calls.append(url)
            return {"title": "t", "description": "", "published": "2026-02-17T16:15:28+00:00"}

        for _ in range(2):
            items = self._collect(_feed("https://a/old"), fetch)
            self.assertEqual(items[0]["published"], "2026-02-17T16:15:28+00:00")
        self.assertEqual(calls, ["https://a/old"])

    def test_feed_date_kept_when_page_has_no_date_or_fetch_fails(self):
        def fetch(url):
            if url.endswith("down"):
                raise OSError("timeout")
            return {"title": "t", "description": "", "published": None}

        items = self._collect(_feed("https://a/nodate", "https://a/down"), fetch)
        self.assertEqual([i["published"] for i in items], [FEED_DATE, FEED_DATE])
        # A completed no-date lookup is not refetched inside the TTL.
        calls = []
        self._collect(_feed("https://a/nodate"), lambda url: calls.append(url) or {})
        self.assertEqual(calls, [])

    def test_fetch_budget_caps_new_lookups(self):
        calls = []
        self._collect(
            _feed("https://a/p0", "https://a/p1", "https://a/p2"),
            lambda url: calls.append(url) or {"published": "2026-01-01T00:00:00+00:00"},
            _source(page_meta_fetch_budget=2),
        )
        self.assertEqual(len(calls), 2)

    def test_feed_dates_untouched_without_flag(self):
        def fetch(url):
            raise AssertionError("fetched")

        items = self._collect(_feed("https://a/p"), fetch, {"name": "plain", "url": "https://a/rss/"})
        self.assertEqual(items[0]["published"], FEED_DATE)


if __name__ == "__main__":
    unittest.main()
