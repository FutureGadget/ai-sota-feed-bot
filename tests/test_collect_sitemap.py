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
        self.assertEqual(items[0]["published"], "2026-06-12")
        cache_row = saved_cache["https://example.com/blog/fable-mythos-access"]
        self.assertEqual(cache_row["title"], items[0]["title"])
        self.assertEqual(cache_row["description"], items[0]["summary"])


if __name__ == "__main__":
    unittest.main()
