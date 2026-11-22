"""Tests for pipeline/build_localized_feed.py.

The builder runs as a script, so import it by its bare name with pipeline/ on
sys.path. Translation goes through a fake Anthropic client; no test calls the API.
"""

from __future__ import annotations

import json
import os
import subprocess
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


class FeedParamsTest(unittest.TestCase):
    NOW = datetime(2026, 11, 22, 15, 9, 33, 376000, tzinfo=timezone.utc)  # 00:09 KST on the 23rd

    def test_home_params_are_the_english_home_default_request(self) -> None:
        self.assertEqual(
            localized.home_params(self.NOW),
            {
                "label": "brief",
                "limit": "200",
                "window": "arrival",
                "from": "2026-11-21T15:09:33.376Z",
                "to": "2026-11-22T15:09:33.376Z",
            },
        )

    def test_home_params_match_what_the_home_template_requests_by_default(self) -> None:
        # buildFeedUrl() in ui/templates/index.html, the source of the English
        # and the Korean home alike: drift here means the Korean reader is
        # translated a different set of cards than the home page shows.
        page = (ROOT / "ui" / "templates" / "index.html").read_text(encoding="utf-8")
        self.assertIn("let limitState = '200';", page)
        self.assertIn("const DEFAULT_SECTION_LABELS = ['brief'];", page)
        self.assertIn("u.searchParams.set('window', 'arrival');", page)
        self.assertIn("now.getTime() - 24 * 60 * 60 * 1000", page)

    def test_fetch_hands_the_params_to_the_feed_handler_and_parses_its_json(self) -> None:
        completed = subprocess.CompletedProcess([], 0, stdout='{"items": []}', stderr="")
        with patch.object(localized.subprocess, "run", return_value=completed) as run:
            feed = localized._fetch_english_feed({"label": "brief", "limit": "5"})

        self.assertEqual(feed, {"items": []})
        env = run.call_args.kwargs["env"]
        self.assertEqual(json.loads(env["FEED_PARAMS"]), {"label": "brief", "limit": "5"})
        self.assertEqual(run.call_args.kwargs["cwd"], localized.ROOT)


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

    def test_entry_keeps_hash_model_and_also_covered_urls(self) -> None:
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
        now = datetime(2026, 7, 10, 20, 0, tzinfo=timezone.utc)
        entry = localized._card_entry(item, result, "model-x", now)
        self.assertEqual(
            entry,
            {
                "source_hash": localized._source_hash(item),
                "model": "model-x",
                "translated_at": now.isoformat(),
                "last_seen": now.isoformat(),
                "title": "한국어 제목",
                "summary_1line": "한국어 요약",
                "why_it_matters": "한국어 이유",
                "also_covered": [{"url": "https://other.example/story", "title": "다른 보도"}],
            },
        )

    def test_entry_falls_back_to_english_for_fields_the_model_left_out(self) -> None:
        item = _mk_item(1)
        entry = localized._card_entry(
            item, translator.Result(item["url"], {"title": "한국어 제목"}, 0.0), "m", datetime.now(timezone.utc)
        )
        self.assertEqual(entry["summary_1line"], "Summary 1.")

    def test_unique_keeps_first_seen_order_and_each_key_once(self) -> None:
        a, b, c = _mk_item(1), _mk_item(2), _mk_item(3)
        dup_of_b = _mk_item(2, title="same url, other title")
        self.assertEqual(localized._unique([a, b, dup_of_b, c, a]), [a, b, c])


