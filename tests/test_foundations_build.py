from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pipeline import build_foundations


PAGE = """\
---
slug: prompt-reliability
title: "What makes a prompt reliable?"
question: "What makes a prompt reliable?"
summary: "Reliable prompts reduce ambiguity and make failures measurable."
status: active
cluster: prompting
updated: 2026-06-25
audience: "strong-software-engineer"
math_depth: intuition
related_topics: [agent-evaluation]
related_playbook_cards: []
related_storylines: [agentic-memory]
evidence:
  - id: brown-2020-language-models
    kind: theory-paper
    title: "Language Models are Few-Shot Learners"
    url: "https://arxiv.org/abs/2005.14165"
    added: 2026-06-25
    note: "Few-shot prompting works through text examples, not gradient updates."
  - id: evals-field-report
    kind: production-field-report
    title: "Lessons from Building Evals"
    url: "https://example.com/evals"
    sid: "00678eb9b30563c3"
    added: 2026-07-10
    note: "A team found prompt changes regressed silently until they added evals."
  - id: story-00678eb9b30563c3
    kind: story
    sid: "00678eb9b30563c3"
    added: 2026-06-25
---

## Builder consequence
Reliable prompts are interfaces, not prose.

## Short answer
Good prompts reduce entropy in the next-token distribution.

## Mechanism
Instructions, examples, and schemas condition the continuation.

## Math intuition
Think of the prompt as moving probability mass toward acceptable outputs.

## How to apply
Write prompts as contracts with inputs, outputs, and tests.

## Failure modes
Long context can bury the decisive instruction.
"""


class FoundationsBuildTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.concepts = root / "data" / "foundations" / "concepts"
        self.concepts.mkdir(parents=True)
        self.write(PAGE)
        stories = root / "data" / "stories" / "index.json"
        stories.parent.mkdir(parents=True)
        stories.write_text(
            json.dumps({"00678eb9b30563c3": {"title": "Lessons from Building Evals"}}),
            encoding="utf-8",
        )
        storylines = root / "data" / "storylines" / "index.json"
        storylines.parent.mkdir(parents=True)
        storylines.write_text(
            json.dumps({"storylines": [{"slug": "agentic-memory", "label": "Agentic memory"}]}),
            encoding="utf-8",
        )
        wiki = root / "data" / "wiki" / "index.json"
        wiki.parent.mkdir(parents=True)
        wiki.write_text(
            json.dumps({"nodes": {"agent-evaluation": {"title": "Measuring whether an agent worked"}}}),
            encoding="utf-8",
        )
        self.stories = stories
        self.patches = [
            patch.object(build_foundations, "FOUNDATIONS_DIR", root / "data" / "foundations"),
            patch.object(build_foundations, "STORIES_INDEX", stories),
            patch.object(build_foundations, "STORYLINES_INDEX", storylines),
            patch.object(build_foundations, "WIKI_INDEX", wiki),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self) -> None:
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def write(self, text: str, slug: str = "prompt-reliability") -> None:
        (self.concepts / f"{slug}.md").write_text(text, encoding="utf-8")

    def errors(self) -> str:
        _, errors = build_foundations.compile_foundations()
        return "\n".join(msg for _, msg in errors)

    def test_builds_index_with_tiered_evidence_and_related_topics(self) -> None:
        concept = build_foundations.build_index()["concepts"]["prompt-reliability"]
        self.assertEqual(concept["cluster"], "prompting")
        self.assertEqual(concept["math_depth"], "intuition")
        self.assertIn("Builder consequence", [s["heading"] for s in concept["sections"]])
        self.assertEqual(concept["related_topics"][0]["slug"], "agent-evaluation")
        self.assertEqual(concept["related_storylines"][0]["slug"], "agentic-memory")

    def test_evidence_is_newest_first_with_dates_and_feed_sids(self) -> None:
        concept = build_foundations.build_index()["concepts"]["prompt-reliability"]
        ids = [ev["id"] for ev in concept["evidence"]]
        # Newest first; same-day entries keep the page's own order.
        self.assertEqual(ids, ["evals-field-report", "brown-2020-language-models", "story-00678eb9b30563c3"])
        report = concept["evidence"][0]
        self.assertEqual(report["added"], "2026-07-10")
        self.assertEqual(report["sid"], "00678eb9b30563c3")
        self.assertEqual(report["title"], "Lessons from Building Evals")  # external title kept
        self.assertEqual(concept["evidence"][1]["tier"], "theory/paper-backed")
        self.assertEqual(concept["evidence"][2]["title"], "Lessons from Building Evals")  # story resolves
        self.assertEqual(concept["latest_evidence_added"], "2026-07-10")
        self.assertEqual(concept["updated"], "2026-07-10")

    def test_recent_evidence_skips_story_entries(self) -> None:
        recent = build_foundations.build_index()["recent_evidence"]
        self.assertEqual([r["id"] for r in recent], ["evals-field-report", "brown-2020-language-models"])
        self.assertEqual(recent[0]["concept"], "prompt-reliability")

    def test_rejects_unresolved_story_evidence(self) -> None:
        self.stories.write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(build_foundations.FoundationsError, "story sid"):
            build_foundations.build_index()

    def test_rejects_evidence_section_and_overlong_sections(self) -> None:
        self.write(PAGE.replace(
            "## How to apply",
            "## Evidence\nThe study shows things.\n\n## How to apply",
        ).replace("Instructions, examples, and schemas condition the continuation.", "word " * 351))
        errors = self.errors()
        self.assertIn("section '## Evidence' is not allowed (study details go in evidence notes)", errors)
        self.assertIn("'## Mechanism' is 351 words (max 350)", errors)

    def test_evidence_rules(self) -> None:
        self.write(PAGE.replace("    added: 2026-07-10\n", "").replace(
            "Few-shot prompting works through text examples, not gradient updates.", "word " * 81
        ))
        errors = self.errors()
        self.assertIn("evidence evals-field-report: `added:` must be YYYY-MM-DD", errors)
        self.assertIn("evidence brown-2020-language-models: note is 81 words (max 80)", errors)

    def test_external_evidence_needs_a_note(self) -> None:
        self.write(PAGE.replace(
            '    note: "A team found prompt changes regressed silently until they added evals."\n', ""
        ))
        self.assertIn("evidence evals-field-report: needs a note", self.errors())

    def test_evidence_count_is_capped(self) -> None:
        extra = "".join(
            f'  - id: paper-{i}\n    kind: theory-paper\n    title: "Paper {i}"\n'
            f'    url: "https://example.com/{i}"\n    added: 2026-06-25\n    note: "Shows {i}."\n'
            for i in range(10)
        )
        self.write(PAGE.replace("---\n\n## Builder consequence", extra + "---\n\n## Builder consequence"))
        self.assertIn("13 evidence entries (max 12)", self.errors())

    def test_all_errors_reported_and_scoped_by_slug(self) -> None:
        self.write(PAGE.replace("cluster: prompting", "cluster: nope"), slug="prompt-reliability")
        other = PAGE.replace("slug: prompt-reliability", "slug: other-concept").replace(
            "    added: 2026-07-10\n", ""
        )
        self.write(other, slug="other-concept")
        _, errors = build_foundations.compile_foundations()
        slugs = {slug for slug, _ in errors}
        self.assertEqual(slugs, {"prompt-reliability", "other-concept"})


class MarkdownTest(unittest.TestCase):
    def test_numbered_and_bulleted_lists(self) -> None:
        html = build_foundations.md_to_html(
            "Intro line.\n1. **One.** first\n   wrapped\n2. Two\n- bullet"
        )
        self.assertEqual(
            html,
            "<p>Intro line.</p>\n<ol><li><strong>One.</strong> first wrapped</li><li>Two</li></ol>\n"
            "<ul><li>bullet</li></ul>",
        )


if __name__ == "__main__":
    unittest.main()
