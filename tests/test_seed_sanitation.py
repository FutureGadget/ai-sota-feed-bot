"""Content sanitation and windowing for the crawler-visible feed seed.

The seed is what crawlers, unfurlers, and no-JS readers see at `/`, and its
helpers silently *delete* reader-visible text, so the thresholds are pinned
here rather than left to manual spot checks.
"""

from __future__ import annotations

import json
import unittest
from datetime import date
from pathlib import Path

from pipeline import render_static_pages as render


ROOT = Path(__file__).resolve().parents[1]
SAMPLES = json.loads(
    (ROOT / "tests" / "fixtures" / "keyword_spam_samples.json").read_text(encoding="utf-8")
)
RANKED_BECAUSE_SAMPLES = json.loads(
    (ROOT / "tests" / "fixtures" / "ranked_because_samples.json").read_text(encoding="utf-8")
)


class KeywordListHeuristicTest(unittest.TestCase):
    def test_tag_spam_is_detected(self) -> None:
        for sample in SAMPLES["spam"]:
            with self.subTest(sample=sample[:60]):
                self.assertTrue(render._looks_like_keyword_list(sample))

    def test_editorial_prose_is_kept(self) -> None:
        for sample in SAMPLES["prose"]:
            with self.subTest(sample=sample[:60]):
                self.assertFalse(render._looks_like_keyword_list(sample))

    def test_segment_count_floor(self) -> None:
        # Five short tag-like segments stay below the floor on purpose: real
        # summaries routinely list three or four things.
        self.assertFalse(render._looks_like_keyword_list("agents, evals, memory, tools, cost"))
        self.assertTrue(render._looks_like_keyword_list("agents, evals, memory, tools, cost, rag"))

    def test_trailing_ellipsis_does_not_defeat_detection(self) -> None:
        # Clipped summaries arrive with an ellipsis; it must not count as
        # sentence punctuation or inflate the average segment length.
        self.assertTrue(
            render._looks_like_keyword_list("agents, evals, memory, tools, cost, rag…")
        )
        self.assertTrue(
            render._looks_like_keyword_list("agents, evals, memory, tools, cost, rag...")
        )


class StripHtmlTagsTest(unittest.TestCase):
    def test_markup_is_collapsed_to_text(self) -> None:
        self.assertEqual(
            render._strip_html_tags("<p>Hello   <b>there</b></p>"), "Hello there"
        )


class EchoesTitleTest(unittest.TestCase):
    def test_bare_version_bump_is_an_echo(self) -> None:
        self.assertTrue(
            render._echoes_title("codex 0.150.0-alpha.7", "Release 0.150.0-alpha.7")
        )

    def test_informative_release_note_is_kept(self) -> None:
        self.assertFalse(
            render._echoes_title(
                "codex 0.150.0-alpha.7",
                "Release 0.150.0-alpha.7 fixes sandbox escaping on macOS",
            )
        )

    def test_empty_after_version_strip_is_an_echo(self) -> None:
        self.assertTrue(render._echoes_title("codex 0.150.0-alpha.7", "v0.150.0"))

    def test_punctuation_and_casing_cannot_hide_the_echo(self) -> None:
        self.assertTrue(render._echoes_title("codex 0.150.0-alpha.7", "Codex 0.150.0-alpha.7!"))


class GenericReleaseNotesTest(unittest.TestCase):
    def test_generic_prefixes_match(self) -> None:
        for sample in (
            "Bug fixes",
            "Reliability improvements and perf work",
            "Maintenance release",
            "minor fixes",
            "No release notes",
        ):
            with self.subTest(sample=sample):
                self.assertTrue(render._GENERIC_RELEASE_NOTES_RE.search(sample))

    def test_specific_notes_do_not_match(self) -> None:
        self.assertIsNone(
            render._GENERIC_RELEASE_NOTES_RE.search("Fixed a sandbox escape on macOS")
        )


