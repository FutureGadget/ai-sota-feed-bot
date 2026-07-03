from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class VoicesSurfaceTest(unittest.TestCase):
    """Structural guards for the redesigned /voices reading guide.

    Reader job: decide who is worth reading and why. The editor's reason must be
    the dominant content; links are quiet; the list is curated, not ranked. These
    assertions pin that hierarchy and the hand-curated data/outbound links.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.html = (ROOT / "web" / "voices.html").read_text(encoding="utf-8")

    def test_uses_shared_instrument_token_system(self) -> None:
        self.assertIn("--bg:#f5f7fa;", self.html)
        self.assertIn("--accent:#2457d6;", self.html)
        self.assertIn("--bg:#11151c;", self.html)  # dark
        self.assertIn('"Avenir Next Condensed"', self.html)
        self.assertIn("ui-monospace", self.html)

    def test_annotated_reading_guide_signature(self) -> None:
        self.assertIn('class="voices-list"', self.html)
        self.assertIn('class="voice"', self.html)
        self.assertIn('class="voice-name"', self.html)
        self.assertIn('class="voice-why"', self.html)
        self.assertIn('class="voice-read"', self.html)
        self.assertIn(">Read</span>", self.html)
        # The old equal-card list + link pills are gone.
        self.assertNotIn('class="links"', self.html)
        self.assertNotIn('class="why"', self.html)
        self.assertNotIn('class="role"', self.html)

    def test_curated_not_ranked(self) -> None:
        # No leaderboard framing; the order is explicitly editorial.
        self.assertIn("curated, not ranked", self.html)
        self.assertIn("the order is editorial, not a ranking", self.html)
        self.assertIn("Who to actually read on AI", self.html)

    def test_preserves_curated_people_and_outbound_links(self) -> None:
        for name in ("Dario Amodei", "Andrej Karpathy", "Simon Willison", "Lilian Weng"):
            self.assertIn(name, self.html)
        # Outbound links open safely in a new tab; the curated data is intact.
        self.assertIn('target="_blank" rel="noopener"', self.html)
        self.assertIn("karpathy.ai", self.html)
        self.assertIn("lilianweng.github.io", self.html)
        self.assertEqual(self.html.count("name: '"), 12)

    def test_quality_floor(self) -> None:
        self.assertIn("outline:3px solid color-mix(in srgb,var(--accent) 50%,transparent)", self.html)
        self.assertIn('id="themeToggle"', self.html)
        self.assertIn("isLocalPreview", self.html)  # mascot opt-out in local preview

    def test_no_oat_gray_hover_fill_on_nav(self) -> None:
        self.assertIn('menu a[role="button"]:hover', self.html)
        self.assertIn("border-color:var(--accent); color:var(--accent); background:transparent;", self.html)


if __name__ == "__main__":
    unittest.main()
