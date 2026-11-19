from __future__ import annotations

import copy
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
import recap_i18n  # noqa: E402
import render_static_pages as render  # noqa: E402

DAILY_ID = "2026-11-18"
WEEKLY_ID = "2026-W46"


class RecapHashTest(unittest.TestCase):
    def test_video_does_not_change_the_hash(self):
        recap = {"date": "2026-01-02", "title": "t", "categories": []}
        with_video = dict(recap, video={"youtube_id": "abcdefghijk"})
        self.assertEqual(render.i18n_source_hash(recap), render.i18n_source_hash(with_video))
        self.assertTrue(render.i18n_hash_matches(render.i18n_source_hash(recap), with_video))

    def test_legacy_full_hash_stays_fresh(self):
        recap = {"date": "2026-01-02", "title": "t", "video": {"youtube_id": "abcdefghijk"}}
        legacy = render._i18n_hash_payload(recap)
        self.assertTrue(render.i18n_hash_matches(legacy, recap))
        self.assertFalse(render.i18n_hash_matches(legacy, dict(recap, title="changed")))


class RecapTranslationTest(unittest.TestCase):
    def setUp(self):
        self.source = json.loads((ROOT / "data" / "daily" / f"{DAILY_ID}.json").read_text(encoding="utf-8"))

    def test_committed_korean_recaps_are_valid_and_fresh(self):
        self.assertEqual(recap_i18n.check("daily", DAILY_ID, "ko"), [])
        self.assertEqual(recap_i18n.check("weekly", WEEKLY_ID, "ko"), [])

    def test_untranslated_or_reordered_input_is_rejected(self):
        skel = recap_i18n.skeleton(self.source)
        errs = recap_i18n.validate(skel, self.source, "ko")
        self.assertTrue(any("not translated" in e for e in errs))
        artifact = json.loads((ROOT / "data" / "i18n" / "ko" / "daily" / f"{DAILY_ID}.json").read_text(encoding="utf-8"))
        moved = copy.deepcopy(artifact)
        moved["categories"][0]["articles"].reverse()
        self.assertTrue(any(".url: must stay" in e for e in recap_i18n.validate(moved, self.source, "ko")))
        dropped = copy.deepcopy(artifact)
        dropped["categories"].pop()
        self.assertTrue(any("categories: expected" in e for e in recap_i18n.validate(dropped, self.source, "ko")))

    def test_load_localized_overlays_korean_text(self):
        recap = recap_i18n.load_localized("daily", DAILY_ID, "ko")
        self.assertIsNotNone(recap)
        self.assertIn("AI 데일리", recap["title"])
        self.assertEqual(recap["categories"][0]["articles"][0]["url"], self.source["categories"][0]["articles"][0]["url"])
        self.assertIsNone(recap_i18n.load_localized("daily", "1999-01-01", "ko"))

    def test_google_translate_skips_agent_translated_recaps(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        import translate

        self.assertEqual(translate.AGENT_TRANSLATED_SURFACES, {"daily", "weekly"})


class KoreanEmailTest(unittest.TestCase):
    def setUp(self):
        self.cfg = email.load_config()
        self.recap = json.loads((ROOT / "data" / "daily" / f"{DAILY_ID}.json").read_text(encoding="utf-8"))

    def test_korean_daily_uses_translation_labels_and_korean_links(self):
        source, used = email.localized_or_english("daily", self.recap, DAILY_ID, "ko")
        self.assertEqual(used, "ko")
        subject, body = email.render_daily(self.cfg, source, [], used)
        first = source["categories"][0]["articles"][0]["title"]
        self.assertTrue(subject.startswith(first[:12]), subject)
        self.assertRegex(subject, r" · \d+개, 약 \d+분$")
        self.assertIn("30초 요약", body)
        self.assertIn("오늘 브리프는 여기까지입니다", body)
        self.assertIn(f"/ko/daily/{DAILY_ID}?utm_source=", body)
        self.assertIn(f"/ko/community/daily/{DAILY_ID}?utm_source=", body)
        self.assertIn("커뮤니티에서", body)
        self.assertNotIn("In 30 seconds", body)

    def test_english_daily_is_unchanged_by_locale_support(self):
        subject, body = email.render_daily(self.cfg, self.recap, [])
        first = self.recap["categories"][0]["articles"][0]["title"]
        self.assertTrue(subject.startswith(first[:12]), subject)
        self.assertRegex(subject, r" · \d+ picks, ~\d+ min$")
        self.assertIn("In 30 seconds", body)
        self.assertIn(f"/daily/{DAILY_ID}?utm_source=", body)
        self.assertNotIn("/ko/", body)

    def test_missing_translation_falls_back_to_english(self):
        with mock.patch.object(email.recap_i18n, "load_localized", return_value=None):
            source, used = email.localized_or_english("daily", self.recap, DAILY_ID, "ko")
        self.assertEqual(used, "en")
        self.assertIs(source, self.recap)

    def test_korean_weekly_renders(self):
        wk = json.loads((ROOT / "data" / "weekly" / f"{WEEKLY_ID}.json").read_text(encoding="utf-8"))
        source, used = email.localized_or_english("weekly", wk, WEEKLY_ID, "ko")
        subject, body = email.render_weekly(self.cfg, source, [], [], None, used)
        self.assertIn("AI 위클리", subject)
        self.assertIn("이번 주 핵심", body)
        self.assertIn(f"/ko/weekly/{WEEKLY_ID}?utm_source=", body)

    def test_send_targets_each_segment_and_keeps_separate_cursors(self):
        built = ("subject", "<p>body</p>", [], DAILY_ID)
        sent = []

        def fake_send(cfg, api_key, subject, body, name="", kind="daily", locale="en", slot="kst"):
            sent.append(locale)
            return True

        state: dict = {}
        env = {"EMAIL_API_KEY": "k", "EMAIL_SEGMENT_ID": "seg-en", "EMAIL_SEGMENT_ID_KO": "seg-ko"}
        with mock.patch.dict(os.environ, env), \
             mock.patch.object(email, "build_daily", return_value=built), \
             mock.patch.object(email, "send_broadcast", side_effect=fake_send), \
             mock.patch.object(email, "ensure_reader_id_property", return_value=False), \
             mock.patch.object(email, "load_state", return_value=state), \
             mock.patch.object(email, "save_state"), \
             mock.patch.object(sys, "argv", ["publish_email.py", "--kind", "daily"]), \
             redirect_stdout(io.StringIO()):
            self.assertEqual(email.main(), 0)
        self.assertEqual(sent, ["en", "ko"])
        self.assertEqual(state["daily"]["last_sent_date"], DAILY_ID)
        self.assertEqual(state["daily_ko"]["last_sent_date"], DAILY_ID)

    def test_korean_send_skips_without_segment_and_failure_keeps_english_cursor(self):
        built = ("subject", "<p>body</p>", [], DAILY_ID)
        state: dict = {}
        env = {"EMAIL_API_KEY": "k", "EMAIL_SEGMENT_ID": "seg-en", "EMAIL_SEGMENT_ID_KO": ""}
        out = io.StringIO()
        with mock.patch.dict(os.environ, env), \
             mock.patch.object(email, "build_daily", return_value=built), \
             mock.patch.object(email, "send_broadcast", return_value=True), \
             mock.patch.object(email, "ensure_reader_id_property", return_value=False), \
             mock.patch.object(email, "load_state", return_value=state), \
             mock.patch.object(email, "save_state"), \
             mock.patch.object(sys, "argv", ["publish_email.py", "--kind", "daily"]), \
             redirect_stdout(out):
            self.assertEqual(email.main(), 0)
        self.assertIn("locale=ko slot=kst reason=no_segment", out.getvalue())
        self.assertNotIn("daily_ko", state)

        def ko_fails(cfg, api_key, subject, body, name="", kind="daily", locale="en", slot="kst"):
            if locale == "ko":
                raise RuntimeError("boom")
            return True

        state = {}
        env["EMAIL_SEGMENT_ID_KO"] = "seg-ko"
        with mock.patch.dict(os.environ, env), \
             mock.patch.object(email, "build_daily", return_value=built), \
             mock.patch.object(email, "send_broadcast", side_effect=ko_fails), \
             mock.patch.object(email, "ensure_reader_id_property", return_value=False), \
             mock.patch.object(email, "load_state", return_value=state), \
             mock.patch.object(email, "save_state"), \
             mock.patch.object(sys, "argv", ["publish_email.py", "--kind", "daily"]), \
             redirect_stdout(io.StringIO()):
            self.assertEqual(email.main(), 1)
        self.assertEqual(state["daily"]["last_sent_date"], DAILY_ID)
        self.assertNotIn("daily_ko", state)


class LanguageSwitchTest(unittest.TestCase):
    def setUp(self):
        self.cfg = email.load_config()
        self.recap = json.loads((ROOT / "data" / "daily" / f"{DAILY_ID}.json").read_text(encoding="utf-8"))
        self.week = json.loads((ROOT / "data" / "weekly" / f"{WEEKLY_ID}.json").read_text(encoding="utf-8"))

    def test_each_edition_links_to_the_other(self):
        with mock.patch.dict(os.environ, {"EMAIL_SEGMENT_ID_KO": "seg-ko"}):
            _, en_daily = email.render_daily(self.cfg, self.recap, [])
            ko_source, _ = email.localized_or_english("daily", self.recap, DAILY_ID, "ko")
            _, ko_daily = email.render_daily(self.cfg, ko_source, [], "ko")
            _, en_weekly = email.render_weekly(self.cfg, self.week, [], [], None)
            ko_week, _ = email.localized_or_english("weekly", self.week, WEEKLY_ID, "ko")
            _, ko_weekly = email.render_weekly(self.cfg, ko_week, [], [], None, "ko")
        for body in (en_daily, en_weekly):
            self.assertIn("/subscribe?lang=ko&amp;utm_source=", body)
            self.assertIn("이 메일을 한국어로 받기", body)
        for body in (ko_daily, ko_weekly):
            self.assertIn("/subscribe?lang=en&amp;utm_source=", body)
            self.assertIn("Get this email in English", body)

    def test_no_switch_link_without_a_korean_edition(self):
        env = {k: v for k, v in os.environ.items() if k != "EMAIL_SEGMENT_ID_KO"}
        with mock.patch.dict(os.environ, env, clear=True):
            _, body = email.render_daily(self.cfg, self.recap, [])
        self.assertNotIn("/subscribe?lang=", body)

    def test_signup_page_explains_switching(self):
        page = (ROOT / "web" / "subscribe.html").read_text(encoding="utf-8")
        self.assertIn("Already subscribed?", page)


class KoreanEmailLineBreakTest(unittest.TestCase):
    def setUp(self):
        self.cfg = email.load_config()
        self.recap = json.loads((ROOT / "data" / "daily" / f"{DAILY_ID}.json").read_text(encoding="utf-8"))
        self.week = json.loads((ROOT / "data" / "weekly" / f"{WEEKLY_ID}.json").read_text(encoding="utf-8"))

    def test_korean_editions_break_between_words(self):
        ko_day, _ = email.localized_or_english("daily", self.recap, DAILY_ID, "ko")
        ko_week, _ = email.localized_or_english("weekly", self.week, WEEKLY_ID, "ko")
        for _, body in (
            email.render_daily(self.cfg, ko_day, [], "ko"),
            email.render_weekly(self.cfg, ko_week, [], [], None, "ko"),
        ):
            self.assertIn('lang="ko"', body)
            self.assertIn("word-break:keep-all", body)
            self.assertIn("Apple SD Gothic Neo", body)

    def test_english_editions_keep_default_breaking(self):
        for _, body in (
            email.render_daily(self.cfg, self.recap, []),
            email.render_weekly(self.cfg, self.week, [], [], None),
        ):
            self.assertNotIn("keep-all", body)
            self.assertIn("max-width:640px", body)


class RecapSkillWiringTest(unittest.TestCase):
    def test_recap_skills_write_korean_before_the_index_rebuild(self):
        for kind in ("daily", "weekly"):
            skill = (ROOT / ".agents" / "skills" / f"{kind}-summary" / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn(".agents/skills/recap-translation/SKILL.md", skill)
            self.assertLess(skill.index("recap-translation"), skill.index("Validate + rebuild the index"))
            routine = (ROOT / ".agents" / "routines" / f"{kind}-recap" / "prompt.md").read_text(encoding="utf-8")
            self.assertIn(f"data/i18n/ko/{kind}/", routine)

    def test_korean_pages_link_signup_with_korean_locale(self):
        html = render.render_page(
            title="t", description="d", canonical="https://x/ko/daily/1", published=None, h1="h",
            meta_line="m", json_href="", archive="", recap_title="r", recap_range="", intro_html="",
            body_html='<a href="/subscribe">s</a>', lang="ko",
        )
        self.assertIn('href="/subscribe?lang=ko"', html)
        self.assertNotIn('href="/subscribe"', html)


if __name__ == "__main__":
    unittest.main()


class CommunityPositionTest(unittest.TestCase):
    def setUp(self):
        self.cfg = email.load_config()

    def test_daily_community_card_sits_between_intro_and_themes(self):
        recap = json.loads((ROOT / "data" / "daily" / f"{DAILY_ID}.json").read_text(encoding="utf-8"))
        for locale in ("en", "ko"):
            source, used = email.localized_or_english("daily", recap, DAILY_ID, locale)
            _, body = email.render_daily(self.cfg, source, [], used)
            card = body.index("border-left:4px solid #1a6dd6")
            first_theme = email.html.escape(source["categories"][0]["name"])
            self.assertLess(body.index(email._t(used, "tldr")), card)
            self.assertLess(card, body.index(first_theme))

    def test_weekly_community_card_follows_the_highlights(self):
        wk = json.loads((ROOT / "data" / "weekly" / f"{WEEKLY_ID}.json").read_text(encoding="utf-8"))
        for locale in ("en", "ko"):
            source, used = email.localized_or_english("weekly", wk, WEEKLY_ID, locale)
            _, body = email.render_weekly(self.cfg, source, [], [], None, used)
            card = body.index("border-left:4px solid #1a6dd6")
            self.assertLess(body.index(email._t(used, "weekly_highlights")), card)
            self.assertLess(card, body.index(email._t(used, "by_theme")))
