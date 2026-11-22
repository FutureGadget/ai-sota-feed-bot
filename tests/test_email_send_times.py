"""Send-time editions: the original 23:00 UTC send and the 11:30 UTC English one."""

from __future__ import annotations

import io
import json
import os
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "pipeline"))

import publish.publish_email as email  # noqa: E402

DAILY_ID = "2026-11-18"
WEEKLY_ID = "2026-W46"
ENV = {"EMAIL_API_KEY": "k", "EMAIL_SEGMENT_ID": "seg-en", "EMAIL_SEGMENT_ID_KO": "seg-ko", "EMAIL_SEGMENT_ID_EN_US": "seg-us"}
THREAD = {"slug": "s", "label": "S", "last_updated": "2026-11-18T10:00:00+00:00", "member_sids": ["a", "b"],
          "latest_title": "T", "item_count": 2, "day_count": 2, "whats_new": "W"}


def _recap(kind: str, ident: str) -> dict:
    return json.loads((ROOT / "data" / kind / f"{ident}.json").read_text(encoding="utf-8"))


def run(argv, state, env=ENV, kind="daily"):
    """Run main() against fixed recaps, not whatever recap is newest in data/."""
    sent = []

    def fake_send(cfg, api_key, subject, body, name="", kind="daily", locale="en", slot="kst"):
        sent.append((locale, slot, email.segment_for(locale, slot)))
        return True

    out = io.StringIO()
    with mock.patch.dict(os.environ, env, clear=False), \
         mock.patch.object(email, "storyline_deltas", return_value=[THREAD]), \
         mock.patch.object(email, "send_broadcast", side_effect=fake_send), \
         mock.patch.object(email, "ensure_reader_id_property", return_value=False), \
         mock.patch.object(email, "load_state", return_value=state), \
         mock.patch.object(email, "_latest_daily", return_value=_recap("daily", DAILY_ID)), \
         mock.patch.object(email, "_latest_weekly", return_value=_recap("weekly", WEEKLY_ID)), \
         mock.patch.object(email, "save_state"), \
         mock.patch.object(sys, "argv", ["publish_email.py", "--kind", kind, *argv]), \
         redirect_stdout(out):
        code = email.main()
    return code, sent, out.getvalue()


class SendTimeTest(unittest.TestCase):
    def test_default_run_is_the_original_send(self):
        state: dict = {}
        code, sent, _ = run([], state)
        self.assertEqual(code, 0)
        self.assertEqual(sent, [("en", "kst", "seg-en"), ("ko", "kst", "seg-ko")])
        self.assertEqual(state["daily"]["last_sent_date"], DAILY_ID)
        self.assertEqual(state["storylines"]["seen_sids"], ["a", "b"])
        self.assertNotIn("daily_en_us", state)

    def test_us_run_sends_only_the_us_segment_with_its_own_cursors(self):
        state = {"daily": {"last_sent_date": DAILY_ID}, "storylines": {"sent_through": "x", "seen_sids": ["z"]}}
        code, sent, _ = run(["--slot", "us"], state)
        self.assertEqual(code, 0)
        self.assertEqual(sent, [("en", "us", "seg-us")])
        self.assertEqual(state["daily_en_us"]["last_sent_date"], DAILY_ID)
        self.assertEqual(state["storylines_en_us"]["seen_sids"], ["a", "b", "z"])
        self.assertEqual(state["storylines"]["seen_sids"], ["z"], "the original cursor is untouched")
        code, sent, out = run(["--slot", "us"], state)
        self.assertEqual(sent, [])
        self.assertIn("slot=us reason=already_sent_recap", out)

    def test_us_run_without_its_segment_sends_nothing(self):
        env = dict(ENV, EMAIL_SEGMENT_ID_EN_US="")
        state: dict = {}
        _, sent, out = run(["--slot", "us"], state, env)
        self.assertEqual(sent, [])
        self.assertIn("slot=us reason=no_segment", out)
        self.assertNotIn("daily_en_us", state)

    def test_korean_has_no_us_edition(self):
        _, sent, out = run(["--slot", "us", "--locale", "ko"], {})
        self.assertEqual(sent, [])
        self.assertIn("reason=no_edition", out)

    def test_weekly_us_keeps_its_own_cursor(self):
        state = {"weekly": {"last_sent_week": "2026-W46", "sent_skill_lab_ids": []}}
        _, sent, _ = run(["--slot", "us"], state, kind="weekly")
        self.assertEqual(sent, [("en", "us", "seg-us")])
        self.assertEqual(state["weekly_en_us"]["last_sent_week"], "2026-W46")
        self.assertEqual(state["weekly"]["last_sent_week"], "2026-W46")

    def test_footer_offers_the_other_send_time_in_english_only(self):
        cfg = email.load_config()
        recap = json.loads((ROOT / "data" / "daily" / f"{DAILY_ID}.json").read_text(encoding="utf-8"))
        with mock.patch.dict(os.environ, ENV):
            _, kst = email.render_daily(cfg, recap, [], "en", "kst")
            _, us = email.render_daily(cfg, recap, [], "en", "us")
            ko_src, _ = email.localized_or_english("daily", recap, DAILY_ID, "ko")
            _, ko = email.render_daily(cfg, ko_src, [], "ko", "kst")
        self.assertIn("/subscribe?lang=en&amp;time=us&amp;", kst)
        self.assertIn("Get it in the US morning instead (11:30 UTC)", kst)
        self.assertIn("/subscribe?lang=en&amp;time=kst&amp;", us)
        self.assertIn("Get it at 8:00 Seoul time instead (23:00 UTC)", us)
        self.assertNotIn("time=us", ko)
        self.assertIn("utm_campaign=daily-2026-11-18-en-us", us)
        self.assertIn('utm_campaign=daily-2026-11-18-en"', kst)
        without = {k: v for k, v in ENV.items() if k != "EMAIL_SEGMENT_ID_EN_US"}
        with mock.patch.dict(os.environ, without, clear=True):
            _, plain = email.render_daily(cfg, recap, [], "en", "kst")
        self.assertNotIn("time=us", plain)

    def test_state_keys(self):
        self.assertEqual(email.edition_state_key("daily", "en", "kst"), "daily")
        self.assertEqual(email.edition_state_key("daily", "ko", "kst"), "daily_ko")
        self.assertEqual(email.edition_state_key("weekly", "en", "us"), "weekly_en_us")


if __name__ == "__main__":
    unittest.main()
