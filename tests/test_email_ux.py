"""Digest email layout: subject, length, feedback, type, dark mode, footer."""

from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

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
        self.assertEqual(subject, "Microsoft agent-framework compromised twice on PyPI · 26 picks, ~13 min")
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


if __name__ == "__main__":
    unittest.main()
