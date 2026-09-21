"""Page-body enrichment for sources whose feed carries only a teaser.

`collectors/collect.py` fetches the article body for sources configured with
`fetch_content: true` and stores it as `content_excerpt`. The keyword gates
downstream then score the real content instead of a one-line teaser.

The invariant these tests exist to protect: an item with no `content_excerpt`
must score exactly as it did before the feature existed, so enabling it for one
source cannot move any other source's ranking.
"""

from __future__ import annotations

import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from collectors.collect import attach_content_excerpts
from pipeline.llm_label import _token_present, heuristic_label
from pipeline.ranking import stage_a_prefilter

NOW = datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc)
PUBLISHED = "2026-09-21T10:00:00+00:00"

# The real teaser from the archerhume RSS feed. It names no AI vocabulary at
# all, despite the article being entirely about serving architecture.
TEASER = (
    "I probed Jev with 10,000 API calls to work out roughly how it's built, "
    "and why most of the grifter takes on X are completely wrong."
)
BODY = (
    "An ordinary LLM generates 90% confident as text. The evidence points "
    "toward a causal transformer repurposed for decisions, with shared-state "
    "encoding and direct probability readouts. End inference with a readout. "
    "Signatures in latency scaling under different context lengths."
)


class TokenPresenceTest(unittest.TestCase):
    def test_teaser_keeps_substring_match(self) -> None:
        """Historical behaviour: title+summary matched as substrings."""
        self.assertTrue(_token_present("eval", "the evaluation harness", ""))

    def test_excerpt_is_matched_whole_word(self) -> None:
        """1200+ chars of prose turn a substring match into a false positive."""
        self.assertFalse(_token_present("code", "", "the decoder stage"))
        self.assertFalse(_token_present("agent", "", "change management process"))
        self.assertTrue(_token_present("code", "", "the code sample"))
        self.assertTrue(_token_present("inference", "", "end inference with a readout"))

    def test_caller_strips_markup_before_matching(self) -> None:
        """_token_present matches text; heuristic_label owns the strip (see below)."""
        self.assertTrue(_token_present("agent", "", "an agent loop"))


class HeuristicLabelTest(unittest.TestCase):
    def test_teaser_alone_floors_the_label(self) -> None:
        label = heuristic_label({"title": "Jev's Architecture Unmasked", "summary": TEASER})
        self.assertEqual(label["fit_agentic_platform"], 2)

    def test_excerpt_raises_fit(self) -> None:
        label = heuristic_label(
            {
                "title": "Jev's Architecture Unmasked",
                "summary": TEASER,
                "content_excerpt": BODY,
            }
        )
        self.assertEqual(label["fit_agentic_platform"], 3)

    def test_excerpt_cannot_raise_hype_risk(self) -> None:
        """A penalty sourced from a passing mention in the body is a false positive."""
        base = {"title": "A Post", "summary": "about things"}
        hypey = dict(base, content_excerpt="revolutionary breakthrough unprecedented")
        self.assertEqual(heuristic_label(hypey)["hype_risk"], heuristic_label(base)["hype_risk"])

    def test_excerpt_cannot_raise_novelty(self) -> None:
        """"new" appears in almost any 1200-char body; novelty stays a headline signal."""
        base = {"title": "A Post", "summary": "about things"}
        with_body = dict(base, content_excerpt="we introduced a new approach here")
        self.assertEqual(heuristic_label(with_body)["novelty"], heuristic_label(base)["novelty"])

    def test_markup_in_excerpt_is_not_a_topic_signal(self) -> None:
        """An href is not something the reader reads (same rule as relevance_floor)."""
        base = {"title": "A Post", "summary": "about things"}
        markup = dict(base, content_excerpt='<a href="/tags/agent">x</a> <img alt="eval">')
        self.assertEqual(
            heuristic_label(markup)["fit_agentic_platform"],
            heuristic_label(base)["fit_agentic_platform"],
        )

    def test_item_without_excerpt_is_unchanged(self) -> None:
        """The invariant: no excerpt, no behaviour change, for every other source."""
        item = {"title": "vLLM serving benchmark", "summary": "inference latency on code"}
        self.assertEqual(heuristic_label(item), heuristic_label(dict(item, content_excerpt="")))


