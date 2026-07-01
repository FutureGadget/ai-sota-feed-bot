from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PlaybookSurfaceTest(unittest.TestCase):
    """Structural guards for the redesigned /playbook surface.

    The Playbook's reader job is "what should I change in my agent?", so each
    entry is a change record with a SIGNAL -> APPLY -> EXPECTED spine where the
    APPLY block is the single dominant element. These assertions pin the visual
    contract so a future edit can't silently revert it to generic equal-weight
    cards or pill badges.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.html = (ROOT / "web" / "playbook.html").read_text(encoding="utf-8")

    def test_uses_shared_instrument_token_system(self) -> None:
        # Same cool instrument-paper palette / blue accent as the recap surfaces.
        self.assertIn("--bg:#f5f7fa;", self.html)
        self.assertIn("--accent:#2457d6;", self.html)
        self.assertIn("--bg:#11151c;", self.html)  # dark theme
        self.assertIn('"Avenir Next Condensed"', self.html)  # condensed display
        self.assertIn("ui-monospace", self.html)  # monospace utility labels

    def test_change_record_signature(self) -> None:
        # Records, not boxed cards; SIGNAL -> APPLY -> EXPECTED spine.
        self.assertIn('class="pb-record"', self.html)
        self.assertIn('class="pb-apply"', self.html)
        self.assertIn(">Signal</span>", self.html)
        self.assertIn(">Apply</span>", self.html)
        self.assertIn(">→ Expected</span>", self.html)

    def test_apply_is_the_dominant_block(self) -> None:
        # The Apply block carries the accent rule + wash + the largest body type.
        self.assertIn("border-left:3px solid var(--apply-edge)", self.html)
        self.assertIn("background:var(--apply-wash)", self.html)
        self.assertIn(".pb-apply p { margin:0; font-size:1.06rem;", self.html)
        # Apply text (1.06rem) is larger than the signal/expected text (.88/.9rem).
        self.assertIn(".pb-signal p { margin:0; font-size:.88rem;", self.html)

    def test_effort_is_a_meter_not_a_colored_pill(self) -> None:
        self.assertIn("pb-eff-seg", self.html)
        # The old generic card/pill treatment must be gone.
        self.assertNotIn(".pcard", self.html)
        self.assertNotIn("effort-low", self.html)
        self.assertNotIn('class="badge area"', self.html)

    def test_finishable_framing(self) -> None:
        self.assertIn("worth making", self.html)
        self.assertIn("That's the edition", self.html)

    def test_preserves_api_archive_and_source_behavior(self) -> None:
        self.assertIn("/api/playbook", self.html)
        self.assertIn('id="archive"', self.html)
        self.assertIn('id="jsonLink"', self.html)
        self.assertIn('data-track="playbook-link"', self.html)
        # Source links open the primary article in a new, no-referrer tab.
        self.assertIn('target="_blank" rel="noopener"', self.html)

    def test_localhost_data_fallbacks_for_visual_qa(self) -> None:
        self.assertIn("'/data/playbook/latest.json'", self.html)
        self.assertIn("'/data/playbook/index.json'", self.html)
        self.assertIn("/data/playbook/${encodeURIComponent(date)}.json", self.html)

    def test_preserves_nav_update_indicator(self) -> None:
        # Freshness/read-tracking logic is the shared script, not an inline fork.
        self.assertIn('src="/nav-updates.js', self.html)

    def test_quality_floor(self) -> None:
        # Visible keyboard focus, reduced motion, theme toggle, mascot opt-out.
        self.assertIn("outline:3px solid color-mix(in srgb,var(--accent) 50%,transparent)", self.html)
        self.assertIn("@media (prefers-reduced-motion:reduce)", self.html)
        self.assertIn('id="themeToggle"', self.html)
        self.assertIn("isLocalPreview", self.html)

    def test_no_oat_gray_hover_fill_on_nav(self) -> None:
        # Nav buttons keep a transparent fill on hover (no Oat default gray box).
        self.assertIn(
            'menu a[role="button"]:hover, #themeToggle:hover, .archive select:hover',
            self.html,
        )
        self.assertIn("border-color:var(--accent); color:var(--accent); background:transparent;", self.html)


if __name__ == "__main__":
    unittest.main()
