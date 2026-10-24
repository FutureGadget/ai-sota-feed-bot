from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pipeline import editorial_judge


class FakeProvider:
    name = "fake"

    def __init__(self, scores=None, choices=None, error=False):
        self.scores = scores or {}
        self.choices = choices or {}
        self.error = error

    def configured(self):
        return True

    def score(self, item, cfg):
        if self.error:
            raise RuntimeError("fake_failure")
        key = str(item.get("id"))
        return {
            "score": self.scores.get(key, 0.7),
            "signals": {"platform_relevant": 0.9, "release_lane": 0.1},
            "choices": {
                "category": {
                    "choice": self.choices.get(key, "agent_engineering"),
                    "confidence": 0.8,
                    "probabilities": {"agent_engineering": 0.8},
                }
            },
            "latency_ms": 1,
            "cached": False,
        }


def _cfg(**overrides):
    cfg = {
        "enabled": True,
        "provider": "openrouter",
        "version": "feed-quality-v1",
        "openrouter": {
            "model": "jev-1.14",
            "max_items": 10,
            "max_workers": 2,
            "time_budget_seconds": 10,
            "score_mode": "hybrid",
            "hybrid": {"primary": "keep", "drop_if_above": {"release_lane": 0.6}},
        },
        "ranking": {"drop_below": 0.15, "keep_at": 0.5, "max_drop_share": 0.6},
    }
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(cfg.get(key), dict):
            cfg[key] = {**cfg[key], **value}
        else:
            cfg[key] = value
    return cfg


def _items():
    return [
        {"id": str(i), "title": f"story {i}", "source": "vllm_blog", "source_role": "first_party", "freshness": 1.0}
        for i in range(5)
    ]


class ApplyJudgeTest(unittest.TestCase):
    def test_disabled_is_noop(self) -> None:
        items = _items()
        out, diag = editorial_judge.apply_judge(items, {"enabled": False})
        self.assertEqual(out, items)
        self.assertFalse(diag["enabled"])
        self.assertEqual(diag["reason"], "disabled")

    def test_not_configured_is_noop(self) -> None:
        class NotConfigured:
            name = "fake"

            def configured(self):
                return False

        items = _items()
        with patch.object(editorial_judge, "provider_from_config", return_value=NotConfigured()):
            out, diag = editorial_judge.apply_judge(items, _cfg())
        self.assertEqual(out, items)
        self.assertFalse(diag["enabled"])
        self.assertEqual(diag["reason"], "not_configured")

    def test_attaches_verdict_category_and_writes_classified(self) -> None:
        items = _items()
        provider = FakeProvider(
            scores={"0": 0.8, "1": 0.4, "2": 0.05, "3": 0.9, "4": 0.7},
            choices={"0": "inference_serving", "2": "off_topic"},
        )
        with tempfile.TemporaryDirectory() as tmp:
            with (
                patch.object(editorial_judge, "provider_from_config", return_value=provider),
                patch.object(editorial_judge, "CLASSIFIED_DIR", Path(tmp)),
                patch.object(editorial_judge, "COMPACT_CLASSIFIED", Path(tmp) / "classified.json"),
            ):
                out, diag = editorial_judge.apply_judge(items, _cfg())
            self.assertTrue(diag["enabled"])
            self.assertEqual(diag["judged"], 5)
            self.assertEqual(out[0]["judge_verdict"], "keep")
            self.assertEqual(out[1]["judge_verdict"], "review")
            self.assertEqual(out[2]["judge_verdict"], "drop")
            self.assertEqual(out[0]["judge_category"], "inference_serving")
            self.assertEqual(out[2]["judge_category"], "off_topic")
            self.assertIsNotNone(out[0]["judge_score"])
            files = [path for path in Path(tmp).glob("*.json") if path.name != "classified.json"]
            self.assertEqual(len(files), 1)
            payload = json.loads(files[0].read_text(encoding="utf-8"))
            self.assertEqual(payload["model"], "jev-1.14")
            self.assertEqual(payload["item_count"], 5)
            compact = json.loads((Path(tmp) / "classified.json").read_text(encoding="utf-8"))
            self.assertEqual(compact["item_count"], 5)
            self.assertEqual(len(compact["items"]), 5)

    def test_fail_open_marks_unjudged(self) -> None:
        items = _items()
        with tempfile.TemporaryDirectory() as tmp:
            with (
                patch.object(editorial_judge, "provider_from_config", return_value=FakeProvider(error=True)),
                patch.object(editorial_judge, "CLASSIFIED_DIR", Path(tmp)),
                patch.object(editorial_judge, "COMPACT_CLASSIFIED", Path(tmp) / "classified.json"),
            ):
                out, diag = editorial_judge.apply_judge(items, _cfg())
        self.assertEqual(diag["errors"], 5)
        self.assertEqual(diag["judged"], 0)
        self.assertTrue(all(item["judge_verdict"] == "unjudged" for item in out))
        self.assertTrue(all("judge_error" in item for item in out))

    def test_drop_cap_downgrades_excess_drops(self) -> None:
        items = [
            {"id": str(i), "judge_verdict": "drop", "judge_score": 0.1 + i * 0.01}
            for i in range(10)
        ]
        out, downgraded = editorial_judge._cap_drops(items, 0.6)
        self.assertEqual(downgraded, 4)
        self.assertEqual(sum(1 for item in out if item["judge_verdict"] == "drop"), 6)
        self.assertEqual(sum(1 for item in out if item.get("judge_drop_downgraded")), 4)


if __name__ == "__main__":
    unittest.main()
