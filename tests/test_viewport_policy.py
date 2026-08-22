from __future__ import annotations

import unittest
from pathlib import Path

from pipeline import render_static_pages as render


ROOT = Path(__file__).resolve().parents[1]
VIEWPORT_POLICY = 'content="width=device-width, initial-scale=1.0"'
HAND_AUTHORED_PAGES = (
    "daily.html",
    "index.html",
    "map.html",
    "models.html",
    "playbook.html",
    "storyline.html",
    "subscribe.html",
    "voices.html",
    "weekly.html",
)


class ViewportPolicyTest(unittest.TestCase):
    def test_hand_authored_pages_allow_pinch_zoom(self) -> None:
        for filename in HAND_AUTHORED_PAGES:
            with self.subTest(filename=filename):
                html = (ROOT / "web" / filename).read_text(encoding="utf-8")
                self.assertIn(VIEWPORT_POLICY, html)
                self.assertNotIn("user-scalable", html)

    def test_generated_pages_allow_pinch_zoom(self) -> None:
        head = render.render_head(
            title="Example",
            description="Example page",
            canonical="https://www.llm-digest.com/example",
            published=None,
        )
        redirect = render.render_redirect_page(
            "https://www.llm-digest.com",
            "old-thread",
            "current-thread",
        )

        self.assertIn(VIEWPORT_POLICY, head)
        self.assertIn(VIEWPORT_POLICY, redirect)

    def test_share_fallback_allows_pinch_zoom(self) -> None:
        source = (ROOT / "api" / "share.js").read_text(encoding="utf-8")
        self.assertIn(VIEWPORT_POLICY, source)


if __name__ == "__main__":
    unittest.main()
