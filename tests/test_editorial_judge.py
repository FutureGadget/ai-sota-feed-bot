from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pipeline import editorial_judge
from pipeline import judgment_store as js


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


def _cfg(store_path=None, **overrides):
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
        "judgment_store": {},
    }
    if store_path is not None:
        cfg["judgment_store"] = {"path": str(store_path), "ttl_days": 14, "max_entries": 6000}
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
                out, diag = editorial_judge.apply_judge(items, _cfg(Path(tmp) / "judgments.json"))
            self.assertTrue(diag["enabled"])
            self.assertEqual(diag["judged"], 5)
            self.assertEqual(out[0]["judge_verdict"], "keep")
            self.assertEqual(out[1]["judge_verdict"], "review")
            self.assertEqual(out[2]["judge_verdict"], "drop")
            self.assertEqual(out[0]["judge_category"], "inference_serving")
            self.assertEqual(out[2]["judge_category"], "off_topic")
            self.assertIsNotNone(out[0]["judge_score"])
            files = [
                path for path in Path(tmp).glob("*.json")
                if path.name not in {"classified.json", "judgments.json"}
            ]
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
                out, diag = editorial_judge.apply_judge(items, _cfg(Path(tmp) / "judgments.json"))
        self.assertEqual(diag["errors"], 5)
        self.assertEqual(diag["judged"], 0)
        self.assertTrue(all(item["judge_verdict"] == "unjudged" for item in out))
        self.assertTrue(all("judge_error" in item for item in out))

    def test_second_run_reuses_the_durable_store(self) -> None:
        items = _items()
        provider = FakeProvider(scores={"0": 0.8, "1": 0.4, "2": 0.05, "3": 0.9, "4": 0.7})
        with tempfile.TemporaryDirectory() as tmp:
            with (
                patch.object(editorial_judge, "provider_from_config", return_value=provider),
                patch.object(editorial_judge, "CLASSIFIED_DIR", Path(tmp)),
                patch.object(editorial_judge, "COMPACT_CLASSIFIED", Path(tmp) / "classified.json"),
            ):
                store_path = Path(tmp) / "judgments.json"
                first, first_diag = editorial_judge.apply_judge(_items(), _cfg(store_path))
                second, second_diag = editorial_judge.apply_judge(_items(), _cfg(store_path))
        self.assertEqual(first_diag["judged"], 5)
        self.assertEqual(second_diag["judged"], 0)
        self.assertEqual(second_diag["store_hits"], 5)
        self.assertEqual([item["judge_score"] for item in second], [item["judge_score"] for item in first])
        self.assertTrue(all(item.get("judge_store_cached") for item in second))

    def test_drop_cap_downgrades_excess_drops(self) -> None:
        items = [
            {"id": str(i), "judge_verdict": "drop", "judge_score": 0.1 + i * 0.01}
            for i in range(10)
        ]
        out, downgraded = editorial_judge._cap_drops(items, 0.6)
        self.assertEqual(downgraded, 4)
        self.assertEqual(sum(1 for item in out if item["judge_verdict"] == "drop"), 6)
        self.assertEqual(sum(1 for item in out if item.get("judge_drop_downgraded")), 4)


def _evidence_cfg(store_path=None, min_chars=300):
    cfg = _cfg(store_path)
    cfg["content_fetch"] = {
        "enabled": True,
        "min_evidence_chars": min_chars,
        "min_evidence_exempt_roles": ["release"],
    }
    return cfg


def _evidence_items():
    return [
        {
            "id": "thin",
            "title": "Search snippet",
            "source": "search_example",
            "source_role": "search",
            "url": "https://example.com/thin",
            "summary": "A 40 character teaser only.",
        },
        {
            "id": "full",
            "title": "A real engineering post",
            "source": "vllm_blog",
            "source_role": "first_party",
            "url": "https://example.com/full",
            "summary": "x" * 600,
        },
        {
            "id": "release",
            "title": "v1.2.3",
            "source": "vllm_releases",
            "source_role": "release",
            "url": "https://example.com/release",
            "summary": "",
        },
    ]


