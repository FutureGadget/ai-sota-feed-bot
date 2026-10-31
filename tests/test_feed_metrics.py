"""Served Brief replay metrics: window, top band, coverage, stability."""
from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))

import feed_metrics as fm  # noqa: E402

AT = datetime(2026, 10, 27, 12, 0, tzinfo=timezone.utc)


def item(url: str, *, source="hn", role="community", utility=1.0, admitted_hours_ago=1, **extra):
    return {
        "story_key": f"story:{url}",
        "url": url,
        "title": url,
        "source": source,
        "source_role": role,
        "type": "news",
        "published": (AT - timedelta(hours=admitted_hours_ago + 2)).isoformat(),
        "admitted_at": (AT - timedelta(hours=admitted_hours_ago)).isoformat(),
        "first_seen": (AT - timedelta(hours=admitted_hours_ago)).isoformat(),
        "utility": utility,
        **extra,
    }


class FeedMetricsTest(unittest.TestCase):
    def test_jaccard_and_rank_displacement(self):
        self.assertEqual(fm.jaccard(["a", "b", "c"], ["b", "c", "d"]), 0.5)
        self.assertEqual(fm.jaccard([], []), 1.0)
        self.assertEqual(fm.jaccard(["a"], []), 0.0)
        self.assertEqual(fm.rank_displacement(["a", "b", "c"], ["c", "b", "a"]), 1.33)
        self.assertIsNone(fm.rank_displacement(["a"], ["b"]))

    def test_active_window_keeps_latest_admission_and_expires(self):
        old = item("https://a/old", admitted_hours_ago=30)
        new = item("https://a/old", admitted_hours_ago=2, utility=2)
        other = item("https://a/other", admitted_hours_ago=1)
        window = fm.active_window([old, new, other], AT)
        self.assertEqual([row["utility"] for row in window], [2, 1])
        self.assertEqual(len(window), 2)
        self.assertEqual(window[0]["admitted_at"], new["admitted_at"])

    def test_brief_order_caps_one_source_in_the_top_band(self):
        items = [item(f"https://a/{i}", source="hn", utility=10 - i) for i in range(4)]
        items.append(item("https://a/filler", source="infoq_ai_ml", role="practitioner", utility=2))
        items.append(item("https://a/other", source="simon_willison", role="practitioner", utility=1))
        ordered = fm.brief_order(items)
        self.assertEqual([row["source"] for row in ordered[:5]].count("hn"), 3)
        self.assertIn("simon_willison", [row["source"] for row in ordered[:5]])

    def test_day_summary_counts_keep_coverage(self):
        pool = {
            "https://a/1": {"story_key": "story:https://a/1", "first_seen_run": "2026-10-27T09:00:00+00:00", "judge_verdict": "keep"},
            "https://a/2": {"story_key": "story:https://a/2", "first_seen_run": "2026-10-27T09:00:00+00:00", "judge_verdict": "keep"},
            "https://a/3": {"story_key": "story:https://a/3", "first_seen_run": "2026-10-27T09:00:00+00:00", "judge_verdict": "drop"},
            "https://a/old": {"story_key": "story:https://a/old", "first_seen_run": "2026-10-26T09:00:00+00:00", "judge_verdict": "keep"},
        }
        ledger = {
            "date": "2026-10-27",
            "diagnostics": {
                "rejected_gate": {"off_topic": 1},
                "rejected_quota": {"source_quota": 2},
                "prior_story": 1,
            },
            "items": [
                item("https://a/1", admitted_hours_ago=1),
                item("https://a/release", admitted_hours_ago=2, type="release", judge_verdict="drop"),
            ],
        }
        summary = fm.day_summary("2026-10-27", ledger, pool)
        self.assertEqual(summary["admitted"], 2)
        self.assertEqual(summary["keeps_total"], 2)
        self.assertEqual(summary["keeps_admitted"], 1)
        self.assertEqual(summary["keeps_admission_rate"], 0.5)
        self.assertEqual(summary["rejected_quota"], {"source_quota": 2})
        self.assertEqual(summary["prior_story"], 1)

    def test_stability_reports_no_unexpected_removals(self):
        entries = [
            item("https://a/1", utility=5, admitted_hours_ago=2),
            item("https://a/2", utility=4, admitted_hours_ago=1),
            item("https://a/old", utility=9, admitted_hours_ago=30),
        ]
        times = [AT - timedelta(hours=1), AT]
        block = fm.stability(entries, times)
        self.assertEqual(block["pairs"], 1)
        self.assertEqual(block["unexpected_removals"], 0)
        self.assertEqual(block["expired_total"], 0)
        self.assertEqual(block["rated_pairs"], 0)  # too few visible items to rate


if __name__ == "__main__":
    unittest.main()
