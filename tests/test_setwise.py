from __future__ import annotations

import importlib.util
import unittest
from collections import Counter
from pathlib import Path

from pipeline import setwise

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("setwise_eval", ROOT / "scripts" / "setwise_eval.py")
setwise_eval = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(setwise_eval)


class SetwiseTest(unittest.TestCase):
    def test_groups_cover_every_item_once_per_round(self) -> None:
        ids = list(range(26))
        groups = setwise.make_groups(ids, size=8, rounds=4, seed=1)
        self.assertTrue(all(2 <= len(g) <= 8 for g in groups))
        self.assertEqual(Counter(i for g in groups for i in g), Counter({i: 4 for i in ids}))
        self.assertEqual(groups, setwise.make_groups(ids, size=8, rounds=4, seed=1))

    def test_small_day_is_one_group(self) -> None:
        self.assertEqual(setwise.make_groups(["a", "b", "c"], size=8), [["a", "b", "c"]])
        self.assertEqual(setwise.make_groups(["a"], size=8), [])

    def test_bradley_terry_orders_by_wins_and_stays_finite(self) -> None:
        pairs = setwise.pairs_from_ranking(["a", "b", "c"]) * 3
        scores = setwise.bradley_terry(["a", "b", "c", "d"], pairs)
        self.assertGreater(scores["a"], scores["b"])
        self.assertGreater(scores["b"], scores["c"])
        self.assertAlmostEqual(sum(scores.values()), 0.0, places=6)
        self.assertTrue(all(abs(v) < 10 for v in scores.values()))

    def test_auc(self) -> None:
        self.assertEqual(setwise.auc({"a": 2, "b": 1, "c": 0}, {"a", "b"}, {"c"}), 1.0)
        self.assertEqual(setwise.auc({"a": 0, "b": 1}, {"a"}, {"b"}), 0.0)
        self.assertIsNone(setwise.auc({"a": 1}, {"a"}, set()))

    def test_parse_ranking_needs_every_letter_once(self) -> None:
        letters = {"A": "x", "B": "y", "C": "z"}
        self.assertEqual(setwise_eval.parse_ranking("C, A,B", letters), ["z", "x", "y"])
        self.assertIsNone(setwise_eval.parse_ranking("C,A", letters))
        self.assertIsNone(setwise_eval.parse_ranking("C,A,A", letters))

    def test_evaluate_scores_an_oracle_at_one_and_a_contrarian_at_zero(self) -> None:
        stories = [{"id": f"s{i}", "title": f"t{i}", "grade": 1 if i % 3 else 0, "judge_score": 0.5} for i in range(20)]
        days = [("2026-10-24", stories)]

        def oracle(group, _key):
            return [s["id"] for s in sorted(group, key=lambda s: -s["grade"])]

        def contrarian(group, _key):
            return [s["id"] for s in sorted(group, key=lambda s: s["grade"])]

        good = setwise_eval.evaluate(days, oracle, size=8, rounds=4)
        bad = setwise_eval.evaluate(days, contrarian, size=8, rounds=4)
        self.assertEqual(good["days"][0]["auc_setwise"], 1.0)
        self.assertEqual(bad["days"][0]["auc_setwise"], 0.0)
        self.assertEqual(good["days"][0]["auc_jev"], 0.5)

    def test_owner_grades_load(self) -> None:
        days = setwise_eval.load_days("daily")
        if not days:
            self.skipTest("no committed owner grades")
        self.assertTrue(all(s["grade"] in (0, 1, 2) for _, stories in days for s in stories))


if __name__ == "__main__":
    unittest.main()
