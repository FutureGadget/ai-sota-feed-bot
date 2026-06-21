from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class StorylineIndexSurfaceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = (ROOT / "web" / "storyline.html").read_text(encoding="utf-8")

    def test_index_uses_story_trace_hierarchy(self) -> None:
        self.assertIn("Stories do not end at launch.", self.html)
        self.assertIn("Latest change", self.html)
        self.assertIn("Builder action:", self.html)
        self.assertIn("Open evidence trace", self.html)
        self.assertIn("sl-mini-track", self.html)

    def test_index_keeps_following_filter_and_local_preview_fallback(self) -> None:
        self.assertIn('data-list-mode="following"', self.html)
        self.assertIn("ai_feed_storyline_follows_v1", self.html)
        self.assertIn("'/data/storylines/index.json'", self.html)

    def test_index_has_responsive_and_reduced_motion_rules(self) -> None:
        self.assertIn("@media (max-width: 560px)", self.html)
        self.assertIn("@media (prefers-reduced-motion:reduce)", self.html)


if __name__ == "__main__":
    unittest.main()