class RelevanceFloorWithExcerptTest(unittest.TestCase):
    """The floor is an allowlist, so body text can only rescue, never drop."""

    CFG = {
        "candidate_pool_cap": 100,
        "slots": {
            "practitioner_analysis": {
                "sources": ["archer_hume"],
                "freshness_hours": 72,
                "max_per_source": 4,
            }
        },
    }
    PROFILE = {
        "selection": {"exclude_title_regex": []},
        "off_topic": {"enabled": False},
        "relevance_floor": {
            "enabled": True,
            "sources": ["archer_hume"],
            "keywords": ["ai", "llm", "agent", "token", "inference"],
        },
    }

    def _run(self, item):
        with patch("pipeline.ranking._now_utc", return_value=NOW):
            return stage_a_prefilter([item], self.CFG, self.PROFILE, {"archer_hume": 1.0})

    def _item(self, **extra):
        return {
            "source": "archer_hume",
            "title": "Jev's Architecture Unmasked",
            "summary": TEASER,
            "url": "https://archerhume.com/posts/jevs-architecture-unmasked/",
            "published": PUBLISHED,
            **extra,
        }

    def test_teaser_alone_fails_the_floor(self) -> None:
        candidates, diag = self._run(self._item())
        self.assertEqual(candidates, [])
        self.assertEqual(diag["prefilter_reasons"].get("no_topic_signal"), 1)

    def test_excerpt_rescues_the_on_topic_item(self) -> None:
        candidates, diag = self._run(self._item(content_excerpt=BODY))
        self.assertEqual(len(candidates), 1)
        self.assertNotIn("no_topic_signal", diag["prefilter_reasons"])


class AttachContentExcerptsTest(unittest.TestCase):
    SOURCES = [
        {"name": "archer_hume", "fetch_content": True},
        {"name": "simon_willison"},
    ]

    def test_noop_without_any_opted_in_source(self) -> None:
        items = [{"source": "simon_willison", "url": "https://example.com/a"}]
        with patch("collectors.collect.build_content_map") as fetch:
            self.assertEqual(attach_content_excerpts(items, [{"name": "simon_willison"}]), 0)
        fetch.assert_not_called()
        self.assertNotIn("content_excerpt", items[0])

    def test_fetches_only_opted_in_sources(self) -> None:
        items = [
            {"source": "archer_hume", "url": "https://archerhume.com/posts/a/"},
            {"source": "simon_willison", "url": "https://simonwillison.net/b/"},
        ]
        with patch(
            "collectors.collect.build_content_map",
            return_value={"https://archerhume.com/posts/a/": BODY},
        ) as fetch:
            attached = attach_content_excerpts(items, self.SOURCES)

        self.assertEqual(attached, 1)
        self.assertEqual(items[0]["content_excerpt"], BODY)
        self.assertNotIn("content_excerpt", items[1])
        # Only the opted-in item is ever handed to the fetcher.
        self.assertEqual([i["source"] for i in fetch.call_args.args[0]], ["archer_hume"])

    def test_fetch_failure_is_not_fatal(self) -> None:
        """A slow or unreachable page costs the excerpt and nothing else."""
        items = [{"source": "archer_hume", "url": "https://archerhume.com/posts/a/"}]
        with patch("collectors.collect.build_content_map", side_effect=OSError("timeout")):
            self.assertEqual(attach_content_excerpts(items, self.SOURCES), 0)
        self.assertNotIn("content_excerpt", items[0])

    def test_url_fragment_is_stripped_when_matching(self) -> None:
        """build_content_map keys on the canonical url; the item may carry a #anchor."""
        items = [{"source": "archer_hume", "url": "https://archerhume.com/posts/a/#intro"}]
        with patch(
            "collectors.collect.build_content_map",
            return_value={"https://archerhume.com/posts/a/": BODY},
        ):
            self.assertEqual(attach_content_excerpts(items, self.SOURCES), 1)
        self.assertEqual(items[0]["content_excerpt"], BODY)


if __name__ == "__main__":
    unittest.main()
