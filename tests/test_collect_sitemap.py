from __future__ import annotations

import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from collectors import collect


class FakeResponse:
    def __init__(self, body: str) -> None:
        self.body = body.encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def read(self) -> bytes:
        return self.body


class SitemapCollectionTest(unittest.TestCase):
    def test_date_only_publication_metadata_uses_neutral_midday_anchor(self) -> None:
        page = """
        <html>
          <head>
            <meta name="date" content="2026-08-26">
          </head>
        </html>
        """
        with patch.object(collect.urllib.request, "urlopen", return_value=FakeResponse(page)):
            result = collect._fetch_page_meta("https://example.com/blog/date-only")

        self.assertEqual(result["published"], "2026-08-26T12:00:00+00:00")

    def test_fetch_page_meta_handles_attribute_order_and_quotes(self) -> None:
        page = """
        <html>
          <head>
            <meta content="A launch for &quot;platform teams&quot; &amp; builders"
                  property="og:description">
            <meta content="The Real Launch Title" property="og:title">
            <meta content="2026-06-13T08:30:00-07:00"
                  property="article:published_time">
            <title>Fallback title | Example</title>
          </head>
        </html>
        """
        with patch.object(collect.urllib.request, "urlopen", return_value=FakeResponse(page)):
            result = collect._fetch_page_meta("https://example.com/blog/launch")

        self.assertEqual(result["title"], "The Real Launch Title")
        self.assertEqual(
            result["description"],
            'A launch for "platform teams" & builders',
        )
        self.assertEqual(result["published"], "2026-06-13T15:30:00+00:00")

    def test_fetch_page_meta_extracts_anthropic_visible_article_date(self) -> None:
        page = """
        <html>
          <body>
            <h1 class="headline-1 PostDetail-module__title">
              Introducing 100K context windows
            </h1>
            <div class="body-3 agate">May 11, 2023</div>
          </body>
        </html>
        """
        with patch.object(collect.urllib.request, "urlopen", return_value=FakeResponse(page)):
            result = collect._fetch_page_meta(
                "https://www.anthropic.com/news/100k-context-windows"
            )

        self.assertEqual(result["published"], "2023-05-11T00:00:00+00:00")

    def test_extract_enabled_sitemap_does_not_use_lastmod_as_publication(self) -> None:
        sitemap = """
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
          <url>
            <loc>https://example.com/blog/old-post</loc>
            <lastmod>2026-08-26T18:11:29.000Z</lastmod>
          </url>
        </urlset>
        """
        page = """
        <html>
          <head><title>Old post</title></head>
          <body><p>This page exposes no publication metadata.</p></body>
        </html>
        """
        source = {
            "name": "example_blog",
            "type": "sitemap",
            "url": "https://example.com/sitemap.xml",
            "include_prefixes": ["https://example.com/blog/"],
            "extract_published_from_page": True,
        }
        now = datetime(2026, 8, 28, tzinfo=timezone.utc)
        saved_cache = {}

        def save_cache(cache):
            saved_cache.update(cache)

        with (
            patch.object(
                collect.urllib.request,
                "urlopen",
                side_effect=[FakeResponse(sitemap), FakeResponse(page)],
            ),
            patch.object(collect, "_load_sitemap_meta_cache", return_value={}),
            patch.object(collect, "_save_sitemap_meta_cache", side_effect=save_cache),
        ):
            items = collect.collect_from_sitemap(source, now)

        self.assertEqual(items[0]["published"], now.isoformat())
        self.assertEqual(
            saved_cache["https://example.com/blog/old-post"]["discovered_at"],
            now.isoformat(),
        )

    def test_sitemap_items_use_fetched_title_and_description(self) -> None:
        sitemap = """
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
          <url>
            <loc>https://example.com/blog/fable-mythos-access</loc>
            <lastmod>2026-06-12</lastmod>
          </url>
        </urlset>
        """
        page = """
        <html>
          <head>
            <meta property="og:title" content="Claude access expands for teams">
            <meta property="article:published_time" content="2026-06-12">
            <meta name="description"
                  content="Anthropic explains the rollout, controls, and availability.">
          </head>
        </html>
        """
        source = {
            "name": "example_blog",
            "type": "sitemap",
            "url": "https://example.com/sitemap.xml",
            "include_prefixes": ["https://example.com/blog/"],
            "extract_published_from_page": True,
        }
        saved_cache = {}

        def save_cache(cache):
            saved_cache.update(cache)

        with (
            patch.object(
                collect.urllib.request,
                "urlopen",
                side_effect=[FakeResponse(sitemap), FakeResponse(page)],
            ),
            patch.object(collect, "_load_sitemap_meta_cache", return_value={}),
            patch.object(collect, "_save_sitemap_meta_cache", side_effect=save_cache),
        ):
            items = collect.collect_from_sitemap(
                source,
                datetime(2026, 6, 14, tzinfo=timezone.utc),
            )

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "Claude access expands for teams")
        self.assertEqual(
            items[0]["summary"],
            "Anthropic explains the rollout, controls, and availability.",
        )
        self.assertEqual(items[0]["published"], "2026-06-12T12:00:00+00:00")
        cache_row = saved_cache["https://example.com/blog/fable-mythos-access"]
        self.assertEqual(cache_row["title"], items[0]["title"])
        self.assertEqual(cache_row["description"], items[0]["summary"])

    def _launch_source(self, **extra) -> dict:
        source = {
            "name": "anthropic_newsroom",
            "type": "sitemap",
            "url": "https://www.anthropic.com/sitemap.xml",
            "include_prefixes": ["https://www.anthropic.com/news/"],
            "include_patterns": [r"^https://www\.anthropic\.com/claude-[a-z0-9-]+$"],
        }
        source.update(extra)
        return source

    def test_include_patterns_keep_top_level_launch_pages(self) -> None:
        sitemap = """
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
          <url><loc>https://www.anthropic.com/claude-opus-5-5</loc><lastmod>2026-10-10</lastmod></url>
          <url><loc>https://www.anthropic.com/claude/fable</loc><lastmod>2026-11-01</lastmod></url>
          <url><loc>https://www.anthropic.com/news/s1-sec</loc><lastmod>2026-10-26</lastmod></url>
          <url><loc>https://www.anthropic.com/careers</loc><lastmod>2026-11-02</lastmod></url>
        </urlset>
        """
        now = datetime(2026, 11, 10, tzinfo=timezone.utc)
        with patch.object(collect.urllib.request, "urlopen", return_value=FakeResponse(sitemap)):
            items = collect.collect_from_sitemap(self._launch_source(), now)

        self.assertEqual(
            [i["url"] for i in items],
            [
                "https://www.anthropic.com/news/s1-sec",
                "https://www.anthropic.com/claude-opus-5-5",
            ],
        )

    def test_index_page_links_surface_launch_missing_from_sitemap(self) -> None:
        sitemap = """
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
          <url><loc>https://www.anthropic.com/news/s1-sec</loc><lastmod>2026-10-26</lastmod></url>
        </urlset>
        """
        index = """
        <html><body>
          <a href="/news">All news</a>
          <a href="/claude-fable-and-mythos-5-2">Introducing Claude Fable 5.2</a>
          <a href="https://www.anthropic.com/news/s1-sec?utm=x">S-1</a>
          <a href="/claude/fable">Fable product page</a>
          <a href="/careers">Careers</a>
        </body></html>
        """
        source = self._launch_source(index_pages=["https://www.anthropic.com/news"])
        now = datetime(2026, 11, 10, tzinfo=timezone.utc)
        with patch.object(
            collect.urllib.request,
            "urlopen",
            side_effect=[FakeResponse(sitemap), FakeResponse(index)],
        ):
            items = collect.collect_from_sitemap(source, now)

        self.assertEqual(
            [i["url"] for i in items],
            [
                "https://www.anthropic.com/claude-fable-and-mythos-5-2",
                "https://www.anthropic.com/news/s1-sec",
            ],
        )

    def test_index_page_failure_does_not_fail_sitemap_source(self) -> None:
        sitemap = """
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
          <url><loc>https://www.anthropic.com/news/s1-sec</loc><lastmod>2026-10-26</lastmod></url>
        </urlset>
        """
        source = self._launch_source(index_pages=["https://www.anthropic.com/news"])
        now = datetime(2026, 11, 10, tzinfo=timezone.utc)
        with patch.object(
            collect.urllib.request,
            "urlopen",
            side_effect=[FakeResponse(sitemap), OSError("boom")],
        ):
            items = collect.collect_from_sitemap(source, now)

        self.assertEqual([i["url"] for i in items], ["https://www.anthropic.com/news/s1-sec"])

    def test_undated_pattern_page_is_dropped_but_dated_one_kept(self) -> None:
        sitemap = """
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
          <url><loc>https://www.anthropic.com/claude-opus-5-5</loc><lastmod>2026-11-09</lastmod></url>
          <url><loc>https://www.anthropic.com/claude-fable-and-mythos-5-2</loc><lastmod>2026-11-09</lastmod></url>
          <url><loc>https://www.anthropic.com/news/undated-post</loc><lastmod>2026-11-08</lastmod></url>
        </urlset>
        """
        undated = "<html><head><title>Introducing Claude Opus 5.5</title></head></html>"
        dated = (
            '<html><head><meta property="og:title" content="Fable 5.2">'
            '<meta property="article:published_time" content="2026-11-09"></head></html>'
        )
        news = "<html><head><title>Undated news</title></head></html>"
        source = self._launch_source(extract_published_from_page=True)
        now = datetime(2026, 11, 10, tzinfo=timezone.utc)
        pages = {
            "https://www.anthropic.com/claude-opus-5-5": undated,
            "https://www.anthropic.com/claude-fable-and-mythos-5-2": dated,
            "https://www.anthropic.com/news/undated-post": news,
        }

        def fake_urlopen(req, timeout=30):
            url = req.full_url
            return FakeResponse(sitemap if url.endswith("sitemap.xml") else pages[url])

        with (
            patch.object(collect.urllib.request, "urlopen", side_effect=fake_urlopen),
            patch.object(collect, "_load_sitemap_meta_cache", return_value={}),
            patch.object(collect, "_save_sitemap_meta_cache"),
        ):
            items = collect.collect_from_sitemap(source, now)

        self.assertEqual(
            sorted(i["url"] for i in items),
            [
                "https://www.anthropic.com/claude-fable-and-mythos-5-2",
                "https://www.anthropic.com/news/undated-post",
            ],
        )


if __name__ == "__main__":
    unittest.main()
