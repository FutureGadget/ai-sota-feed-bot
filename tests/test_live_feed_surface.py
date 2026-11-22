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


def _ui_runtime(source: str) -> str:
    """The page's own t(), tHtml(), localHref(), localeParam() and embedded window.UI."""
    data = re.search(r"window\.UI = (\{.*?\n    \});", source, re.S)
    assert data, "the page embeds window.UI"
    functions = "\n".join(_extract_js_function(source, name) for name in ("t", "tHtml", "localHref", "localeParam"))
    return f"globalThis.window = globalThis;\nwindow.UI = {data.group(1)};\n{functions}\n"


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

    def test_feed_uses_ranked_finite_reading_hierarchy(self) -> None:
        # The masthead is the title plus one status line; no kicker or promise.
        hero = self.html.split('<section class="feed-hero">', 1)[1].split("</section>", 1)[0]
        self.assertIn('<h2 class="feed-title">The daily paper for AI engineers.</h2>', hero)
        self.assertIn('<p id="meta">', hero)
        self.assertNotIn("feed-kicker", hero)
        self.assertNotIn("feed-promise", hero)
        self.assertIn('class="rank-no"', self.html)
        self.assertIn("You're all caught up", self.html)
        self.assertEqual(self.html.count('id="meta"'), 1)

    def test_default_range_is_past_24h_at_every_site(self) -> None:
        # The finishable promise only holds if the default window can end, and
        # the default lives in six places that must agree - a mismatch either
        # writes Past 24h into every share URL or makes Last 7d unreachable.
        self.assertIn('<option value="1" selected>Past 24h</option>', self.html)
        self.assertNotIn('<option value="7" selected>', self.html)
        self.assertIn("let presetDaysState = '1';", self.html)
        self.assertIn("includes(presetDaysState) ? presetDaysState : '1'", self.html)
        self.assertIn("presetDaysState === '1'", self.html)
        self.assertIn("setDateRangeDays(valid ? days : 1)", self.html)
        self.assertIn("} else if (presetDaysState !== '1') {", self.html)
        self.assertNotIn("Number(presetDaysState || 7)", self.html)

    def test_catchup_band_is_collapsed_and_overflow_stays_visible(self) -> None:
        # The new-arrival band is opt-in so it cannot push the stable body
        # down, and cap-overflow stories continue below an explicit fold
        # instead of disappearing when a newer story arrives.
        self.assertIn('data-catchup-toggle="1"', self.html)
        self.assertIn('id="catchup-new-list"', self.html)
        self.assertIn('data-catchup-open=', self.html)
        self.assertIn('data-pool-toggle="1"', self.html)
        self.assertIn("t('pool.moreFrom', { range: where })", self.html)
        self.assertIn("beyond-cap-card", self.html)
        self.assertIn("beyond_cap", self.html)

    def test_empty_window_widens_once(self) -> None:
        # A quiet 24-hour window can still be empty; the homepage must not
        # answer that with an empty state.
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

    def test_section_and_saved_tabs_have_an_initial_pressed_state(self) -> None:
        buttons = re.findall(r'<button[^>]+(?:data-section="[^"]*"|id="savedTab")[^>]*>', self.html)
        self.assertEqual(len(buttons), 7)
        self.assertTrue(all('aria-pressed=' in button for button in buttons))
        brief = next(button for button in buttons if 'data-section="brief"' in button)
        self.assertIn('aria-pressed="true"', brief)
        self.assertTrue(
            all('aria-pressed="false"' in button for button in buttons if button != brief)
        )

    def test_rank_climb_context_is_available_to_assistive_technology(self) -> None:
        self.assertIn("const climbingLabel = isClimbing", self.html)
        self.assertIn("const rankLabel = rank === null ? '' : `${t('card.rank', { rank })}${climbingLabel}`;", self.html)
        self.assertEqual(self.html.count('aria-label="${esc(rankLabel)}"'), 2)

    def test_list_rewrites_restore_focus_with_ordered_fallbacks(self) -> None:
        self.assertIn("function captureListFocus(list)", self.html)
        self.assertIn("function restoreListFocus(list, snapshot, fallback)", self.html)
        self.assertIn("const focusSnapshot = captureListFocus(list);", self.html)
        self.assertGreaterEqual(
            self.html.count("restoreListFocus(list, focusSnapshot"),
            3,
        )
        self.assertIn("snapshot.cardIndex", self.html)
        self.assertIn("snapshot.controlSelector", self.html)

    def test_feed_promos_compose_independently_of_response_order(self) -> None:
        updates = (ROOT / "web" / "nav-updates.js").read_text(encoding="utf-8")
        self.assertIn("[data-editorial-catchup]", updates)
        self.assertIn("var target = combined || anchor", updates)
        self.assertIn("<div data-editorial-catchup></div>", self.html)
        self.assertIn("window.llmDigestUpdates?.renderFeed?.()", self.html)
        self.assertNotIn("promoOwner", updates)
        self.assertNotIn("promoOwner", self.html)

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
            "setFeedStatus(t('feed.unavailableStatus'));",
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

    def test_front_page_roles_follow_rank(self) -> None:
        role = _extract_js_function(self.html, "frontPageRole")
        script = f"""
          const FRONT_PAGE_STORIES = 5;
          {role}
          console.log([0, 1, 2, 3, 4, 5, 9].map(frontPageRole).join(','));
        """
        self.assertEqual(_run_node(script), "lead,second,second,second,second,,")

    def test_front_page_only_on_the_unsearched_brief(self) -> None:
        render = _extract_js_function(self.html, "renderFeedList")
        self.assertIn("const frontPage = !q\n          && activeSection() === 'brief'", render)
        self.assertIn("&& capCompliant >= FRONT_PAGE_MIN_STORIES;", render)
        self.assertIn("const capCompliant = overflowCount > 0 ? overflowStart : visible.length;", render)
        self.assertIn("frontPage: frontPage && i < capCompliant ? frontPageRole(i) : ''", render)
        self.assertIn("const FRONT_PAGE_MIN_STORIES = 4;", self.html)
        self.assertIn("const FRONT_PAGE_STORIES = 5;", self.html)
        # Companions never split the full five-story front page or its heading.
        self.assertIn("const companionAfter = Math.min(capCompliant, FRONT_PAGE_STORIES + 3);", render)
        self.assertIn("insert.after = Math.max(Number(insert.after) || 0, companionAfter);", render)
        self.assertIn("html: frontPageRuleHtml(restOfBrief)", render)

    def test_front_page_lead_has_a_standfirst(self) -> None:
        css = (ROOT / "web" / "front-page.css").read_text(encoding="utf-8")
        self.assertNotIn("text-transform:uppercase", css)  # Precision: sentence case
        self.assertIn("function leadExcerpt(it)", self.html)
        self.assertIn("if (!summaryRaw && frontPage === 'lead') summaryRaw = leadExcerpt(it);", self.html)
        self.assertIn("const FRONT_PAGE_CATEGORY_LABELS = {", self.html)
        clean = _extract_js_function(self.html, "cleanText")
        keywords = _extract_js_function(self.html, "looksLikeKeywordList")
        debris = _extract_js_function(self.html, "stripExcerptDebris")
        lead = _extract_js_function(self.html, "leadExcerpt")
        script = f"""
          {clean}
          {keywords}
          {debris}
          {lead}
          console.log(leadExcerpt({{content_excerpt: 'A design skill for Claude Code, Codex, Cursor and OpenCode that refuses to look AI-generated. usehallmark.com and more.'}}));
        """
        self.assertEqual(
            _run_node(script),
            "A design skill for Claude Code, Codex, Cursor and OpenCode that refuses to look AI-generated.",
        )

    def test_front_page_cards_stay_direct_list_children(self) -> None:
        # Selection, swipe and focus restore all query `#list > article`, so
        # the front page is a CSS reflow of ordinary cards, never a wrapper.
        # Slice by position: the destructured signature defeats the brace
        # matcher in _extract_js_function.
        card = self.html.split("function cardHtml(", 1)[1].split("function matchesQuery(", 1)[0]
        self.assertIn("frontPage ? `fp-${frontPage}` : ''", card)
        self.assertIn('class="fp-kicker"', card)
        css = (ROOT / "web" / "front-page.css").read_text(encoding="utf-8")
        self.assertIn("#list:has(> article.fp-lead) { display:flow-root; min-width:0; }", css)

    def test_story_cards_are_a_headline_and_one_source_line(self) -> None:
        card = self.html.split("function cardHtml(", 1)[1].split("function matchesQuery(", 1)[0]
        # Only the lead story carries its summary; thumbnails are gone.
        self.assertIn("${summary && frontPage === 'lead' ? `<p class=\"why\"${enAttr}>${summary}</p>` : ''}", card)
        self.assertNotIn('class="thumb"', card)
        # Save stays one tap away; everything else sits in the card's "⋯" panel.
        more = card.split('<details class="card-more">', 1)[1].split("</details>", 1)[0]
        for marker in ("data-share-id", "data-hide-id", 'class="fb-row', "matters", "card.alsoCovered", "badge-boost"):
            with self.subTest(marker=marker):
                self.assertIn(marker, more)
        before_more = card.split('<details class="card-more">', 1)[0]
        self.assertIn("data-save-id", before_more)
        self.assertNotIn("data-share-id", before_more)
        # The panel closes on outside click and Escape, one open at a time.
        panels = _extract_js_function(self.html, "initCardMorePanels")
        self.assertIn("e.key !== 'Escape'", panels)
        self.assertIn("if (!d.contains(e.target)) d.open = false;", panels)
        self.assertIn("initCardMorePanels();", self.html)

    def test_default_brief_shows_no_filter_chips(self) -> None:
        chips = _extract_js_function(self.html, "renderSelectedLabelsChips")
        self.assertIn("if (sameLabels(labels, DEFAULT_SECTION_LABELS)) {", chips)
        css = (ROOT / "web" / "front-page.css").read_text(encoding="utf-8")
        self.assertIn(".selected-labels:empty { display:none; }", css)

    def test_feed_has_responsive_and_reduced_motion_rules(self) -> None:
        self.assertIn("@media (max-width:640px)", self.html)
        self.assertIn("prefers-reduced-motion", self.html)

    def test_editor_desk_playbook_inserts_match_source_urls(self) -> None:
        self.assertIn("function playbookCardForItem(it)", self.html)
        self.assertIn("normStorylineUrl(card?.source_url) === url", self.html)
        self.assertNotIn("playbookSources[itemKey(it)]", self.html)

    def test_skill_lab_editor_desk_load_is_fail_soft(self) -> None:
        self.assertIn("/api/playbook?lab=latest", self.html)
        self.assertIn("function ensureSkillLabData()", self.html)
        core_loader = _extract_js_function(self.html, "ensureEditorDeskData")
        self.assertNotIn("lab=latest", core_loader)
        self.assertIn("editorDeskData.skillLab = response.ok && skillLab && typeof skillLab === 'object'", self.html)
        self.assertIn(".catch(() => null)", self.html)
        self.assertIn("editorDeskData?.skillLab", self.html)

    def test_skill_lab_promotion_has_strict_reader_and_view_gates(self) -> None:
        self.assertIn("function skillLabPromoEligible()", self.html)
        eligibility = _extract_js_function(self.html, "skillLabPromoEligible")
        self.assertIn("activeSection() !== 'brief'", eligibility)
        self.assertIn("viewState !== 'feed'", eligibility)
        self.assertIn("searchQueryState.trim()", eligibility)
        self.assertIn("!isOnboardingDone()", eligibility)
        self.assertIn("!isSubscribeNudgeDone()", eligibility)
        self.assertIn("featured_until", eligibility)
        self.assertIn("isSkillLabPromoSeen", eligibility)

    def test_skill_lab_consumes_existing_editor_desk_budget(self) -> None:
        inserts = _extract_js_function(self.html, "editorDeskInserts")
        self.assertIn("skillLabPromoEligible()", inserts)
        self.assertIn("visible.length >= 4", inserts)
        self.assertIn("after: 5", inserts)
        self.assertIn("genericInsertUsed = true", inserts)
        self.assertIn("if (!genericInsertUsed && playbookMatch)", inserts)
        self.assertIn("if (!genericInsertUsed && upd", inserts)
        self.assertIn(".slice(0, 2)", inserts)

    def test_skill_lab_promotion_dismissal_retires_and_open_is_attributed(self) -> None:
        self.assertIn("SKILL_LAB_PROMO_SEEN_PREFIX", self.html)
        self.assertIn("localStorage.setItem(SKILL_LAB_PROMO_SEEN_PREFIX + id, '1')", self.html)
        self.assertIn("markSkillLabPromoSeen(editorDismiss.dataset.skillLabPromo)", self.html)
        self.assertIn("?ref=feed_insert", self.html)
        self.assertNotIn("posthogCapture('skill_lab_open'", self.html)
        self.assertIn("window.addEventListener('pageshow'", self.html)
        self.assertIn("event.persisted", self.html)
        self.assertIn("isSkillLabPromoSeen(id)", self.html)

    def test_skill_lab_feed_impression_is_visibility_based_and_once_per_id(self) -> None:
        self.assertIn("function observeSkillLabFeedPromo()", self.html)
        self.assertIn("IntersectionObserver", self.html)
        self.assertIn("skillLabFeedViews.has(id)", self.html)
        self.assertIn("skillLabMeetsVisibility(entries, SKILL_LAB_PROMO_VIEW_THRESHOLD)", self.html)
        self.assertIn("skill_lab_feature_view", self.html)
        self.assertIn("placement: 'feed_insert'", self.html)

    def test_skill_lab_feed_actions_have_touch_size_floor(self) -> None:
        self.assertIn(
            ".editor-desk[data-skill-lab-promo] .editor-desk-actions a",
            self.html,
        )
        self.assertIn(
            ".editor-desk[data-skill-lab-promo] .catchup-dismiss",
            self.html,
        )

    def test_fresh_editorial_updates_stay_in_the_feed_reading_column(self) -> None:
        """The freshness strip must not become a third item in the wide rail."""
        updates = (ROOT / "web" / "nav-updates.js").read_text(encoding="utf-8")
        self.assertIn('id="freshUpdates" class="fresh-updates"', self.html)
        self.assertIn('class="feed-column"', self.html)
        self.assertIn("target.appendChild(el);", updates)
        self.assertNotIn("parent.insertBefore(strip, anchor);", updates)

    def test_fresh_updates_wrapper_cannot_widen_the_feed_grid_track(self) -> None:
        """The strip is an unwrappable flex row inside a grid item.

        Without an explicit min-width:0 the wrapper keeps a grid item's default
        min-width:auto, so its min-content width (the whole unwrapped row)
        floors the auto track and drags #list and every article past the
        viewport, where main's overflow-x:clip hides them instead of scrolling.
        """
        self.assertIn(".feed-column { display:grid;", self.html)
        self.assertIn(".fresh-updates { min-width:0; }", self.html)

    def test_editorial_rows_clamp_to_their_container(self) -> None:
        css = (ROOT / "web" / "editorial-updates.css").read_text(encoding="utf-8")
        self.assertIn("min-width:0; max-width:100%", css)
        self.assertIn("overflow-wrap:anywhere", css)
        self.assertNotIn("overflow-x:auto", css)

    # Model Release Radar companion (feed teaser linking to /models).
    # These tests cover: the hidden desktop rail, its wide-viewport layout,
    # and the mobile inline snapshot. The mobile version must be anchored to
    # story rank rather than the rendered-card index: catch-up, onboarding,
    # and editorial modules are allowed to move without burying the Radar.

    def test_model_radar_rail_wraps_list_and_starts_hidden(self) -> None:
        self.assertIn('<div class="feed-layout">', self.html)
        self.assertIn(
            '<aside id="modelRadarRail" class="model-radar-rail" '
            'aria-label="Model Release Radar" data-model-radar-placement="desktop_rail" hidden></aside>',
            self.html,
        )
        # The desktop rail remains a DOM sibling after #list. On narrow
        # viewports it is visually hidden in favor of the inline snapshot,
        # which is only emitted after the models payload has loaded.
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

    def test_model_radar_uses_an_inline_three_model_snapshot_below_the_rail_breakpoint(self) -> None:
        # The old stacked rail followed the entire feed and exposed only one
        # model. Mobile instead gets an inline, three-model snapshot while the
        # desktop rail is removed from the visual and accessibility tree.
        self.assertIn("@media (max-width:1199.98px) {", self.html)
        self.assertIn(".model-radar-rail { display:none !important; }", self.html)
        self.assertIn(".model-radar-inline { display:block; }", self.html)
        self.assertIn("function mrSurfaceHtml(data, limit)", self.html)
        self.assertIn("mrSurfaceHtml(data, 3)", self.html)

    def test_model_radar_mobile_snapshot_keeps_source_credit(self) -> None:
        # Scores remain visible in the mobile snapshot, so the mandatory
        # source credit must never be hidden with the desktop-only detail.
        block = self.html.split("@media (max-width:1199.98px) {", 1)[1].split("\n    }", 1)[0]
        self.assertNotIn(".mr-rail-sources", block)
        self.assertIn(".model-radar-inline .mr-rail-lede { display:none; }", block)

    def test_feed_inserts_anchor_the_mobile_radar_after_fourth_story(self) -> None:
        interleave = _extract_js_function(self.html, "interleaveFeedCards")
        script = f"""
          {interleave}
          const full = interleaveFeedCards(
            ['story-1', 'story-2', 'story-3', 'story-4', 'story-5', 'story-6'],
            [
              {{ after: 3, html: 'onboarding' }},
              {{ after: 4, html: 'model-radar' }},
              {{ after: 6, html: 'editor-desk' }},
            ],
          );
          const short = interleaveFeedCards(
            ['story-1', 'story-2'],
            [{{ after: 4, html: 'model-radar' }}],
          );
          console.log(JSON.stringify({{ full, short }}));
        """
        self.assertEqual(
            _run_node(script),
            '{"full":["story-1","story-2","story-3","onboarding","story-4","model-radar","story-5","story-6","editor-desk"],"short":["story-1","story-2","model-radar"]}',
        )

    def test_model_radar_rail_row_splits_org_off_the_metric_line(self) -> None:
        # Keep organization separate and the input price basis visible on narrow rails.
        script = f"""
          {self._extract_model_radar_functions()}
          console.log(mrRowHtml({{ name: 'model-a', organization: 'lab-a', aa_intelligence_index: 63.14, price_input_per_1m: 10 }}, 'aa_intelligence_index'));
        """
        row = _run_node(script)
        self.assertIn('<span class="mr-rail-org">lab-a</span>', row)
        self.assertIn("63.1 AA index &middot; $10/1M input", row)

    def test_model_radar_rail_badge_is_separated_from_the_model_name(self) -> None:
        # Rendered as "Kimi K3Open weights" before - the badge was concatenated
        # straight onto the name with no separator.
        script = f"""
          {self._extract_model_radar_functions()}
          console.log(mrRowHtml({{ name: 'Kimi K3', open_weights: true, arena_elo_coding: 1500 }}, 'arena_elo_coding'));
        """
        self.assertIn('Kimi K3 <span class="mr-rail-badge">Open weights</span>', _run_node(script))

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

    def test_model_radar_rail_clears_the_fixed_site_bar_when_sticky(self) -> None:
        self.assertIn(
            "position:sticky; top:calc(4rem + env(safe-area-inset-top, 0px));",
            self.html,
        )

    def test_model_radar_rail_cta_links_to_models_page(self) -> None:
        # Short enough to hold one line in the 200px rail; the heading above it
        # already says what the radar is.
        script = f"""
          {self._extract_model_radar_functions()}
          console.log(mrSurfaceHtml({{ sources: {{}}, models: [{{ name: 'm', arena_elo_coding: 1500 }}] }}));
        """
        self.assertIn('href="/models" data-model-radar-target="full">Full radar →</a>', _run_node(script))

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
        self.assertIn(
            ".catch(function () {\n          modelRadarInlineHtml = '';\n          rail.remove();\n        });",
            self.html,
        )

    def test_model_radar_does_not_replace_the_feed_failure_fallback(self) -> None:
        # The Radar is an enhancement. When /api/feed fails, the crawler seed
        # remains the reader's last good brief; a late models response must not
        # rerender #list from its empty runtime cache.
        self.assertIn(
            "if (feedCache.items.length && typeof renderFeedList === 'function') renderFeedList();",
            self.html,
        )

    def test_model_radar_records_visible_mobile_impressions_and_link_destinations(self) -> None:
        self.assertIn('data-model-radar-placement="mobile_inline"', self.html)
        self.assertIn('data-model-radar-target="detail"', self.html)
        self.assertIn('data-model-radar-target="full"', self.html)
        self.assertIn("posthogCapture('model_radar_open'", self.html)
        self.assertIn("posthogCapture('model_radar_impression'", self.html)
        self.assertIn("new IntersectionObserver", self.html)

    # The sidebar's helpers are all "mr"-prefixed (mrEsc, mrSafeUrl, ...) so
    # they never collide with the main feed script's own esc/safeUrl earlier
    # in the same file - _extract_js_function matches by first textual
    # occurrence, so a shared name would silently pull the wrong function.
    def _extract_model_radar_functions(self) -> str:
        names = [
            "mrEsc", "mrSafeUrl", "mrDisplayName", "mrFmtPrice", "mrCapabilityField", "mrCollapseVariants",
            "mrSourceLabel", "mrSourcesLine", "mrDetailUrl", "mrRowHtml", "mrSurfaceHtml", "mrRender",
        ]
        functions = "\n".join(_extract_js_function(self.html, name) for name in names)
        return f"{_ui_runtime(self.html)}\n{functions}"

    def test_model_radar_mobile_snapshot_renders_three_ranked_models(self) -> None:
        functions = self._extract_model_radar_functions()
        script = f"""
          {functions}
          const html = mrSurfaceHtml({{
            sources: {{ lmarena: {{}}, artificial_analysis: {{}} }},
            models: [
              {{ name: 'model-a', organization: 'lab-a', arena_elo_coding: 1503, open_weights: false, price_input_per_1m: 3 }},
              {{ name: 'model-b', organization: 'lab-b', arena_elo_coding: 1502, open_weights: true, price_input_per_1m: null }},
              {{ name: 'model-c', organization: 'lab-c', arena_elo_coding: 1501, open_weights: false, price_input_per_1m: null }},
              {{ name: 'model-d', organization: 'lab-d', arena_elo_coding: 1500, open_weights: false, price_input_per_1m: null }},
            ],
          }}, 3);
          console.log(JSON.stringify({{
            rowCount: (html.match(/mr-rail-row/g) || []).length,
            hasThirdModel: html.includes('model-c'),
            omitsFourthModel: !html.includes('model-d'),
            keepsAttribution: html.includes('LMArena') && html.includes('OpenRouter'),
            hasFullRadarLink: html.includes('href="/models"'),
          }}));
        """
        self.assertEqual(
            _run_node(script),
            '{"rowCount":3,"hasThirdModel":true,"omitsFourthModel":true,"keepsAttribution":true,"hasFullRadarLink":true}',
        )

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
                 open_weights: true, price_input_per_1m: null }},
              {{ name: 'model-b', organization: 'labB', arena_elo_coding: null,
                 open_weights: false, price_input_per_1m: null }}
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

    def test_model_radar_rail_render_credits_openrouter_when_price_shown(self) -> None:
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
                 open_weights: false, price_input_per_1m: 3.5 }}
            ]
          }};
          mrRender(rail, data);
          console.log(JSON.stringify({{
            hasPrice: rail.innerHTML.includes('\\$3.50/1M input'),
            creditsBothSources: rail.innerHTML.includes('LMArena') && rail.innerHTML.includes('OpenRouter'),
          }}));
        """
        self.assertEqual(
            _run_node(script),
            '{"hasPrice":true,"creditsBothSources":true}',
        )

    def test_shortcuts_dialog_and_keyboard_navigation(self) -> None:
        self.assertIn('id="shortcutsToggle"', self.html)
        self.assertIn('id="shortcutsDialog"', self.html)
        self.assertIn('id="shortcutsClose"', self.html)
        self.assertIn("function initShortcutsDialog()", self.html)
        self.assertIn("function initKeyboardNavigation()", self.html)
        self.assertIn("function selectCard(card", self.html)
        self.assertIn("function moveCardSelection(delta)", self.html)
        self.assertIn("#list > article.card-selected", self.html)
        self.assertIn("restoreCardSelection()", self.html)

    def test_search_scope_transparency_and_recovery_actions(self) -> None:
        self.assertIn('data-search-action="all"', self.html)
        self.assertIn('data-search-action="30d"', self.html)
        self.assertIn('data-search-action="clear"', self.html)
        self.assertIn("data-search-action", self.html)
        self.assertIn("empty-search-actions", self.html)

    def test_saved_view_markdown_copy_and_undo(self) -> None:
        self.assertIn('data-copy-saved="1"', self.html)
        self.assertIn("function buildSavedMarkdown(items)", self.html)
        self.assertIn("function copySavedMarkdown()", self.html)
        self.assertIn("Story removed from saved", self.html)

    def test_swipe_edge_guard_avoids_browser_gesture_conflict(self) -> None:
        self.assertIn("touchX < 24 || touchX > window.innerWidth - 24", self.html)


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
            f'open_weights: false, price_input_per_1m: null }}'
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
                 arena_elo_coding: 1600, aa_intelligence_index: 40, open_weights: false, price_input_per_1m: null }},
              {{ name: 'low-elo-high-index', slug: 'b', base_slug: 'b', organization: 'labB',
                 arena_elo_coding: 1400, aa_intelligence_index: 90, open_weights: false, price_input_per_1m: null }}
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
            f'organization: "anthropic", arena_elo_coding: {1600 - i}, open_weights: false, price_input_per_1m: null }}'
            for i, suffix in enumerate(["max", "high", "medium", "low", "xhigh"])
        )
        script = f"""
          {functions}
          const rail = {{ innerHTML: '', hidden: true }};
          const models = [
            {anthropic_variants},
            {{ name: 'kimi-k3', slug: 'kimik3', base_slug: 'kimik3', organization: 'moonshot',
               arena_elo_coding: 1550, open_weights: true, price_input_per_1m: null }},
            {{ name: 'glm-5.2', slug: 'glm52', base_slug: 'glm52', organization: 'zai',
               arena_elo_coding: 1540, open_weights: true, price_input_per_1m: null }}
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
                 organization: 'openai', arena_elo_coding: 1500, price_input_per_1m: null }},
              {{ name: 'claude-opus-5-max-adaptive', slug: 'b',
                 organization: 'anthropic', arena_elo_coding: 1490, price_input_per_1m: null }}
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
                 arena_elo_coding: 1500, price_input_per_1m: null }},
              {{ name: 'legacy-model', slug: 'legacyslug', organization: 'acme',
                 arena_elo_coding: 1490, price_input_per_1m: null }}
            ]
          }};
          mrRender(rail, data);
          console.log(JSON.stringify({{
            linksToUrlSlug: rail.innerHTML.includes('<a class="mr-rail-link" href="/models/claude-opus-5" data-model-radar-target="detail" data-model-radar-model="claude-opus-5">'),
            fallsBackToSlugWhenUrlSlugAbsent: rail.innerHTML.includes('<a class="mr-rail-link" href="/models/legacyslug" data-model-radar-target="detail" data-model-radar-model="legacyslug">'),
          }}));
        """
        result = json.loads(_run_node(script))
        self.assertEqual(
            result,
            {"linksToUrlSlug": True, "fallsBackToSlugWhenUrlSlugAbsent": True},
        )

    def test_model_radar_rows_are_full_touch_targets(self) -> None:
        self.assertIn(
            ".mr-rail-link { display:block; min-height:44px; color:inherit; text-decoration:none; }",
            self.html,
        )
        self.assertIn('<a class="mr-rail-link" href="\' + mrDetailUrl(m)', self.html)


if __name__ == "__main__":
    unittest.main()
