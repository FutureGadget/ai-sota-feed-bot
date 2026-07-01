from __future__ import annotations

import importlib.util
import shutil
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DAILY_SCRIPTS = ROOT / ".agents" / "skills" / "daily-summary" / "scripts"


def load_daily_common():
    path = DAILY_SCRIPTS / "daily_common.py"
    spec = importlib.util.spec_from_file_location("daily_common_cursor_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class DailyRecapCursorTest(unittest.TestCase):
    """Isolated tests for the target-date cursor: build_daily_input.py's
    automatic mode must advance past confirmed-empty days instead of
    recomputing the same stuck target forever."""

    def setUp(self) -> None:
        self.dc = load_daily_common()
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: shutil.rmtree(self.tmp, ignore_errors=True))
        self.dc.DAILY_DIR = self.tmp
        self.dc.DAILY_STATE_PATH = self.tmp / "state.json"

    def _touch_recap(self, day: str) -> None:
        (self.tmp / f"{day}.json").write_text('{"date": "%s"}' % day, encoding="utf-8")

    def test_bootstraps_to_yesterday_with_no_history(self) -> None:
        target = self.dc.next_target_date(date(2026, 7, 1))
        self.assertEqual(target, date(2026, 6, 30))

    def test_advances_past_latest_published_recap(self) -> None:
        self._touch_recap("2026-06-28")
        target = self.dc.next_target_date(date(2026, 7, 1))
        self.assertEqual(target, date(2026, 6, 29))

    def test_record_skipped_date_advances_past_empty_day(self) -> None:
        self._touch_recap("2026-06-28")
        # 6/29 had zero genuine articles; without recording it, next_target_date
        # would recompute 6/29 forever since no data/daily/2026-06-29.json is
        # ever written.
        self.dc.record_skipped_date("2026-06-29")
        target = self.dc.next_target_date(date(2026, 7, 1))
        self.assertEqual(target, date(2026, 6, 30))

    def test_record_skipped_date_tracks_audit_trail(self) -> None:
        self.dc.record_skipped_date("2026-06-15")
        self.dc.record_skipped_date("2026-06-12")
        state = self.dc.read_state()
        self.assertEqual(state["skipped_dates"], ["2026-06-12", "2026-06-15"])
        self.assertEqual(state["last_checked_date"], "2026-06-15")

    def test_cursor_never_regresses(self) -> None:
        self.dc.record_skipped_date("2026-06-20")
        # A stale/out-of-order call (e.g. a manual backfill checking an older
        # day) must not move last_checked_date backwards.
        self.dc.record_skipped_date("2026-06-10")
        state = self.dc.read_state()
        self.assertEqual(state["last_checked_date"], "2026-06-20")
        self.assertEqual(state["skipped_dates"], ["2026-06-10", "2026-06-20"])

    def test_target_due_when_kst_date_is_one_past_latest_published(self) -> None:
        # 06:00 KST on 2026-07-01 is still 2026-06-30 in UTC. If the latest
        # published recap is 2026-06-30, the target (2026-06-30 + 1 =
        # 2026-07-01) must be due because the KST calendar has already
        # turned over to it, even though the UTC day hasn't.
        self.assertTrue(self.dc.is_target_due(date(2026, 7, 1), date(2026, 7, 1)))

    def test_target_not_due_before_its_kst_date_arrives(self) -> None:
        self.assertFalse(self.dc.is_target_due(date(2026, 7, 2), date(2026, 7, 1)))

    def test_target_due_once_kst_date_has_passed_it(self) -> None:
        self.assertTrue(self.dc.is_target_due(date(2026, 6, 30), date(2026, 7, 1)))


if __name__ == "__main__":
    unittest.main()
