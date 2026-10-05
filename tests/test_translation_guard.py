"""Spend guard: reserve-before-send, fail-closed, pacing, and refund rules."""

from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))

import google_translate as gt  # noqa: E402
import translation_guard as tg  # noqa: E402

NOON = datetime(2026, 10, 4, 19, 0, tzinfo=timezone.utc)  # 12:00 PT, Oct 4


class FakeResp:
    def __init__(self, n: int):
        self._n = n

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        return json.dumps({"data": {"translations": [{"translatedText": "x"}] * self._n}}).encode()


def http_error(code: int, body: str = "{}") -> urllib.error.HTTPError:
    return urllib.error.HTTPError("u", code, "e", {}, io.BytesIO(body.encode()))


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "spend_guard.json"
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(gt.set_spend_guard, None)

    def guard(self, **kw):
        kw.setdefault("daily_cap", 1000)
        kw.setdefault("monthly_cap", 5000)
        kw.setdefault("max_chars_per_minute", 0)
        return tg.SpendGuard(self.path, now=lambda: NOON, **kw)

    def state(self):
        return json.loads(self.path.read_text())

    def test_reserve_charges_and_refuses_over_daily_cap(self):
        g = self.guard()
        g.reserve(600)
        with self.assertRaises(gt.SpendLimitError) as ctx:
            g.reserve(500)
        self.assertEqual(ctx.exception.reason, "spend_guard_daily")
        self.assertEqual(self.state()["day_chars"], 600)  # refused request charged nothing

    def test_monthly_ceiling(self):
        g = self.guard(daily_cap=10_000, monthly_cap=1500)
        g.reserve(1000)
        with self.assertRaises(gt.SpendLimitError) as ctx:
            g.reserve(600)
        self.assertEqual(ctx.exception.reason, "spend_guard_monthly")

    def test_day_and_month_roll_over_on_pacific_clock(self):
        self.path.write_text(json.dumps({"month": "2026-09", "month_chars": 440000, "day": "2026-10-03", "day_chars": 999}))
        g = self.guard(daily_cap=1000, monthly_cap=450000)
        g.reserve(900)  # new month and new day: both counters reset
        self.assertEqual(self.state()["month_chars"], 900)
        self.assertEqual(self.state()["day_chars"], 900)

    def test_corrupt_ledger_fails_closed(self):
        self.path.write_text("{not json")
        with self.assertRaises(gt.SpendLimitError) as ctx:
            self.guard().reserve(10)
        self.assertEqual(ctx.exception.reason, "spend_guard_unreadable")

    def test_pacer_sleeps_between_requests_but_lets_a_lone_oversize_through(self):
        clock = {"t": 0.0}
        slept: list[float] = []

        def sleep(s):
            slept.append(s)
            clock["t"] += s

        g = self.guard(daily_cap=100_000, monthly_cap=100_000, max_chars_per_minute=1000,
                       monotonic=lambda: clock["t"], sleep=sleep)
        g.reserve(5000)  # empty window: allowed even though it exceeds the per-minute cap
        self.assertEqual(slept, [])
        g.reserve(500)  # must wait for the window to clear
        self.assertTrue(slept and sum(slept) >= 59.9)

    def test_api_call_reserves_before_send_and_blocks_when_exhausted(self):
        g = self.guard(daily_cap=100)
        gt.set_spend_guard(g)
        with patch("urllib.request.urlopen") as urlopen:
            with self.assertRaises(gt.SpendLimitError):
                gt._call_api(["x" * 200], "ko", "en", "k")
            urlopen.assert_not_called()  # never sent

    def test_success_keeps_charge(self):
        gt.set_spend_guard(self.guard())
        with patch("urllib.request.urlopen", return_value=FakeResp(1)):
            gt._call_api(["hello"], "ko", "en", "k")
        self.assertEqual(self.state()["day_chars"], 5)

    def test_rejected_4xx_is_refunded_but_5xx_and_timeouts_stay_charged(self):
        gt.set_spend_guard(self.guard())
        with patch("urllib.request.urlopen", side_effect=http_error(400)):
            with self.assertRaises(ConnectionError):
                gt._call_api(["hello"], "ko", "en", "k")
        self.assertEqual(self.state()["day_chars"], 0)

        with patch("urllib.request.urlopen", side_effect=[http_error(503), FakeResp(1)]), patch("time.sleep"):
            gt._call_api(["hello"], "ko", "en", "k")
        self.assertEqual(self.state()["day_chars"], 10)  # failed attempt + retry both charged

        with patch("urllib.request.urlopen", side_effect=TimeoutError("t")):
            with self.assertRaises(ConnectionError):
                gt._call_api(["hello"], "ko", "en", "k")
        self.assertEqual(self.state()["day_chars"], 15)  # timeout may have been billed

    def test_google_daily_quota_403_trips_the_day_shut(self):
        gt.set_spend_guard(self.guard())
        body = json.dumps({"error": {"errors": [{"reason": "dailyLimitExceeded"}]}})
        with patch("urllib.request.urlopen", side_effect=http_error(403, body)):
            with self.assertRaises(gt.QuotaExceededError):
                gt._call_api(["hello"], "ko", "en", "k")
        self.assertEqual(self.state()["day_chars"], 1000)
        with self.assertRaises(gt.SpendLimitError):
            self.guard().reserve(1)

    def test_per_minute_rate_limit_does_not_trip_the_day(self):
        gt.set_spend_guard(self.guard())
        body = json.dumps({"error": {"errors": [{"reason": "userRateLimitExceeded"}]}})
        with patch("urllib.request.urlopen", side_effect=http_error(403, body)):
            with self.assertRaises(gt.QuotaExceededError):
                gt._call_api(["hello"], "ko", "en", "k")
        self.assertEqual(self.state()["day_chars"], 0)

    def test_install_default_respects_kill_switch(self):
        with patch.dict("os.environ", {"GOOGLE_TRANSLATE_GUARD": "0"}):
            self.assertIsNone(tg.install_default(self.path))
        self.assertIsNone(gt.get_spend_guard())
        with patch.dict("os.environ", {"GOOGLE_TRANSLATE_GUARD": "1"}):
            self.assertIsNotNone(tg.install_default(self.path))


if __name__ == "__main__":
    unittest.main()
