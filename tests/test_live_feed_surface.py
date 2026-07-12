from __future__ import annotations

import re
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _extract_js_function(source: str, name: str) -> str:
    """Pull a top-level `function name(...) {...}` block out of a <script>."""
    start = source.index(f"function {name}(")
    brace = source.index("{", start)
    depth = 0
    for i in range(brace, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return source[start : i + 1]
    raise AssertionError(f"unterminated function {name}")


def _run_node(script: str) -> str:
    result = subprocess.run(
        ["node", "-e", script],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


class LiveFeedSurfaceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        cls.ko_html = (ROOT / "web" / "ko" / "index.html").read_text(encoding="utf-8")

    def test_feed_uses_ranked_finite_reading_hierarchy(self) -> None:
        self.assertIn("Ranked signal · finite reading", self.html)
        self.assertIn("The AI brief that ends.", self.html)
        self.assertIn('class="rank-no"', self.html)
        self.assertIn("You're all caught up", self.html)
        self.assertEqual(self.html.count('id="meta"'), 1)

    def test_local_preview_falls_back_to_processed_feed(self) -> None:
        self.assertIn("'/data/processed/latest.json'", self.html)
        self.assertIn("Array.isArray(data)", self.html)

    def test_mechanical_ranking_copy_is_not_editorial_context(self) -> None:
        self.assertIn("/^Matches feed focus:/i.test(why)", self.html)
        self.assertIn(".trust-banner[hidden]", self.html)

    def test_feed_has_responsive_and_reduced_motion_rules(self) -> None:
        self.assertIn("@media (max-width:640px)", self.html)
        self.assertIn("prefers-reduced-motion", self.html)

    def test_editor_desk_playbook_inserts_match_source_urls(self) -> None:
        self.assertIn("function playbookCardForItem(it)", self.html)
        self.assertIn("normStorylineUrl(card?.source_url) === url", self.html)
        self.assertNotIn("playbookSources[itemKey(it)]", self.html)

    def test_korean_feed_shell_uses_localized_snapshot_endpoint(self) -> None:
        html = (ROOT / "web" / "ko" / "index.html").read_text(encoding="utf-8")
        self.assertIn('<html lang="ko">', html)
        self.assertIn('<meta name="robots" content="noindex" />', html)
        self.assertIn('href="https://www.llm-digest.com/"', html)
        self.assertIn("localized_snapshot", html)
        self.assertIn("u.searchParams.set('label', 'brief')", html)
        self.assertIn("u.searchParams.set('limit', '20')", html)
        self.assertIn("영어 live feed 보기", html)

    # translation-budget-governor plan, Phase 6.1: the calm one-line
    # budget_paused notice, formatted with the KST resume date, replaces
    # (not stacks with) the generic stale banner.
    def test_korean_feed_paused_notice_formats_resume_date_in_kst(self) -> None:
        format_kst_date = _extract_js_function(self.ko_html, "formatKstDate")
        paused_resume_copy = _extract_js_function(self.ko_html, "pausedResumeCopy")

        # monthly_budget: resumes_at is a specific future date -> "M월 D일".
        script = f"""
          {format_kst_date}
          {paused_resume_copy}
          console.log(pausedResumeCopy({{ reason: 'monthly_budget', resumes_at: '2026-08-01T00:00:00Z' }}));
        """
        self.assertEqual(_run_node(script), "8월 1일")

        # provider_daily_cap: always "내일" (tomorrow), regardless of the
        # exact resumes_at instant.
        script = f"""
          {format_kst_date}
          {paused_resume_copy}
          console.log(pausedResumeCopy({{ reason: 'provider_daily_cap', resumes_at: '2026-07-13T15:00:00Z' }}));
        """
        self.assertEqual(_run_node(script), "내일")

    def test_korean_feed_paused_notice_replaces_generic_stale_banner(self) -> None:
        self.assertIn("function renderPausedNotice(data)", self.ko_html)
        self.assertIn("const pausedShown = renderPausedNotice(data);", self.ko_html)
        # Non-paused staleness still falls through to the generic banner text.
        self.assertIn("한국어 피드가 아직 최신 상태가 아닙니다", self.ko_html)
        self.assertIn(
            "이번 달 번역 예산이 소진되어 ${esc(snapshotDate)} 스냅샷을 보여드리고 있습니다",
            self.ko_html,
        )

    # Phase 6.2: dated-edition heading, computed from source_run_at in KST.
    def test_korean_feed_dated_edition_heading_uses_kst_source_run_at(self) -> None:
        self.assertIn('id="editionHeading"', self.ko_html)
        self.assertIn("기준 한국어 브리핑", self.ko_html)
        format_kst_date = _extract_js_function(self.ko_html, "formatKstDate")
        render_edition_heading = _extract_js_function(self.ko_html, "renderEditionHeading")
        script = f"""
          const el = {{ hidden: true, textContent: '' }};
          globalThis.document = {{ getElementById: () => el }};
          {format_kst_date}
          {render_edition_heading}
          renderEditionHeading({{ status: 'budget_paused', is_current: false, source_run_at: '2026-07-10T02:00:00Z' }});
          console.log(JSON.stringify({{ hidden: el.hidden, text: el.textContent }}));
        """
        result = _run_node(script)
        self.assertEqual(result, '{"hidden":false,"text":"7월 10일 기준 한국어 브리핑"}')

    # Phase 6.3: the "Newer in English" strip is labeled, kept out of the
    # main Korean card list, and gated behind a single obvious constant.
    def test_korean_feed_newer_in_english_strip_labeled_and_gated(self) -> None:
        self.assertIn(
            'aria-label="그 이후 새로 올라온 소식 (영어)"',
            self.ko_html,
        )
        self.assertIn("그 이후 새로 올라온 소식 (영어)", self.ko_html)
        self.assertRegex(
            self.ko_html,
            r"const SHOW_NEWER_IN_ENGLISH_STRIP = (true|false);",
        )
        # Titles render as plain list text, never as clickable feed cards
        # mixed into the Korean list.
        section_match = re.search(
            r"async function renderNewerInEnglish\(data\) \{.*?\n    \}",
            self.ko_html,
            re.S,
        )
        self.assertIsNotNone(section_match, "renderNewerInEnglish body not found")
        section = section_match.group(0)
        self.assertIn("<li>${esc(it.title", section)
        self.assertNotIn('href="${esc(it.url', section)
        self.assertNotIn("<article>", section)

    # Phase 6 SEO note: budget_paused rides the same noindex/out-of-sitemap
    # path as any other non-current /ko/ state (the shell has no branch that
    # ever emits an indexable robots tag or adds itself to the sitemap).
    def test_korean_feed_paused_and_expired_stays_noindexed_and_out_of_sitemap(self) -> None:
        self.assertEqual(self.ko_html.count('<meta name="robots" content="noindex" />'), 1)
        self.assertNotIn("data-language-link", self.ko_html)  # no conditional indexable branch
        sitemap = (ROOT / "web" / "sitemap.xml").read_text(encoding="utf-8")
        self.assertNotIn("<loc>https://www.llm-digest.com/ko/</loc>", sitemap)


    # Frozen-snapshot cards: the paused state keeps the last complete Korean
    # snapshot readable instead of clearing the list (only when the API
    # guarantees the items are the Korean snapshot via frozen_snapshot).
    def test_korean_feed_paused_state_renders_frozen_snapshot_cards(self) -> None:
        self.assertIn("data?.frozen_snapshot === true", self.ko_html)
        self.assertIn("frozen.map(frozenCardHtml)", self.ko_html)
        # Both non-current branches keep frozen cards readable: the paused
        # branch and the transient-incomplete branch (light meta line, no
        # heavy stale banner while a complete snapshot exists).
        self.assertEqual(self.ko_html.count("renderFrozenList(data)"), 2)
        self.assertIn("일부 최신 항목의 번역을 준비 중입니다", self.ko_html)
        esc = _extract_js_function(self.ko_html, "esc")
        pretty = _extract_js_function(self.ko_html, "prettifySource")
        card = _extract_js_function(self.ko_html, "frozenCardHtml")
        script = f"""
          {esc}
          {pretty}
          {card}
          const html = frozenCardHtml({{
            url: 'https://example.com/a', source: 'simon_willison',
            published: '2026-07-09T08:00:00Z', title: '한국어 제목',
            summary_1line: '요약.', why_it_matters: '중요한 이유.'
          }}, 0);
          console.log(JSON.stringify({{
            article: html.includes('<article>'),
            src: html.includes('Simon Willison'),
            href: html.includes('https://example.com/a'),
            title: html.includes('한국어 제목'),
            rank: html.includes('>01<'),
          }}));
        """
        self.assertEqual(
            _run_node(script),
            '{"article":true,"src":true,"href":true,"title":true,"rank":true}',
        )

    # 내일 takes no particle; explicit dates take 에 (8월 1일에 vs 내일).
    def test_korean_feed_paused_notice_resume_particle(self) -> None:
        esc = _extract_js_function(self.ko_html, "esc")
        fmt = _extract_js_function(self.ko_html, "formatKstDate")
        copy_fn = _extract_js_function(self.ko_html, "pausedResumeCopy")
        notice = _extract_js_function(self.ko_html, "renderPausedNotice")
        script = f"""
          const el = {{ hidden: true, innerHTML: '' }};
          globalThis.document = {{ getElementById: () => el }};
          {esc}
          {fmt}
          {copy_fn}
          {notice}
          renderPausedNotice({{ status: 'budget_paused', reason: 'provider_daily_cap',
            source_run_at: '2026-07-09T08:00:00Z' }});
          const daily = el.innerHTML;
          renderPausedNotice({{ status: 'budget_paused', reason: 'monthly_budget',
            resumes_at: '2026-08-01T07:00:00Z', source_run_at: '2026-07-09T08:00:00Z' }});
          const monthly = el.innerHTML;
          console.log(JSON.stringify({{
            daily_ok: daily.includes('내일 재개됩니다') && !daily.includes('내일에'),
            monthly_ok: monthly.includes('8월 1일에 재개됩니다'),
          }}));
        """
        self.assertEqual(_run_node(script), '{"daily_ok":true,"monthly_ok":true}')


if __name__ == "__main__":
    unittest.main()
