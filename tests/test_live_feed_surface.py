from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class LiveFeedSurfaceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")

    def test_feed_uses_ranked_finite_reading_hierarchy(self) -> None:
        self.assertIn("Ranked signal · finite reading", self.html)
        self.assertIn("The AI brief that ends.", self.html)
        self.assertIn('class="rank-no"', self.html)
        self.assertIn("You're all caught up", self.html)
        self.assertEqual(self.html.count('id="meta"'), 1)

    def test_local_preview_falls_back_to_processed_feed(self) -> None:
        self.assertIn("'/data/processed/latest.json'", self.html)
        self.assertIn("Array.isArray(data)", self.html)

    def test_mechanical_ranking_copy_is_not_editorial_context(self) -> None:
        self.assertIn("/^Matches feed focus:/i.test(why)", self.html)
        self.assertIn(".trust-banner[hidden]", self.html)

    def test_feed_has_responsive_and_reduced_motion_rules(self) -> None:
        self.assertIn("@media (max-width:640px)", self.html)
        self.assertIn("prefers-reduced-motion", self.html)

    def test_editor_desk_playbook_inserts_match_source_urls(self) -> None:
        self.assertIn("function playbookCardForItem(it)", self.html)
        self.assertIn("normStorylineUrl(card?.source_url) === url", self.html)
        self.assertNotIn("playbookSources[itemKey(it)]", self.html)

    def test_korean_feed_shell_uses_localized_snapshot_endpoint(self) -> None:
        html = (ROOT / "web" / "ko" / "index.html").read_text(encoding="utf-8")
        self.assertIn('<html lang="ko">', html)
        self.assertIn('<meta name="robots" content="noindex" />', html)
        self.assertIn('href="https://www.llm-digest.com/"', html)
        self.assertIn("localized_snapshot", html)
        self.assertIn("u.searchParams.set('label', 'brief')", html)
        self.assertIn("u.searchParams.set('limit', '20')", html)
        self.assertIn("영어 live feed 보기", html)


if __name__ == "__main__":
    unittest.main()