class TrimTitleSuffixTest(unittest.TestCase):
    def test_source_slug_suffix_is_dropped(self) -> None:
        self.assertEqual(
            render._trim_title_suffix(
                "Anthropic ships a new agent SDK - infoq", "infoq", "https://www.infoq.com/a"
            ),
            "Anthropic ships a new agent SDK",
        )

    def test_multiword_display_name_suffix_is_dropped(self) -> None:
        # The JS side reaches this through sourceDisplayName(); here the
        # underscore-to-space form of the slug plus case-insensitive matching
        # has to cover it, or seed titles keep a suffix the feed strips.
        self.assertEqual(
            render._trim_title_suffix(
                "Stop Making TUIs - Simon Willison",
                "simon_willison",
                "https://simonwillison.net/x",
            ),
            "Stop Making TUIs",
        )

    def test_host_suffix_is_dropped(self) -> None:
        self.assertEqual(
            render._trim_title_suffix(
                "Anthropic ships a new agent SDK - infoq.com",
                "some_slug",
                "https://www.infoq.com/a",
            ),
            "Anthropic ships a new agent SDK",
        )

    def test_unrelated_suffix_is_kept(self) -> None:
        title = "Claude Code - a terminal agent"
        self.assertEqual(
            render._trim_title_suffix(title, "infoq", "https://www.infoq.com/a"), title
        )

    def test_short_remainder_reverts(self) -> None:
        # Trimming must never leave a stub that reads worse than the original.
        title = "Agents - infoq"
        self.assertEqual(
            render._trim_title_suffix(title, "infoq", "https://www.infoq.com/a"), title
        )


class RankedBecauseTest(unittest.TestCase):
    def test_matches_shared_fixture(self) -> None:
        # Same fixture tests/test_ranked_because.mjs pins the JS twin against;
        # a failure here means the seed and the live feed would disagree.
        for sample in RANKED_BECAUSE_SAMPLES:
            with self.subTest(item=sample["item"]):
                self.assertEqual(
                    render._ranked_because(sample["item"]), sample["expected"]
                )

    def test_non_dict_item_is_empty(self) -> None:
        self.assertEqual(render._ranked_because(None), "")
        self.assertEqual(render._ranked_because("nope"), "")


class SeedHeadingTest(unittest.TestCase):
    def test_single_day(self) -> None:
        self.assertEqual(
            render._seed_heading([date(2026, 8, 22)]), "Top signals · Aug 22, 2026"
        )

    def test_same_month_span(self) -> None:
        self.assertEqual(
            render._seed_heading([date(2026, 8, 20), date(2026, 8, 22)]),
            "Top signals · Aug 20–22, 2026",
        )

    def test_cross_month_span(self) -> None:
        self.assertEqual(
            render._seed_heading([date(2026, 7, 30), date(2026, 8, 2)]),
            "Top signals · Jul 30 – Aug 2, 2026",
        )

    def test_cross_year_span_keeps_both_years(self) -> None:
        self.assertEqual(
            render._seed_heading([date(2026, 12, 30), date(2027, 1, 2)]),
            "Top signals · Dec 30, 2026 – Jan 2, 2027",
        )

    def test_undated_seed(self) -> None:
        self.assertEqual(render._seed_heading([]), "Top signals")


class SeedWindowTest(unittest.TestCase):
    @staticmethod
    def _entries(*days: int | None) -> list[tuple[date | None, dict]]:
        return [
            (date(2026, 8, d) if d is not None else None, {"n": i})
            for i, d in enumerate(days)
        ]

    def test_newest_day_wins_when_it_fills_the_seed(self) -> None:
        entries = self._entries(22, 22, 22, 22, 22, 22, 21, 20)
        chosen = render.select_seed_window(entries)
        self.assertEqual({d for d, _ in chosen}, {date(2026, 8, 22)})

    def test_window_widens_one_day_at_a_time_until_it_fills(self) -> None:
        # Aug 22 alone has 3 cards (under the floor), Aug 21+22 has 6, so the
        # window stops there instead of swallowing Aug 20 as well.
        entries = self._entries(22, 22, 22, 21, 21, 21, 20)
        chosen = render.select_seed_window(entries)
        self.assertEqual(len(chosen), 6)
        self.assertEqual({d for d, _ in chosen}, {date(2026, 8, 22), date(2026, 8, 21)})

    def test_ranked_order_is_preserved(self) -> None:
        entries = self._entries(22, 21, 22, 21, 22, 21, 22)
        chosen = render.select_seed_window(entries)
        self.assertEqual([it["n"] for _, it in chosen], sorted(it["n"] for _, it in chosen))

    def test_max_items_cap(self) -> None:
        entries = self._entries(*([22] * 30))
        self.assertEqual(len(render.select_seed_window(entries)), render.FEED_SEED_MAX_ITEMS)

    def test_undated_entries_fall_back_to_plain_ranking(self) -> None:
        entries = self._entries(None, None, None)
        self.assertEqual(len(render.select_seed_window(entries)), 3)


if __name__ == "__main__":
    unittest.main()
