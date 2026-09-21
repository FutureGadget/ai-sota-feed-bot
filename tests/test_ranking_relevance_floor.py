from __future__ import annotations

import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from pipeline.ranking import (
    build_relevance_floor,
    passes_relevance_floor,
    stage_a_prefilter,
)

NOW = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)
PUBLISHED = "2026-09-20T10:00:00+00:00"

CFG = {
    "candidate_pool_cap": 100,
    "slots": {
        "practitioner_analysis": {
            "sources": ["simon_willison"],
            "freshness_hours": 72,
            "max_per_source": 4,
        },
        "agent_tooling_releases": {
            "sources": ["openai_codex_releases"],
            "freshness_hours": 72,
            "max_per_source": 4,
        },
    },
}


def _profile(**overrides):
    profile = {
        "selection": {"exclude_title_regex": []},
        "off_topic": {"enabled": False},
        "relevance_floor": {
            "enabled": True,
            "sources": ["simon_willison"],
            "keywords": ["ai", "llm", "agent", "model", "token", "prompt", "claude", "pelican"],
        },
    }
    profile.update(overrides)
    return profile


def _item(source: str, title: str, summary: str = "") -> dict:
    return {
        "source": source,
        "title": title,
        "summary": summary,
        "url": f"https://example.com/{abs(hash((source, title)))}",
        "published": PUBLISHED,
    }


def _run(items, profile):
    health = {it["source"]: 1.0 for it in items}
    with patch("pipeline.ranking._now_utc", return_value=NOW):
        return stage_a_prefilter(items, CFG, profile, health)


class RelevanceFloorTest(unittest.TestCase):
    def test_drops_off_topic_item_from_mixed_source(self) -> None:
        """A wildlife post on simonwillison.net reached feed rank #5 on 2026-09-20."""
        items = [
            _item(
                "simon_willison",
                "California Sea Lion, Brandt's Cormorant",
                "<p>California Sea Lion, Brandt&#x27;s Cormorant, in Pillar Point Harbor,"
                ' CA, US</p><p>Tags: <a href="/tags/wildlife">wildlife</a></p>',
            )
        ]
        candidates, diag = _run(items, _profile())

        self.assertEqual(candidates, [])
        self.assertEqual(diag["prefilter_reasons"].get("no_topic_signal"), 1)

    def test_keeps_on_topic_item_from_mixed_source(self) -> None:
        items = [
            _item(
                "simon_willison",
                "Self-generated prompt injections in compaction summaries",
                "<p>A coding agent summarising its own context window.</p>",
            )
        ]
        candidates, diag = _run(items, _profile())

        self.assertEqual(len(candidates), 1)
        self.assertNotIn("no_topic_signal", diag["prefilter_reasons"])

    def test_signal_only_in_summary_is_enough(self) -> None:
        """Simon's "Quoting X" posts carry the topic in the body, never the title."""
        items = [
            _item(
                "simon_willison",
                "Quoting Thariq Shihipar",
                "<p>Being a computer scientist who refuses to find anything about LLMs"
                " interesting right now...</p>",
            )
        ]
        candidates, _diag = _run(items, _profile())

        self.assertEqual(len(candidates), 1)

    def test_markup_is_not_a_topic_signal(self) -> None:
        """"details" contains "ai"; an href or attribute must not rescue an item."""
        items = [
            _item(
                "simon_willison",
                "The Creative Spirit of Who Framed Roger Rabbit",
                '<p>Cypress Frankenfeld <a href="https://example.com/x">gathered more'
                " details</a> on the scene.</p>",
            )
        ]
        candidates, diag = _run(items, _profile())

        self.assertEqual(candidates, [])
        self.assertEqual(diag["prefilter_reasons"].get("no_topic_signal"), 1)

    def test_floor_does_not_apply_to_unlisted_sources(self) -> None:
        """Terse release notes carry no keyword; dedicated sources must be exempt."""
        items = [_item("openai_codex_releases", "codex 0.156.0-alpha.9")]
        candidates, diag = _run(items, _profile())

        self.assertEqual(len(candidates), 1)
        self.assertNotIn("no_topic_signal", diag["prefilter_reasons"])

    def test_disabled_floor_is_a_no_op(self) -> None:
        items = [_item("simon_willison", "California Sea Lion, Brandt's Cormorant")]
        candidates, _diag = _run(
            items,
            _profile(relevance_floor={"enabled": False, "sources": ["simon_willison"]}),
        )

        self.assertEqual(len(candidates), 1)

    def test_missing_floor_config_is_a_no_op(self) -> None:
        items = [_item("simon_willison", "California Sea Lion, Brandt's Cormorant")]
        profile = {"selection": {"exclude_title_regex": []}, "off_topic": {"enabled": False}}
        candidates, _diag = _run(items, profile)

        self.assertEqual(len(candidates), 1)


class RelevanceFloorUrlTest(unittest.TestCase):
    """A URL or bare hostname is a name, not prose, and must not rescue an item."""

    def setUp(self) -> None:
        self.floor_sources, self.floor_re = build_relevance_floor(_profile())

    def _passes(self, title: str, summary: str) -> bool:
        item = _item("simon_willison", title, summary)
        return passes_relevance_floor(item, self.floor_sources, self.floor_re)

    def test_hostname_does_not_rescue(self) -> None:
        """"agent.datasette.io" in a Datasette release body matched \\bagent\\b."""
        self.assertFalse(
            self._passes(
                "datasette-auth-github 1.0",
                "<p>I run this GitHub login plugin on the agent.datasette.io demo site"
                " and my sessions were not lasting very long.</p>",
            )
        )

    def test_url_in_href_does_not_rescue(self) -> None:
        self.assertFalse(
            self._passes(
                "Kākāpō parrots",
                '<p>Photos from the trip.</p><p>Tags: <a href="https://x.com/tags/llm">'
                "wildlife</a></p>",
            )
        )

    def test_prose_still_rescues_alongside_a_url(self) -> None:
        """Stripping URLs must not cost an item whose prose carries the signal."""
        self.assertTrue(
            self._passes(
                "So you want to use OpenRouter?",
                "<p>Notes on calling a model through the proxy, see https://example.com/x</p>",
            )
        )


class BuildTier1FloorTest(unittest.TestCase):
    """Tier-1 feeds the served feed directly, so it must gate too."""

    def test_build_tier1_shares_the_ranking_floor(self) -> None:
        from pipeline import build_tier1

        floor_sources, floor_re = build_relevance_floor(build_tier1.load_profile())
        sea_lion = _item(
            "simon_willison",
            "California Sea Lion, Brandt's Cormorant",
            '<p>In Pillar Point Harbor.</p><p>Tags: <a href="/tags/wildlife">wildlife</a></p>',
        )
        on_topic = _item(
            "simon_willison",
            "Self-generated prompt injections in compaction summaries",
            "<p>A coding agent summarising its own context window.</p>",
        )
        release_note = _item("openai_codex_releases", "codex 0.156.0-alpha.9")

        self.assertFalse(passes_relevance_floor(sea_lion, floor_sources, floor_re))
        self.assertTrue(passes_relevance_floor(on_topic, floor_sources, floor_re))
        self.assertTrue(passes_relevance_floor(release_note, floor_sources, floor_re))


if __name__ == "__main__":
    unittest.main()
