from __future__ import annotations

import unittest

from pipeline import render_static_pages as render


CONCEPT = {
    "slug": "prompt-reliability",
    "title": "What makes a prompt reliable?",
    "question": "What makes a prompt reliable?",
    "summary": "Reliable prompts reduce ambiguity and make failures measurable.",
    "status": "active",
    "cluster": "prompting",
    "cluster_label": "Prompting and instruction following",
    "updated": "2026-06-25",
    "audience": "strong-software-engineer",
    "math_depth": "intuition",
    "sections": [
        {"heading": "Builder consequence", "html": "<p>Reliable prompts are interfaces.</p>"},
        {"heading": "Short answer", "html": "<p>Constrain the continuation.</p>"},
        {"heading": "Math intuition", "html": "<p>Move probability mass.</p>"},
        {"heading": "How to apply", "html": "<p>Write contracts and eval them.</p>"},
    ],
    "evidence": [
        {
            "id": "brown-2020-language-models",
            "kind": "theory-paper",
            "tier": "theory/paper-backed",
            "title": "Language Models are Few-Shot Learners",
            "url": "https://arxiv.org/abs/2005.14165",
            "sid": "00678eb9b30563c3",
            "added": "2026-07-10",
            "note": "Few-shot demonstrations specify tasks in context.",
        },
        {
            "id": "internal-inference",
            "kind": "editorial-inference",
            "tier": "editorial inference",
            "title": "LLM Digest synthesis",
            "added": "2026-06-25",
        },
    ],
    "related_topics": [{"slug": "agent-evaluation", "title": "Measuring whether an agent worked"}],
    "related_storylines": [],
}

FOUNDATIONS = {
    "clusters": [{"slug": "prompting", "label": "Prompting and instruction following", "concepts": ["prompt-reliability"]}],
    "recent_evidence": [
        {"concept": "prompt-reliability", "concept_title": "What makes a prompt reliable?",
         "id": "brown-2020-language-models", "title": "Language Models are Few-Shot Learners",
         "tier": "theory/paper-backed", "kind": "theory-paper", "added": "2026-07-10"},
        {"concept": "gone", "concept_title": "Gone", "id": "x", "title": "Ghost evidence",
         "tier": "", "kind": "theory-paper", "added": "2026-07-01"},
    ],
    "concepts": {"prompt-reliability": CONCEPT},
}


class FoundationsSurfaceTest(unittest.TestCase):
    def test_foundations_index_is_clustered_and_not_a_landing_page(self) -> None:
        body = render.foundations_index_body(FOUNDATIONS)
        self.assertIn("Agent Builder Foundations", body)
        self.assertIn("Prompting and instruction following", body)
        self.assertIn('href="/foundations/prompt-reliability"', body)
        self.assertIn("1 concept", body)
        self.assertIn("2 sources<br>updated Jun 25, 2026", body)

    def test_foundations_index_lists_recent_evidence(self) -> None:
        body = render.foundations_index_body(FOUNDATIONS)
        self.assertIn("Recently added evidence", body)
        self.assertIn('href="/foundations/prompt-reliability#ev-brown-2020-language-models"', body)
        self.assertIn("Jul 10, 2026", body)
        self.assertNotIn("Ghost evidence", body)
        self.assertLess(body.index("recent-evidence"), body.index("foundation-cluster"))

    def test_foundation_concept_page_renders_mechanism_and_evidence(self) -> None:
        hero = render.foundation_concept_hero(CONCEPT)
        self.assertIn("Agent foundations", hero)
        self.assertIn("What makes a prompt reliable?", hero)
        self.assertIn("math intuition", hero)

        body = render.render_foundation_body(CONCEPT)
        self.assertLess(body.index("Reliable prompts are interfaces"), body.index("Math intuition"))
        self.assertIn("Evidence · 2 sources", body)
        self.assertIn("theory/paper-backed", body)
        self.assertIn("editorial inference", body)
        self.assertIn('href="/topic/agent-evaluation"', body)
        self.assertIn("2 sources", hero)
        self.assertNotIn("evidence tier", hero)

    def test_foundation_evidence_is_dated_and_linkable(self) -> None:
        body = render.render_foundation_body(CONCEPT)
        self.assertIn("What's new in the evidence", body)
        self.assertIn('href="#ev-brown-2020-language-models"', body)
        self.assertIn('<li id="ev-brown-2020-language-models">', body)
        self.assertIn("added Jul 10, 2026", body)
        self.assertIn('<a href="/story/00678eb9b30563c3">in the feed</a>', body)
        self.assertIn("Few-shot demonstrations specify tasks in context.", body)
        self.assertIn("newest first", body)
        self.assertLess(body.index("foundation-new"), body.index("Math intuition"))


if __name__ == "__main__":
    unittest.main()
