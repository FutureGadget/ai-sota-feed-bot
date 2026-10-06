from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pipeline import build_wiki


OBSTACLE = """\
---
slug: agent-evaluation
kind: obstacle
title: "Measuring whether an agent worked is hard"
area: evaluation
status: active
solutions: [llm-as-judge]
related_storylines: [agent-evals]
evidence: []
updated: 2026-09-01
themes:
  - key: trajectory
    title: Grading the trajectory
    summary: Judge the steps an agent took, not only its final answer.
  - key: benchmarks
    title: Benchmarks under distribution shift
    summary: Static leaderboards overstate how agents do in new environments.
---

## TL;DR
Agents must be graded on what they did, not only what they said.

## State of the art
Evaluation splits into trajectory judging and outcome judging.

## Why it matters for platform engineers
You cannot ship a model upgrade without a regression signal.
"""

SOLUTION = """\
---
slug: llm-as-judge
kind: solution
title: "LLM-as-judge"
status: active
obstacles: []
updated: 2026-08-01
themes:
  - key: cost
    title: Cheaper judges
    summary: Small judges cut cost.
---

## TL;DR
Use a model to grade a model.

## Trade-offs
Judges have biases.
"""


def entry(title: str, date: str, theme: str, evidence: list[str], body: str = "A finding.", also=None) -> str:
    lines = ["---", f'title: "{title}"', f"date: {date}", f"theme: {theme}", f"evidence: [{', '.join(evidence)}]"]
    if also:
        lines.append(f"also: [{', '.join(also)}]")
    return "\n".join(lines + ["---", body, ""])


class WikiBuildTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.wiki = root / "wiki"
        (self.wiki / "obstacles").mkdir(parents=True)
        (self.wiki / "solutions").mkdir(parents=True)
        (self.wiki / "obstacles" / "agent-evaluation.md").write_text(OBSTACLE)
        (self.wiki / "solutions" / "llm-as-judge.md").write_text(SOLUTION)
        stories = root / "stories.json"
        stories.write_text(json.dumps({sid: {"title": f"Story {sid}"} for sid in ("aaaa", "bbbb", "cccc")}))
        storylines = root / "storylines.json"
        storylines.write_text(json.dumps({"storylines": [{"slug": "agent-evals", "label": "Agent evals"}]}))
        self.write_entry("agent-evaluation", "2026-09-20-trajectory-judging", entry(
            "Strands Evals returns causal failure chains", "2026-09-20", "trajectory", ["aaaa"], also=["llm-as-judge"]))
        self.write_entry("agent-evaluation", "2026-09-28-shift", entry(
            "Agents degrade beyond familiar environments", "2026-09-28", "benchmarks", ["bbbb", "aaaa"]))
        self.write_entry("llm-as-judge", "2026-07-01-cheap-judge", entry(
            "A 100x cheaper trace judge", "2026-07-01", "cost", ["cccc"]))
        self.patches = [
            patch.object(build_wiki, "WIKI_DIR", self.wiki),
            patch.object(build_wiki, "ENTRIES_DIR", self.wiki / "entries"),
            patch.object(build_wiki, "STORIES_INDEX", stories),
            patch.object(build_wiki, "STORYLINES_INDEX", storylines),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self) -> None:
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def write_entry(self, topic: str, stem: str, text: str) -> Path:
        d = self.wiki / "entries" / topic
        d.mkdir(parents=True, exist_ok=True)
        path = d / f"{stem}.md"
        path.write_text(text)
        return path

    def compile_ok(self) -> dict:
        index, errors = build_wiki.compile_wiki()
        self.assertEqual(errors.for_slug(None), [])
        return index

    def compile_errors(self) -> list[str]:
        _, errors = build_wiki.compile_wiki()
        return errors.for_slug(None)

    def test_compiles_entries_newest_first_grouped_by_theme(self) -> None:
        node = self.compile_ok()["nodes"]["agent-evaluation"]
        self.assertEqual([e["id"] for e in node["entries"]], ["2026-09-28-shift", "2026-09-20-trajectory-judging"])
        self.assertEqual([(t["key"], t["count"]) for t in node["themes"]], [("trajectory", 1), ("benchmarks", 1)])
        self.assertEqual(node["entries"][0]["evidence"][0], {"sid": "bbbb", "title": "Story bbbb"})
        self.assertIn("<p>A finding.</p>", node["entries"][0]["html"])
        self.assertEqual(node["entry_count"], 2)

    def test_updated_is_newest_of_page_and_entries(self) -> None:
        nodes = self.compile_ok()["nodes"]
        self.assertEqual(nodes["agent-evaluation"]["updated"], "2026-09-28")
        self.assertEqual(nodes["llm-as-judge"]["updated"], "2026-08-01")

    def test_evidence_ledger_is_deduplicated_union(self) -> None:
        node = self.compile_ok()["nodes"]["agent-evaluation"]
        self.assertEqual([e["sid"] for e in node["evidence"]], ["bbbb", "aaaa"])

    def test_also_cross_lists_and_edges_symmetrize(self) -> None:
        nodes = self.compile_ok()["nodes"]
        judge = nodes["llm-as-judge"]
        self.assertEqual([c["id"] for c in judge["cross_entries"]], ["2026-09-20-trajectory-judging"])
        self.assertEqual(judge["cross_entries"][0]["topic"], "agent-evaluation")
        self.assertEqual(judge["obstacles"], [{"slug": "agent-evaluation", "title": "Measuring whether an agent worked is hard"}])

    def test_latest_entries_span_the_wiki(self) -> None:
        latest = self.compile_ok()["latest_entries"]
        self.assertEqual([e["id"] for e in latest][:2], ["2026-09-28-shift", "2026-09-20-trajectory-judging"])
        self.assertEqual(latest[-1]["topic"], "llm-as-judge")

    def test_catalog_is_generated(self) -> None:
        md = build_wiki.render_catalog(self.compile_ok())
        self.assertIn("do not hand-edit", md)
        self.assertIn("theme `trajectory` — Grading the trajectory (1)", md)

    def test_whats_new_section_is_rejected(self) -> None:
        path = self.wiki / "obstacles" / "agent-evaluation.md"
        path.write_text(path.read_text() + "\n## What's new\nSomething.\n")
        self.assertTrue(any("What's new" in e and "entries" in e for e in self.compile_errors()))

    def test_overlong_state_of_the_art_is_rejected(self) -> None:
        path = self.wiki / "obstacles" / "agent-evaluation.md"
        path.write_text(path.read_text().replace(
            "Evaluation splits into trajectory judging and outcome judging.", "word " * 351))
        self.assertTrue(any("'## State of the art' is 351 words (max 350)" in e for e in self.compile_errors()))

    def test_entry_validation(self) -> None:
        self.write_entry("agent-evaluation", "2026-09-29-bad", entry(
            "x" * 111, "2026-09-30", "nope", ["zzzz"], body="word " * 131, also=["agent-evaluation"]))
        errors = "\n".join(self.compile_errors())
        self.assertIn("filename date 2026-09-29 != date 2026-09-30", errors)
        self.assertIn("title is 111 chars", errors)
        self.assertIn("theme 'nope' is not declared", errors)
        self.assertIn("body is 131 words", errors)
        self.assertIn("evidence sid zzzz not in stories index", errors)
        self.assertIn("`also` names unknown or own topic 'agent-evaluation'", errors)

    def test_bad_entry_filename_and_orphan_dir(self) -> None:
        self.write_entry("agent-evaluation", "notes", entry("T", "2026-09-01", "trajectory", ["aaaa"]))
        self.write_entry("ghost-topic", "2026-09-01-x", entry("T", "2026-09-01", "trajectory", ["aaaa"]))
        errors = "\n".join(self.compile_errors())
        self.assertIn("filename must be <YYYY-MM-DD>-<name>.md", errors)
        self.assertIn("entries/ghost-topic/ has no matching topic page", errors)

    def test_unused_theme_is_rejected(self) -> None:
        (self.wiki / "entries" / "agent-evaluation" / "2026-09-28-shift.md").unlink()
        self.assertIn(
            "agent-evaluation: theme 'benchmarks' has no entries; remove it or file one",
            self.compile_errors(),
        )

    def test_page_without_themes_is_rejected(self) -> None:
        path = self.wiki / "solutions" / "llm-as-judge.md"
        text = path.read_text()
        path.write_text(text[: text.index("themes:")] + text[text.index("---\n\n## TL;DR"):])
        self.assertIn(
            "llm-as-judge: front matter needs at least one theme under `themes:`",
            self.compile_errors(),
        )

    def test_slug_filter_scopes_errors(self) -> None:
        self.write_entry("llm-as-judge", "2026-07-02-bad", entry("T", "2026-07-02", "missing", ["cccc"]))
        _, errors = build_wiki.compile_wiki()
        self.assertEqual(errors.for_slug("agent-evaluation"), [])
        self.assertTrue(errors.for_slug("llm-as-judge"))

    def test_md_to_html_joins_wrapped_bullets(self) -> None:
        html = build_wiki.md_to_html("- first line\n  continues here\n- second *point*")
        self.assertEqual(html, "<ul><li>first line continues here</li><li>second <em>point</em></li></ul>")


if __name__ == "__main__":
    unittest.main()
