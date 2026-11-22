"""Tests for pipeline/card_store.py, the per-card translation store."""

from __future__ import annotations

import json
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))

import card_store  # noqa: E402

NOW = datetime(2026, 11, 23, 3, 0, tzinfo=timezone.utc)


def _entry(last_seen: datetime, **overrides) -> dict:
    entry = {
        "source_hash": "h1",
        "model": "m1",
        "translated_at": last_seen.isoformat(),
        "last_seen": last_seen.isoformat(),
        "title": "제목",
        "summary_1line": "요약",
        "why_it_matters": "이유",
        "also_covered": [],
    }
    entry.update(overrides)
    return entry


class CardStoreTest(unittest.TestCase):
    def test_store_lives_beside_the_snapshot(self) -> None:
        self.assertEqual(
            card_store.store_path(Path("/r"), "ko"), Path("/r/data/i18n/ko/feed/cards.json")
        )

    def test_missing_or_corrupt_file_loads_as_an_empty_store(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "cards.json"
            empty = {"locale": "ko", "updated_at": "", "cards": {}}
            self.assertEqual(card_store.load(path, "ko"), empty)
            path.write_text("{not json", encoding="utf-8")
            self.assertEqual(card_store.load(path, "ko"), empty)
            path.write_text('["a list"]', encoding="utf-8")
            self.assertEqual(card_store.load(path, "ko"), empty)

    def test_save_then_load_round_trips_with_keys_sorted(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "feed" / "cards.json"
            store = {"locale": "ko", "updated_at": "", "cards": {"b": _entry(NOW), "a": _entry(NOW)}}
            card_store.save(path, store, NOW)

            on_disk = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(list(on_disk["cards"]), ["a", "b"])
            self.assertEqual(on_disk["updated_at"], NOW.isoformat())
            self.assertEqual(card_store.load(path, "ko")["cards"], store["cards"])

    def test_entry_is_fresh_only_for_the_same_source_hash_and_model(self) -> None:
        entry = _entry(NOW)
        self.assertTrue(card_store.is_fresh(entry, "h1", "m1"))
        self.assertFalse(card_store.is_fresh(entry, "h2", "m1"))
        self.assertFalse(card_store.is_fresh(entry, "h1", "m2"))
        self.assertFalse(card_store.is_fresh(None, "h1", "m1"))

    def test_prune_drops_entries_unseen_for_fourteen_days(self) -> None:
        store = {
            "locale": "ko",
            "updated_at": "",
            "cards": {
                "seen-today": _entry(NOW),
                "edge": _entry(NOW - timedelta(days=14)),
                "stale": _entry(NOW - timedelta(days=14, seconds=1)),
                "no-last-seen": {**_entry(NOW), "last_seen": ""},
            },
        }
        self.assertEqual(card_store.prune(store, NOW), 2)
        self.assertEqual(sorted(store["cards"]), ["edge", "seen-today"])


if __name__ == "__main__":
    unittest.main()
