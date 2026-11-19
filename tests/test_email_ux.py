"""Digest email layout: subject, length, feedback, type, dark mode, footer."""

from __future__ import annotations

import json
import os
import re
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "pipeline"))

import publish.publish_email as email  # noqa: E402

DAILY_ID = "2026-11-18"
WEEKLY_ID = "2026-W46"


def load(kind: str, ident: str) -> dict:
    return json.loads((ROOT / "data" / kind / f"{ident}.json").read_text(encoding="utf-8"))


class EmailUxTest(unittest.TestCase):
    def setUp(self):
        self.cfg = email.load_config()
        self.day = load("daily", DAILY_ID)
        self.week = load("weekly", WEEKLY_ID)

    def daily(self, locale="en"):
        source, used = email.localized_or_english("daily", self.day, DAILY_ID, locale)
        return source, email.render_daily(self.cfg, source, [], used)

    def weekly(self, locale="en"):
        source, used = email.localized_or_english("weekly", self.week, WEEKLY_ID, locale)
        return source, email.render_weekly(self.cfg, source, [], [], None, used)

    def test_subjects_lead_with_the_news(self):
        _, (subject, _) = self.daily()
        self.assertRegex(subject, r"^Microsoft agent-framework compromised twice on PyPI · 26 picks, ~\d+ min$")
        _, (subject, _) = self.weekly()
        self.assertEqual(subject, "Claude Fable 5.2 and Gemini 4 Carbon shipped one day apart · Your AI week, Nov 7–13")
        _, (ko_subject, _) = self.weekly("ko")
        self.assertTrue(ko_subject.endswith("· AI 위클리 11월 7–13일"), ko_subject)

    def test_only_the_top_items_per_theme_carry_summaries(self):
        source, (_, body) = self.daily()
        per = self.cfg["daily"]["full_items_per_theme"]
        for cat in source["categories"]:
            arts = cat["articles"]
            for a in arts[:per]:
                if a.get("summary"):
                    self.assertIn(email.html.escape(email.clean(a["summary"], 180)), body)
            for a in arts[per:]:
                self.assertIn(email.html.escape(email.clean(a["title"], 140)), body)
                if a.get("summary"):
                    self.assertNotIn(email.html.escape(email.clean(a["summary"], 180)), body)
        self.assertEqual(body.count("Also in this theme"), sum(len(c["articles"]) > per for c in source["categories"]))

    def test_feedback_rides_the_source_line_for_every_item(self):
        source, (_, body) = self.daily()
        n = sum(len(c["articles"]) for c in source["categories"])
        self.assertEqual(body.count('class="ld-fb'), n)
        self.assertEqual(body.count("fb=useful"), n)
        self.assertNotIn("ld-fb", email.html_to_text(body))
        self.assertNotIn("fb=useful", email.html_to_text(body))

    def test_body_text_is_at_least_15px(self):
        _, (_, body) = self.daily()
        for m in re.finditer(r'<div style="font-size:(\d+)px;line-height:1.5;color:#444', body):
            self.assertGreaterEqual(int(m.group(1)), 15)
        self.assertIn('<ul style="font-size:15px', body)

    def test_dark_mode_is_declared_and_every_colour_has_a_class(self):
        for _, (_, body) in (self.daily(), self.daily("ko"), self.weekly(), self.weekly("ko")):
            self.assertTrue(body.startswith("<!DOCTYPE html>"))
            self.assertIn('<meta name="color-scheme" content="light dark">', body)
            self.assertIn("@media (prefers-color-scheme: dark)", body)
            tags = re.findall(r"<[a-z]+ [^>]*style=\"[^\"]*;color:#(?:111|333|444|888|1a6dd6)[^\"]*\"[^>]*>", body)
            self.assertGreater(len(tags), 5)
            for tag in tags:
                self.assertIn("class=", tag, tag[:120])
            self.assertNotIn("@media", email.html_to_text(body))

    def test_footer_says_why_and_offers_forward_and_preferences(self):
        _, (_, en) = self.daily()
        self.assertIn("You're getting this because you subscribed at llm-digest.com.", en)
        self.assertIn("Manage preferences or unsubscribe", en)
        self.assertIn('href="mailto:?subject=Worth%20a%20read', en)
        _, (_, ko) = self.daily("ko")
        self.assertIn("llm-digest.com에서 구독하셔서 받는 메일입니다.", ko)
        self.assertIn("subscribe%3Flang%3Dko", ko)
        _, (_, wk) = self.weekly()
        self.assertIn("mailto:?subject=", wk)

    def test_header_dates_are_readable(self):
        self.assertEqual(email.header_date("2026-11-18"), "Wed, Nov 18")
        self.assertEqual(email.header_date("2026-11-18", "ko"), "11월 18일 (수)")
        self.assertEqual(email.week_range({"start": "2026-10-30", "end": "2026-11-05"}), "Oct 30–Nov 5")
        _, (_, ko) = self.daily("ko")
        self.assertIn("LLM Digest · 11월 18일 (수)", ko)


    def test_reading_time_counts_only_what_the_email_shows(self):
        self.assertEqual(email.reading_minutes("<p>" + "word " * 460 + "</p>"), 2)
        self.assertEqual(email.reading_minutes("<p>" + "word " * 1150 + "</p>"), 5)
        fb = '<span class="ld-fb"> · <a>👍 Useful</a> · <a>👎 Not relevant</a></span>' * 500
        self.assertEqual(email.reading_minutes(fb), 2)
        _, (en_subject, en) = self.daily()
        _, (ko_subject, _) = self.daily("ko")
        en_min = int(re.search(r"~(\d+) min", en_subject).group(1))
        ko_min = int(re.search(r"약 (\d+)분", ko_subject).group(1))
        self.assertLess(en_min, 13, "the old estimate was half a minute per item")
        self.assertLessEqual(abs(en_min - ko_min), 1)
        self.assertIn(f"~{en_min} min", en)

    def test_every_site_link_names_the_issue_and_section(self):
        for kind, (src, (_, body)) in (("daily", self.daily()), ("weekly", self.weekly())):
            ident = DAILY_ID if kind == "daily" else WEEKLY_ID
            links = [l for l in re.findall(r'href="([^"]+)"', body) if l.startswith(self.cfg["site_base"])]
            self.assertTrue(links)
            for link in links:
                self.assertIn("utm_medium=email", link)
                self.assertTrue(f"utm_campaign={kind}-{ident}-en" in link or "utm_campaign=skill_lab" in link, link)
            contents = {m for l in links for m in re.findall(r"utm_content=(\w+)", l)}
            self.assertTrue({"story", "community", "footer"} <= contents, contents)
        _, (_, daily) = self.daily()
        self.assertIn("utm_content=headline", daily)
        _, (_, ko) = self.daily("ko")
        self.assertIn("utm_campaign=daily-2026-11-18-ko", ko)
        tagged = email.tag_reader_links(self.cfg, daily)
        video = re.findall(r'href="([^"]*#video)"', tagged)
        self.assertTrue(video and "rid=" in video[0].split("#")[0])

    def test_storylines_name_the_newest_story_not_the_cluster_label(self):
        threads = [{
            "slug": "routing-inference", "label": "Routing Inference", "last_updated": "2026-11-18T20:13:18+00:00",
            "latest_title": "How Salesforce routes inference across Regions", "item_count": 4, "day_count": 4,
            "whats_new": "AWS describes cross-Region routing for model serving.",
        }]
        rows = email.render_storyline_rows(self.cfg, threads, "en")
        self.assertIn("How Salesforce routes inference across Regions →", rows)
        self.assertIn("AWS describes cross-Region routing", rows)
        self.assertIn("Storyline · 4 stories over 4 days", rows)
        self.assertNotIn(">Routing Inference", rows)
        _, (_, body) = (None, email.render_daily(self.cfg, self.day, threads))
        self.assertIn("Storylines that moved today", body)
        self.assertNotIn("you've been following", body)

    def test_korean_edition_hides_untranslated_storylines(self):
        english = {"slug": "x", "label": "X", "latest_title": "Title", "item_count": 3, "day_count": 2,
                   "whats_new": "English only.", "localized": True}
        korean = dict(english, slug="y", whats_new="한국어 설명이 있는 스토리.")
        self.assertEqual(email.render_storyline_rows(self.cfg, [english], "ko"), "")
        rows = email.render_storyline_rows(self.cfg, [english, korean], "ko")
        self.assertIn("한국어 설명이 있는 스토리.", rows)
        self.assertIn("스토리 · 2일간 3건", rows)
        source, used = email.localized_or_english("daily", self.day, DAILY_ID, "ko")
        _, body = email.render_daily(self.cfg, source, [english], used)
        self.assertNotIn("오늘 움직인 스토리", body)


    def test_reply_invitation_and_header_follow_email_reply_to(self):
        env = {k: v for k, v in os.environ.items() if k != "EMAIL_REPLY_TO"}
        with mock.patch.dict(os.environ, env, clear=True):
            _, (_, body) = self.daily()
            self.assertNotIn("A person reads every reply", body)
        with mock.patch.dict(os.environ, {"EMAIL_REPLY_TO": "owner@example.com"}):
            _, (_, en) = self.daily()
            _, (_, ko) = self.weekly("ko")
            self.assertIn("A person reads every reply", en)
            self.assertIn("사람이 모든 답장을 읽습니다", ko)
            sent = {}

            class Ok:
                status_code = 200

                def raise_for_status(self):
                    return None

            def fake_post(url, headers=None, json=None, timeout=None):
                sent.update(json)
                return Ok()

            env2 = {"EMAIL_SEGMENT_ID": "seg", "EMAIL_FROM": "LLM Digest <d@example.com>", "EMAIL_REPLY_TO": "owner@example.com"}
            with mock.patch.dict(os.environ, env2), mock.patch.object(email.requests, "post", side_effect=fake_post):
                email.send_broadcast(dict(self.cfg, provider="resend"), "k", "s", "<p>b</p>", "n")
            self.assertEqual(sent["reply_to"], "owner@example.com")


if __name__ == "__main__":
    unittest.main()
