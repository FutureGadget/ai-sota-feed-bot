from __future__ import annotations

import unittest
from pathlib import Path

from pipeline import render_static_pages as render


ROOT = Path(__file__).resolve().parents[1]


class WeeklyRecapSurfaceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = (ROOT / "web" / "weekly.html").read_text(encoding="utf-8")

    def test_shell_presents_the_week_as_patterns(self) -> None:
        self.assertIn("Weekly pattern report", self.html)
        self.assertIn("The week in signals", self.html)
        self.assertIn("shifts that shaped AI this week", self.html)
        self.assertIn("supporting item", self.html)
        self.assertIn("The week, resolved into patterns", self.html)

    def test_shell_supports_local_preview_and_archive(self) -> None:
        self.assertIn("'/data/weekly/latest.json'", self.html)
        self.assertIn("'/data/weekly/index.json'", self.html)
        self.assertIn('id="archive"', self.html)

    def test_static_pages_share_the_weekly_visual_system(self) -> None:
        css = render.WEEKLY_RECAP_CSS
        self.assertIn(".weekly-hero", css)
        self.assertIn(".weekly-close", css)
        self.assertIn("@media (prefers-reduced-motion:reduce)", css)


if __name__ == "__main__":
    unittest.main()
