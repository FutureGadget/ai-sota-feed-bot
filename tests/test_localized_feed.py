"""Tests for pipeline/build_localized_feed.py and the translation budget governor.

build_localized_feed.py is designed to run as a script (`import google_translate`
resolves because Python puts the script's own directory on sys.path when it is
executed directly). Mirror that here — matching tests/test_google_translate.py's
convention — by inserting pipeline/ onto sys.path and importing both modules by
their bare names, rather than as `pipeline.build_localized_feed`.
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

import build_localized_feed as localized  # noqa: E402
import google_translate as gt  # noqa: E402


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

    def test_batch_translation_preserves_identity_and_also_covered_urls(self) -> None:
        item = _mk_item(
            1,
            also_covered=[
                {"url": "https://other.example/story", "title": "Other coverage"}
            ],
        )

        with patch(
            "google_translate.translate_texts",
            return_value=["한국어 제목", "한국어 요약", "한국어 이유", "다른 보도"],
        ) as translate:
            translated = localized._translate_items_batch([item], "ko", "test-key")

        translate.assert_called_once_with(
            [item["title"], item["summary_1line"], item["why_it_matters"], "Other coverage"],
            "ko",
            api_key="test-key",
            stats=None,
        )
        self.assertEqual(translated[0]["translation_key"], item["url"])
        self.assertEqual(translated[0]["id"], item["id"])
        self.assertEqual(translated[0]["source_hash"], localized._source_hash(item))
        self.assertEqual(translated[0]["title"], "한국어 제목")
        self.assertEqual(
            translated[0]["also_covered"],
            [{"url": "https://other.example/story", "title": "다른 보도"}],
        )


class LedgerTest(unittest.TestCase):
    def test_month_rollover_resets_chars_used(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "budget.json"
            path.write_text(json.dumps({
                "month": "2026-06",
                "chars_used": 400_000,
                "monthly_cap": 500_000,
                "history": [{"at": "2026-06-15T00:00:00Z", "chars": 100, "run": "r1"}],
            }), encoding="utf-8")

            now = datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc)
            ledger = localized.load_ledger(path, 500_000, now)

            self.assertEqual(ledger["month"], "2026-07")
            self.assertEqual(ledger["chars_used"], 0)
            # History is an audit aid and survives rollover.
            self.assertEqual(len(ledger["history"]), 1)

    def test_month_rollover_uses_pacific_boundary_not_utc(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "budget.json"
            july = {"month": "2026-07", "chars_used": 400_000, "monthly_cap": 500_000, "history": []}

            # Aug 1 05:00 UTC is still Jul 31 22:00 PDT — no rollover yet.
            path.write_text(json.dumps(july), encoding="utf-8")
            before = localized.load_ledger(path, 500_000, datetime(2026, 8, 1, 5, 0, tzinfo=timezone.utc))
            self.assertEqual(before["month"], "2026-07")
            self.assertEqual(before["chars_used"], 400_000)

            # Aug 1 09:00 UTC is Aug 1 02:00 PDT — Google's month has rolled, so ours does too.
            path.write_text(json.dumps(july), encoding="utf-8")
            after = localized.load_ledger(path, 500_000, datetime(2026, 8, 1, 9, 0, tzinfo=timezone.utc))
            self.assertEqual(after["month"], "2026-08")
            self.assertEqual(after["chars_used"], 0)

    def test_load_ledger_missing_file_starts_fresh(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "budget.json"
            now = datetime(2026, 7, 12, tzinfo=timezone.utc)
            ledger = localized.load_ledger(path, 500_000, now)
            self.assertEqual(ledger["month"], "2026-07")
            self.assertEqual(ledger["chars_used"], 0)
            self.assertEqual(ledger["monthly_cap"], 500_000)

    def test_seed_overwrites_current_month_only(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "budget.json"
            path.write_text(json.dumps({"month": "2026-06", "chars_used": 400_000, "monthly_cap": 500_000, "history": []}), encoding="utf-8")

            now = datetime(2026, 7, 12, tzinfo=timezone.utc)
            ledger = localized.load_ledger(path, 500_000, now)
            # Rollover already zeroed the June total before seeding applies.
            self.assertEqual(ledger["chars_used"], 0)

            localized.seed_ledger(ledger, 50_000, "console 2026-07-12", now)
            localized.save_ledger(path, ledger, now)

            reloaded = json.loads(path.read_text())
            self.assertEqual(reloaded["month"], "2026-07")
            self.assertEqual(reloaded["chars_used"], 50_000)
            self.assertEqual(reloaded["seeded_from"], "console 2026-07-12")

    def test_record_usage_accumulates_and_appends_history(self) -> None:
        now = datetime(2026, 7, 12, tzinfo=timezone.utc)
        ledger = {"month": "2026-07", "chars_used": 100, "monthly_cap": 500_000, "history": []}
        localized.record_usage(ledger, 250, "run-1", now)
        self.assertEqual(ledger["chars_used"], 350)
        self.assertEqual(len(ledger["history"]), 1)
        self.assertEqual(ledger["history"][0]["chars"], 250)
        self.assertEqual(ledger["history"][0]["run"], "run-1")

    def test_record_usage_zero_chars_is_a_noop(self) -> None:
        now = datetime(2026, 7, 12, tzinfo=timezone.utc)
        ledger = {"month": "2026-07", "chars_used": 100, "monthly_cap": 500_000, "history": []}
        localized.record_usage(ledger, 0, "run-1", now)
        self.assertEqual(ledger["chars_used"], 100)
        self.assertEqual(ledger["history"], [])

    def test_history_stays_bounded(self) -> None:
        now = datetime(2026, 7, 12, tzinfo=timezone.utc)
        ledger = {"month": "2026-07", "chars_used": 0, "monthly_cap": 500_000, "history": []}
        for i in range(localized.LEDGER_HISTORY_CAP + 25):
            localized.record_usage(ledger, 1, f"run-{i}", now)
        self.assertEqual(len(ledger["history"]), localized.LEDGER_HISTORY_CAP)
        # Oldest entries are dropped, newest kept.
        self.assertEqual(ledger["history"][-1]["run"], f"run-{localized.LEDGER_HISTORY_CAP + 24}")


class MeteringTest(unittest.TestCase):
    """pipeline/google_translate.py Phase 1: input-char metering."""

    def _mock_response(self, translated_texts: list[str]):
        from unittest.mock import MagicMock
        body = {"data": {"translations": [{"translatedText": t} for t in translated_texts]}}
        resp = MagicMock()
        resp.read.return_value = json.dumps(body).encode("utf-8")
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    @patch("google_translate.urllib.request.urlopen")
    def test_metering_counts_input_chars_on_success(self, mock_urlopen) -> None:
        mock_urlopen.return_value = self._mock_response(["안녕"])
        stats: dict = {}
        gt.translate_texts(["hello"], "ko", api_key="test-key", stats=stats)
        # Counts what is actually sent (post html-escape/glossary-wrap), matching
        # the batching loop's own char accounting.
        self.assertEqual(stats["chars_sent"], len("hello"))

    @patch("google_translate.urllib.request.urlopen")
    def test_metering_counts_english_input_not_korean_output(self, mock_urlopen) -> None:
        # Korean output is much longer than the English input; chars_sent must
        # track the input, not the (longer) translated output.
        long_korean_output = "안" * 500
        mock_urlopen.return_value = self._mock_response([long_korean_output])
        stats: dict = {}
        gt.translate_texts(["hi"], "ko", api_key="test-key", stats=stats)
        self.assertEqual(stats["chars_sent"], len("hi"))
        self.assertNotEqual(stats["chars_sent"], len(long_korean_output))

    @patch("google_translate.urllib.request.urlopen")
    def test_metering_no_stats_dict_is_a_noop(self, mock_urlopen) -> None:
        mock_urlopen.return_value = self._mock_response(["안녕"])
        # Should not raise when stats is omitted.
        result = gt.translate_texts(["hello"], "ko", api_key="test-key")
        self.assertEqual(result, ["안녕"])

    @patch("google_translate.urllib.request.urlopen")
    def test_metering_counts_only_successful_batch_not_failed_batch(self, mock_urlopen) -> None:
        # Force one item per batch so two texts become two separate API calls.
        with patch.object(gt, "_BATCH_ITEM_LIMIT", 1):
            first_ok = self._mock_response(["번역1"])
            import io
            from urllib.error import HTTPError
            forbidden_body = json.dumps({
                "error": {"errors": [{"reason": "forbidden", "message": "API key not valid."}]}
            }).encode("utf-8")
            second_fail = HTTPError("https://translation.googleapis.com", 403, "Forbidden", {}, io.BytesIO(forbidden_body))

            mock_urlopen.side_effect = [first_ok, second_fail]
            stats: dict = {}
            with self.assertRaises(ConnectionError):
                gt.translate_texts(["short", "a much longer second string here"], "ko", api_key="test-key", stats=stats)

            # Only the first (successful) batch's chars were billed.
            self.assertEqual(stats["chars_sent"], len("short"))


class GovernorModeTableTest(unittest.TestCase):
    def _ledger(self, chars_used: int, monthly_cap: int) -> dict:
        return {"month": "2026-07", "chars_used": chars_used, "monthly_cap": monthly_cap, "history": []}

    def test_normal_when_on_pace(self) -> None:
        # Day 10 of 31 => ~32% elapsed; spend well under pace.
        now = datetime(2026, 7, 10, 20, 0, tzinfo=timezone.utc)  # 13:00 PDT, Pacific day 10
        ledger = self._ledger(chars_used=100_000, monthly_cap=1_000_000)  # 10% used
        mode, reason, resumes_at = localized.select_mode(ledger, now, {}, True, 6.0)
        self.assertEqual(mode, "normal")
        self.assertIsNone(reason)

    # day=10, days_in_month=31, monthly_cap=620_000: 620_000/31 = 20_000, so
    # both 10/31 and 10/31+0.15 land on exact integer char counts, avoiding
    # float-rounding noise right at the boundary.
    def test_conserve_boundary_exactly_at_pro_rata_is_normal(self) -> None:
        now = datetime(2026, 7, 10, 20, 0, tzinfo=timezone.utc)  # 13:00 PDT, Pacific day 10  # day 10, 31-day month
        ledger = self._ledger(chars_used=200_000, monthly_cap=620_000)  # exactly 10/31
        mode, _, _ = localized.select_mode(ledger, now, {}, True, 6.0)
        self.assertEqual(mode, "normal")

    def test_conserve_just_above_pro_rata(self) -> None:
        now = datetime(2026, 7, 10, 20, 0, tzinfo=timezone.utc)  # 13:00 PDT, Pacific day 10
        ledger = self._ledger(chars_used=200_001, monthly_cap=620_000)
        mode, _, _ = localized.select_mode(ledger, now, {}, True, 6.0)
        self.assertEqual(mode, "conserve")

    def test_economy_boundary_at_plus_15_is_conserve_not_economy(self) -> None:
        # 293_000 is exactly 10/31 + 0.15 of 620_000 in real-number terms, but
        # float division of the two sides can land a hair on either side of
        # that value — so assert just-at-or-under, not bit-exact equality.
        now = datetime(2026, 7, 10, 20, 0, tzinfo=timezone.utc)  # 13:00 PDT, Pacific day 10
        ledger = self._ledger(chars_used=292_999, monthly_cap=620_000)
        mode, _, _ = localized.select_mode(ledger, now, {}, True, 6.0)
        self.assertEqual(mode, "conserve")

    def test_economy_just_above_plus_15(self) -> None:
        now = datetime(2026, 7, 10, 20, 0, tzinfo=timezone.utc)  # 13:00 PDT, Pacific day 10
        ledger = self._ledger(chars_used=293_001, monthly_cap=620_000)
        mode, _, _ = localized.select_mode(ledger, now, {}, True, 6.0)
        self.assertEqual(mode, "economy")

    def test_paused_below_2pct_floor(self) -> None:
        now = datetime(2026, 7, 10, 20, 0, tzinfo=timezone.utc)  # 13:00 PDT, Pacific day 10
        ledger = self._ledger(chars_used=981_000, monthly_cap=1_000_000)  # 1.9% remaining
        mode, reason, resumes_at = localized.select_mode(ledger, now, {}, True, 6.0)
        self.assertEqual(mode, "paused")
        self.assertEqual(reason, "monthly_budget")
        # Pacific midnight Aug 1 (PDT, UTC-7) — Google's billing boundary.
        self.assertEqual(resumes_at, "2026-08-01T07:00:00+00:00")

    def test_not_paused_at_exactly_2pct_remaining(self) -> None:
        now = datetime(2026, 7, 10, 20, 0, tzinfo=timezone.utc)  # 13:00 PDT, Pacific day 10
        ledger = self._ledger(chars_used=980_000, monthly_cap=1_000_000)  # exactly 2% remaining
        mode, _, _ = localized.select_mode(ledger, now, {}, True, 6.0)
        self.assertNotEqual(mode, "paused")

    def test_paused_december_rolls_to_january(self) -> None:
        now = datetime(2026, 12, 15, tzinfo=timezone.utc)
        ledger = self._ledger(chars_used=990_000, monthly_cap=1_000_000)
        mode, reason, resumes_at = localized.select_mode(ledger, now, {}, True, 6.0)
        self.assertEqual(mode, "paused")
        # Pacific midnight Jan 1 (PST, UTC-8).
        self.assertEqual(resumes_at, "2027-01-01T08:00:00+00:00")

    def test_kill_switch_forces_normal_even_when_paused_conditions_hold(self) -> None:
        now = datetime(2026, 7, 10, 20, 0, tzinfo=timezone.utc)  # 13:00 PDT, Pacific day 10
        ledger = self._ledger(chars_used=999_000, monthly_cap=1_000_000)  # would be paused
        mode, reason, resumes_at = localized.select_mode(ledger, now, {}, False, 6.0)
        self.assertEqual(mode, "normal")
        self.assertIsNone(reason)
        self.assertIsNone(resumes_at)

    def test_provider_daily_cap_still_in_effect_carries_over(self) -> None:
        now = datetime(2026, 7, 10, 12, 0, tzinfo=timezone.utc)
        ledger = self._ledger(chars_used=1_000, monthly_cap=1_000_000)
        prev_status = {
            "status": "budget_paused",
            "reason": "provider_daily_cap",
            "resumes_at": (now + timedelta(hours=3)).isoformat(),
        }
        mode, reason, resumes_at = localized.select_mode(ledger, now, prev_status, True, 6.0)
        self.assertEqual(mode, "paused")
        self.assertEqual(reason, "provider_daily_cap")
        self.assertEqual(resumes_at, prev_status["resumes_at"])

    def test_provider_daily_cap_expired_falls_through(self) -> None:
        now = datetime(2026, 7, 10, 12, 0, tzinfo=timezone.utc)
        ledger = self._ledger(chars_used=1_000, monthly_cap=1_000_000)
        prev_status = {
            "status": "budget_paused",
            "reason": "provider_daily_cap",
            "resumes_at": (now - timedelta(hours=1)).isoformat(),
        }
        mode, reason, resumes_at = localized.select_mode(ledger, now, prev_status, True, 6.0)
        self.assertNotEqual(mode, "paused")


class QuotaClassificationTest(unittest.TestCase):
    def _http_error(self, body: dict):
        import io
        from urllib.error import HTTPError
        return HTTPError(
            "https://translation.googleapis.com", 403, "Forbidden", {},
            io.BytesIO(json.dumps(body).encode("utf-8")),
        )

    @patch("google_translate.urllib.request.urlopen")
    def test_daily_limit_exceeded_raises_quota_error(self, mock_urlopen) -> None:
        mock_urlopen.side_effect = self._http_error({
            "error": {"errors": [{"reason": "dailyLimitExceeded", "message": "Daily Limit Exceeded"}]}
        })
        with self.assertRaises(gt.QuotaExceededError) as ctx:
            gt.translate_texts(["hello"], "ko", api_key="test-key")
        self.assertEqual(ctx.exception.reason, "dailyLimitExceeded")

    @patch("google_translate.urllib.request.urlopen")
    def test_rate_limit_exceeded_raises_quota_error(self, mock_urlopen) -> None:
        mock_urlopen.side_effect = self._http_error({
            "error": {"errors": [{"reason": "rateLimitExceeded", "message": "Rate Limit Exceeded"}]}
        })
        with self.assertRaises(gt.QuotaExceededError):
            gt.translate_texts(["hello"], "ko", api_key="test-key")

    @patch("google_translate.urllib.request.urlopen")
    def test_loose_quota_wording_match(self, mock_urlopen) -> None:
        mock_urlopen.side_effect = self._http_error({
            "error": {"errors": [{"reason": "somethingElse", "message": "Monthly quota has been exhausted"}]}
        })
        with self.assertRaises(gt.QuotaExceededError):
            gt.translate_texts(["hello"], "ko", api_key="test-key")

    @patch("google_translate.urllib.request.urlopen")
    def test_bad_api_key_403_is_not_classified_as_quota(self, mock_urlopen) -> None:
        mock_urlopen.side_effect = self._http_error({
            "error": {"errors": [{"reason": "forbidden", "message": "API key not valid. Please pass a valid API key."}]}
        })
        with self.assertRaises(ConnectionError) as ctx:
            gt.translate_texts(["hello"], "ko", api_key="bad-key")
        self.assertNotIsInstance(ctx.exception, gt.QuotaExceededError)

    @patch("google_translate.urllib.request.urlopen")
    def test_malformed_403_body_is_not_classified_as_quota(self, mock_urlopen) -> None:
        mock_urlopen.side_effect = self._http_error(None)  # will serialize as `null`, not a dict
        with self.assertRaises(ConnectionError) as ctx:
            gt.translate_texts(["hello"], "ko", api_key="bad-key")
        self.assertNotIsInstance(ctx.exception, gt.QuotaExceededError)


class BuildLocalizedFeedGovernorIntegrationTest(unittest.TestCase):
    """Exercises pipeline/build_localized_feed.py main() end to end with a temp
    ROOT and mocked English-feed fetch / translation calls."""

    def setUp(self) -> None:
        self._tmpdir = TemporaryDirectory()
        self.tmp_path = Path(self._tmpdir.name)
        self.feed_dir = self.tmp_path / "data" / "i18n" / "ko" / "feed"
        self.feed_dir.mkdir(parents=True)
        self.latest_path = self.feed_dir / "latest.json"
        self.status_path = self.feed_dir / "status.json"
        self.budget_path = self.feed_dir / "budget.json"

        self._root_patch = patch.object(localized, "ROOT", self.tmp_path)
        self._root_patch.start()

        # monthly_cap is env-driven, not persisted (load_ledger recomputes it every
        # run); pin it so a pre-written budget.json's monthly_cap value is honored.
        self._env_patch = patch.dict(os.environ, {
            "GOOGLE_TRANSLATE_API_KEY": "test-key",
            "GOOGLE_TRANSLATE_MONTHLY_CHAR_CAP": "1000000",
        }, clear=False)
        self._env_patch.start()

    def tearDown(self) -> None:
        self._root_patch.stop()
        self._env_patch.stop()
        self._tmpdir.cleanup()

    def _run_main(self, argv: list[str]):
        with patch.object(sys, "argv", ["build_localized_feed.py"] + argv):
            return localized.main()

    def _write_budget(self, month: str, chars_used: int, monthly_cap: int = 1_000_000) -> None:
        self.budget_path.write_text(json.dumps({
            "month": month, "chars_used": chars_used, "monthly_cap": monthly_cap, "history": [],
        }), encoding="utf-8")

    def _write_existing_snapshot(self, source_run_at: str, items: list[dict] | None = None) -> None:
        now = datetime.now(timezone.utc)
        expires = (datetime.fromisoformat(source_run_at.replace("Z", "+00:00")) + timedelta(hours=24)).isoformat()
        snapshot = {
            "locale": "ko", "surface": "feed", "source_run_at": source_run_at,
            "translated_at": now.isoformat(), "expires_at": expires,
            "max_items": 20, "source_item_count": len(items or []),
            "translated_item_count": len(items or []), "is_complete": True,
            "items": items or [],
        }
        self.latest_path.write_text(json.dumps(snapshot, ensure_ascii=False), encoding="utf-8")

    def test_seed_chars_flag_writes_ledger_and_skips_fetch(self) -> None:
        with patch.object(localized, "_fetch_english_feed") as mock_fetch:
            self._run_main(["--locale", "ko", "--seed-chars", "12345", "--seed-note", "console 2026-07-12"])
            mock_fetch.assert_not_called()
        ledger = json.loads(self.budget_path.read_text())
        self.assertEqual(ledger["chars_used"], 12345)
        self.assertEqual(ledger["seeded_from"], "console 2026-07-12")
        self.assertEqual(ledger["month"], datetime.now(timezone.utc).strftime("%Y-%m"))

    def test_paused_mode_skips_fetch_and_preserves_previous_snapshot(self) -> None:
        current_month = datetime.now(timezone.utc).strftime("%Y-%m")
        self._write_budget(current_month, chars_used=999_500, monthly_cap=1_000_000)  # 0.05% remaining
        self._write_existing_snapshot(
            (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
            items=[{"translation_key": "https://example.com/existing", "title": "기존"}],
        )
        before = self.latest_path.read_text()

        with patch.object(localized, "_fetch_english_feed") as mock_fetch:
            self._run_main(["--locale", "ko", "--label", "brief", "--limit", "20"])
            mock_fetch.assert_not_called()

        self.assertEqual(self.latest_path.read_text(), before)  # untouched
        status = json.loads(self.status_path.read_text())
        self.assertEqual(status["status"], "budget_paused")
        self.assertEqual(status["reason"], "monthly_budget")
        self.assertEqual(status["mode"], "paused")
        self.assertEqual(status["budget"]["chars_used"], 999_500)
        self.assertEqual(status["budget"]["monthly_cap"], 1_000_000)
        self.assertEqual(status["budget"]["month"], current_month)

    def test_conserve_mode_skips_translate_call_for_young_snapshot(self) -> None:
        current_month = datetime.now(timezone.utc).strftime("%Y-%m")
        # Over pace but not paused: forces conserve/economy depending on day-of-month math.
        now = datetime.now(timezone.utc)
        days_in_month = 31 if now.month in (1, 3, 5, 7, 8, 10, 12) else 30
        # chars_used just above pro-rata pace -> conserve (not +0.15 over -> not economy)
        chars_used = int((now.day / days_in_month) * 1_000_000) + 1000
        self._write_budget(current_month, chars_used=chars_used, monthly_cap=1_000_000)
        # Existing snapshot is younger than the default 6h conserve window.
        self._write_existing_snapshot((now - timedelta(hours=1)).isoformat())

        with patch.object(localized, "_fetch_english_feed") as mock_fetch, \
             patch("google_translate.translate_texts") as mock_translate:
            self._run_main(["--locale", "ko", "--label", "brief", "--limit", "20"])
            mock_fetch.assert_not_called()
            mock_translate.assert_not_called()

        status = json.loads(self.status_path.read_text())
        self.assertEqual(status["status"], "current")
        self.assertEqual(status["mode"], "conserve")
        self.assertIn("budget", status)

    def test_conserve_mode_translates_when_snapshot_old_enough(self) -> None:
        current_month = datetime.now(timezone.utc).strftime("%Y-%m")
        now = datetime.now(timezone.utc)
        days_in_month = 31 if now.month in (1, 3, 5, 7, 8, 10, 12) else 30
        chars_used = int((now.day / days_in_month) * 1_000_000) + 1000
        self._write_budget(current_month, chars_used=chars_used, monthly_cap=1_000_000)
        # Existing snapshot is older than the 6h conserve window -> must still refresh.
        self._write_existing_snapshot((now - timedelta(hours=10)).isoformat())

        items = [_mk_item(i) for i in range(3)]
        with patch.object(localized, "_fetch_english_feed", return_value={"items": items}), \
             patch("google_translate.translate_texts", return_value=[f"번역{i}" for i in range(9)]) as mock_translate:
            self._run_main(["--locale", "ko", "--label", "brief", "--limit", "20"])
            mock_translate.assert_called()

        status = json.loads(self.status_path.read_text())
        self.assertEqual(status["mode"], "conserve")
        self.assertEqual(status["status"], "current")

    def test_economy_mode_limits_to_10_and_translates_all_fields(self) -> None:
        # Pin the billing clock early enough in the month that economy mode is
        # mathematically reachable without crossing the 2% pause floor. A test
        # based on the real date becomes impossible during the month's last days.
        fixed_now = datetime(2026, 7, 10, 20, 0, tzinfo=timezone.utc)

        class FixedDatetime(datetime):
            @classmethod
            def now(cls, tz=None):
                return fixed_now if tz is None else fixed_now.astimezone(tz)

        current_month = localized._current_month(fixed_now)
        chars_used = 600_000  # > Pacific day 10/31 + 0.15, with 40% remaining
        self._write_budget(current_month, chars_used=chars_used, monthly_cap=1_000_000)
        # No existing snapshot, so the conserve-cadence skip never applies; economy
        # must still translate this run (first run has nothing to preserve).

        items = [_mk_item(i) for i in range(15)]

        def fake_translate(texts, target, source="en", *, api_key=None, stats=None):
            if stats is not None:
                stats["chars_sent"] = stats.get("chars_sent", 0) + sum(len(t) for t in texts)
            return [f"번역-{t}" for t in texts]

        with patch.object(localized, "datetime", FixedDatetime), \
             patch.object(localized, "_fetch_english_feed", return_value={"items": items}), \
             patch("google_translate.translate_texts", side_effect=fake_translate):
            self._run_main(["--locale", "ko", "--label", "brief", "--limit", "20"])

        snapshot = json.loads(self.latest_path.read_text())
        self.assertEqual(snapshot["max_items"], 10)
        self.assertEqual(snapshot["source_item_count"], 10)
        self.assertTrue(snapshot["is_complete"])
        target_items = [it for it in snapshot["items"] if it["translation_key"] in
                         {localized._translation_key(i) for i in items[:10]}]
        self.assertEqual(len(target_items), 10)
        for it in target_items:
            self.assertTrue(str(it["title"]).startswith("번역-"))
            self.assertTrue(str(it["summary_1line"]).startswith("번역-"))
            self.assertTrue(str(it["why_it_matters"]).startswith("번역-"))

        status = json.loads(self.status_path.read_text())
        self.assertEqual(status["mode"], "economy")
        self.assertEqual(status["eligible_count"], 10)

    def test_snapshot_carries_frozen_render_metadata(self) -> None:
        # source_meta + target_keys let the API serve the frozen snapshot as
        # dated Korean cards when the feed is paused/stale.
        current_month = datetime.now(timezone.utc).strftime("%Y-%m")
        self._write_budget(current_month, chars_used=0, monthly_cap=1_000_000)
        items = [_mk_item(i, source=f"src_{i}", type="news") for i in range(5)]

        def fake_translate(texts, target, source="en", *, api_key=None, stats=None):
            if stats is not None:
                stats["chars_sent"] = stats.get("chars_sent", 0) + sum(len(t) for t in texts)
            return [f"번역-{t}" for t in texts]

        with patch.object(localized, "_fetch_english_feed", return_value={"items": items}), \
             patch("google_translate.translate_texts", side_effect=fake_translate):
            self._run_main(["--locale", "ko", "--label", "brief", "--limit", "20"])

        snapshot = json.loads(self.latest_path.read_text())
        self.assertEqual(
            snapshot["target_keys"],
            [localized._translation_key(it) for it in items],
        )
        for row in snapshot["items"]:
            meta = row.get("source_meta")
            self.assertIsInstance(meta, dict)
            self.assertTrue(str(meta["url"]).startswith("https://example.com/post-"))
            self.assertEqual(meta["published"], "2026-07-05T00:00:00Z")
            self.assertEqual(meta["type"], "news")
            self.assertTrue(str(meta["source"]).startswith("src_"))

    def test_quota_exceeded_writes_budget_paused_and_preserves_snapshot(self) -> None:
        current_month = datetime.now(timezone.utc).strftime("%Y-%m")
        self._write_budget(current_month, chars_used=100, monthly_cap=1_000_000)  # nowhere near the floor
        now = datetime.now(timezone.utc)
        self._write_existing_snapshot(
            (now - timedelta(hours=1)).isoformat(),
            items=[{"translation_key": "https://example.com/keep-me", "title": "유지"}],
        )
        before = self.latest_path.read_text()

        items = [_mk_item(i) for i in range(3)]  # all dirty (not cached), forces a translate attempt

        def raise_quota(texts, target, source="en", *, api_key=None, stats=None):
            raise gt.QuotaExceededError("simulated 403", reason="dailyLimitExceeded")

        with patch.object(localized, "_fetch_english_feed", return_value={"items": items}), \
             patch("google_translate.translate_texts", side_effect=raise_quota):
            self._run_main(["--locale", "ko", "--label", "brief", "--limit", "20"])

        self.assertEqual(self.latest_path.read_text(), before)  # previous snapshot preserved
        status = json.loads(self.status_path.read_text())
        self.assertEqual(status["status"], "budget_paused")
        self.assertEqual(status["reason"], "provider_daily_cap")
        self.assertEqual(status["mode"], "paused")
        self.assertIsNotNone(status["resumes_at"])

    def test_quota_exceeded_monthly_reason_wins_when_partial_spend_crosses_floor(self) -> None:
        current_month = datetime.now(timezone.utc).strftime("%Y-%m")
        # Comfortably above the 2% floor before this run's attempt...
        self._write_budget(current_month, chars_used=970_000, monthly_cap=1_000_000)
        items = [_mk_item(i) for i in range(3)]

        def raise_quota_after_partial_spend(texts, target, source="en", *, api_key=None, stats=None):
            # ...but the failing attempt itself meters enough to cross under the floor.
            if stats is not None:
                stats["chars_sent"] = stats.get("chars_sent", 0) + 40_000
            raise gt.QuotaExceededError("simulated 403", reason="dailyLimitExceeded")

        with patch.object(localized, "_fetch_english_feed", return_value={"items": items}), \
             patch("google_translate.translate_texts", side_effect=raise_quota_after_partial_spend):
            self._run_main(["--locale", "ko", "--label", "brief", "--limit", "20"])

        status = json.loads(self.status_path.read_text())
        self.assertEqual(status["status"], "budget_paused")
        self.assertEqual(status["reason"], "monthly_budget")
        ledger = json.loads(self.budget_path.read_text())
        self.assertEqual(ledger["chars_used"], 1_010_000)

    def test_governor_kill_switch_forces_normal_mode_via_env(self) -> None:
        current_month = datetime.now(timezone.utc).strftime("%Y-%m")
        # Would be economy/paused under the ladder, but the kill switch bypasses it.
        self._write_budget(current_month, chars_used=999_000, monthly_cap=1_000_000)
        items = [_mk_item(i) for i in range(3)]

        def fake_translate(texts, target, source="en", *, api_key=None, stats=None):
            if stats is not None:
                stats["chars_sent"] = stats.get("chars_sent", 0) + sum(len(t) for t in texts)
            return [f"번역-{t}" for t in texts]

        with patch.dict(os.environ, {"LOCALIZED_FEED_BUDGET_GOVERNOR": "0"}), \
             patch.object(localized, "_fetch_english_feed", return_value={"items": items}), \
             patch("google_translate.translate_texts", side_effect=fake_translate) as mock_translate:
            self._run_main(["--locale", "ko", "--label", "brief", "--limit", "20"])
            mock_translate.assert_called()  # not paused despite near-floor budget

        status = json.loads(self.status_path.read_text())
        self.assertEqual(status["mode"], "normal")
        # Metering still records even with the ladder bypassed.
        ledger = json.loads(self.budget_path.read_text())
        self.assertGreater(ledger["chars_used"], 999_000)


if __name__ == "__main__":
    unittest.main()
