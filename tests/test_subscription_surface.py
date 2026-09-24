from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pipeline import render_static_pages as render


ROOT = Path(__file__).resolve().parents[1]


class SubscriptionSurfaceTest(unittest.TestCase):
    def test_canonical_page_contains_all_configuration_states(self) -> None:
        html = (ROOT / "web" / "subscribe.html").read_text(encoding="utf-8")

        self.assertIn("email_subscribe_enabled", html)
        self.assertIn("email_signup_url", html)
        self.assertIn("Email signup is temporarily unavailable", html)
        self.assertIn("ai_feed_email_subscribed_v1", html)
        self.assertIn("Subscription is temporarily unavailable", html)
        self.assertIn("Network error", html)

    def test_promoted_sources_do_not_use_old_hash_or_visible_rss_cta(self) -> None:
        paths = [
            ROOT / "web" / "index.html",
            ROOT / "web" / "daily.html",
            ROOT / "web" / "weekly.html",
            ROOT / "web" / "storyline.html",
            ROOT / "web" / "voices.html",
            ROOT / "pipeline" / "render_static_pages.py",
        ]
        combined = "\n".join(path.read_text(encoding="utf-8") for path in paths)

        self.assertNotIn("/#subscribe", combined)
        self.assertNotIn("🔔 RSS", combined)
        self.assertIn('href="/subscribe"', combined)

    def test_finish_line_ctas_have_placement_tracking(self) -> None:
        combined = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (
                ROOT / "web" / "index.html",
                ROOT / "web" / "daily.html",
                ROOT / "web" / "weekly.html",
                ROOT / "pipeline" / "render_static_pages.py",
            )
        )

        for placement in ("feed_finish", "daily_end", "weekly_end"):
            with self.subTest(placement=placement):
                self.assertIn(f'data-subscribe-placement="{placement}"', combined)

        story = {
            "sid": "abc123",
            "url": "https://example.com/story",
            "title": "Example story",
            "source": "Example",
            "published": "2026-06-25T00:00:00Z",
            "summary_1line": "A short summary.",
        }
        story_html = render.render_story_body(story, {"abc123": story})
        self.assertIn('data-subscribe-placement="story_end"', story_html)

        storyline_html = render.render_storyline_body(
            {
                "slug": "example-thread",
                "label": "Example thread",
                "days": [
                    {
                        "date": "2026-06-25",
                        "items": [
                            {
                                "sid": "abc123",
                                "url": "https://example.com/story",
                                "title": "Example story",
                                "source": "Example",
                                "published": "2026-06-25T00:00:00Z",
                            }
                        ],
                    }
                ],
            },
            {"abc123"},
        )
        self.assertIn('data-subscribe-placement="storyline_end"', storyline_html)

    def test_finish_point_ctas_opt_into_inline_signup(self) -> None:
        cta = render.subscribe_cta_html("story_end", "Title", "Detail")
        self.assertIn('href="/subscribe"', cta)  # no-JS fallback stays a link
        self.assertIn("data-subscribe-inline", cta)
        self.assertIn('data-subscribe-placement="story_end"', cta)
        source = (ROOT / "pipeline" / "render_static_pages.py").read_text(encoding="utf-8")
        self.assertIn('<script defer src="/subscribe-inline.js?v={SITE_CHROME_ASSET_VERSION}"></script>', source)

        feed = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        self.assertIn('data-subscribe-placement="feed_finish" data-subscribe-inline', feed)
        self.assertIn('<script defer src="/subscribe-inline.js?v=', feed)

    def test_inline_signup_script_reuses_the_subscribe_contract(self) -> None:
        script = (ROOT / "web" / "subscribe-inline.js").read_text(encoding="utf-8")
        self.assertIn('fetch("/api/subscribe"', script)
        self.assertIn("reader_id: readerId()", script)
        self.assertIn("ai_feed_email_subscribed_v1", script)
        self.assertIn("email_subscribe_enabled", script)
        self.assertIn("email_signup_url", script)
        self.assertIn('"subscribe_form_view"', script)
        self.assertIn('"subscribe_success"', script)

    def test_sitemap_includes_subscribe(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(render, "WEB_DIR", Path(tmp)):
                render.write_sitemap("https://example.com", [], [])
            xml = (Path(tmp) / "sitemap.xml").read_text(encoding="utf-8")

        self.assertIn("<loc>https://example.com/subscribe</loc>", xml)
        self.assertIn("<loc>https://example.com/playbook</loc>", xml)


if __name__ == "__main__":
    unittest.main()