class EvidenceGateTest(unittest.TestCase):
    def test_thin_items_are_unjudged_and_releases_are_exempt(self) -> None:
        items = _evidence_items()
        provider = FakeProvider(scores={"thin": 0.04, "full": 0.8, "release": 0.05})
        with tempfile.TemporaryDirectory() as tmp:
            with (
                patch.object(editorial_judge, "provider_from_config", return_value=provider),
                patch.object(editorial_judge, "build_paragraph_map", return_value={}),
                patch.object(editorial_judge, "CLASSIFIED_DIR", Path(tmp)),
                patch.object(editorial_judge, "COMPACT_CLASSIFIED", Path(tmp) / "classified.json"),
            ):
                out, diag = editorial_judge.apply_judge(items, _evidence_cfg(Path(tmp) / "judgments.json"))
        self.assertEqual(diag["insufficient_evidence"], 1)
        self.assertEqual(diag["judged"], 2)
        self.assertEqual(out[0]["judge_verdict"], "unjudged")
        self.assertEqual(out[0]["judge_error"], "insufficient_evidence")
        self.assertIsNone(out[0]["judge_score"])
        self.assertEqual(out[1]["judge_verdict"], "keep")
        self.assertEqual(out[2]["judge_verdict"], "drop")

    def test_fetched_text_unblocks_a_judgment(self) -> None:
        items = _evidence_items()[:1]
        provider = FakeProvider(scores={"thin": 0.8})
        fetched = {"https://example.com/thin": "y" * 1200}
        with tempfile.TemporaryDirectory() as tmp:
            with (
                patch.object(editorial_judge, "provider_from_config", return_value=provider),
                patch.object(editorial_judge, "build_paragraph_map", return_value=fetched),
                patch.object(editorial_judge, "CLASSIFIED_DIR", Path(tmp)),
                patch.object(editorial_judge, "COMPACT_CLASSIFIED", Path(tmp) / "classified.json"),
            ):
                out, diag = editorial_judge.apply_judge(items, _evidence_cfg(Path(tmp) / "judgments.json"))
        self.assertEqual(diag["content_fetched"], 1)
        self.assertEqual(diag["judged"], 1)
        self.assertEqual(out[0]["judge_verdict"], "keep")
        self.assertEqual(out[0]["judge_evidence_chars"], 1200)

    def test_thin_store_entry_is_refreshed_after_enrichment(self) -> None:
        item = _evidence_items()[0]
        with tempfile.TemporaryDirectory() as tmp:
            store_path = Path(tmp) / "judgments.json"
            cfg = _evidence_cfg(store_path)
            store = js.load_store(store_path)
            thin_key = js.judgment_key(item, cfg)
            js.put_entry(
                store,
                thin_key,
                {
                    **item,
                    "judge_score": 0.05,
                    "judge_verdict": "drop",
                    "judge_evidence_chars": 0,
                },
                cfg,
            )
            js.save_store(store, store_path)
            provider = FakeProvider(scores={"thin": 0.8})
            fetched = {"https://example.com/thin": "y" * 1200}
            with (
                patch.object(editorial_judge, "provider_from_config", return_value=provider),
                patch.object(editorial_judge, "build_paragraph_map", return_value=fetched),
                patch.object(editorial_judge, "CLASSIFIED_DIR", Path(tmp)),
                patch.object(editorial_judge, "COMPACT_CLASSIFIED", Path(tmp) / "classified.json"),
            ):
                out, diag = editorial_judge.apply_judge([item], cfg)
        self.assertEqual(diag["judged"], 1)
        self.assertEqual(out[0]["judge_verdict"], "keep")
        self.assertEqual(out[0]["judge_score"], 0.8)

    def test_full_evidence_store_entry_is_reused(self) -> None:
        item = _evidence_items()[1]
        with tempfile.TemporaryDirectory() as tmp:
            store_path = Path(tmp) / "judgments.json"
            cfg = _evidence_cfg(store_path)
            store = js.load_store(store_path)
            key = js.judgment_key(item, cfg)
            js.put_entry(
                store,
                key,
                {
                    **item,
                    "judge_score": 0.9,
                    "judge_verdict": "keep",
                    "judge_evidence_chars": 600,
                },
                cfg,
            )
            js.save_store(store, store_path)
            with (
                patch.object(editorial_judge, "provider_from_config", return_value=FakeProvider(error=True)),
                patch.object(editorial_judge, "build_paragraph_map", return_value={}),
                patch.object(editorial_judge, "CLASSIFIED_DIR", Path(tmp)),
                patch.object(editorial_judge, "COMPACT_CLASSIFIED", Path(tmp) / "classified.json"),
            ):
                out, diag = editorial_judge.apply_judge([item], cfg)
        self.assertEqual(diag["store_hits"], 1)
        self.assertEqual(diag["judged"], 0)
        self.assertEqual(out[0]["judge_score"], 0.9)


if __name__ == "__main__":
    unittest.main()
