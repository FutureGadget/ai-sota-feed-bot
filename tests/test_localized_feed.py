from __future__ import annotations

import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import os

from pipeline import build_localized_feed as localized


class LocalizedFeedHelpersTest(unittest.TestCase):
    def test_translation_key_is_url_first_and_title_stable(self) -> None:
        first = {
            "url": "https://example.com/post/",
            "title": "Original English title",
        }
        second = {
            "url": "https://example.com/post",
            "title": "Translated or rewritten title",
        }

        self.assertEqual(localized.translation_key(first), "https://example.com/post")
        self.assertEqual(localized.translation_key(first), localized.translation_key(second))

    def test_source_hash_ignores_ranking_metadata(self) -> None:
        item = {
            "title": "Agent tracing patterns",
            "summary_1line": "A concise explanation of tracing long-running agents.",
            "why_it_matters": "Teams can debug tool failures faster.",
            "also_covered": [{"url": "https://other.example/a", "title": "Tracing agents"}],
            "v2_final_score": 9.9,
            "rank_at_last_seen": 1,
            "reader_adjustment": 0.2,
        }
        changed_metadata = {
            **item,
            "v2_final_score": 1.1,
            "rank_at_last_seen": 12,
            "reader_adjustment": -0.1,
        }
        changed_text = {
            **item,
            "summary_1line": "A different reader-facing summary.",
        }

        self.assertEqual(localized.source_hash(item), localized.source_hash(changed_metadata))
        self.assertNotEqual(localized.source_hash(item), localized.source_hash(changed_text))

    def test_kst_window_uses_last_seven_korean_calendar_days(self) -> None:
        now = datetime(2026, 7, 5, 2, 30, tzinfo=timezone.utc)
        window = localized.kst_rolling_window(now=now, days=7)

        self.assertEqual(window["days"], 7)
        self.assertEqual(window["from"], "2026-06-29T00:00:00+09:00")
        self.assertEqual(window["to"], "2026-07-05T23:59:59.999000+09:00")

    def test_status_currentness_uses_source_run_at(self) -> None:
        source_run_at = "2026-07-05T00:00:00+00:00"
        now_current = datetime(2026, 7, 5, 23, 59, tzinfo=timezone.utc)
        now_stale = datetime(2026, 7, 6, 0, 1, tzinfo=timezone.utc)

        self.assertTrue(localized.is_current(source_run_at, now=now_current))
        self.assertFalse(localized.is_current(source_run_at, now=now_stale))

    def test_select_brief_items_accepts_fewer_than_limit_as_complete(self) -> None:
        items = [
            {"url": "https://example.com/a", "title": "A", "type": "news"},
            {"url": "https://example.com/b", "title": "B", "type": "release"},
            {"url": "https://example.com/c", "title": "C", "type": "research"},
        ]

        selected = localized.select_brief_items(items, limit=20)

        self.assertEqual([it["title"] for it in selected], ["A", "C"])
        self.assertEqual(len(selected), 2)

    def test_canonical_brief_feed_uses_processed_runs_and_publish_window(self) -> None:
        old_data_dir = localized.DATA_DIR
        try:
            with TemporaryDirectory() as tmp:
                data_dir = Path(tmp)
                localized.DATA_DIR = data_dir
                runs_dir = data_dir / "processed" / "runs" / "2026" / "07"
                runs_dir.mkdir(parents=True)
                (data_dir / "processed" / "runs_index.json").write_text(
                    json.dumps([
                        {
                            "run_at": "2026-07-05T01:00:00+00:00",
                            "path": "2026/07/run.json",
                            "item_count": 3,
                        }
                    ]),
                    encoding="utf-8",
                )
                (runs_dir / "run.json").write_text(
                    json.dumps({
                        "run_at": "2026-07-05T01:00:00+00:00",
                        "items": [
                            {"url": "https://example.com/current", "title": "Current", "type": "news", "published": "2026-07-05T00:00:00Z"},
                            {"url": "https://example.com/release", "title": "Release", "type": "release", "published": "2026-07-05T00:00:00Z"},
                            {"url": "https://example.com/old", "title": "Old", "type": "news", "published": "2026-06-20T00:00:00Z"},
                        ],
                    }),
                    encoding="utf-8",
                )

                feed = localized.canonical_brief_feed(
                    limit=20,
                    days=7,
                    now=datetime(2026, 7, 5, 2, 30, tzinfo=timezone.utc),
                )

                self.assertEqual([it["title"] for it in feed["items"]], ["Current"])
                self.assertEqual(feed["total_items"], 1)
                self.assertFalse(feed["has_more"])
                self.assertEqual(feed["source_run_at"], "2026-07-05T01:00:00+00:00")
        finally:
            localized.DATA_DIR = old_data_dir

    def test_builder_kill_switch_returns_disabled_status(self) -> None:
        old_value = os.environ.get("LOCALIZED_FEED_ENABLED")
        try:
            os.environ["LOCALIZED_FEED_ENABLED"] = "0"
            payload = localized.build_snapshot(locale="ko", label="brief", limit=20, dry_run=True)

            self.assertEqual(payload["status"], "disabled")
            self.assertEqual(payload["reason"], "localized_feed_disabled")
        finally:
            if old_value is None:
                os.environ.pop("LOCALIZED_FEED_ENABLED", None)
            else:
                os.environ["LOCALIZED_FEED_ENABLED"] = old_value


if __name__ == "__main__":
    unittest.main()
