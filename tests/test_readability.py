"""Readability contract for the localized recap and community pages.

Korean pages carry Korean chrome labels and Hangul-friendly typography, and
the agent-written titles stay short enough to read on a phone.
"""

from __future__ import annotations

import copy
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))

import community  # noqa: E402
import recap_i18n  # noqa: E402
import render_static_pages as render  # noqa: E402


class KoreanTypographyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.css = (ROOT / "web" / "site-chrome.css").read_text(encoding="utf-8")

    def test_korean_pages_break_between_words_everywhere(self) -> None:
        block = self.css.split('html[lang="ko"] body {', 1)[1].split("}", 1)[0]
        self.assertIn("word-break: keep-all", block)

    def test_font_tokens_name_hangul_fallbacks(self) -> None:
        for token in ("font-display", "font-sans", "font-mono"):
            value = re.search(rf"--{token}:\s*([^;]+);", self.css).group(1)
            with self.subTest(token=token):
                self.assertIn('"Apple SD Gothic Neo"', value)
                self.assertIn('"Noto Sans KR"', value)
                self.assertIn('"Malgun Gothic"', value)

    def test_recap_pages_share_the_readability_rules(self) -> None:
        for css in (render.DAILY_RECAP_CSS, render.WEEKLY_RECAP_CSS):
            self.assertTrue(css.endswith(render.RECAP_READABLE_CSS))
        self.assertIn('html[lang="ko"] :is(.daily-hero, .weekly-hero) .recap-title', render.RECAP_READABLE_CSS)
        self.assertIn(".toc a { font-family:var(--font-sans)", render.RECAP_READABLE_CSS)
        self.assertIn('html[lang="ko"] :is(.thread-post p, .thread-body p)', community.THREAD_CSS)


class KoreanChromeLabelsTest(unittest.TestCase):
    def test_every_label_has_a_korean_string(self) -> None:
        self.assertEqual(set(render.RECAP_COPY["en"]), set(render.RECAP_COPY["ko"]))

    def test_korean_recap_page_has_no_english_chrome(self) -> None:
        html = (ROOT / "web" / "ko" / "daily" / "2026-11-18.html").read_text(encoding="utf-8")
        for korean in ("AI 데일리 리캡", "끝이 있는 데일리 브리프", "30초 요약", "위에서 아래로 읽고 끝",
                       "이번 호는 여기까지입니다", "데일리 설명 영상 (영어)", "댓글 13개"):
            with self.subTest(label=korean):
                self.assertIn(korean, html)
        for english in ("In 30 seconds", "The finishable daily brief", "read top to bottom",
                        "You are caught up for this edition", "Prefer to watch?", "Built from the AI SOTA feed"):
            with self.subTest(label=english):
                self.assertNotIn(english, html)

    def test_english_recap_page_keeps_english_chrome(self) -> None:
        html = (ROOT / "web" / "daily" / "2026-11-18.html").read_text(encoding="utf-8")
        for english in ("In 30 seconds", "The finishable daily brief", "13 comments"):
            self.assertIn(english, html)
        self.assertNotIn("30초 요약", html)

    def test_dates_and_counts_localize(self) -> None:
        self.assertEqual(render.fmt_long_date("2026-11-18", "ko"), "2026년 11월 18일 수요일")
        self.assertEqual(render.fmt_long_date("2026-11-18"), "Wednesday, Nov 18, 2026")
        recap = {"categories": [{"articles": [{}, {}]}]}
        self.assertEqual(render.meta_line_for(recap, "ko"), "기사 2개 · 카테고리 1개")


class SourceLabelTest(unittest.TestCase):
    def test_source_slugs_render_as_names(self) -> None:
        self.assertEqual(render.gnews_source_badge_label({"source": "hackernews_ai"}), "Hacker News AI")
        self.assertEqual(render.gnews_source_badge_label({"source": "some_new_blog"}), "Some New Blog")


class ReadableLengthTest(unittest.TestCase):
    def test_korean_recap_title_and_highlight_caps(self) -> None:
        source = json.loads((ROOT / "data" / "daily" / "2026-11-18.json").read_text(encoding="utf-8"))
        artifact = json.loads(
            (ROOT / "data" / "i18n" / "ko" / "daily" / "2026-11-18.json").read_text(encoding="utf-8")
        )
        long_title = copy.deepcopy(artifact)
        long_title["title"] = "가" * 41
        self.assertTrue(any("title: over 40" in e for e in recap_i18n.validate(long_title, source, "ko")))
        long_highlight = copy.deepcopy(artifact)
        long_highlight["highlights"][0] = "가" * 101
        self.assertTrue(any("highlights[0]: over 100" in e for e in recap_i18n.validate(long_highlight, source, "ko")))

    def test_community_title_caps(self) -> None:
        post = json.loads((ROOT / "data" / "community" / "daily" / "2026-11-18.json").read_text(encoding="utf-8"))
        recap = community.load_recap("daily", "2026-11-18")
        self.assertEqual(community.validate(post, recap, "daily", "2026-11-18"), [])
        long = copy.deepcopy(post)
        long["threads"]["en"]["title"] = "x" * 91
        long["threads"]["ko"]["title"] = "가" * 46
        errs = community.validate(long, recap, "daily", "2026-11-18")
        self.assertTrue(any("threads.en: title over 90" in e for e in errs))
        self.assertTrue(any("threads.ko: title over 45" in e for e in errs))

    def test_skills_state_the_caps(self) -> None:
        translation = (ROOT / ".agents" / "skills" / "recap-translation" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("40 characters or fewer", translation)
        thread = (ROOT / ".agents" / "skills" / "community-thread" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("90 characters or fewer", thread)
        self.assertIn("45자 이하", thread)


if __name__ == "__main__":
    unittest.main()


class KoreanCommunityVoiceTest(unittest.TestCase):
    """Korean threads are written for the board, not translated from English."""

    def _post(self, line):
        return {"threads": {"ko": {"title": "제목", "body": [line], "comments": []}}}

    def test_literal_translation_is_flagged(self):

        issues = community.style_issues(self._post("덜 불타는 소식\n- 뭔가 나옴"))
        self.assertEqual(len(issues), 1)
        self.assertIn("덜 불타는", issues[0])

    def test_phrase_in_reply_is_flagged(self):

        post = {"threads": {"ko": {"title": "제목", "body": ["본문"], "comments": [
            {"author": "ㅇㅇ", "body": "댓글", "replies": [{"author": "ㅇㅇ", "body": "오늘 거 포장 없이 감"}]}]}}}
        self.assertTrue(community.style_issues(post))

    def test_natural_heading_passes(self):

        self.assertEqual(community.style_issues(self._post("나머지 자잘한 거\n- 뭔가 나옴")), [])

    def test_english_thread_is_not_checked(self):

        post = {"threads": {"en": {"title": "t", "body": ["Less on fire: stuff"], "comments": []}}}
        self.assertEqual(community.style_issues(post), [])

    def test_committed_posts_read_natural(self):

        for path in sorted((ROOT / "data" / "community").glob("*/*.json")):
            post = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(community.style_issues(post), [], path.name)

    def test_skill_lists_literal_phrases(self):

        skill = (ROOT / ".agents" / "skills" / "community-thread" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("영어 스레드를 번역하지 말 것", skill)
        for phrase in ("덜 불타는", "포장 없이"):
            self.assertIn(phrase, skill)
            self.assertIn(phrase, community.KO_LITERAL_PHRASES)
