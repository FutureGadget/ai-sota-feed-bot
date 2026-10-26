from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import yaml

from pipeline import deck_quality as dq
from pipeline import story_store

ROOT = Path(__file__).resolve().parents[1]
RUN_AT = "2026-10-23T12:00:00+00:00"
PUB = "2026-10-23T10:00:00Z"
START = datetime(2026, 10, 23, tzinfo=timezone.utc)
END = datetime(2026, 10, 23, 23, 59, 59, tzinfo=timezone.utc)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _classified_row(item_id: str, url: str, title: str, score: float, verdict: str, category: str, role: str) -> dict:
    return {
        "id": item_id,
        "story_key": f"story|{item_id}",
        "title": title,
        "url": url,
        "source": "vllm_blog",
        "source_role": role,
        "published": PUB,
        "judge_score": score,
        "judge_verdict": verdict,
        "judge_category": category,
        "judge_category_confidence": 0.9,
    }


def _store_entry(url: str, title: str, score: float, category: str, role: str) -> dict:
    return {
        "identity": url,
        "story_key": f"story|{title}",
        "url": url,
        "title": title,
        "source": "vllm_blog",
        "source_role": role,
        "judge_score": score,
        "judge_signals": {"keep": score},
        "judge_category": category,
        "judge_category_confidence": 0.8,
        "judge_model": "jev-1.14",
        "judge_rubric_version": "feed-quality-v1",
        "judge_judged_at": "2026-10-23T11:00:00+00:00",
    }


def _run_item(item_id: str, url: str, title: str, *, item_type: str = "news", role: str = "practitioner", excerpt: str = "") -> dict:
    item = {
        "id": item_id,
        "url": url,
        "title": title,
        "source": "vllm_blog",
        "type": item_type,
        "source_role": role,
        "published": PUB,
        "summary_1line": f"{title} teaser",
    }
    if excerpt:
        item["content_excerpt"] = excerpt
    return item


class QualityIndexTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: shutil.rmtree(self.tmp, ignore_errors=True))
        self.processed = self.tmp / "processed"
        self.processed.mkdir()

        classified = {
            "generated_at": RUN_AT,
            "items": [
                _classified_row("a", "https://example.com/drop", "Drop", 0.02, "drop", "agent_engineering", "practitioner"),
                _classified_row("b", "https://example.com/release", "Release", 0.01, "drop", "release_note", "release"),
            ],
        }
        (self.processed / "classified.json").write_text(json.dumps(classified), encoding="utf-8")

        judgments = {
            "version": 1,
            "entries": {
                "c": _store_entry("https://example.com/off-topic", "Off topic", 0.05, "off_topic", "community"),
                "e": _store_entry("https://example.com/excerpt", "Excerpt", 0.9, "inference_serving", "practitioner"),
                "f": _store_entry("https://example.com/release-note", "Release note", 0.2, "release_note", "release"),
            },
        }
        (self.processed / "judgments.json").write_text(json.dumps(judgments), encoding="utf-8")
        self.index = dq.load_quality_index(self.processed)

    def test_thresholds_match_the_judge_config(self) -> None:
        cfg = yaml.safe_load((ROOT / "config" / "judge.yaml").read_text(encoding="utf-8"))
        ranking = cfg.get("ranking") or {}
        self.assertEqual(dq.DROP_BELOW, float(ranking.get("drop_below")))
        self.assertEqual(dq.KEEP_AT, float(ranking.get("keep_at")))

    def test_evidence_floor_is_configured(self) -> None:
        cfg = yaml.safe_load((ROOT / "config" / "judge.yaml").read_text(encoding="utf-8"))
        content = cfg.get("content_fetch") or {}
        self.assertGreater(int(content.get("min_evidence_chars") or 0), 0)
        self.assertIn("release", content.get("min_evidence_exempt_roles") or [])

    def test_annotates_from_classified_and_derives_missing_verdicts(self) -> None:
        article = self.index.annotate({"id": "a", "url": "https://example.com/drop", "title": "Drop"})
        self.assertEqual(article["judge_verdict"], "drop")
        self.assertEqual(article["judge_category"], "agent_engineering")
        self.assertEqual(article["deck_category"], "Agent engineering")

        stored = self.index.annotate({"url": "https://example.com/off-topic", "title": "Off topic"})
        self.assertEqual(stored["judge_verdict"], "drop")
        self.assertEqual(stored["judge_category"], "off_topic")

        review = self.index.annotate({"url": "https://example.com/release-note", "title": "Release note"})
        self.assertEqual(review["judge_verdict"], "review")

    def test_article_fields_win_over_the_join(self) -> None:
        article = {"url": "https://example.com/drop", "judge_verdict": "keep", "judge_category": "frontier_product"}
        self.index.annotate(article)
        self.assertEqual(article["judge_verdict"], "keep")
        self.assertEqual(article["judge_category"], "frontier_product")

    def test_drop_rules_and_release_exemptions(self) -> None:
        drop = self.index.annotate({"url": "https://example.com/drop"})
        release = self.index.annotate({"url": "https://example.com/release"})
        off_topic = self.index.annotate({"url": "https://example.com/off-topic"})
        release_note = self.index.annotate({"url": "https://example.com/release-note"})
        unjudged = self.index.annotate({"url": "https://example.com/unjudged"})

        self.assertTrue(self.index.is_dropped(drop))
        self.assertFalse(self.index.is_dropped(release))
        self.assertTrue(self.index.is_dropped(off_topic))
        self.assertFalse(self.index.is_dropped(unjudged))
        self.assertFalse(self.index.is_dropped(release_note))

        # Decks without a release lane drop routine release notes, including
        # review-band ones, but never a keep.
        self.assertTrue(self.index.is_dropped(release, exempt_releases=False))
        self.assertTrue(self.index.is_dropped(release_note, exempt_releases=False))
        keep_note = self.index.annotate(
            {"url": "https://example.com/release-note", "judge_verdict": "keep", "judge_category": "release_note"}
        )
        self.assertFalse(self.index.is_dropped(keep_note, exempt_releases=False))

    def test_summary_prefers_fetched_excerpt(self) -> None:
        summary, source = dq.deck_summary(
            {"content_excerpt": "Fetched page text", "summary_1line": "Scraped teaser", "summary": "Raw"}
        )
        self.assertEqual((summary, source), ("Fetched page text", "content_excerpt"))
        summary, source = dq.deck_summary({"summary_1line": "Scraped teaser", "summary": "Raw"})
        self.assertEqual((summary, source), ("Scraped teaser", "summary_1line"))
        summary, source = dq.deck_summary({"summary": "Raw"})
        self.assertEqual((summary, source), ("Raw", "summary"))

    def test_category_hint_and_quality_summary(self) -> None:
        articles = [
            self.index.annotate({"url": "https://example.com/release"}),
            self.index.annotate({"url": "https://example.com/excerpt"}),
            self.index.annotate({"url": "https://example.com/unjudged", "category": "Industry News"}),
        ]
        self.assertEqual(
            dq.category_hint(articles),
            [
                {"name": "Inference & serving", "count": 1},
                {"name": "Releases", "count": 1},
                {"name": "Industry News", "count": 1},
            ],
        )
        self.assertEqual(
            dq.quality_summary(articles),
            {
                "judged": 2,
                "unjudged": 1,
                "verdicts": {"drop": 1, "keep": 1, "unjudged": 1},
                "categories": {"inference_serving": 1, "release_note": 1},
            },
        )


class CollectorIntegrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: shutil.rmtree(self.tmp, ignore_errors=True))
        self.processed = self.tmp / "processed"
        self.runs = self.processed / "runs" / "2026" / "10"
        self.runs.mkdir(parents=True)

        classified = {
            "generated_at": RUN_AT,
            "items": [
                _classified_row("a", "https://example.com/drop", "Drop", 0.02, "drop", "agent_engineering", "practitioner"),
                _classified_row("b", "https://example.com/release", "Release", 0.01, "drop", "release_note", "release"),
            ],
        }
        (self.processed / "classified.json").write_text(json.dumps(classified), encoding="utf-8")
        judgments = {
            "version": 1,
            "entries": {
                "c": _store_entry("https://example.com/off-topic", "Off topic", 0.05, "off_topic", "community"),
                "e": _store_entry("https://example.com/excerpt", "Excerpt", 0.9, "inference_serving", "practitioner"),
                "f": _store_entry("https://example.com/release-note", "Release note", 0.2, "release_note", "release"),
            },
        }
        (self.processed / "judgments.json").write_text(json.dumps(judgments), encoding="utf-8")

        self.items = [
            _run_item("a", "https://example.com/drop", "Drop"),
            _run_item("b", "https://example.com/release", "Release", item_type="release", role="release"),
            _run_item("c", "https://example.com/off-topic", "Off topic", role="community"),
            _run_item("d", "https://example.com/unjudged", "Unjudged"),
            _run_item(
                "e",
                "https://example.com/excerpt",
                "Excerpt",
                excerpt="Fetched article text with the actual mechanism.",
            ),
            _run_item("f", "https://example.com/release-note", "Release note", item_type="release", role="release"),
        ]
        run_path = self.runs / "20261023-120000.json"
        run_path.write_text(json.dumps({"run_at": RUN_AT, "item_count": len(self.items), "items": self.items}), encoding="utf-8")
        (self.processed / "runs_index.json").write_text(
            json.dumps([{"run_at": RUN_AT, "path": "2026/10/20261023-120000.json"}]), encoding="utf-8"
        )

    def _load(self, name: str, relative: str):
        module = load_module(ROOT / relative, f"{name}_deck_test")
        module.PROCESSED_DIR = self.processed
        module.PROCESSED_RUNS_DIR = self.processed / "runs"
        module.PROCESSED_RUNS_INDEX = self.processed / "runs_index.json"
        return module

    def test_daily_collector_joins_and_filters(self) -> None:
        daily = self._load("daily_common", ".agents/skills/daily-summary/scripts/daily_common.py")
        articles = daily.collect_day_articles(START, END)
        self.assertEqual({a["id"] for a in articles}, {"b", "d", "e", "f"})

        by_id = {a["id"]: a for a in articles}
        self.assertEqual(by_id["e"]["summary"], "Fetched article text with the actual mechanism.")
        self.assertEqual(by_id["e"]["summary_source"], "content_excerpt")
        self.assertEqual(by_id["e"]["judge_verdict"], "keep")
        self.assertEqual(by_id["e"]["deck_category"], "Inference & serving")
        self.assertEqual(by_id["d"]["summary_source"], "summary_1line")
        self.assertNotIn("judge_verdict", by_id["d"])

        everything = daily.collect_day_articles(START, END, include_dropped=True)
        self.assertEqual({a["id"] for a in everything}, {"a", "b", "c", "d", "e", "f"})

    def test_weekly_and_playbook_collectors_use_the_same_rules(self) -> None:
        weekly = self._load("weekly_common", ".agents/skills/weekly-summary/scripts/weekly_common.py")
        playbook = self._load("playbook_common", ".agents/skills/playbook/scripts/playbook_common.py")
        for collector in (weekly.collect_week_articles, playbook.collect_articles):
            self.assertEqual({a["id"] for a in collector(START, END)}, {"b", "d", "e", "f"})
            self.assertEqual(
                {a["id"] for a in collector(START, END, include_dropped=True)},
                {"a", "b", "c", "d", "e", "f"},
            )

    def test_wiki_and_foundations_helpers_drop_routine_release_notes(self) -> None:
        wiki = load_module(
            ROOT / ".agents/skills/wiki-curator/scripts/build_wiki_input.py",
            "build_wiki_input_deck_test",
        )
        foundations = load_module(
            ROOT / ".agents/skills/foundations-curator/scripts/build_foundations_input.py",
            "build_foundations_input_deck_test",
        )
        index = dq.load_quality_index(self.processed)

        wiki_row = wiki.story_row("b", {"url": "https://example.com/release", "title": "Release"}, index)
        self.assertTrue(index.is_dropped(wiki_row, exempt_releases=False))
        self.assertEqual(wiki_row["judge_category"], "release_note")

        store = {
            "release-note": {
                "url": "https://example.com/release",
                "title": "Release",
                "type": "release",
                "published": PUB,
            },
            "kept": {
                "url": "https://example.com/excerpt",
                "title": "Agent memory evaluation",
                "summary": "A memory benchmark for agent reliability",
                "type": "news",
                "published": PUB,
            },
        }
        with patch.object(foundations, "load_store", return_value=store):
            stories = foundations.recent_stories(3650, index)
        self.assertEqual([s["sid"] for s in stories], ["kept"])
        self.assertEqual(stories[0]["judge_category"], "inference_serving")


class StoryStoreExcerptTest(unittest.TestCase):
    def test_story_record_carries_the_fetched_excerpt(self) -> None:
        rec = story_store.story_record(
            "sid",
            {
                "url": "https://example.com/story",
                "title": "A story",
                "published": PUB,
                "content_excerpt": "<p>Hello <b>world</b></p>",
            },
            RUN_AT,
        )
        self.assertEqual(rec["content_excerpt"], "Hello world")


if __name__ == "__main__":
    unittest.main()
