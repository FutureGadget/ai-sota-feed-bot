"""Deck candidate loader (pool + backfill) and selection metrics."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))

import deck_candidates as dc  # noqa: E402
import deck_metrics as dm  # noqa: E402
import judged_pool  # noqa: E402

DAY = date(2026, 10, 27)


def _write(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


class CandidateLoaderTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        self.processed, self.raw, self.pool = root / "processed", root / "raw", root / "pool"
        # Edition run on the day: one news item that made the feed.
        _write(self.processed / "runs_index.json", [{"run_at": "2026-10-27T10:00:00+00:00", "path": "2026/10/r1.json"}])
        _write(
            self.processed / "runs" / "2026" / "10" / "r1.json",
            {"items": [{"url": "https://a.com/x/", "title": "Edition item", "source": "hn", "source_role": "community", "type": "news", "slot": "community_signal", "published": "2026-10-27T08:00:00+00:00"}]},
        )
        # Judgments: the edition item, a keep that never made an edition, a
        # drop, a release, and a keep published outside the window.
        entries = {
            "1": {"url": "https://a.com/x", "judge_score": 0.8, "judge_verdict": "keep", "judge_category": "agent_engineering", "source": "hn", "source_role": "community"},
            "2": {"url": "https://b.com/y", "judge_score": 0.7, "judge_verdict": "keep", "judge_category": "inference_serving", "source": "blog", "source_role": "practitioner", "title": "Missed keep"},
            "3": {"url": "https://c.com/z", "judge_score": 0.05, "judge_verdict": "drop", "judge_category": "business_policy", "source": "news", "source_role": "search"},
            "4": {"url": "https://d.com/r", "judge_score": 0.02, "judge_verdict": "drop", "judge_category": "release_note", "source": "vllm_releases", "source_role": "release"},
            "5": {"url": "https://e.com/old", "judge_score": 0.9, "judge_verdict": "keep", "source": "blog", "source_role": "practitioner"},
        }
        _write(self.processed / "judgments.json", {"entries": entries})
        _write(
            self.raw / "2026-10-27" / "items.json",
            [
                {"url": "https://b.com/y", "title": "Missed keep", "source": "blog", "published": "Tue, 27 Oct 2026 09:00:00 GMT", "summary": "body"},
                {"url": "https://c.com/z", "title": "Funding round", "source": "news", "published": "2026-10-27T01:00:00Z"},
                {"url": "https://d.com/r", "title": "vLLM v0.12.0", "source": "vllm_releases", "published": "2026-10-27T02:00:00Z"},
            ],
        )
        _write(self.raw / "2026-10-25" / "items.json", [{"url": "https://e.com/old", "title": "Old", "source": "blog", "published": "2026-10-25T02:00:00Z"}])

    def tearDown(self):
        self._tmp.cleanup()

    def load(self, **kwargs):
        return dc.load_candidates(DAY, DAY, processed_dir=self.processed, raw_dir=self.raw, pool_dir=self.pool, **kwargs)

    def test_backfill_recovers_keeps_outside_the_edition_and_applies_filters(self):
        candidates, diag = self.load()
        by_key = {c["key"]: c for c in candidates}
        self.assertEqual(set(by_key), {"https://a.com/x", "https://b.com/y", "https://d.com/r"})
        self.assertEqual(by_key["https://a.com/x"]["edition_runs"], 1)
        self.assertEqual(by_key["https://b.com/y"]["edition_runs"], 0)
        self.assertEqual(by_key["https://b.com/y"]["summary"], "body")
        self.assertEqual(diag["rejects"]["judge_drop"], 1)  # the funding drop; the release is exempt
        self.assertEqual(diag["rejects"]["published_window"], 1)

    def test_type_and_prior_recap_filters(self):
        candidates, diag = self.load(types={"news"}, exclude_urls={"https://a.com/x/"})
        self.assertEqual([c["key"] for c in candidates], ["https://b.com/y"])
        self.assertEqual(diag["rejects"]["prior_recap"], 1)
        self.assertGreaterEqual(diag["rejects"]["type"], 1)

    def test_pool_rows_override_backfill_and_add_unjudged_items(self):
        judged_pool.record_run(
            [
                {"url": "https://b.com/y", "title": "Missed keep", "source": "blog", "type": "news", "published": "2026-10-27T09:00:00Z", "judge_score": 0.75, "judge_verdict": "keep"},
                {"url": "https://f.com/u", "title": "Unjudged scoop", "source": "search_x", "type": "news", "published": "2026-10-27T11:00:00Z", "judge_verdict": "unjudged", "judge_error": "insufficient_evidence"},
            ],
            [],
            run_at="2026-10-27T12:00:00+00:00",
            pool_dir=self.pool,
        )
        candidates, diag = self.load(types={"news"})
        by_key = {c["key"]: c for c in candidates}
        self.assertEqual(by_key["https://b.com/y"]["judge_score"], 0.75)
        self.assertTrue(by_key["https://b.com/y"]["from_pool"])
        self.assertIn("https://f.com/u", by_key)
        self.assertEqual(diag["from_pool"], 2)


class MetricsTest(unittest.TestCase):
    def test_must_cover_recall(self):
        self.assertEqual(dm.must_cover_recall(["a", "b", "c"], {"a", "d"}), 0.5)
        self.assertEqual(dm.must_cover_recall(["b", "a"], {"a"}, k=1), 0.0)
        self.assertIsNone(dm.must_cover_recall(["a"], set()))

    def test_alpha_ndcg_rewards_order_and_penalizes_duplicates(self):
        grades = {"a": 2, "b": 1, "c": 1, "d": 0}
        self.assertEqual(dm.alpha_ndcg(["a", "b", "c"], grades), 1.0)
        self.assertLess(dm.alpha_ndcg(["c", "b", "a"], grades), 1.0)
        # b and c are the same event; e is a different useful story.
        grades = {"a": 2, "b": 1, "c": 1, "e": 1, "d": 0}
        groups = {"b": "g", "c": "g"}
        self.assertEqual(dm.alpha_ndcg(["a", "b", "e"], grades, groups), 1.0)
        redundant = dm.alpha_ndcg(["a", "b", "c"], grades, groups)
        self.assertLess(redundant, 1.0)
        # Without the redundancy discount the two lists tie.
        self.assertEqual(dm.alpha_ndcg(["a", "b", "c"], grades, groups, alpha=0.0), 1.0)
        # A duplicate still beats a drop.
        self.assertGreater(redundant, dm.alpha_ndcg(["a", "b", "d"], grades, groups))
        self.assertIsNone(dm.alpha_ndcg(["d"], {"d": 0}))

    def test_duplicate_groups_resolve_chains(self):
        groups = dm.duplicate_groups({"a": None, "b": "a", "c": "b", "d": None})
        self.assertEqual(groups["c"], groups["a"])
        self.assertNotEqual(groups["d"], groups["a"])

    def test_graded_sum(self):
        self.assertEqual(dm.graded_sum(["a", "x"], {"a": 2}), 2.0)


if __name__ == "__main__":
    unittest.main()
