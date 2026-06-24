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
    note: "Few-shot prompting works through text examples, not gradient updates."
  - id: story-00678eb9b30563c3
    kind: story
    sid: "00678eb9b30563c3"
covers_evidence:
  - brown-2020-language-models
  - story-00678eb9b30563c3
---

## Builder consequence
Reliable prompts are interfaces, not prose.

## Short answer
Good prompts reduce entropy in the next-token distribution.

## Mechanism
Instructions, examples, and schemas condition the continuation.

## Math intuition
Think of the prompt as moving probability mass toward acceptable outputs.

## Evidence
- Few-shot demonstrations can specify new tasks in context.

## How to apply
Write prompts as contracts with inputs, outputs, and tests.

## Failure modes
Long context can bury the decisive instruction.
"""


class FoundationsBuildTest(unittest.TestCase):
    def test_builds_index_with_tiered_evidence_and_related_topics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            concepts = root / "data" / "foundations" / "concepts"
            concepts.mkdir(parents=True)
            (concepts / "prompt-reliability.md").write_text(PAGE, encoding="utf-8")

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

            with (
                patch.object(build_foundations, "FOUNDATIONS_DIR", root / "data" / "foundations"),
                patch.object(build_foundations, "STORIES_INDEX", stories),
                patch.object(build_foundations, "STORYLINES_INDEX", storylines),
                patch.object(build_foundations, "WIKI_INDEX", wiki),
            ):
                index = build_foundations.build_index()

        concept = index["concepts"]["prompt-reliability"]
        self.assertEqual(concept["cluster"], "prompting")
        self.assertEqual(concept["math_depth"], "intuition")
        self.assertIn("Builder consequence", [s["heading"] for s in concept["sections"]])
        self.assertEqual(concept["evidence"][0]["tier"], "theory/paper-backed")
        self.assertEqual(concept["evidence"][1]["title"], "Lessons from Building Evals")
        self.assertEqual(concept["related_topics"][0]["slug"], "agent-evaluation")
        self.assertEqual(concept["related_storylines"][0]["slug"], "agentic-memory")

    def test_rejects_unresolved_story_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            concepts = root / "data" / "foundations" / "concepts"
            concepts.mkdir(parents=True)
            (concepts / "prompt-reliability.md").write_text(PAGE, encoding="utf-8")
            stories = root / "data" / "stories" / "index.json"
            stories.parent.mkdir(parents=True)
            stories.write_text("{}", encoding="utf-8")

            with (
                patch.object(build_foundations, "FOUNDATIONS_DIR", root / "data" / "foundations"),
                patch.object(build_foundations, "STORIES_INDEX", stories),
                patch.object(build_foundations, "STORYLINES_INDEX", root / "missing-storylines.json"),
                patch.object(build_foundations, "WIKI_INDEX", root / "missing-wiki.json"),
            ):
                with self.assertRaisesRegex(build_foundations.FoundationsError, "story sid"):
                    build_foundations.build_index()


if __name__ == "__main__":
    unittest.main()
