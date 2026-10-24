from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pipeline import judgment_store as js


def _cfg():
    return {
        "version": "feed-quality-v1",
        "openrouter": {
            "model": "jev-1.14",
            "score_mode": "hybrid",
            "use_holistic_keep": True,
            "questions": {"keep": {"type": "noul", "instructions": "x"}},
            "hybrid": {"primary": "keep"},
        },
        "instructions": {"task": "x"},
        "criteria": {"true": {"definition": "x"}},
        "content_fetch": {"max_chars": 2500},
    }


class JudgmentKeyTest(unittest.TestCase):
    def test_key_is_stable_for_the_same_item(self) -> None:
        item = {"url": "https://example.com/a?utm=1", "title": "A story", "source": "vllm_blog"}
        self.assertEqual(js.judgment_key(item, _cfg()), js.judgment_key(dict(item), _cfg()))

    def test_key_changes_with_identity_content_and_model(self) -> None:
        item = {"url": "https://example.com/a", "title": "A story", "source": "vllm_blog"}
        base = js.judgment_key(item, _cfg())
        self.assertNotEqual(base, js.judgment_key({**item, "title": "Another story"}, _cfg()))
        cfg = _cfg()
        cfg["openrouter"]["model"] = "jev-1.13"
        self.assertNotEqual(base, js.judgment_key(item, cfg))

    def test_thresholds_do_not_invalidate_a_judgment(self) -> None:
        item = {"url": "https://example.com/a", "title": "A story", "source": "vllm_blog"}
        cfg = _cfg()
        base = js.judgment_key(item, cfg)
        cfg["ranking"] = {"drop_below": 0.2, "keep_at": 0.4}
        self.assertEqual(base, js.judgment_key(item, cfg))


class StoreTest(unittest.TestCase):
    def test_save_load_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "judgments.json"
            store = js.load_store(path)
            item = {
                "url": "https://example.com/a",
                "title": "A story",
                "source": "vllm_blog",
                "judge_score": 0.8,
                "judge_verdict": "keep",
                "judge_judged_at": datetime.now(timezone.utc).isoformat(),
            }
            key = js.judgment_key(item, _cfg())
            js.put_entry(store, key, item, _cfg())
            js.save_store(store, path)
            loaded = js.load_store(path)
            self.assertIn(key, loaded["entries"])
            entry = js.get_entry(loaded, key, 14)
            self.assertIsNotNone(entry)
            self.assertEqual(entry["judge_score"], 0.8)
            self.assertEqual(entry["judge_verdict"], "keep")

    def test_ttl_expires_entries(self) -> None:
        store = js.load_store(Path("/nonexistent/judgments.json"))
        old = (datetime.now(timezone.utc) - timedelta(days=20)).isoformat()
        store["entries"]["old"] = {"judge_judged_at": old, "judge_score": 0.5}
        self.assertIsNone(js.get_entry(store, "old", 14))

    def test_prune_removes_old_and_caps_entries(self) -> None:
        now = datetime.now(timezone.utc)
        store = {"entries": {}}
        for i in range(5):
            store["entries"][f"k{i}"] = {
                "judge_judged_at": (now - timedelta(days=i)).isoformat(),
                "judge_score": 0.5,
            }
        store["entries"]["old"] = {
            "judge_judged_at": (now - timedelta(days=30)).isoformat(),
            "judge_score": 0.1,
        }
        pruned, dropped = js.prune_store(store, ttl_days=14, max_entries=3)
        self.assertEqual(dropped, 3)
        self.assertEqual(len(pruned["entries"]), 3)
        self.assertNotIn("old", pruned["entries"])


if __name__ == "__main__":
    unittest.main()
