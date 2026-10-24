from __future__ import annotations

import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from pipeline import quality_benchmark as qb


class FrozenBenchmarkTest(unittest.TestCase):
    def test_benchmark_has_unique_ids_and_both_labels(self) -> None:
        items = qb.load_items(qb.DEFAULT_ITEMS)
        ids = [item["id"] for item in items]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(len(items), 40)
        self.assertTrue(all(item.get("expected") in {"keep", "drop"} for item in items))
        self.assertTrue(all(item.get("expected_label") in {"must_read", "useful", "filler", "junk"} for item in items))
        self.assertGreaterEqual(len({item.get("slice") for item in items}), 6)
        self.assertGreater(sum(1 for item in items if item["expected"] == "keep"), 0)
        self.assertGreater(sum(1 for item in items if item["expected"] == "drop"), 0)

    def test_fixture_scores_cover_every_item(self) -> None:
        items = qb.load_items(qb.DEFAULT_ITEMS)
        fixture_path = qb.DEFAULT_ITEMS.parent / "fixture_scores.json"
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        scores = fixture.get("scores", fixture)
        self.assertEqual(set(scores), {item["id"] for item in items})


class ExtractScoreTest(unittest.TestCase):
    def test_direct_and_nested_shapes(self) -> None:
        self.assertEqual(qb.extract_score(0.72), 0.72)
        self.assertEqual(qb.extract_score({"probability": 0.61}), 0.61)
        self.assertEqual(qb.extract_score({"data": {"probability": 0.43}}), 0.43)
        self.assertEqual(qb.extract_score({"outputs": [{"score": 0.88}]}), 0.88)
        self.assertEqual(qb.extract_score({"answer": {"probability": "0.25"}}), 0.25)
        self.assertEqual(qb.extract_score({"label": "true"}), 1.0)
        self.assertEqual(qb.extract_score({"label": "no"}), 0.0)

    def test_invalid_response_raises(self) -> None:
        with self.assertRaises(ValueError):
            qb.extract_score({"unexpected": "shape"})


class PayloadTest(unittest.TestCase):
    def test_payload_includes_rubric_and_truncated_input(self) -> None:
        cfg = qb.load_judge_config(qb.DEFAULT_CONFIG)
        cfg["context_chars"] = 20
        item = {
            "title": "A concrete serving optimization",
            "source": "vllm_blog",
            "source_role": "first_party",
            "published": "2026-10-24T00:00:00Z",
            "url": "https://example.com/post",
            "excerpt": "x" * 200,
        }
        payload = qb.build_payload(item, cfg)
        self.assertEqual(payload["question_id"], "is_substantive_platform_content")
        self.assertEqual(payload["type"], "noul")
        self.assertIn("instructions", payload)
        self.assertIn("criteria", payload)
        self.assertEqual(payload["input"]["title"], item["title"])
        self.assertEqual(len(payload["input"]["excerpt"]), 20)

    def test_payload_key_wrapper(self) -> None:
        cfg = qb.load_judge_config(qb.DEFAULT_CONFIG)
        cfg["payload_key"] = "request"
        payload = qb.build_payload({"title": "x"}, cfg)
        self.assertIn("request", payload)
        self.assertEqual(payload["request"]["input"]["title"], "x")


