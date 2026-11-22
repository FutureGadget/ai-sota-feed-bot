"""The home page is one UI in every language.

Each language's page is built from the same template, so Korean readers get the
English home's sections and features with Korean text. These tests check what
a reader or a crawler sees in the committed pages: the language declarations,
that the pages differ only in text, and that every link into a localized page
reaches a page that exists.
"""

from __future__ import annotations

import json
import re
import unittest
from datetime import date, datetime, timezone

from pipeline import locales, render_home
from pipeline import render_static_pages as render
from tests.test_i18n_static_pages import route_target

DEFAULT = locales.DEFAULT
KO = "ko"
HANGUL = re.compile(r"[가-힣]")


def page(code: str) -> str:
    return render_home.output_path(code).read_text(encoding="utf-8")


def without_seed(html: str) -> str:
    region = render_home.seed_region(html)
    return html.replace(region, "") if region else html


def window_ui(html: str) -> dict:
    match = re.search(r"window\.UI = (\{.*?\n    \});", html, re.S)
    assert match, "page embeds window.UI"
    return json.loads(match.group(1))


class LanguageDeclarationTest(unittest.TestCase):
    def test_each_page_declares_its_language_canonical_and_alternates(self) -> None:
        for code in locales.LOCALES:
            with self.subTest(code=code):
                html = page(code)
                self.assertIn(f'<html lang="{code}">', html)
                self.assertIn(f'<link rel="canonical" href="{render_home.page_url(code)}" />', html)
                for other in locales.LOCALES:
                    self.assertIn(f'hreflang="{other}" href="{render_home.page_url(other)}"', html)
                self.assertIn(f'hreflang="x-default" href="{render_home.page_url(DEFAULT)}"', html)

    def test_each_page_links_to_the_other_languages_home(self) -> None:
        for code in locales.LOCALES:
            for other in locales.others(code):
                with self.subTest(code=code, other=other):
                    self.assertIn(
                        f'href="{locales.get(other).path_prefix}/" data-language-link data-language-locale="{other}"',
                        page(code),
                    )

    def test_each_page_tells_its_scripts_the_locale(self) -> None:
        for code in locales.LOCALES:
            with self.subTest(code=code):
                ui = window_ui(page(code))
                self.assertEqual(ui["locale"], code)
                self.assertEqual(ui["defaultLocale"], DEFAULT)


class SameUiTest(unittest.TestCase):
    """Korean is the English home with Korean text, not a second page."""

    def test_pages_have_the_same_sections_and_the_same_assets(self) -> None:
        english = without_seed(page(DEFAULT))
        korean = without_seed(page(KO))
        for pattern in (
            r'\sid="([^"]+)"',
            r'<script[^>]*\ssrc="([^"?]+)',
            r'<link[^>]*rel="stylesheet"[^>]*href="([^"?]+)',
        ):
            self.assertEqual(sorted(re.findall(pattern, korean)), sorted(re.findall(pattern, english)), pattern)

    def test_korean_page_keeps_analytics(self) -> None:
        self.assertIn("posthog", page(KO).lower())

    def test_korean_page_text_is_korean(self) -> None:
        html = page(KO)
        title = re.search(r"<title>(.*?)</title>", html).group(1)
        self.assertRegex(title, HANGUL)
        heading = re.search(r"<h1[^>]*>(.*?)</h1>", without_seed(html), re.S).group(1)
        self.assertRegex(heading, HANGUL)
        self.assertNotRegex(re.search(r"<title>(.*?)</title>", page(DEFAULT)).group(1), HANGUL)

    def test_korean_page_embeds_korean_strings_for_its_scripts(self) -> None:
        strings = window_ui(page(KO))["strings"]
        self.assertTrue(strings)
        for key, value in strings.items():
            with self.subTest(key=key):
                self.assertEqual(value, locales.ui(KO)[key])

    def test_the_default_page_embeds_no_links(self) -> None:
        self.assertEqual(window_ui(page(DEFAULT))["links"], {})


class LocalizedLinksTest(unittest.TestCase):
    def test_every_localized_link_has_a_route_and_a_file(self) -> None:
        links = window_ui(page(KO))["links"]
        self.assertEqual(links["/"], "/ko/")
        for english, localized in links.items():
            with self.subTest(path=english):
                target = route_target(localized.split("?", 1)[0])
                self.assertIsNotNone(target, f"{localized} has no worker route, so it would 404")
                if target.startswith("/web/") and "${" not in target:
                    self.assertTrue((render_home.ROOT / target.lstrip("/")).is_file(), target)

    def test_a_page_with_no_localized_version_keeps_its_english_path(self) -> None:
        for path in ("/models", "/playbook/2026-11-20", "/skills"):
            with self.subTest(path=path):
                self.assertEqual(render_home.localize(KO, path), path)

    def test_a_story_is_localized_only_when_its_page_exists(self) -> None:
        story = next((render_home.WEB_DIR / "ko" / "story").glob("*.html"))
        self.assertEqual(render_home.localize(KO, f"/story/{story.stem}"), f"/ko/story/{story.stem}")
        self.assertEqual(render_home.localize(KO, "/story/0000000000000000"), "/story/0000000000000000")
        self.assertEqual(render_home.localize(DEFAULT, f"/story/{story.stem}"), f"/story/{story.stem}")

    def test_every_ko_link_in_the_page_has_a_route(self) -> None:
        html = page(KO)
        for href in sorted(set(re.findall(r'href="(/ko/[^"?#]*)', html))):
            with self.subTest(href=href):
                self.assertIsNotNone(route_target(href), f"{href} has no worker route")


class SeedLanguageTest(unittest.TestCase):
    def test_seed_heading_follows_the_languages_date_patterns(self) -> None:
        one, two = date(2026, 8, 20), date(2026, 8, 22)
        stamp = datetime(2026, 8, 22, 9, 5, tzinfo=timezone.utc)
        self.assertEqual(render._seed_heading([one, two], None, KO), "주요 시그널 · 2026년 8월 20일–8월 22일")
        self.assertEqual(
            render._seed_heading([one], stamp, KO), "주요 시그널 · 2026년 8월 20일 · 8월 22일 09:05 UTC 업데이트"
        )
        self.assertEqual(render._seed_heading([], None, KO), "주요 시그널")

    def test_ranking_line_uses_the_languages_words(self) -> None:
        item = {"matched_topics": ["agent"], "slot": "research_watch", "time_decay_factor": 0.5, "final_score": 2}
        self.assertEqual(render._ranked_because(item, KO), "랭킹 근거: agent 일치 · 연구 동향 · 신선도 0.50 · 점수 2.00")
        self.assertEqual(render._ranked_because(item), "Ranked: agent match · research watch · fresh 0.50 · score 2.00")

    def test_korean_seed_has_korean_chrome_and_marks_english_items(self) -> None:
        seed = render_home.seed_region(page(KO))
        self.assertIsNotNone(seed)
        self.assertRegex(seed, r"<h2>주요 시그널")
        self.assertIn("데일리 리캡", seed)
        self.assertRegex(seed, r'<h3><a href="[^"]+" rel="noopener" lang="en">')
        self.assertNotIn("Top signals", seed)

    def test_default_seed_is_unmarked(self) -> None:
        seed = render_home.seed_region(page(DEFAULT))
        self.assertIn("Top signals", seed)
        self.assertNotIn('lang="en"', seed)


if __name__ == "__main__":
    unittest.main()
