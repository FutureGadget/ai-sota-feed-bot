"""Tests for pipeline/build_localized_feed.py.

The builder runs as a script, so import it by its bare name with pipeline/ on
sys.path. Translation goes through a fake Anthropic client; no test calls the API.
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))
sys.path.insert(0, str(ROOT / "tests"))

import build_localized_feed as localized  # noqa: E402
import translator  # noqa: E402
from claude_fakes import PREFIX, EchoClient  # noqa: E402


def _mk_item(i: int, **overrides) -> dict:
    item = {
        "id": f"item-{i}",
        "url": f"https://example.com/post-{i}",
        "title": f"Title {i}",
        "summary_1line": f"Summary {i}.",
        "why_it_matters": f"Why it matters {i}.",
        "also_covered": [],
        "first_seen": "2026-07-05T00:00:00Z",
        "published": "2026-07-05T00:00:00Z",
    }
    item.update(overrides)
    return item


def _fixed_datetime(fixed_now: datetime):
    """A `datetime` subclass whose `now()` always returns `fixed_now`."""

    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now if tz is None else fixed_now.astimezone(tz)

    return FixedDatetime


class TranslationKeyAndHashTest(unittest.TestCase):
    def test_translation_key_is_url_first_and_title_stable(self) -> None:
        first = {"url": "https://example.com/post/", "title": "Original English title"}
        second = {"url": "https://example.com/post", "title": "Translated or rewritten title"}

        self.assertEqual(localized._translation_key(first), "https://example.com/post")
        self.assertEqual(localized._translation_key(first), localized._translation_key(second))

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
        changed_metadata = {**item, "v2_final_score": 1.1, "rank_at_last_seen": 12, "reader_adjustment": -0.1}
        changed_text = {**item, "summary_1line": "A different reader-facing summary."}

        self.assertEqual(localized._source_hash(item), localized._source_hash(changed_metadata))
        self.assertNotEqual(localized._source_hash(item), localized._source_hash(changed_text))


class ItemJobTest(unittest.TestCase):
    def test_job_carries_visible_fields_and_the_excerpt_as_context(self) -> None:
        item = _mk_item(
            1,
            also_covered=[
                {"url": "https://other.example/story", "title": "Other coverage"},
                {"url": "https://other.example/blank", "title": " "},
            ],
            content_excerpt="The article body.",
            summary="ignored when an excerpt exists",
        )
        job = localized.item_job(item)
        self.assertEqual(job.key, item["url"])
        self.assertEqual(job.context, "The article body.")
        self.assertEqual(
            job.fields,
            {
                "title": "Title 1",
                "summary_1line": "Summary 1.",
                "why_it_matters": "Why it matters 1.",
                "also_covered_title_0": "Other coverage",
            },
        )

    def test_context_falls_back_to_summary_and_blank_fields_are_not_sent(self) -> None:
        job = localized.item_job(_mk_item(2, why_it_matters="  ", summary="Fallback summary"))
        self.assertEqual(job.context, "Fallback summary")
        self.assertNotIn("why_it_matters", job.fields)

    def test_card_keeps_identity_hash_and_also_covered_urls(self) -> None:
        item = _mk_item(1, also_covered=[{"url": "https://other.example/story", "title": "Other coverage"}])
        result = translator.Result(
            item["url"],
            {
                "title": "한국어 제목",
                "summary_1line": "한국어 요약",
                "why_it_matters": "한국어 이유",
                "also_covered_title_0": "다른 보도",
            },
            0.0,
        )
        card = localized._localized_card(item, result)
        self.assertEqual(card["translation_key"], item["url"])
        self.assertEqual(card["id"], item["id"])
        self.assertEqual(card["source_hash"], localized._source_hash(item))
        self.assertEqual(card["title"], "한국어 제목")
        self.assertEqual(card["also_covered"], [{"url": "https://other.example/story", "title": "다른 보도"}])


class BuildLocalizedFeedTest(unittest.TestCase):
    """Runs main() end to end against a temp ROOT, a mocked English-feed fetch,
    and a fake Anthropic client."""

    def setUp(self) -> None:
        self._tmpdir = TemporaryDirectory()
        self.tmp_path = Path(self._tmpdir.name)
        self.feed_dir = self.tmp_path / "data" / "i18n" / "ko" / "feed"
        self.feed_dir.mkdir(parents=True)
        self.latest_path = self.feed_dir / "latest.json"
        self.status_path = self.feed_dir / "status.json"
        self.ledger_path = self.tmp_path / "data" / "i18n" / "translation_spend.json"

        self._root_patch = patch.object(localized, "ROOT", self.tmp_path)
        self._root_patch.start()

        self.now = datetime(2026, 7, 10, 20, 0, tzinfo=timezone.utc)
        self._clock_patch = patch.object(localized, "datetime", _fixed_datetime(self.now))
        self._clock_patch.start()

        self._env_patch = patch.dict(os.environ, {translator.CAP_ENV: "60"})
        self._env_patch.start()
        self.client = EchoClient()

    def tearDown(self) -> None:
        self._clock_patch.stop()
        self._root_patch.stop()
        self._env_patch.stop()
        self._tmpdir.cleanup()

    def _run_main(self, items: list[dict], *, limit: int = 20, client=None) -> None:
        argv = ["build_localized_feed.py", "--locale", "ko", "--label", "brief", "--limit", str(limit)]
        with patch.object(sys, "argv", argv), \
             patch.object(localized, "_fetch_english_feed", return_value={"items": items}):
            localized.main(client=client or self.client)

    def _snapshot(self) -> dict:
        return json.loads(self.latest_path.read_text())

    def _status(self) -> dict:
        return json.loads(self.status_path.read_text())

    def _write_existing_snapshot(self, items: list[dict]) -> str:
        source_run_at = (self.now - timedelta(hours=1)).isoformat()
        snapshot = {
            "locale": "ko", "surface": "feed", "source_run_at": source_run_at,
            "translated_at": self.now.isoformat(),
            "expires_at": (self.now + timedelta(hours=23)).isoformat(),
            "max_items": 20, "source_item_count": len(items),
            "translated_item_count": len(items), "is_complete": True,
            "items": items,
        }
        self.latest_path.write_text(json.dumps(snapshot, ensure_ascii=False), encoding="utf-8")
        return self.latest_path.read_text()

    def test_cards_are_translated_in_feed_order_with_all_fields(self) -> None:
        items = [_mk_item(i, also_covered=[{"url": f"https://o.example/{i}", "title": f"Other {i}"}]) for i in range(3)]
        self._run_main(items)

        snapshot = self._snapshot()
        self.assertEqual([c["translation_key"] for c in snapshot["items"]], [it["url"] for it in items])
        self.assertEqual(snapshot["target_keys"], [it["url"] for it in items])
        for i, card in enumerate(snapshot["items"]):
            self.assertEqual(card["title"], f"{PREFIX}Title {i}")
            self.assertEqual(card["summary_1line"], f"{PREFIX}Summary {i}.")
            self.assertEqual(card["why_it_matters"], f"{PREFIX}Why it matters {i}.")
            self.assertEqual(card["also_covered"], [{"url": f"https://o.example/{i}", "title": f"{PREFIX}Other {i}"}])
        self.assertEqual([r["title"] for r in self.client.requested], ["Title 0", "Title 1", "Title 2"])
        self.assertTrue(snapshot["is_complete"])
        self.assertEqual(snapshot["model"], translator.model_for("feed"))
        self.assertEqual(snapshot["target_path"], "/ko/")
        self.assertEqual(self._status()["status"], "current")

    def test_each_call_is_cached_system_prompt_plus_the_card_and_its_context(self) -> None:
        self._run_main([_mk_item(0, content_excerpt="Body of the post.")])

        (call,) = self.client.calls
        self.assertEqual(call["model"], translator.model_for("feed"))
        self.assertEqual(call["system"][0]["cache_control"], {"type": "ephemeral"})
        self.assertIn("Body of the post.", call["messages"][0]["content"])

    def test_unchanged_cards_are_skipped_and_changed_cards_are_retranslated(self) -> None:
        items = [_mk_item(i) for i in range(3)]
        self._run_main(items)
        self.assertEqual(len(self.client.calls), 3)

        items[1] = _mk_item(1, summary_1line="A rewritten summary.")
        again = EchoClient()
        self._run_main(items, client=again)

        self.assertEqual([r["title"] for r in again.requested], ["Title 1"])
        cards = {c["translation_key"]: c for c in self._snapshot()["items"]}
        self.assertEqual(cards[items[1]["url"]]["summary_1line"], f"{PREFIX}A rewritten summary.")
        self.assertEqual(cards[items[0]["url"]]["summary_1line"], f"{PREFIX}Summary 0.")

    def test_cards_from_another_model_are_retranslated(self) -> None:
        items = [_mk_item(i) for i in range(2)]
        self._run_main(items)
        snapshot = self._snapshot()
        self.assertEqual({c["model"] for c in snapshot["items"]}, {translator.model_for("feed")})

        # A card left by the previous translator: same source, no per-card model.
        legacy = dict(snapshot["items"][0])
        legacy.pop("model")
        legacy["title"] = "Google text"
        self._write_existing_snapshot([legacy, snapshot["items"][1]])
        again = EchoClient()
        self._run_main(items, client=again)

        self.assertEqual([r["title"] for r in again.requested], ["Title 0"])
        cards = {c["translation_key"]: c for c in self._snapshot()["items"]}
        self.assertEqual(cards[items[0]["url"]]["title"], f"{PREFIX}Title 0")

    def test_nothing_dirty_makes_no_call(self) -> None:
        items = [_mk_item(i) for i in range(2)]
        self._run_main(items)
        again = EchoClient()
        self._run_main(items, client=again)
        self.assertEqual(again.calls, [])
        self.assertEqual(self._status()["status"], "current")

    def test_spend_is_recorded_in_the_shared_ledger_and_status(self) -> None:
        self._run_main([_mk_item(i) for i in range(2)])

        ledger = json.loads(self.ledger_path.read_text())
        self.assertEqual(ledger["month"], "2026-07")
        self.assertEqual({h["surface"] for h in ledger["history"]}, {"feed"})
        self.assertEqual(len(ledger["history"]), 2)
        budget = self._status()["budget"]
        self.assertAlmostEqual(budget["usd_spent"], ledger["usd"], places=4)
        self.assertEqual(budget["monthly_usd_cap"], 60)
        self.assertEqual(budget["month"], "2026-07")

    def test_snapshot_carries_frozen_render_metadata(self) -> None:
        # source_meta + target_keys let the API serve the frozen snapshot as
        # dated Korean cards when the feed is paused/stale.
        items = [_mk_item(i, source=f"src_{i}", type="news") for i in range(5)]
        self._run_main(items)

        snapshot = self._snapshot()
        self.assertEqual(snapshot["target_keys"], [localized._translation_key(it) for it in items])
        for row in snapshot["items"]:
            meta = row.get("source_meta")
            self.assertIsInstance(meta, dict)
            self.assertTrue(str(meta["url"]).startswith("https://example.com/post-"))
            self.assertEqual(meta["published"], "2026-07-05T00:00:00Z")
            self.assertEqual(meta["type"], "news")
            self.assertTrue(str(meta["source"]).startswith("src_"))

    def test_limit_selects_targets_and_translates_lookahead_too(self) -> None:
        items = [_mk_item(i) for i in range(6)]
        self._run_main(items, limit=4)

        snapshot = self._snapshot()
        self.assertEqual(snapshot["max_items"], 4)
        self.assertEqual(snapshot["source_item_count"], 4)
        self.assertEqual(len(snapshot["target_keys"]), 4)
        self.assertEqual(len(snapshot["items"]), 6)

    def test_budget_exceeded_pauses_and_keeps_the_frozen_snapshot(self) -> None:
        before = self._write_existing_snapshot([{"translation_key": "https://example.com/keep-me", "title": "유지"}])

        with patch.dict(os.environ, {translator.CAP_ENV: "0.0001"}):
            self._run_main([_mk_item(i) for i in range(3)])

        self.assertEqual(self.latest_path.read_text(), before)
        self.assertEqual(self.client.calls, [])
        status = self._status()
        self.assertEqual(status["status"], "budget_paused")
        self.assertEqual(status["reason"], "monthly_cap")
        self.assertEqual(status["resumes_at"], "2026-08-01T00:00:00+00:00")
        self.assertEqual(status["translated_count"], 1)
        self.assertEqual(status["missing_count"], 3)
        self.assertEqual(status["budget"]["monthly_usd_cap"], 0.0001)

    def test_cap_reached_mid_run_pauses_and_still_keeps_the_frozen_snapshot(self) -> None:
        before = self._write_existing_snapshot([{"translation_key": "https://example.com/keep-me", "title": "유지"}])
        # One call costs about $0.003 (the fake client's usage); room for one.
        with patch.dict(os.environ, {translator.CAP_ENV: "0.0045"}):
            self._run_main([_mk_item(i) for i in range(3)])

        self.assertEqual(len(self.client.calls), 1)
        self.assertEqual(self.latest_path.read_text(), before)
        self.assertEqual(self._status()["status"], "budget_paused")
        self.assertGreater(json.loads(self.ledger_path.read_text())["usd"], 0)

    def test_december_pause_resumes_on_january_first(self) -> None:
        self.assertEqual(
            localized._next_month_start(datetime(2026, 12, 31, 23, 0, tzinfo=timezone.utc)).isoformat(),
            "2027-01-01T00:00:00+00:00",
        )

    def test_failed_card_leaves_the_snapshot_incomplete_and_exits_nonzero(self) -> None:
        items = [_mk_item(i) for i in range(3)]
        client = EchoClient(fail_when=lambda fields: fields["title"] == "Title 1")

        with self.assertRaises(SystemExit) as raised:
            self._run_main(items, client=client)

        self.assertEqual(raised.exception.code, 1)
        status = self._status()
        self.assertEqual(status["status"], "incomplete")
        self.assertEqual(status["missing_count"], 1)
        # The other cards were still translated; the bad card is retried once, not dropped silently.
        self.assertEqual(len(client.calls), 4)

    def test_failed_card_does_not_replace_an_existing_complete_snapshot(self) -> None:
        before = self._write_existing_snapshot([])
        client = EchoClient(fail_when=lambda fields: True)

        with self.assertRaises(SystemExit):
            self._run_main([_mk_item(0)], client=client)

        self.assertEqual(self.latest_path.read_text(), before)
        self.assertEqual(self._status()["status"], "incomplete")

    def test_dry_run_calls_nothing_and_writes_nothing(self) -> None:
        argv = ["build_localized_feed.py", "--dry-run"]
        with patch.object(sys, "argv", argv), \
             patch.object(localized, "_fetch_english_feed", return_value={"items": [_mk_item(0)]}):
            localized.main(client=self.client)
        self.assertEqual(self.client.calls, [])
        self.assertFalse(self.latest_path.exists())
        self.assertFalse(self.ledger_path.exists())


if __name__ == "__main__":
    unittest.main()