class MetricsTest(unittest.TestCase):
    def rows(self):
        return [
            {"score": 0.9, "expected": 1},
            {"score": 0.8, "expected": 1},
            {"score": 0.2, "expected": 0},
            {"score": 0.1, "expected": 0},
        ]

    def test_perfect_classifier(self) -> None:
        metrics = qb.compute_metrics(self.rows(), 0.5)
        self.assertEqual(metrics["tp"], 2)
        self.assertEqual(metrics["tn"], 2)
        self.assertEqual(metrics["precision"], 1.0)
        self.assertEqual(metrics["recall"], 1.0)
        self.assertEqual(metrics["f1"], 1.0)
        self.assertEqual(metrics["accuracy"], 1.0)
        self.assertAlmostEqual(metrics["brier"], 0.025, places=4)
        self.assertEqual(qb.roc_auc(self.rows()), 1.0)

    def test_false_positive_and_false_negative(self) -> None:
        rows = [
            {"score": 0.9, "expected": 0},
            {"score": 0.1, "expected": 1},
            {"score": 0.8, "expected": 1},
            {"score": 0.2, "expected": 0},
        ]
        metrics = qb.compute_metrics(rows, 0.5)
        self.assertEqual(metrics["fp"], 1)
        self.assertEqual(metrics["fn"], 1)
        self.assertEqual(metrics["precision"], 0.5)
        self.assertEqual(metrics["recall"], 0.5)

    def test_threshold_sweep_prefers_qualified_threshold(self) -> None:
        rows = [
            {"score": 0.9, "expected": 1},
            {"score": 0.8, "expected": 1},
            {"score": 0.4, "expected": 1},
            {"score": 0.2, "expected": 0},
            {"score": 0.1, "expected": 0},
        ]
        sweep, threshold = qb.threshold_sweep(rows)
        self.assertTrue(sweep)
        self.assertGreaterEqual(threshold, 0.05)
        chosen = qb.compute_metrics(rows, threshold)
        self.assertGreaterEqual(chosen["f1"], 0.5)

    def test_review_queue_splits_false_positives_and_negatives(self) -> None:
        rows = [
            {"id": "fp", "score": 0.9, "expected": 0},
            {"id": "fn", "score": 0.1, "expected": 1},
            {"id": "ok", "score": 0.9, "expected": 1},
        ]
        review = qb._review_items(rows, 0.5)
        self.assertEqual([row["id"] for row in review["false_positives"]], ["fp"])
        self.assertEqual([row["id"] for row in review["false_negatives"]], ["fn"])


class ProviderTest(unittest.TestCase):
    def test_fixture_provider(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "scores.json"
            path.write_text(json.dumps({"scores": {"a": 0.7, "b": {"score": 0.2}}}), encoding="utf-8")
            provider = qb.FixtureProvider(path)
            self.assertEqual(provider.score({"id": "a"}, {})["score"], 0.7)
            self.assertEqual(provider.score({"id": "b"}, {})["score"], 0.2)

    def test_heuristic_provider_uses_content_not_expected(self) -> None:
        provider = qb.HeuristicProvider()
        engineering = provider.score(
            {"title": "Cutting inference latency with a new KV cache kernel", "source": "vllm_blog", "excerpt": "serving benchmark"},
            {},
        )["score"]
        marketing = provider.score(
            {"title": "Customer story: how a bank uses our ads product", "source": "openai_blog", "excerpt": ""},
            {},
        )["score"]
        self.assertGreater(engineering, marketing)

    def test_jev_provider_requires_configuration(self) -> None:
        provider = qb.JevProvider({"endpoint": "", "api_key_env": "MISSING_JEV_KEY"})
        self.assertFalse(provider.configured())
        with self.assertRaises(RuntimeError):
            provider.score({"title": "x"}, {})


class RunTest(unittest.TestCase):
    def test_fixture_run_writes_report_and_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            items_path = root / "items.json"
            scores_path = root / "scores.json"
            out_dir = root / "out"
            items = [
                {
                    "id": "a",
                    "slice": "engineering",
                    "source": "vllm_blog",
                    "source_role": "first_party",
                    "title": "Concrete inference optimization",
                    "url": "https://example.com/a",
                    "published": "2026-10-24T00:00:00Z",
                    "excerpt": "A detailed serving optimization.",
                    "expected": "keep",
                    "expected_label": "must_read",
                    "notes": "engineering",
                },
                {
                    "id": "b",
                    "slice": "marketing",
                    "source": "openai_blog",
                    "source_role": "first_party",
                    "title": "Customer story about ads",
                    "url": "https://example.com/b",
                    "published": "2026-10-24T00:00:00Z",
                    "excerpt": "A customer story.",
                    "expected": "drop",
                    "expected_label": "junk",
                    "notes": "marketing",
                },
            ]
            items_path.write_text(json.dumps({"benchmark_version": "test", "items": items}), encoding="utf-8")
            scores_path.write_text(json.dumps({"scores": {"a": 0.9, "b": 0.1}}), encoding="utf-8")
            args = Namespace(
                provider="fixture",
                items=str(items_path),
                config=str(qb.DEFAULT_CONFIG),
                scores=str(scores_path),
                out=str(out_dir),
                threshold=None,
                limit=None,
                request_only=False,
            )
            code = qb.run(args)
            self.assertEqual(code, 0)
            self.assertTrue((out_dir / "report.md").exists())
            self.assertTrue((out_dir / "review.md").exists())
            payload = json.loads((out_dir / "report.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["at_0_5"]["n"], 2)
            self.assertEqual(payload["tuned"]["precision"], 1.0)


if __name__ == "__main__":
    unittest.main()
