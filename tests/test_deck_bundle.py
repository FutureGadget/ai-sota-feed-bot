"""Recall additions and event groups for the recap bundles."""
from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))

import deck_bundle  # noqa: E402

DAY = date(2026, 10, 27)
CFG = {"decks": {"daily": {"bundle": {"pool_additions": True, "verdicts": ["keep"], "max_additions": 2}}}}


def row(key, verdict="keep", published="2026-10-27T10:00:00Z", **extra):
    return {"key": key, "url": key, "title": key, "source": "hn", "type": "news", "published": published, "judge_verdict": verdict, "judge_score": 0.8, "excerpt": "body", **extra}


class PoolAdditionsTest(unittest.TestCase):
    def run_with(self, candidates, **kwargs):
        with patch.object(deck_bundle.deck_candidates, "load_candidates", return_value=(candidates, {"candidates": len(candidates), "from_pool": 0})):
            return deck_bundle.pool_additions("daily", DAY, DAY, types={"news"}, exclude_urls=set(), cfg=CFG, **kwargs)

    def test_adds_only_missing_keeps_newest_first_under_cap(self):
        candidates = [
            row("https://a/1"),
            row("https://a/2", published="2026-10-27T12:00:00Z"),
            row("https://a/3", published="2026-10-27T11:00:00Z"),
            row("https://a/4", verdict="review"),
            row("https://a/5", verdict="unjudged"),
            row("https://a/6", published="2026-10-27T01:00:00Z"),
        ]
        items, diag = self.run_with(candidates, existing_urls={"https://a/1/"})
        self.assertEqual([i["url"] for i in items], ["https://a/2", "https://a/3"])
        self.assertEqual(diag["added"], 2)
        self.assertEqual(diag["capped"], 1)
        self.assertEqual(items[0]["content_excerpt"], "body")
        self.assertEqual(items[0]["judge_verdict"], "keep")

    def test_disabled_and_failure_add_nothing(self):
        items, diag = self.run_with([row("https://a/1")], existing_urls=set(), enabled=False)
        self.assertEqual((items, diag["enabled"]), ([], False))
        with patch.object(deck_bundle.deck_candidates, "load_candidates", side_effect=RuntimeError("boom")):
            items, diag = deck_bundle.pool_additions("daily", DAY, DAY, types=None, exclude_urls=set(), existing_urls=set(), cfg=CFG)
        self.assertEqual(items, [])
        self.assertIn("boom", diag["error"])

    def test_shipped_config_enables_daily_and_weekly(self):
        for deck in ("daily", "weekly"):
            self.assertTrue(deck_bundle.bundle_config(deck)["pool_additions"])


class EventGroupTest(unittest.TestCase):
    def test_groups_same_model_version_and_labels_by_shared_anchor(self):
        articles = [
            {"title": "Kimi K3.1 Pro: 1M context, open weights"},
            {"title": "Moonshot apologises after botched Kimi K3.1 Pro launch"},
            {"title": "Kimi K3.1 Pro vs. Claude Opus 5.5"},
            {"title": "Claude Code adds hooks"},
            {"title": "Kimi K3 on AMD MI355X"},
        ]
        self.assertEqual(deck_bundle.annotate_event_groups(articles), 1)
        self.assertEqual([a.get("event_group") for a in articles[:3]], ["kimi|3.1"] * 3)
        self.assertNotIn("event_group", articles[3])
        self.assertNotIn("event_group", articles[4])


if __name__ == "__main__":
    unittest.main()
