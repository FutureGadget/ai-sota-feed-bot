from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pipeline import hn_signal

NOW = datetime(2026, 11, 25, 12, 0, tzinfo=timezone.utc)


def raw(item_id: int, url: str, hours_ago: float) -> dict:
    published = (NOW - timedelta(hours=hours_ago)).strftime("%a, %d %b %Y %H:%M:%S +0000")
    return {
        "source": "hackernews_ai",
        "url": url,
        "published": published,
        "summary": f'<p>Comments URL: <a href="https://news.ycombinator.com/item?id={item_id}">x</a></p><p>Points: 1</p>',
    }


class FakeHN:
    def __init__(self, scores: dict[str, int]) -> None:
        self.scores = scores
        self.calls: list[str] = []

    def __call__(self, item_id: str) -> dict | None:
        self.calls.append(item_id)
        if item_id not in self.scores:
            raise OSError("unreachable")
        return {"score": self.scores[item_id], "descendants": 3}


class HnSignalTest(unittest.TestCase):
    def test_reads_votes_for_young_stories_only(self) -> None:
        store = {"version": 1, "items": {}}
        fake = FakeHN({"1": 120, "2": 4})
        stats = hn_signal.refresh(
            store,
            [raw(1, "https://a.example/post", 20), raw(2, "https://b.example", 2), raw(3, "https://old.example", 80)],
            NOW,
            fetch=fake,
        )
        self.assertEqual(sorted(fake.calls), ["1", "2"])
        self.assertEqual(store["items"]["1"]["points"], 120)
        self.assertEqual(store["items"]["1"]["comments"], 3)
        self.assertNotIn("points", store["items"]["3"])
        self.assertEqual(stats["read"], 2)

    def test_recent_read_is_not_repeated_and_old_read_is(self) -> None:
        store = {"version": 1, "items": {}}
        hn_signal.refresh(store, [raw(1, "https://a.example", 10)], NOW, fetch=FakeHN({"1": 5}))
        fake = FakeHN({"1": 90})
        hn_signal.refresh(store, [], NOW + timedelta(hours=1), fetch=fake)
        self.assertEqual(fake.calls, [])
        hn_signal.refresh(store, [], NOW + timedelta(hours=hn_signal.REFRESH_HOURS), fetch=fake)
        self.assertEqual(store["items"]["1"]["points"], 90)

    def test_unreachable_item_keeps_the_rest_and_is_retried(self) -> None:
        store = {"version": 1, "items": {}}
        stats = hn_signal.refresh(store, [raw(1, "https://a", 5), raw(2, "https://b", 5)], NOW, fetch=FakeHN({"2": 7}))
        self.assertEqual((stats["read"], stats["failed"]), (1, 1))
        self.assertNotIn("checked_at", store["items"]["1"])

    def test_request_cap_reads_least_recently_checked_first(self) -> None:
        store = {"version": 1, "items": {}}
        hn_signal.refresh(store, [raw(1, "https://a", 5)], NOW - timedelta(hours=8), fetch=FakeHN({"1": 1}))
        fake = FakeHN({"1": 2, "2": 2})
        hn_signal.refresh(store, [raw(2, "https://b", 5)], NOW, fetch=fake, max_requests=1)
        self.assertEqual(fake.calls, ["2"])

    def test_old_entries_are_pruned(self) -> None:
        store = {"version": 1, "items": {"9": {"url": "u", "posted_at": (NOW - timedelta(days=11)).isoformat()}}}
        hn_signal.refresh(store, [], NOW, fetch=FakeHN({}))
        self.assertEqual(store["items"], {})

    def test_annotate_joins_by_hn_id_or_url(self) -> None:
        store = {"version": 1, "items": {}}
        hn_signal.refresh(
            store, [raw(1, "https://a.example/post", 5), raw(2, "https://news.ycombinator.com/item?id=2", 5)], NOW,
            fetch=FakeHN({"1": 150, "2": 30}),
        )
        articles = [
            {"source": "hackernews_ai", "url": "https://a.example/post", "summary": "a written summary"},
            {"source": "hackernews_ai", "url": "https://news.ycombinator.com/item?id=2"},
            {"source": "openai_blog", "url": "https://a.example/post"},
        ]
        self.assertEqual(hn_signal.annotate(articles, store), 2)
        self.assertEqual((articles[0]["hn_points"], articles[1]["hn_points"]), (150, 30))
        self.assertNotIn("hn_points", articles[2])

    def test_store_round_trips(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "hn_signal.json"
            self.assertEqual(hn_signal.load_store(path), {"version": 1, "items": {}})
            hn_signal.save_store({"version": 1, "items": {"1": {"points": 3}}}, path)
            self.assertEqual(json.loads(path.read_text())["items"]["1"]["points"], 3)

    def test_every_raw_hn_item_carries_its_id(self) -> None:
        days = sorted(Path(hn_signal.RAW_DIR).glob("*/items.json"))[-3:]
        rows = []
        for path in days:
            data = json.loads(path.read_text())
            rows += [r for r in (data.get("items") if isinstance(data, dict) else data) if r.get("source") == hn_signal.SOURCE]
        if not rows:
            self.skipTest("no committed raw HN items")
        self.assertTrue(all(hn_signal.hn_id(r) for r in rows))


if __name__ == "__main__":
    unittest.main()