class BuildLocalizedFeedTest(unittest.TestCase):
    """Runs main() end to end against a temp ROOT, a mocked English-feed fetch,
    and a fake Anthropic client that echoes every field with a Korean prefix."""

    def setUp(self) -> None:
        self._tmpdir = TemporaryDirectory()
        self.tmp_path = Path(self._tmpdir.name)
        self.feed_dir = self.tmp_path / "data" / "i18n" / "ko" / "feed"
        self.feed_dir.mkdir(parents=True)
        self.store_path = self.feed_dir / "cards.json"
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

    def _run_main(self, items: list[dict], *, client=None) -> None:
        """Run the builder. `items` is what the English home's default request returns."""
        self.fetched: list[dict] = []

        def fetch(params):
            self.fetched.append(params)
            return {"items": items, "runs": []}

        with patch.object(sys, "argv", ["build_localized_feed.py", "--locale", "ko"]), \
             patch.object(localized, "_fetch_english_feed", side_effect=fetch):
            localized.main(client=client or self.client)

    def _store(self) -> dict:
        return json.loads(self.store_path.read_text())

    def test_the_run_fetches_only_the_english_home_default(self) -> None:
        self._run_main([_mk_item(0)])
        self.assertEqual(self.fetched, [localized.home_params(self.now)])

    def test_no_snapshot_or_status_file_is_written(self) -> None:
        self._run_main([_mk_item(0)])
        self.assertEqual(sorted(p.name for p in self.feed_dir.iterdir()), ["cards.json"])

    def test_cards_are_translated_in_feed_order_with_all_fields(self) -> None:
        items = [_mk_item(i, also_covered=[{"url": f"https://o.example/{i}", "title": f"Other {i}"}]) for i in range(3)]
        self._run_main(items)

        self.assertEqual([r["title"] for r in self.client.requested], ["Title 0", "Title 1", "Title 2"])
        cards = self._store()["cards"]
        for i, it in enumerate(items):
            card = cards[it["url"]]
            self.assertEqual(card["title"], f"{PREFIX}Title {i}")
            self.assertEqual(card["summary_1line"], f"{PREFIX}Summary {i}.")
            self.assertEqual(card["why_it_matters"], f"{PREFIX}Why it matters {i}.")
            self.assertEqual(card["also_covered"], [{"url": f"https://o.example/{i}", "title": f"{PREFIX}Other {i}"}])

    def test_each_call_is_cached_system_prompt_plus_the_card_and_its_context(self) -> None:
        self._run_main([_mk_item(0, content_excerpt="Body of the post.")])

        (call,) = self.client.calls
        self.assertEqual(call["model"], translator.model_for("feed"))
        self.assertEqual(call["system"][0]["cache_control"], {"type": "ephemeral"})
        self.assertIn("Body of the post.", call["messages"][0]["content"])

    def test_store_has_one_entry_per_card_with_the_documented_shape(self) -> None:
        item = _mk_item(0, also_covered=[{"url": "https://o.example/0", "title": "Other 0"}])
        self._run_main([item])

        store = self._store()
        self.assertEqual(store["locale"], "ko")
        self.assertEqual(store["updated_at"], self.now.isoformat())
        self.assertEqual(list(store["cards"]), [item["url"]])
        self.assertEqual(
            store["cards"][item["url"]],
            {
                "source_hash": localized._source_hash(item),
                "model": translator.model_for("feed"),
                "translated_at": self.now.isoformat(),
                "last_seen": self.now.isoformat(),
                "title": f"{PREFIX}Title 0",
                "summary_1line": f"{PREFIX}Summary 0.",
                "why_it_matters": f"{PREFIX}Why it matters 0.",
                "also_covered": [{"url": "https://o.example/0", "title": f"{PREFIX}Other 0"}],
            },
        )

    def test_a_card_listed_twice_is_translated_once(self) -> None:
        self._run_main([_mk_item(0), _mk_item(1), _mk_item(0)])
        self.assertEqual([r["title"] for r in self.client.requested], ["Title 0", "Title 1"])

    def test_unchanged_cards_are_skipped_and_changed_cards_are_retranslated(self) -> None:
        items = [_mk_item(i) for i in range(3)]
        self._run_main(items)
        self.assertEqual(len(self.client.calls), 3)

        items[1] = _mk_item(1, summary_1line="A rewritten summary.")
        again = EchoClient()
        self._run_main(items, client=again)

        self.assertEqual([r["title"] for r in again.requested], ["Title 1"])
        cards = self._store()["cards"]
        self.assertEqual(cards[items[1]["url"]]["summary_1line"], f"{PREFIX}A rewritten summary.")
        self.assertEqual(cards[items[0]["url"]]["summary_1line"], f"{PREFIX}Summary 0.")

    def test_nothing_dirty_makes_no_call(self) -> None:
        items = [_mk_item(i) for i in range(2)]
        self._run_main(items)
        again = EchoClient()
        self._run_main(items, client=again)
        self.assertEqual(again.calls, [])

    def test_cards_from_another_model_are_retranslated(self) -> None:
        items = [_mk_item(i) for i in range(2)]
        self._run_main(items)
        for entry in self._store()["cards"].values():
            self.assertEqual(entry["model"], translator.model_for("feed"))

        # Make one stored card look like it came from an earlier translator.
        store = self._store()
        store["cards"][items[0]["url"]]["model"] = "an-older-model"
        self.store_path.write_text(json.dumps(store), encoding="utf-8")
        again = EchoClient()
        self._run_main(items, client=again)

        self.assertEqual([r["title"] for r in again.requested], ["Title 0"])
        self.assertEqual(self._store()["cards"][items[0]["url"]]["model"], translator.model_for("feed"))

    def test_a_card_is_reused_across_runs_with_its_translated_at_kept_and_last_seen_bumped(self) -> None:
        items = [_mk_item(0)]
        self._run_main(items)
        later = self.now + timedelta(hours=1)
        with patch.object(localized, "datetime", _fixed_datetime(later)):
            self._run_main(items, client=EchoClient())

        entry = self._store()["cards"][items[0]["url"]]
        self.assertEqual(entry["translated_at"], self.now.isoformat())
        self.assertEqual(entry["last_seen"], later.isoformat())

    def test_entries_unseen_for_fourteen_days_are_pruned(self) -> None:
        def stored(last_seen: datetime) -> dict:
            return {
                "source_hash": "x", "model": "m", "translated_at": last_seen.isoformat(),
                "last_seen": last_seen.isoformat(), "title": "t", "summary_1line": "s",
                "why_it_matters": "w", "also_covered": [],
            }

        self.store_path.write_text(json.dumps({"locale": "ko", "updated_at": "", "cards": {
            "https://example.com/old": stored(self.now - timedelta(days=15)),
            "https://example.com/recent": stored(self.now - timedelta(days=13)),
        }}), encoding="utf-8")
        self._run_main([_mk_item(0)])

        self.assertEqual(
            sorted(self._store()["cards"]),
            ["https://example.com/post-0", "https://example.com/recent"],
        )

    def test_spend_is_recorded_in_the_shared_ledger(self) -> None:
        self._run_main([_mk_item(i) for i in range(2)])

        ledger = json.loads(self.ledger_path.read_text())
        self.assertEqual(ledger["month"], "2026-07")
        self.assertEqual({h["surface"] for h in ledger["history"]}, {"feed"})
        self.assertEqual(len(ledger["history"]), 2)
        self.assertGreater(ledger["usd"], 0)

    def test_cap_already_reached_translates_nothing_and_exits_normally(self) -> None:
        with patch.dict(os.environ, {translator.CAP_ENV: "0.0001"}):
            self._run_main([_mk_item(i) for i in range(3)])

        self.assertEqual(self.client.calls, [])
        self.assertEqual(self._store()["cards"], {})
        self.assertEqual(sorted(p.name for p in self.feed_dir.iterdir()), ["cards.json"])

    def test_cap_reached_mid_run_keeps_the_cards_translated_so_far(self) -> None:
        # One call costs about $0.003 (the fake client's usage); room for one.
        with patch.dict(os.environ, {translator.CAP_ENV: "0.0045"}):
            self._run_main([_mk_item(i) for i in range(3)])

        self.assertEqual(len(self.client.calls), 1)
        self.assertEqual(list(self._store()["cards"]), ["https://example.com/post-0"])
        self.assertGreater(json.loads(self.ledger_path.read_text())["usd"], 0)

    def test_a_failed_card_does_not_stop_the_others(self) -> None:
        items = [_mk_item(i) for i in range(3)]
        client = EchoClient(fail_when=lambda fields: fields["title"] == "Title 1")

        self._run_main(items, client=client)

        self.assertEqual(sorted(self._store()["cards"]), [items[0]["url"], items[2]["url"]])

    def test_one_run_translates_at_most_max_translations_cards(self) -> None:
        with patch.object(localized, "MAX_TRANSLATIONS", 2):
            self._run_main([_mk_item(i) for i in range(6)])
        self.assertEqual(len(self.client.calls), 2)
        self.assertEqual(len(self._store()["cards"]), 2)

    def test_dry_run_calls_nothing_and_writes_nothing(self) -> None:
        with patch.object(sys, "argv", ["build_localized_feed.py", "--dry-run"]), \
             patch.object(localized, "_fetch_english_feed", return_value={"items": [_mk_item(0)]}):
            localized.main(client=self.client)
        self.assertEqual(self.client.calls, [])
        self.assertFalse(self.store_path.exists())
        self.assertFalse(self.ledger_path.exists())


if __name__ == "__main__":
    unittest.main()
