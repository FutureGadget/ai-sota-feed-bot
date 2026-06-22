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

    def test_sitemap_includes_subscribe(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(render, "WEB_DIR", Path(tmp)):
                render.write_sitemap("https://example.com", [], [])
            xml = (Path(tmp) / "sitemap.xml").read_text(encoding="utf-8")

        self.assertIn("<loc>https://example.com/subscribe</loc>", xml)
        self.assertIn("<loc>https://example.com/playbook</loc>", xml)


if __name__ == "__main__":
    unittest.main()
