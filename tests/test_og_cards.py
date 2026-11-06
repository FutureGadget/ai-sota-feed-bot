from __future__ import annotations

import io
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pipeline import og_cards
from pipeline import render_static_pages as render

ROOT = Path(__file__).resolve().parents[1]


def _hex(rgb: tuple[int, int, int]) -> str:
    return "#%02x%02x%02x" % rgb


@unittest.skipUnless(og_cards.HAVE_PIL, "Pillow not installed")
class OgCardTest(unittest.TestCase):
    def test_vendored_fonts_are_present(self) -> None:
        self.assertTrue(og_cards.fonts_available())
        self.assertTrue((og_cards.FONT_DIR / "OFL.txt").exists())

    def test_palette_matches_the_site_light_theme(self) -> None:
        css = (ROOT / "web" / "site-chrome.css").read_text(encoding="utf-8")
        light = css.split('html[data-theme="dark"]', 1)[0]
        self.assertIn(f"--bg: {_hex(og_cards.PAPER)};", light)
        self.assertIn(f"--fg: {_hex(og_cards.INK)};", light)
        self.assertIn(f"--accent: {_hex(og_cards.RED)};", light)

    def test_card_is_a_stable_paper_png(self) -> None:
        from PIL import Image

        kwargs = dict(
            kicker="The finishable daily brief",
            title="What happened in AI — Oct 9, 2026",
            stats="32 articles · 4 categories",
            dateline="Friday, Oct 9, 2026",
            dek="GitHub migrated 800,000+ lines of Copilot runtime to Rust.",
        )
        first = og_cards._render_card(**kwargs)
        # Byte-stable output is what keeps hourly runs from re-committing cards.
        self.assertEqual(first, og_cards._render_card(**kwargs))
        img = Image.open(io.BytesIO(first))
        self.assertEqual(img.size, (1200, 630))
        self.assertEqual(img.convert("RGB").getpixel((4, 4)), og_cards.PAPER)

    def test_long_title_and_summary_stay_above_the_footer(self) -> None:
        from PIL import Image

        png = og_cards._render_card(
            kicker="AI storyline · what happened next",
            title=" ".join(["Moonshot breaks out of its security test sandbox"] * 3),
            stats="12 items · 7 sources · 9 days",
            dek=" ".join(["A postmortem describes the escape."] * 6),
        )
        img = Image.open(io.BytesIO(png)).convert("RGB")
        footer_y = og_cards.H - 110
        # The band just above the footer rule stays blank paper.
        band = {img.getpixel((x, y)) for x in range(80, 1120, 7) for y in range(footer_y - 14, footer_y - 2)}
        self.assertEqual(band, {og_cards.PAPER})

    def test_ensure_keeps_committed_cards_without_fonts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            committed = out / "daily-2026-10-09.png"
            committed.write_bytes(b"committed")
            with mock.patch.object(og_cards, "OG_DIR", out), mock.patch.object(
                og_cards, "DISPLAY_FONT", out / "missing.ttf"
            ):
                rel = og_cards.ensure("daily", "2026-10-09", kicker="k", title="t", stats="s")
                missing = og_cards.ensure("daily", "2026-10-10", kicker="k", title="t", stats="s")
            self.assertEqual(rel, "/og/daily-2026-10-09.png")
            self.assertEqual(committed.read_bytes(), b"committed")
            self.assertEqual(missing, "")


class OgCopyTest(unittest.TestCase):
    def test_dek_is_the_first_highlight(self) -> None:
        recap = {"highlights": ["", "  First real   bullet. ", "Second"]}
        self.assertEqual(render.og_dek(recap), "First real bullet.")
        self.assertEqual(render.og_dek({}), "")

    def test_week_dateline(self) -> None:
        self.assertEqual(render.og_week_dateline("2026-W41", "2026-10-03", "2026-10-09"), "Oct 3 – 9, 2026")
        self.assertEqual(render.og_week_dateline("2026-W40", "2026-09-28", "2026-10-04"), "Sep 28 – Oct 4, 2026")
        self.assertEqual(render.og_week_dateline("2026-W53", "2026-12-28", "2027-01-03"), "Dec 28, 2026 – Jan 3, 2027")
        self.assertEqual(render.og_week_dateline("2026-W41", "", ""), "2026-W41")

    def test_storyline_dateline(self) -> None:
        self.assertEqual(render.og_storyline_dateline({"last_updated": "2026-10-08T10:03:48Z"}), "Updated Oct 8, 2026")
        self.assertEqual(render.og_storyline_dateline({}), "")

    def test_default_card_copy_matches_the_feed_masthead(self) -> None:
        script = (ROOT / "scripts" / "make_og_assets.py").read_text(encoding="utf-8")
        html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        title = re.search(r'TITLE = "([^"]+)"', script).group(1)
        self.assertIn(f'<h2 class="feed-title">{title}</h2>', html)
        self.assertIn("Scan what changed, save what matters", script)
        self.assertNotIn("10-minute", script)


if __name__ == "__main__":
    unittest.main()
