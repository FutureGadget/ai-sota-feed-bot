from __future__ import annotations

import json
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

    def test_default_range_is_today_at_every_site(self) -> None:
        # The finishable promise only holds if the default window can end, and
        # the default lives in six places that must agree - a mismatch either
        # writes Today into every share URL or makes Last 7d unreachable.
        self.assertIn('<option value="1" selected>Today</option>', self.html)
        self.assertNotIn('<option value="7" selected>', self.html)
        self.assertIn("let presetDaysState = '1';", self.html)
        self.assertIn("includes(presetDaysState) ? presetDaysState : '1'", self.html)
        self.assertIn("presetDaysState === '1'", self.html)
        self.assertIn("setDateRangeDays(valid ? days : 1)", self.html)
        self.assertIn("} else if (presetDaysState !== '1') {", self.html)
        self.assertNotIn("Number(presetDaysState || 7)", self.html)

    def test_empty_today_window_widens_once(self) -> None:
        # A reader arriving just after local midnight gets a window minutes
        # wide; the homepage must not answer that with an empty state.
        self.assertIn("let emptyWindowWidened = false;", self.html)
        self.assertIn("emptyWindowWidened = true;", self.html)
        self.assertIn("setDateRangeDays(3);", self.html)
        # It must not disarm the two paths that own their own widening: an
        # explicit range pick, and the share landing's 30d retry.
        self.assertIn("&& !pendingSharedItemUrl", self.html)
        self.assertIn(
            "emptyWindowWidened = true;\n        setDateRangeDays(e.target.value);", self.html
        )

    def test_clear_filters_restores_the_finishable_default_and_can_widen(self) -> None:
        self.assertIn(
            "setSelectedLabels(DEFAULT_SECTION_LABELS);\n          setDateRangeDays(1);",
            self.html,
        )
        self.assertIn(
            "searchQueryState = '';\n          emptyWindowWidened = false;",
            self.html,
        )

    def test_visible_section_counts_are_exposed_to_assistive_technology(self) -> None:
        self.assertNotIn("span.setAttribute('aria-hidden', 'true');", self.html)

    def test_list_status_is_announced_from_every_render_path(self) -> None:
        # #list is not a live region any more, so each path that rewrites it
        # has to report through #feedStatus or the change is never announced.
        self.assertIn('<p id="feedStatus" class="visually-hidden" role="status">', self.html)
        self.assertIn("function setFeedStatus(text)", self.html)
        self.assertNotIn('id="list" aria-live', self.html)
        # Feed render, saved view, and the fetch-failure path each report.
        for anchor in (
            "setFeedStatus(countText);\n      syncSectionTabs();",
            "document.getElementById('meta').textContent = countText;\n      setFeedStatus(countText);",
            "setFeedStatus('Feed unavailable.",
        ):
            with self.subTest(anchor=anchor[:40]):
                self.assertIn(anchor, self.html)

    def test_action_button_hit_areas_do_not_overlap(self) -> None:
        # The ::after halos are invisible: if they overlap, the later sibling
        # silently steals taps aimed at the earlier one.
        halo = re.search(
            r"\.save-btn::after,\s*\.share-btn::after,\s*\.hide-btn::after \{[^}]*inset: -([\d.]+)rem;",
            self.html,
        )
        self.assertIsNotNone(halo)
        gap = re.search(r"\.card-actions \{[^}]*gap: ([\d.]+)rem;", self.html)
        self.assertIsNotNone(gap)
        self.assertGreaterEqual(float(gap.group(1)), 2 * float(halo.group(1)))

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

    def test_fresh_editorial_updates_stay_in_the_feed_reading_column(self) -> None:
        """The freshness strip must not become a third item in the wide rail."""
        updates = (ROOT / "web" / "nav-updates.js").read_text(encoding="utf-8")
        self.assertIn('id="freshUpdates" class="fresh-updates"', self.html)
        self.assertIn('class="feed-column"', self.html)
        self.assertIn("anchor.insertBefore(strip, anchor.firstChild);", updates)
        self.assertNotIn("parent.insertBefore(strip, anchor);", updates)

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
        self.assertIn("if (!renderFrozenList(data))", self.ko_html)   # paused branch
        self.assertIn("else if (renderFrozenList(data))", self.ko_html)  # incomplete branch
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
    # Model Release Radar sidebar (feed page teaser linking to /models).
    # These tests cover: the wrapper markup and its zero-shift hidden default,
    # the wide-viewport rail vs. stacked-card breakpoint math (the article
    # column must never shrink), and the render/attribution logic itself
    # (extracted and run under node, same pattern as the /ko/ tests above).

    def test_model_radar_rail_wraps_list_and_starts_hidden(self) -> None:
        self.assertIn('<div class="feed-layout">', self.html)
        self.assertIn(
            '<aside id="modelRadarRail" class="model-radar-rail" '
            'aria-label="Model Release Radar" hidden></aside>',
            self.html,
        )
        # The rail is a DOM sibling *after* #list, so removing it on failure
        # never disturbs the feed-seed region above it - and stacked layouts
        # render it below the articles for free, which is what we want.
        list_open = self.html.index('<section id="list"')
        rail = self.html.index('id="modelRadarRail"')
        self.assertLess(list_open, rail)

    def test_model_radar_rail_wide_breakpoint_math_never_shrinks_article_column(self) -> None:
        # Stacked default: the rail follows #list in DOM order and must NOT be
        # hoisted above it. An earlier `order:-1` pushed every brief article
        # below the radar, burying the feed the page exists to deliver.
        self.assertIn(".feed-layout { display:flex; flex-direction:column; }", self.html)
        self.assertNotIn(".model-radar-rail { order:-1;", self.html)
        # Wide rail: the breakpoint IS the widened main width, so there is no
        # in-between viewport range where main has grown past 980px but the
        # rail hasn't fully landed yet - .feed-column keeps the exact calc used by
        # the base 980px `main` rule (980px - 2 * 1.35rem side padding).
        self.assertIn("@media (min-width:1200px) {", self.html)
        self.assertIn("main { max-width:1200px; }", self.html)
        self.assertIn(".feed-column { flex:1 1 auto; min-width:0; max-width:calc(980px - 2.7rem); }", self.html)

    def test_model_radar_rail_collapses_to_one_row_below_the_rail_breakpoint(self) -> None:
        # The feed is the product on a phone. A five-row radar block anywhere
        # in the flow competes with it, so narrow viewports keep only the
        # leading model plus the CTA; the full list returns with the >=1200px
        # rail, where it costs the article column nothing.
        self.assertIn("@media (max-width:1199.98px) {", self.html)
        self.assertIn(".model-radar-rail .mr-rail-row + .mr-rail-row { display:none; }", self.html)
        self.assertIn(".model-radar-rail .mr-rail-lede { display:none; }", self.html)

    def test_model_radar_rail_keeps_source_credit_when_collapsed(self) -> None:
        # A score is still on screen in the collapsed state, so the source
        # credit line must NOT be among what the media query hides.
        block = self.html.split("@media (max-width:1199.98px) {", 1)[1].split("\n    }", 1)[0]
        self.assertNotIn(".mr-rail-sources", block)
        self.assertNotIn(".mr-rail-cta", block)

    def test_model_radar_rail_row_splits_org_off_the_metric_line(self) -> None:
        # One run-on meta line ("anthropic - 63.1 AA intelligence index -
        # $10/1M blended") wrapped to three ragged lines in the 200px rail.
        # Org gets its own line, the metric label is shortened (the credit
        # line below spells it out), and the " blended" qualifier moves to the
        # tooltip - the visible line has to hold one row at 200px.
        self.assertIn('<span class="mr-rail-org">', self.html)
        self.assertIn("var shortLabel = capIsIndex ? 'AA index'", self.html)
        self.assertIn("price.replace(/ blended$/, '')", self.html)

    def test_model_radar_rail_badge_is_separated_from_the_model_name(self) -> None:
        # Rendered as "Kimi K3Open weights" before - the badge was concatenated
        # straight onto the name with no separator.
        self.assertIn("""' <span class="mr-rail-badge">Open weights</span>'""", self.html)

    def test_model_radar_rail_credits_the_source_by_name_not_by_url(self) -> None:
        # The config attribution is a full sentence carrying the URL inline;
        # used verbatim as link text it rendered
        # "Artificial Analysis (https://artificialanalysis.ai/) - independent
        # benchmarking." across three lines. Credit is still mandatory, so the
        # link stays - only the visible label is shortened, with the full
        # sentence preserved as the title.
        self.assertIn("function mrSourceLabel(attribution, fallback)", self.html)
        self.assertIn('title="\' + mrEsc(aaFull) + \'"', self.html)

    def test_model_radar_rail_widens_on_large_screens(self) -> None:
        # 200px left the rail cramped while the page margins went unused; the
        # article column is deliberately unchanged.
        self.assertIn("@media (min-width:1440px) {", self.html)
        self.assertIn("main { max-width:1280px; }", self.html)
        self.assertIn(".model-radar-rail { flex:0 0 280px; width:280px; }", self.html)

    def test_model_radar_rail_cta_links_to_models_page(self) -> None:
        self.assertIn(
            # Short enough to hold one line in the 200px rail; the heading
            # above it already says what the radar is.
            'href="/models">Full radar &rarr;',
            self.html,
        )

    def test_model_radar_rail_fetches_the_prebuilt_static_slice(self) -> None:
        # A static asset, not a serverless function: the Hobby plan caps a
        # deployment at 12 functions and the project was already at 12, so an
        # api/models.js failed every deploy. The slice is pre-ordered by the
        # metric the rail ranks by, so a top model cannot fall outside the
        # window, and it is ~14 KB rather than the ~300 KB full catalog.
        self.assertIn("fetch('/models-top.json')", self.html)
        self.assertNotIn("/api/models", self.html)
        # Deferred past the feed's own load, idle-tick before the network call.
        self.assertIn("window.addEventListener('load', mrSchedule)", self.html)
        self.assertIn(
            "'requestIdleCallback' in window ? requestIdleCallback(mrRun, { timeout: 4000 })",
            self.html,
        )
        # Same local-preview fallback contract as /models itself.
        self.assertIn(
            "if (res.status === 404 && mrIsLocal()) return fetch('/data/models/latest.json'",
            self.html,
        )
        # Any failure removes the element outright rather than leaving an
        # error state or empty skeleton behind.
        self.assertIn(".catch(function () { rail.remove(); });", self.html)

    # The sidebar's helpers are all "mr"-prefixed (mrEsc, mrSafeUrl, ...) so
    # they never collide with the main feed script's own esc/safeUrl earlier
    # in the same file - _extract_js_function matches by first textual
    # occurrence, so a shared name would silently pull the wrong function.
    def _extract_model_radar_functions(self) -> str:
        names = [
            "mrEsc", "mrSafeUrl", "mrDisplayName", "mrFmtPrice", "mrCapabilityField", "mrCollapseVariants",
            "mrSourceLabel", "mrSourcesLine", "mrDetailUrl", "mrRowHtml", "mrRender",
        ]
        return "\n".join(_extract_js_function(self.html, name) for name in names)

    def test_model_radar_rail_render_shows_top_models_and_omits_null_price(self) -> None:
        functions = self._extract_model_radar_functions()
        script = f"""
          {functions}
          const rail = {{ innerHTML: '', hidden: true }};
          const data = {{
            sources: {{
              lmarena: {{ attribution: 'LMArena', url: 'https://lmarena.ai' }},
              artificial_analysis: {{ attribution: 'Artificial Analysis', url: 'https://artificialanalysis.ai' }}
            }},
            models: [
              {{ name: 'model-a', organization: 'labA', arena_elo_coding: 1500.4,
                 open_weights: true, price_blended_per_1m: null }},
              {{ name: 'model-b', organization: 'labB', arena_elo_coding: null,
                 open_weights: false, price_blended_per_1m: null }}
            ]
          }};
          const ok = mrRender(rail, data);
          console.log(JSON.stringify({{
            ok, hidden: rail.hidden,
            hasModelA: rail.innerHTML.includes('model-a'),
            excludesNullEloModel: !rail.innerHTML.includes('model-b'),
            hasOpenWeightsBadge: rail.innerHTML.includes('Open weights'),
            noPriceRendered: !rail.innerHTML.includes('/1M'),
            creditsLmarenaOnly: rail.innerHTML.includes('LMArena') && !rail.innerHTML.includes('Artificial Analysis'),
          }}));
        """
        result = json.loads(_run_node(script))
        self.assertEqual(
            result,
            {
                "ok": True,
                "hidden": False,
                "hasModelA": True,
                "excludesNullEloModel": True,
                "hasOpenWeightsBadge": True,
                "noPriceRendered": True,
                "creditsLmarenaOnly": True,
            },
        )

    def test_model_radar_rail_render_credits_artificial_analysis_when_price_shown(self) -> None:
        functions = self._extract_model_radar_functions()
        script = f"""
          {functions}
          const rail = {{ innerHTML: '', hidden: true }};
          const data = {{
            sources: {{
              lmarena: {{ attribution: 'LMArena', url: 'https://lmarena.ai' }},
              artificial_analysis: {{ attribution: 'Artificial Analysis', url: 'https://artificialanalysis.ai' }}
            }},
            models: [
              {{ name: 'model-a', organization: 'labA', arena_elo_coding: 1500,
                 open_weights: false, price_blended_per_1m: 3.5 }}
            ]
          }};
          mrRender(rail, data);
          console.log(JSON.stringify({{
            hasPrice: rail.innerHTML.includes('\\$3.50/1M blended'),
            creditsBothSources: rail.innerHTML.includes('LMArena') && rail.innerHTML.includes('Artificial Analysis'),
          }}));
        """
        self.assertEqual(
            _run_node(script),
            '{"hasPrice":true,"creditsBothSources":true}',
        )

    def test_model_radar_rail_render_returns_false_and_stays_hidden_when_no_ranked_models(self) -> None:
        functions = self._extract_model_radar_functions()
        script = f"""
          {functions}
          const rail = {{ innerHTML: '', hidden: true }};
          const ok = mrRender(rail, {{ models: [] }});
          console.log(JSON.stringify({{ ok, hidden: rail.hidden, empty: rail.innerHTML === '' }}));
        """
        self.assertEqual(_run_node(script), '{"ok":false,"hidden":true,"empty":true}')

    def test_model_radar_rail_render_defaults_to_five_rows_without_outer_limit_var(self) -> None:
        # mrRender takes `limit` as a parameter (default 5) rather than
        # closing over an outer LIMIT constant, so calling it with just
        # (rail, data) - as the real mrRun() call site does - must still cap
        # at 5 rows given more than 5 ranked models.
        functions = self._extract_model_radar_functions()
        models = ",".join(
            f'{{ name: "model-{i}", organization: "lab", arena_elo_coding: {1500 - i}, '
            f'open_weights: false, price_blended_per_1m: null }}'
            for i in range(8)
        )
        script = f"""
          {functions}
          const rail = {{ innerHTML: '', hidden: true }};
          mrRender(rail, {{ models: [{models}] }});
          const rowCount = (rail.innerHTML.match(/mr-rail-row/g) || []).length;
          console.log(JSON.stringify({{ rowCount }}));
        """
        self.assertEqual(_run_node(script), '{"rowCount":5}')

    def test_model_radar_rail_prefers_aa_intelligence_index_over_elo_when_available(self) -> None:
        # The rail's default ordering must match /models' own default
        # (aa_intelligence_index descending) so the two surfaces tell the
        # same story - see web/models.html's SORT_OPTIONS.
        functions = self._extract_model_radar_functions()
        script = f"""
          {functions}
          const rail = {{ innerHTML: '', hidden: true }};
          const data = {{
            sources: {{
              lmarena: {{ attribution: 'LMArena', url: 'https://lmarena.ai' }},
              artificial_analysis: {{ attribution: 'Artificial Analysis', url: 'https://artificialanalysis.ai' }}
            }},
            models: [
              {{ name: 'high-elo-low-index', slug: 'a', base_slug: 'a', organization: 'labA',
                 arena_elo_coding: 1600, aa_intelligence_index: 40, open_weights: false, price_blended_per_1m: null }},
              {{ name: 'low-elo-high-index', slug: 'b', base_slug: 'b', organization: 'labB',
                 arena_elo_coding: 1400, aa_intelligence_index: 90, open_weights: false, price_blended_per_1m: null }}
            ]
          }};
          mrRender(rail, data);
          console.log(JSON.stringify({{
            firstModelIsHighIndex: rail.innerHTML.indexOf('low-elo-high-index') < rail.innerHTML.indexOf('high-elo-low-index'),
            showsIndexLabel: rail.innerHTML.includes('AA intelligence index'),
            creditsArtificialAnalysis: rail.innerHTML.includes('AA intelligence index from') && rail.innerHTML.includes('Artificial Analysis'),
          }}));
        """
        result = json.loads(_run_node(script))
        self.assertEqual(
            result,
            {"firstModelIsHighIndex": True, "showsIndexLabel": True, "creditsArtificialAnalysis": True},
        )

    def test_model_radar_rail_collapses_variant_spam_before_ranking(self) -> None:
        # Regression test for the reported bug: a single lab publishing many
        # reasoning-effort variants of the same base model (all at the same
        # or a very close Elo) must not fill the whole 5-row teaser by
        # itself - one row per base_slug, same as the /models page.
        functions = self._extract_model_radar_functions()
        anthropic_variants = ",".join(
            f'{{ name: "claude-opus-5-{suffix}", slug: "opus5{suffix}", base_slug: "claudeopus5", '
            f'organization: "anthropic", arena_elo_coding: {1600 - i}, open_weights: false, price_blended_per_1m: null }}'
            for i, suffix in enumerate(["max", "high", "medium", "low", "xhigh"])
        )
        script = f"""
          {functions}
          const rail = {{ innerHTML: '', hidden: true }};
          const models = [
            {anthropic_variants},
            {{ name: 'kimi-k3', slug: 'kimik3', base_slug: 'kimik3', organization: 'moonshot',
               arena_elo_coding: 1550, open_weights: true, price_blended_per_1m: null }},
            {{ name: 'glm-5.2', slug: 'glm52', base_slug: 'glm52', organization: 'zai',
               arena_elo_coding: 1540, open_weights: true, price_blended_per_1m: null }}
          ];
          mrRender(rail, {{ models }});
          const rowCount = (rail.innerHTML.match(/mr-rail-row/g) || []).length;
          console.log(JSON.stringify({{
            rowCount,
            anthropicRowCount: (rail.innerHTML.match(/anthropic/g) || []).length,
            includesKimi: rail.innerHTML.includes('kimi-k3'),
            includesGlm: rail.innerHTML.includes('glm-5.2'),
          }}));
        """
        result = json.loads(_run_node(script))
        self.assertEqual(result["rowCount"], 3, "5 spammed Anthropic rows + 2 other labs collapse to 3 distinct models")
        self.assertEqual(result["anthropicRowCount"], 1, "the Anthropic variant family must appear only once")
        self.assertTrue(result["includesKimi"])
        self.assertTrue(result["includesGlm"])

    def test_model_radar_rail_renders_display_name_not_raw_name(self) -> None:
        # The rail's 200px width is the exact case the display_name fix
        # targets: a raw name mixing AA verbose variant strings and LMArena
        # lowercase-dashed slugs wraps to two lines there - see
        # docs/design-docs/decision-log.md, 2026-08-06.
        functions = self._extract_model_radar_functions()
        script = f"""
          {functions}
          const rail = {{ innerHTML: '', hidden: true }};
          const data = {{
            sources: {{ lmarena: {{}}, artificial_analysis: {{}} }},
            models: [
              {{ name: 'gpt-5.6-sol-xhigh', display_name: 'GPT-5.6 Sol', slug: 'a',
                 organization: 'openai', arena_elo_coding: 1500, price_blended_per_1m: null }},
              {{ name: 'claude-opus-5-max-adaptive', slug: 'b',
                 organization: 'anthropic', arena_elo_coding: 1490, price_blended_per_1m: null }}
            ]
          }};
          mrRender(rail, data);
          console.log(JSON.stringify({{
            showsDisplayName: rail.innerHTML.includes('GPT-5.6 Sol'),
            hidesRawName: !rail.innerHTML.includes('gpt-5.6-sol-xhigh'),
            fallsBackToRawNameWhenFieldAbsent: rail.innerHTML.includes('claude-opus-5-max-adaptive'),
          }}));
        """
        result = json.loads(_run_node(script))
        self.assertEqual(
            result,
            {"showsDisplayName": True, "hidesRawName": True, "fallsBackToRawNameWhenFieldAbsent": True},
        )

    def test_model_radar_rail_rows_link_to_detail_page(self) -> None:
        # The whole point of the ranked-list restructure (see web/models.html):
        # every row - including the compact feed-sidebar teaser - links to
        # its own /models/<url_slug> detail page, keyboard-accessible (a
        # real <a>, not a click handler on a <span>).
        functions = self._extract_model_radar_functions()
        script = f"""
          {functions}
          const rail = {{ innerHTML: '', hidden: true }};
          const data = {{
            sources: {{ lmarena: {{}}, artificial_analysis: {{}} }},
            models: [
              {{ name: 'claude-opus-5-high', display_name: 'Claude Opus 5', slug: 'claudeopus5high',
                 base_slug: 'claudeopus5', url_slug: 'claude-opus-5', organization: 'anthropic',
                 arena_elo_coding: 1500, price_blended_per_1m: null }},
              {{ name: 'legacy-model', slug: 'legacyslug', organization: 'acme',
                 arena_elo_coding: 1490, price_blended_per_1m: null }}
            ]
          }};
          mrRender(rail, data);
          console.log(JSON.stringify({{
            linksToUrlSlug: rail.innerHTML.includes('<a class="mr-rail-name" href="/models/claude-opus-5">'),
            fallsBackToSlugWhenUrlSlugAbsent: rail.innerHTML.includes('<a class="mr-rail-name" href="/models/legacyslug">'),
          }}));
        """
        result = json.loads(_run_node(script))
        self.assertEqual(
            result,
            {"linksToUrlSlug": True, "fallsBackToSlugWhenUrlSlugAbsent": True},
        )

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
