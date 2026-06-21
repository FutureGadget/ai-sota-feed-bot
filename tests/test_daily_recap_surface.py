from __future__ import annotations

import unittest
from pathlib import Path

from pipeline import render_static_pages as render


ROOT = Path(__file__).resolve().parents[1]


class DailyRecapSurfaceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = (ROOT / "web" / "daily.html").read_text(encoding="utf-8")

    def test_shell_uses_finishable_brief_hierarchy(self) -> None:
        self.assertIn("The finishable daily brief", self.html)
        self.assertIn("read top to bottom · then stop", self.html)
        self.assertIn("You are caught up for this edition", self.html)
        self.assertIn("class=\"cat-head\"", self.html)

    def test_shell_supports_local_preview_and_archive(self) -> None:
        self.assertIn("'/data/daily/latest.json'", self.html)
        self.assertIn("'/data/daily/index.json'", self.html)
        self.assertIn("'/data/playbook/source-index.json'", self.html)
        self.assertIn('id="archive"', self.html)

    def test_static_pages_share_the_daily_visual_system(self) -> None:
        css = render.DAILY_RECAP_CSS
        self.assertIn(".daily-hero", css)
        self.assertIn(".finish-line", css)
        self.assertIn(".playbook-takeaway", css)
        self.assertIn("@media (prefers-reduced-motion:reduce)", css)

    def test_shell_renders_capped_playbook_takeaways(self) -> None:
        self.assertIn("renderPlaybookTakeaway", self.html)
        self.assertIn("PLAYBOOK_CAP = 3", self.html)
        self.assertIn('data-track="daily-playbook"', self.html)


if __name__ == "__main__":
    unittest.main()
