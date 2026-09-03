from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HAS_NODE = shutil.which("node") is not None


class ModelsSurfaceTest(unittest.TestCase):
    """Structural guards for the /models (Model Release Radar) surface.

    The reader job is "a new model just dropped - is it real, what does it
    cost, and should I route to it?" The page is a search-result style
    RANKED LIST (not a chart): every tracked model gets a row, ordered by
    Artificial Analysis intelligence index by default, each row a link to
    its own /models/<url_slug> detail page. It must stay finishable (a
    capped, curated view by default, with an explicit "show all" opt-in),
    must never fabricate a value, and must always credit LMArena and
    Artificial Analysis wherever their data could appear - these assertions
    pin that contract.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.html = (ROOT / "web" / "models.html").read_text(encoding="utf-8")

    # ---- shared chrome ----

    def test_includes_shared_site_chrome_assets(self) -> None:
        self.assertIn("/site-chrome.css", self.html)
        self.assertIn("/site-chrome.js", self.html)
        self.assertIn("/nav-updates.js", self.html)
        self.assertIn('class="site-chrome"', self.html)
        self.assertIn('data-site-section="/models"', self.html)

    def test_nav_fallback_links_to_models_and_back_to_existing_surfaces(self) -> None:
        self.assertIn('data-site-destination="/models" aria-current="page"', self.html)
        self.assertIn('data-site-destination="/"', self.html)
        self.assertIn('data-site-destination="/daily"', self.html)
        self.assertIn('data-site-destination="/foundations"', self.html)
        self.assertIn('data-site-destination="/playbook"', self.html)

    def test_uses_shared_instrument_token_system(self) -> None:
        # Same cool instrument-paper palette / blue accent as playbook/foundations.
        self.assertIn("--bg:#f5f7fa;", self.html)
        self.assertIn("--accent:#2457d6;", self.html)
        self.assertIn("--bg:#11151c;", self.html)  # dark theme
        self.assertIn('"Avenir Next Condensed"', self.html)
        self.assertIn("ui-monospace", self.html)

    def test_theme_toggle_present(self) -> None:
        self.assertIn('id="themeToggle"', self.html)
        self.assertIn("applyTheme", self.html)
        self.assertIn("prefers-color-scheme: dark", self.html)

    def test_json_view_link(self) -> None:
        self.assertIn('id="jsonLink"', self.html)
        self.assertIn("/models-data.json", self.html)

    # ---- attribution (licensing obligation) ----

    def test_renders_attribution_for_both_sources(self) -> None:
        self.assertIn("class=\"mr-sources\"", self.html)
        self.assertIn("lmarena", self.html)
        self.assertIn("artificial_analysis", self.html)
        self.assertIn("sources.lmarena", self.html)
        self.assertIn("sources.artificial_analysis", self.html)
        # Attribution text is rendered from the API's sources block, not
        # hardcoded literal strings - the page must not invent its own wording.
        self.assertIn("s.attribution", self.html)
        self.assertIn("renderSources", self.html)

    def test_renders_deepswe_attribution(self) -> None:
        # DeepSWE / Datacurve is the only source with a measured (not
        # per-token-estimated) per-task cost - attribution is a licensing
        # obligation the same as LMArena/Artificial Analysis (AGENTS.md).
        self.assertIn("sources.deepswe", self.html)
        self.assertIn("DeepSWE / Datacurve", self.html)

    def test_renders_first_party_launch_provenance(self) -> None:
        self.assertIn("sources.first_party", self.html)
        self.assertIn("First-party model announcements", self.html)

    def test_highlights_recent_first_party_launches_awaiting_measurements(self) -> None:
        self.assertIn("function firstPartyAnnouncements(models)", self.html)
        self.assertIn("Awaiting independent measurements", self.html)

    def test_artificial_analysis_absence_is_disclosed_not_hidden(self) -> None:
        self.assertIn("aa.available", self.html)
        self.assertIn("not yet connected", self.html)

    # ---- ranked-list ordering (Step: chart -> ranked list restructure) ----

    def test_default_order_is_intelligence_index_descending(self) -> None:
        self.assertIn("const SORT_OPTIONS", self.html)
        self.assertIn("{ key: 'aa_intelligence_index', dir: 'desc', label: 'Intelligence index'", self.html)
        # The default must be the FIRST entry, never reordered at runtime.
        self.assertIn("aaAvailable ? SORT_OPTIONS[0] : FALLBACK_SORT", self.html)

    def test_offers_a_small_set_of_alternate_orderings(self) -> None:
        self.assertIn("key: 'aa_coding_index'", self.html)
        self.assertIn("key: 'price_blended_per_1m'", self.html)
        # A small, fixed set - not a full column-sort matrix. Exactly 3
        # selectable SORT_OPTIONS entries, plus the one automatic
        # AA-unavailable FALLBACK_SORT (never reachable from the <select>).
        options_block = self.html[self.html.index("const SORT_OPTIONS"):self.html.index("const FALLBACK_SORT")]
        matches = re.findall(r"\{ key: '\w+', dir: '(?:asc|desc)'", options_block)
        self.assertEqual(len(matches), 3, "expected exactly the 3 documented orderings")

    def test_never_fabricates_a_value(self) -> None:
        self.assertIn("function fmtPrice", self.html)
        self.assertIn("function fmtNum", self.html)
        self.assertIn("undisclosed", self.html)
        self.assertNotIn("estimated price", self.html.lower())
        self.assertNotIn("approx. $", self.html.lower())

    def test_missing_metric_sorts_last_never_as_zero(self) -> None:
        self.assertIn("function sortModels", self.html)
        self.assertIn("nulls always last", self.html)
        # The comparator must short-circuit on null BEFORE any numeric
        # comparison, so a missing value can never silently compare as 0.
        self.assertIn("if (aNull) return 1", self.html)
        self.assertIn("if (bNull) return -1", self.html)

    # ---- every model shown, frontier badged, frontier-only filter ----

    def test_shows_all_models_not_just_frontier(self) -> None:
        self.assertIn("function collapseVariants", self.html)
        self.assertIn("function buildView", self.html)
        # buildView's default scope is the full distinct catalog, not a
        # frontier-filtered subset - frontierOnly is an opt-in toggle.
        self.assertIn("let frontierOnly = false;", self.html)

    def test_frontier_membership_is_badged(self) -> None:
        self.assertIn("function isOnFrontier", self.html)
        self.assertIn("mr-frontier-tag", self.html)
        self.assertIn("on_frontier === true", self.html)

    def test_frontier_only_filter_present_and_data_driven(self) -> None:
        self.assertIn('id="toggleFrontier"', self.html)
        self.assertIn("frontierOnly = !frontierOnly", self.html)
        # The toggle itself only renders when there is at least one frontier
        # model to show - never an always-on control with nothing behind it.
        self.assertIn("showFrontierToggle", self.html)
        self.assertIn("view.frontierCount > 0", self.html)

    def test_variant_collapse_keeps_one_row_per_base_model_with_a_count_badge(self) -> None:
        self.assertIn("mr-variant-badge", self.html)
        self.assertIn("variantCount", self.html)
        self.assertIn("url_slug", self.html)

    # ---- every row links to its detail page ----

    def test_every_row_links_to_its_detail_page(self) -> None:
        self.assertIn("function detailUrl", self.html)
        self.assertIn("'/models/' + encodeURIComponent(slug)", self.html)
        self.assertIn('class="mr-row-link" href="${detailUrl(m)}"', self.html)

    def test_row_link_is_keyboard_accessible(self) -> None:
        # A real <a> wrapping the row content (not a click handler on a
        # <div>/<span>) - keyboard/tab focus and screen readers get it for free.
        self.assertIn("<li class=\"mr-row\">", self.html)
        self.assertIn("<a class=\"mr-row-link\"", self.html)
        self.assertIn(".mr-row-link:focus-visible", self.html)

    def test_row_shows_the_required_compact_fields(self) -> None:
        # rank, name, lab, intelligence index, price, open-weights badge,
        # frontier badge, variant count - the row-content contract.
        self.assertIn("mr-rank", self.html)
        self.assertIn("mr-row-name", self.html)
        self.assertIn("mr-row-org", self.html)
        self.assertIn("aa_intelligence_index, 1", self.html)
        self.assertIn("price_blended_per_1m", self.html)
        self.assertIn("mr-badge", self.html)
        self.assertIn("mr-frontier-tag", self.html)
        self.assertIn("mr-variant-badge", self.html)

    # ---- finishable selection ----

    def test_selection_cap_is_a_single_named_constant(self) -> None:
        matches = re.findall(r"MODEL_CAP\s*=\s*(\d+)", self.html)
        self.assertEqual(len(matches), 1, "expected exactly one MODEL_CAP definition")
        cap = int(matches[0])
        self.assertTrue(20 <= cap <= 40, f"MODEL_CAP={cap} should stay in the finishable 20-40 range")
        self.assertGreaterEqual(self.html.count("MODEL_CAP"), 3)

    def test_full_list_is_opt_in_not_default(self) -> None:
        self.assertIn("Show all", self.html)
        self.assertIn("showingAll = false", self.html)
        self.assertIn('id="toggleAll"', self.html)
        # The cap toggle only renders when there is actually more to show -
        # data-driven, same "a control earns its place" philosophy as the
        # rest of this codebase.
        self.assertIn("showCapToggle", self.html)
        self.assertIn("view.scopedCount > MODEL_CAP", self.html)

    def test_counts_are_stated_plainly(self) -> None:
        self.assertIn("function controlsSummary", self.html)
        self.assertIn("distinctCount", self.html)

    # ---- no chart: it moved to the per-model detail pages ----

    def test_no_pareto_chart_or_chart_markup_remains(self) -> None:
        self.assertNotIn("<svg", self.html)
        self.assertNotIn("function buildChart", self.html)
        self.assertNotIn("function paretoFrontier", self.html)
        self.assertNotIn("function wireChartInteractivity", self.html)
        self.assertNotIn("mr-chart", self.html)
        self.assertNotIn("mr-point", self.html)
        self.assertNotIn("mr-frontier-path", self.html)
        self.assertNotIn("mr-gridline", self.html)
        self.assertNotIn("mr-tooltip", self.html)
        self.assertNotIn("mr-axis", self.html)
        self.assertNotIn("Math.log10", self.html)
        self.assertNotIn("capabilityField", self.html)

    def test_no_axis_metric_toggle_remains(self) -> None:
        # The Y-axis toggle only ever served the chart; it must be gone
        # entirely, not just hidden - along with its whole support code.
        self.assertNotIn("metricSelect", self.html)
        self.assertNotIn("renderAxisControl", self.html)
        self.assertNotIn("axis_metric_options", self.html)
        self.assertNotIn("DEFAULT_AXIS_METRIC_OPTIONS", self.html)
        self.assertNotIn("MIN_METRIC_COVERAGE", self.html)
        self.assertNotIn("buildMetricEntries", self.html)
        self.assertNotIn("withActiveMetric", self.html)
        self.assertNotIn("fmtMetricValue", self.html)
        self.assertNotIn("fmtAxisTick", self.html)
        self.assertNotIn("metricRawValue", self.html)
        self.assertNotIn("metricCoverageCount", self.html)

    def test_no_table_markup_remains(self) -> None:
        self.assertNotIn("<table", self.html)
        self.assertNotIn("mr-table", self.html)
        self.assertNotIn("data-sort-key", self.html)
        self.assertNotIn("function visibleColumns", self.html)
        self.assertNotIn("function renderRow(m, isFrontier, cols)", self.html)
        self.assertNotIn("const COLUMNS", self.html)

    # ---- null handling ----

    def test_null_values_render_as_muted_placeholder_never_zero_or_fabricated(self) -> None:
        self.assertIn("mr-undisclosed", self.html)
        self.assertIn("nulls always last", self.html)

    def test_open_weights_and_frontier_status_never_default_to_a_false_looking_value(self) -> None:
        self.assertIn("m.open_weights === true", self.html)
        self.assertIn("m.open_weights === false", self.html)
        self.assertIn("weights unknown", self.html)

    # ---- responsive / no page-body horizontal scroll ----

    def test_responsive_no_horizontal_scroll(self) -> None:
        self.assertIn("overflow-x: clip", self.html)  # html/body guard, sticky-safe
        self.assertIn("@media (max-width:620px)", self.html)
        self.assertIn("flex-wrap:wrap", self.html)

    def test_no_external_resource_references_besides_shared_site_assets(self) -> None:
        # Every external URL referenced must be one of the repo's own known
        # allowed hosts (the Oat CSS reset and analytics are self-hosted now,
        # Vercel speed insights ships from /_vercel/) or a data source link
        # rendered from API JSON at runtime (not embedded here).
        urls = re.findall(r'(?:href|src)="(https?://[^"]+)"', self.html)
        allowed_hosts = ("www.llm-digest.com",)
        for url in urls:
            self.assertTrue(
                any(host in url for host in allowed_hosts),
                f"unexpected external resource reference: {url}",
            )

    def test_no_chart_library_or_cdn_reference(self) -> None:
        for banned in ("d3.", "chart.js", "highcharts", "plotly", "cdn.jsdelivr", "unpkg.com"):
            self.assertNotIn(banned, self.html.lower())

    def test_respects_reduced_motion(self) -> None:
        self.assertIn("prefers-reduced-motion", self.html)

    # ---- repo-wide rules ----

    def test_no_em_dash(self) -> None:
        # Use the unicode escape, not a literal em dash, so this assertion
        # doesn't itself introduce the banned character into the repo.
        self.assertNotIn("—", self.html)


    def test_row_stats_wrap_and_keep_the_effort_out_of_the_label(self) -> None:
        # The stats strip is a flex row; without flex-wrap it overflowed on a
        # phone, so values ran together ("$11.25/1M70.7%") and the weights
        # badge was clipped off the right edge. The effort qualifier also has
        # to ride with the VALUE - folded into the label it made
        # "DEEPSWE PASS@1 (XHIGH EFFORT)" wrap to three lines and shoved the
        # neighbouring stats into each other.
        self.assertIn("flex-wrap:wrap; justify-content:flex-end;", self.html)
        self.assertIn(".mr-stat-qualifier {", self.html)
        self.assertIn('<span class="mr-stat-label">DeepSWE pass@1</span>', self.html)
        self.assertNotIn("DeepSWE pass@1${qualifyingEffort}", self.html)
        # Mobile: stats must be allowed to shrink rather than force overflow.
        self.assertIn(".mr-stat { align-items:flex-start; min-width:0; }", self.html)


@unittest.skipUnless(HAS_NODE, "node is required to execute the page's ranking/selection logic")
@unittest.skipUnless(HAS_NODE, "node is required to execute the page's ranking/selection logic")
class ModelsRankedListBehaviorTest(unittest.TestCase):
    """Executes the actual page JS (collapseVariants / sortModels / buildView /
    isOnFrontier / detailUrl / renderRow) in Node against fixture model rows,
    so the ranked-list behavior is verified by running the code, not just by
    grepping for its presence.
    """

    @classmethod
    def setUpClass(cls) -> None:
        html = (ROOT / "web" / "models.html").read_text(encoding="utf-8")
        scripts = re.findall(r"<script>(.*?)</script>", html, re.S)
        # The second inline <script> holds all function/const declarations.
        # Strip the trailing top-level `initThemeToggle(); run();` calls -
        # everything else is a declaration, safe to eval without a real DOM.
        assert len(scripts) >= 2, "expected the main behavior <script> block"
        lib = scripts[1].replace("initThemeToggle();\n    run();", "")
        assert "initThemeToggle();" not in lib
        cls._lib = lib

    def _run(self, probe_js: str):
        harness = f"""
        global.window = {{ location: {{ origin: 'https://www.llm-digest.com' }} }};
        global.location = {{ hostname: 'www.llm-digest.com' }};
        global.document = {{ getElementById: () => null, querySelector: () => null, querySelectorAll: () => [] }};
        global.localStorage = {{ getItem: () => null, setItem: () => {{}} }};
        global.navigator = {{}};
        {self._lib}
        {probe_js}
        """
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
            f.write(harness)
            path = f.name
        try:
            proc = subprocess.run(["node", path], capture_output=True, text=True, timeout=20)
        finally:
            Path(path).unlink(missing_ok=True)
        self.assertEqual(proc.returncode, 0, f"node execution failed:\n{proc.stderr}")
        return json.loads(proc.stdout.strip().splitlines()[-1])

    def _model(self, slug, **overrides):
        base = dict(
            slug=slug, url_slug=slug, base_slug=slug, name=slug, organization="acme",
            aa_intelligence_index=None, aa_coding_index=None, arena_elo_coding=None,
            arena_votes=None, open_weights=None, price_blended_per_1m=None,
            official_url=None, frontier={},
        )
        base.update(overrides)
        return base

    # ---- default ordering ----

    def test_sort_models_orders_by_intelligence_index_descending_by_default(self) -> None:
        models = [
            self._model("low", aa_intelligence_index=40),
            self._model("high", aa_intelligence_index=90),
            self._model("mid", aa_intelligence_index=65),
        ]
        result = self._run(f"""
          const sorted = sortModels({json.dumps(models)}, 'aa_intelligence_index', 'desc');
          console.log(JSON.stringify(sorted.map(m => m.slug)));
        """)
        self.assertEqual(result, ["high", "mid", "low"])

    def test_sort_models_pushes_missing_metric_to_the_end_never_as_zero(self) -> None:
        models = [
            self._model("known-low", aa_intelligence_index=10),
            self._model("unknown", aa_intelligence_index=None),
            self._model("known-high", aa_intelligence_index=80),
        ]
        result = self._run(f"""
          const desc = sortModels({json.dumps(models)}, 'aa_intelligence_index', 'desc').map(m => m.slug);
          const asc = sortModels({json.dumps(models)}, 'aa_intelligence_index', 'asc').map(m => m.slug);
          console.log(JSON.stringify({{ desc, asc }}));
        """)
        self.assertEqual(result["desc"], ["known-high", "known-low", "unknown"])
        self.assertEqual(result["asc"], ["known-low", "known-high", "unknown"], "nulls last regardless of direction")

    def test_price_ordering_is_ascending_cheapest_first(self) -> None:
        result = self._run("""
          console.log(JSON.stringify(SORT_OPTIONS.find(o => o.key === 'price_blended_per_1m').dir));
        """)
        self.assertEqual(result, "asc")

    # ---- frontier ----

    def test_is_on_frontier_reads_the_active_metrics_aggregated_flag(self) -> None:
        m = self._model("a", frontier={"aa_intelligence_index": {"on_frontier": True}, "aa_coding_index": {"on_frontier": False}})
        result = self._run(f"""
          console.log(JSON.stringify({{
            intel: isOnFrontier({json.dumps(m)}, 'aa_intelligence_index'),
            coding: isOnFrontier({json.dumps(m)}, 'aa_coding_index'),
            missing: isOnFrontier({json.dumps(m)}, 'terminalbench_v2_1'),
          }}));
        """)
        self.assertEqual(result, {"intel": True, "coding": False, "missing": False})

    def test_build_view_frontier_only_filters_to_exactly_the_frontier_set(self) -> None:
        models = [
            self._model("frontier-1", aa_intelligence_index=90, frontier={"aa_intelligence_index": {"on_frontier": True}}),
            self._model("frontier-2", aa_intelligence_index=50, frontier={"aa_intelligence_index": {"on_frontier": True}}),
            self._model("dominated", aa_intelligence_index=70, frontier={"aa_intelligence_index": {"on_frontier": False}}),
        ]
        activeSort = {"key": "aa_intelligence_index", "dir": "desc", "frontierMetric": "aa_intelligence_index"}
        result = self._run(f"""
          const view = buildView({json.dumps(models)}, {json.dumps(activeSort)}, true, false);
          console.log(JSON.stringify({{
            scopedCount: view.scopedCount,
            slugs: view.visible.map(m => m.slug),
            frontierCount: view.frontierCount,
          }}));
        """)
        self.assertEqual(result["scopedCount"], 2)
        self.assertEqual(set(result["slugs"]), {"frontier-1", "frontier-2"})
        self.assertEqual(result["frontierCount"], 2)

    def test_build_view_frontier_count_is_stable_regardless_of_the_toggle(self) -> None:
        # frontierCount reflects the FULL catalog, not the filtered scope -
        # so the toggle's own "Frontier only (N)" label never changes while
        # being flipped on and off.
        models = [
            self._model("frontier-1", aa_intelligence_index=90, frontier={"aa_intelligence_index": {"on_frontier": True}}),
            self._model("dominated", aa_intelligence_index=70, frontier={"aa_intelligence_index": {"on_frontier": False}}),
        ]
        activeSort = {"key": "aa_intelligence_index", "dir": "desc", "frontierMetric": "aa_intelligence_index"}
        result = self._run(f"""
          const off = buildView({json.dumps(models)}, {json.dumps(activeSort)}, false, false);
          const on = buildView({json.dumps(models)}, {json.dumps(activeSort)}, true, false);
          console.log(JSON.stringify({{ off: off.frontierCount, on: on.frontierCount }}));
        """)
        self.assertEqual(result, {"off": 1, "on": 1})

    # ---- finishable cap ----

    def test_build_view_caps_to_model_cap_unless_showing_all(self) -> None:
        models = [self._model(f"m{i}", aa_intelligence_index=100 - i) for i in range(40)]
        activeSort = {"key": "aa_intelligence_index", "dir": "desc", "frontierMetric": "aa_intelligence_index"}
        result = self._run(f"""
          const capped = buildView({json.dumps(models)}, {json.dumps(activeSort)}, false, false);
          const all = buildView({json.dumps(models)}, {json.dumps(activeSort)}, false, true);
          console.log(JSON.stringify({{
            cappedLen: capped.visible.length,
            cappedIsCap: capped.visible.length === MODEL_CAP,
            allLen: all.visible.length,
          }}));
        """)
        self.assertTrue(result["cappedIsCap"])
        self.assertEqual(result["allLen"], 40)

    # ---- variant collapse ----

    def test_collapse_variants_reduces_reasoning_effort_spam_to_one_row(self) -> None:
        models = [
            self._model("gpt56solxhigh", url_slug="gpt-5-6-sol", base_slug="gpt56sol",
                        variant_label="xhigh", aa_intelligence_index=70),
            self._model("gpt56solmedium", url_slug="gpt-5-6-sol", base_slug="gpt56sol",
                        variant_label="medium", aa_intelligence_index=65),
            self._model("gpt56sollow", url_slug="gpt-5-6-sol", base_slug="gpt56sol",
                        variant_label="low", aa_intelligence_index=60),
        ]
        result = self._run(f"""
          const collapsed = collapseVariants({json.dumps(models)});
          console.log(JSON.stringify({{
            count: collapsed.length,
            slug: collapsed[0].slug,
            variantCount: collapsed[0].variantCount,
          }}));
        """)
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["slug"], "gpt56solxhigh")  # highest aa_intelligence_index
        self.assertEqual(result["variantCount"], 3)

    def test_variant_count_counts_distinct_efforts_not_duplicate_rows(self) -> None:
        # An effort the two sources spell differently enough not to join shows
        # up twice (both of claude-opus-5's "max" rows). Counting raw rows made
        # this page claim one more variant than the detail page, which dedupes
        # by label.
        models = [
            self._model("a", url_slug="claude-opus-5", base_slug="claudeopus5",
                        variant_label="max", aa_intelligence_index=70),
            self._model("b", url_slug="claude-opus-5", base_slug="claudeopus5",
                        variant_label="max", aa_intelligence_index=None),
            self._model("c", url_slug="claude-opus-5", base_slug="claudeopus5",
                        variant_label="high", aa_intelligence_index=65),
        ]
        result = self._run(f"""
          const collapsed = collapseVariants({json.dumps(models)});
          console.log(JSON.stringify({{ variantCount: collapsed[0].variantCount }}));
        """)
        self.assertEqual(result["variantCount"], 2)

    def test_collapse_variants_never_merges_distinct_models(self) -> None:
        models = [
            self._model("gemini3flash", url_slug="gemini-3-flash", base_slug="gemini3flash", aa_intelligence_index=50),
            self._model("gemini3pro", url_slug="gemini-3-pro", base_slug="gemini3pro", aa_intelligence_index=70),
        ]
        result = self._run(f"""
          console.log(JSON.stringify(collapseVariants({json.dumps(models)}).length));
        """)
        self.assertEqual(result, 2)

    def test_collapse_variants_groups_by_url_slug(self) -> None:
        # Grouping key must be url_slug first (the stable, ONE-per-base-model
        # identity the detail-page restructure introduced) - base_slug/slug
        # are only a fallback for an older cached artifact.
        models = [
            self._model("a1", url_slug="shared-url-slug", base_slug="basea", aa_intelligence_index=90),
            self._model("a2", url_slug="shared-url-slug", base_slug="baseb", aa_intelligence_index=80),
        ]
        result = self._run(f"""
          console.log(JSON.stringify(collapseVariants({json.dumps(models)}).length));
        """)
        self.assertEqual(result, 1)

    # ---- detail-page links ----

    def test_detail_url_uses_url_slug(self) -> None:
        result = self._run(f"""
          console.log(JSON.stringify(detailUrl({json.dumps(self._model("x", url_slug="claude-opus-5"))})));
        """)
        self.assertEqual(result, "/models/claude-opus-5")

    def test_detail_url_falls_back_to_base_slug_then_slug(self) -> None:
        result = self._run("""
          console.log(JSON.stringify({
            baseSlug: detailUrl({ slug: 'x', base_slug: 'y', url_slug: null }),
            slugOnly: detailUrl({ slug: 'z', base_slug: null, url_slug: null }),
            none: detailUrl({ slug: null, base_slug: null, url_slug: null }),
          }));
        """)
        self.assertEqual(result, {"baseSlug": "/models/y", "slugOnly": "/models/z", "none": "/models"})

    def test_render_row_links_to_the_detail_page_and_includes_required_fields(self) -> None:
        m = self._model(
            "claudeopus5high", url_slug="claude-opus-5", display_name="Claude Opus 5",
            organization="anthropic", aa_intelligence_index=63.1, price_blended_per_1m=10.0,
            open_weights=False, variantCount=3,
            frontier={"aa_intelligence_index": {"on_frontier": True}},
        )
        activeSort = {"key": "aa_intelligence_index", "dir": "desc", "frontierMetric": "aa_intelligence_index"}
        result = self._run(f"""
          const html = renderRow({json.dumps(m)}, 4, {json.dumps(activeSort)});
          console.log(JSON.stringify({{
            linksToDetail: html.includes('href="/models/claude-opus-5"'),
            hasRank: html.includes('>04<'),
            hasName: html.includes('Claude Opus 5'),
            hasOrg: html.includes('anthropic'),
            hasIntelligence: html.includes('63.1'),
            hasPrice: html.includes('$10.00/1M') || html.includes('$10/1M'),
            hasFrontierTag: html.includes('mr-frontier-tag'),
            hasVariantBadge: html.includes('+2 variant'),
            hasClosedBadge: html.includes('mr-badge-closed'),
          }}));
        """)
        self.assertEqual(
            result,
            {
                "linksToDetail": True,
                "hasRank": True,
                "hasName": True,
                "hasOrg": True,
                "hasIntelligence": True,
                "hasPrice": True,
                "hasFrontierTag": True,
                "hasVariantBadge": True,
                "hasClosedBadge": True,
            },
        )

    def test_render_row_never_shows_a_frontier_tag_for_a_dominated_model(self) -> None:
        m = self._model("dominated", aa_intelligence_index=40, frontier={"aa_intelligence_index": {"on_frontier": False}})
        activeSort = {"key": "aa_intelligence_index", "dir": "desc", "frontierMetric": "aa_intelligence_index"}
        result = self._run(f"""
          const html = renderRow({json.dumps(m)}, 1, {json.dumps(activeSort)});
          console.log(JSON.stringify(html.includes('mr-frontier-tag')));
        """)
        self.assertFalse(result)

    def test_render_row_honest_placeholders_for_null_price_and_unknown_weights(self) -> None:
        m = self._model("no-data", aa_intelligence_index=None, price_blended_per_1m=None, open_weights=None)
        activeSort = {"key": "aa_intelligence_index", "dir": "desc", "frontierMetric": "aa_intelligence_index"}
        result = self._run(f"""
          const html = renderRow({json.dumps(m)}, 1, {json.dumps(activeSort)});
          console.log(JSON.stringify({{
            hasUndisclosed: html.includes('mr-undisclosed'),
            hasWeightsUnknown: html.includes('weights unknown'),
            noZeroIntelligence: !html.includes('>0<'),
          }}));
        """)
        self.assertEqual(
            result,
            {"hasUndisclosed": True, "hasWeightsUnknown": True, "noZeroIntelligence": True},
        )


@unittest.skipUnless(HAS_NODE, "node is required to execute the display-name presentation logic")
class ModelsDisplayNamePresentationTest(unittest.TestCase):
    """Executes the actual page JS (displayName) in Node against fixture
    rows, pinning that /models uses the clean data-layer display_name field
    - not the raw `name` field, which mixes AA verbose variant strings and
    LMArena lowercase-dashed slugs in one list (docs/design-docs/decision-log.md,
    2026-08-06) - while still falling back to `name` for an older cached
    artifact without the field.
    """

    @classmethod
    def setUpClass(cls) -> None:
        html = (ROOT / "web" / "models.html").read_text(encoding="utf-8")
        scripts = re.findall(r"<script>(.*?)</script>", html, re.S)
        assert len(scripts) >= 2, "expected the main behavior <script> block"
        lib = scripts[1].replace("initThemeToggle();\n    run();", "")
        assert "initThemeToggle();" not in lib
        cls._lib = lib

    def _run(self, probe_js: str):
        harness = f"""
        global.window = {{ location: {{ origin: 'https://www.llm-digest.com' }} }};
        global.location = {{ hostname: 'www.llm-digest.com' }};
        global.document = {{ getElementById: () => null, querySelector: () => null, querySelectorAll: () => [] }};
        global.localStorage = {{ getItem: () => null, setItem: () => {{}} }};
        global.navigator = {{}};
        {self._lib}
        {probe_js}
        """
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
            f.write(harness)
            path = f.name
        try:
            proc = subprocess.run(["node", path], capture_output=True, text=True, timeout=20)
        finally:
            Path(path).unlink(missing_ok=True)
        self.assertEqual(proc.returncode, 0, f"node execution failed:\n{proc.stderr}")
        return json.loads(proc.stdout.strip().splitlines()[-1])

    def test_display_name_prefers_the_data_layer_field_over_raw_name(self) -> None:
        result = self._run("""
          console.log(JSON.stringify(displayName({ name: 'gpt-5.6-sol-xhigh', display_name: 'GPT-5.6 Sol' })));
        """)
        self.assertEqual(result, "GPT-5.6 Sol")

    def test_display_name_falls_back_to_raw_name_when_field_absent(self) -> None:
        result = self._run("""
          console.log(JSON.stringify(displayName({ name: 'claude-fable-5' })));
        """)
        self.assertEqual(result, "claude-fable-5")

    def test_display_name_never_throws_on_a_null_model(self) -> None:
        result = self._run("""
          console.log(JSON.stringify(displayName(null)));
        """)
        self.assertEqual(result, "")


if __name__ == "__main__":
    unittest.main()


class ModelsServedStaticallyTest(unittest.TestCase):
    """The radar must not add a serverless function.

    Vercel's Hobby plan caps a deployment at 12 functions and this project was
    already at 12, so shipping an api/models.js failed every deploy. Nothing
    about the radar needs request-time compute - the pages do their own
    collapsing, filtering and sorting - so the payloads are static assets.
    """

    def test_no_models_serverless_function_exists(self) -> None:
        self.assertFalse((ROOT / "api" / "models.js").exists())

    def test_function_count_stays_within_the_hobby_plan_cap(self) -> None:
        functions = sorted((ROOT / "api").glob("*.js"))
        self.assertLessEqual(
            len(functions), 12, f"too many serverless functions: {[f.name for f in functions]}"
        )

    def test_vercel_config_has_no_models_function_entry(self) -> None:
        config = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
        self.assertNotIn("api/models.js", config.get("functions", {}))
        # The page rewrites must survive - they are how /models resolves.
        sources = {r["source"] for r in config.get("rewrites", [])}
        self.assertIn("/models", sources)
