from __future__ import annotations

import re
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pipeline import render_static_pages as render


def _row(**kwargs) -> dict:
    base = {
        "slug": "rowslug",
        "name": "Row Name",
        "base_slug": "modela",
        "variant_label": None,
        "organization": "acme-labs",
        "license": "Proprietary",
        "open_weights": False,
        "release_date": "2026-06-01",
        "price_input_per_1m": 4.0,
        "price_output_per_1m": 16.0,
        "price_blended_per_1m": 8.0,
        "arena_elo_overall": None,
        "arena_elo_coding": None,
        "arena_votes": None,
        "aa_intelligence_index": None,
        "aa_coding_index": None,
        "median_output_tokens_per_second": None,
        "official_url": None,
        "joined_sources": ["artificial_analysis"],
        "display_name": "Model A",
        "benchmarks": {},
        "url_slug": "model-a",
        "frontier": {},
    }
    base.update(kwargs)
    return base


class ModelDetailHelpersTest(unittest.TestCase):
    def test_group_models_by_url_slug_groups_variants_together(self) -> None:
        rows = [
            _row(slug="a1", url_slug="model-a", variant_label="high"),
            _row(slug="a2", url_slug="model-a", variant_label="low"),
            _row(slug="b1", url_slug="model-b"),
        ]
        groups = render.group_models_by_url_slug(rows)
        self.assertEqual(set(groups), {"model-a", "model-b"})
        self.assertEqual(len(groups["model-a"]), 2)
        self.assertEqual(len(groups["model-b"]), 1)

    def test_group_models_by_url_slug_drops_rows_with_invalid_slug(self) -> None:
        rows = [_row(url_slug=""), _row(url_slug="Not Valid!"), _row(url_slug="model-a")]
        groups = render.group_models_by_url_slug(rows)
        self.assertEqual(set(groups), {"model-a"})

    def test_pick_primary_prefers_most_complete_identity_row(self) -> None:
        sparse = _row(
            slug="sparse", variant_label="max", license=None, open_weights=None,
            joined_sources=["artificial_analysis"],
        )
        complete = _row(
            slug="complete", variant_label="high", license="Proprietary", open_weights=False,
            official_url="https://example.com/model-a", joined_sources=["lmarena", "artificial_analysis"],
        )
        primary = render.pick_primary_model([sparse, complete])
        self.assertIs(primary, complete)

    def test_pick_primary_is_deterministic_on_ties(self) -> None:
        group = [_row(slug="first"), _row(slug="second")]
        # Both rows have identical completeness scores; the first encountered
        # must win so repeated runs over the same input never flip pages.
        self.assertIs(render.pick_primary_model(group), group[0])
        self.assertIs(render.pick_primary_model(list(reversed(group))), group[1])


class ModelScaleFormattingTest(unittest.TestCase):
    def test_index_scale_is_never_treated_as_a_fraction(self) -> None:
        # aa_coding_index/aa_intelligence_index are ~0-100 composites - must
        # render as a plain number, never multiplied into a percentage.
        self.assertEqual(render.fmt_index_value(76.5), "76.5")
        self.assertEqual(render.fmt_index_value(None), "-")

    def test_fraction_scale_benchmarks_render_as_percentage(self) -> None:
        # Raw AA benchmarks (scicode, terminalbench_v2_1, ...) are 0-1
        # fractions - must be scaled into a percentage, never shown bare.
        self.assertEqual(render.fmt_fraction_pct(0.543), "54.3%")
        self.assertEqual(render.fmt_fraction_pct(None), "-")

    def test_scores_section_formats_index_and_fraction_metrics_on_their_own_scale(self) -> None:
        primary = _row(
            aa_coding_index=76.5,
            aa_intelligence_index=61.5,
            benchmarks={"scicode": 0.543, "terminalbench_v2_1": 0.876},
            frontier={
                "aa_coding_index": {
                    "cost_field": "price_blended_per_1m", "cost_basis": "per_token_price_proxy",
                    "on_frontier": True, "dominated_by": [],
                },
            },
        )
        html = render.model_scores_section(primary)
        self.assertIn("76.5", html)  # aa_coding_index, index scale, not "7650.0%"
        self.assertIn("61.5", html)  # aa_intelligence_index
        self.assertIn("54.3%", html)  # scicode 0.543 -> fraction scale
        self.assertIn("87.6%", html)  # terminalbench_v2_1 0.876 -> fraction scale
        self.assertNotIn("7650.0%", html)
        self.assertNotIn("6150.0%", html)

    def test_price_formatting_strips_trailing_zero_cents_at_or_above_ten(self) -> None:
        self.assertEqual(render.fmt_model_price(10.0), "$10/1M")
        self.assertEqual(render.fmt_model_price(9.5), "$9.50/1M")
        self.assertEqual(render.fmt_model_price(None), "undisclosed")


class ModelFrontierSectionTest(unittest.TestCase):
    def test_on_frontier_metric_states_no_dominator(self) -> None:
        primary = _row(
            frontier={
                "aa_coding_index": {
                    "cost_field": "price_blended_per_1m", "cost_basis": "per_token_price_proxy",
                    "on_frontier": True, "dominated_by": [],
                },
            },
        )
        html = render.model_frontier_section(primary, {"model-a": primary})
        self.assertIn("On frontier", html)
        self.assertIn("AA coding index", html)
        self.assertNotIn("Behind frontier", html)

    def test_off_frontier_metric_links_to_dominating_models(self) -> None:
        dominator = _row(url_slug="model-b", display_name="Model B", slug="b1")
        primary = _row(
            url_slug="model-a",
            frontier={
                "aa_coding_index": {
                    "cost_field": "price_blended_per_1m", "cost_basis": "per_token_price_proxy",
                    "on_frontier": False, "dominated_by": ["model-b"],
                },
            },
        )
        html = render.model_frontier_section(primary, {"model-a": primary, "model-b": dominator})
        self.assertIn("Behind frontier", html)
        self.assertIn('href="/models/model-b"', html)
        self.assertIn("Model B", html)
        # "cheaper and at least as capable" framing, in the repo's own words.
        self.assertIn("priced the same or lower and at least as capable", html)

    def test_dominated_by_links_use_valid_slug_shape(self) -> None:
        dominator = _row(url_slug="model-b", display_name="Model B")
        primary = _row(
            url_slug="model-a",
            frontier={
                "aa_coding_index": {
                    "cost_field": "price_blended_per_1m", "cost_basis": "per_token_price_proxy",
                    "on_frontier": False, "dominated_by": ["model-b"],
                },
            },
        )
        html = render.model_frontier_section(primary, {"model-a": primary, "model-b": dominator})
        hrefs = re.findall(r'href="/models/([a-z0-9-]+)"', html)
        self.assertTrue(hrefs)
        for slug in hrefs:
            self.assertTrue(render.SLUG_RE.match(slug), f"{slug!r} is not a valid url_slug")

    def test_no_frontier_data_renders_explanatory_note_not_a_blank_section(self) -> None:
        primary = _row(frontier={})
        html = render.model_frontier_section(primary, {"model-a": primary})
        self.assertIn("Frontier position", html)
        self.assertIn("Not enough paired price and capability data", html)


class ModelCostBasisTest(unittest.TestCase):
    def test_known_cost_basis_spells_out_the_per_token_caveat(self) -> None:
        label = render.cost_basis_label("per_token_price_proxy")
        self.assertIn("per-1M-token price", label)
        self.assertIn("not a measured", label)
        self.assertIn("per-task cost", label)

    def test_unknown_cost_basis_falls_back_without_crashing(self) -> None:
        label = render.cost_basis_label("per_task_cost")
        self.assertIn("per task cost", label)

    def test_missing_cost_basis_never_crashes(self) -> None:
        self.assertTrue(render.cost_basis_label(None))
        self.assertTrue(render.cost_basis_label(""))

    def test_scores_section_never_shows_a_cost_column_for_aa_scores(self) -> None:
        # 2026-08-17: the per-token-price-proxy frontier is gone entirely -
        # an AA score (even one carrying a stale/hand-built frontier entry,
        # as this fixture does) must never render alongside a cost figure,
        # since that would imply a comparability that no longer exists.
        primary = _row(
            aa_coding_index=76.5,
            frontier={
                "aa_coding_index": {
                    "cost_field": "price_blended_per_1m", "cost_basis": "per_token_price_proxy",
                    "on_frontier": True, "dominated_by": [],
                },
            },
        )
        html = render.model_scores_section(primary)
        self.assertIn("no measured per-task cost, so no frontier claim is made", html)
        self.assertNotIn("Cost proxy", html)
        self.assertNotIn("$8.00/1M", html)

    def test_scores_section_shows_deepswe_measured_cost_when_present(self) -> None:
        primary = _row(
            deepswe_pass_at_1=0.736,
            deepswe_cost_per_task_usd=11.84,
            deepswe_median_cost_usd=10.43,
            deepswe_n_runs=4,
            deepswe_ci_lo=0.698,
            deepswe_ci_hi=0.775,
            frontier={
                "deepswe_pass_at_1": {
                    "cost_field": "deepswe_cost_per_task_usd", "cost_basis": "measured_per_task",
                    "on_frontier": True, "dominated_by": [],
                },
            },
        )
        html = render.model_scores_section(primary)
        self.assertIn("Measured cost per task (DeepSWE)", html)
        self.assertIn("73.6%", html)  # pass_at_1 formatted as a fraction, not an index
        self.assertIn("$11.84", html)
        self.assertIn("median $10.43", html)
        self.assertIn('<span class="badge">frontier</span>', html)

    def test_scores_section_states_plainly_when_deepswe_has_no_result(self) -> None:
        primary = _row()
        html = render.model_scores_section(primary)
        self.assertIn("has not been measured on DeepSWE", html)


class ModelVariantsAndCommunityTest(unittest.TestCase):
    def test_single_row_group_has_no_variants_section(self) -> None:
        primary = _row()
        self.assertEqual(render.model_variants_section([primary], primary), "")

    def test_multi_row_group_lists_every_variant(self) -> None:
        high = _row(slug="a-high", variant_label="high", aa_coding_index=76.5)
        low = _row(slug="a-low", variant_label="low", aa_coding_index=66.9)
        html = render.model_variants_section([high, low], high)
        self.assertIn("High effort", html)
        self.assertIn("Low effort", html)
        self.assertIn("76.5", html)
        self.assertIn("66.9", html)
        self.assertIn("shown above", html)

    def test_community_section_reports_no_rating_when_absent(self) -> None:
        primary = _row()
        html = render.model_community_section([primary])
        self.assertIn("No LMArena community rating", html)

    def test_community_section_renders_elo_and_votes(self) -> None:
        primary = _row(arena_elo_coding=1529.58, arena_elo_overall=1505.34, arena_votes=19792)
        html = render.model_community_section([primary])
        self.assertIn("1,530", html)
        self.assertIn("1,505", html)
        self.assertIn("19,792", html)


class ModelAttributionTest(unittest.TestCase):
    SOURCES = {
        "lmarena": {"available": True, "attribution": "LMArena (arena.ai) - community-voted model preference",
                    "url": "https://example.com/lmarena"},
        "artificial_analysis": {"available": True, "attribution": "Artificial Analysis (https://artificialanalysis.ai/)",
                                 "url": "https://example.com/aa"},
    }

    def test_attribution_rendered_when_aa_and_elo_data_present(self) -> None:
        primary = _row(aa_coding_index=76.5, arena_elo_coding=1500.0)
        html = render.model_sources_section(self.SOURCES, [primary])
        self.assertIn("LMArena (arena.ai)", html)
        self.assertIn("Artificial Analysis (https://artificialanalysis.ai/)", html)
        self.assertIn("https://example.com/lmarena", html)
        self.assertIn("https://example.com/aa", html)

    def test_attribution_text_and_url_come_from_the_artifact_not_hardcoded(self) -> None:
        custom_sources = {
            "lmarena": {"available": True, "attribution": "Custom LMArena Label", "url": "https://custom.example/lm"},
            "artificial_analysis": {"available": True, "attribution": "Custom AA Label", "url": "https://custom.example/aa"},
        }
        primary = _row(aa_coding_index=76.5, arena_elo_coding=1500.0)
        html = render.model_sources_section(custom_sources, [primary])
        self.assertIn("Custom LMArena Label", html)
        self.assertIn("Custom AA Label", html)
        self.assertIn("https://custom.example/lm", html)
        self.assertIn("https://custom.example/aa", html)

    def test_lmarena_attribution_omitted_when_no_elo_data_shown(self) -> None:
        primary = _row(aa_coding_index=76.5)  # no arena_elo_* fields
        html = render.model_sources_section(self.SOURCES, [primary])
        self.assertNotIn("LMArena", html)
        self.assertIn("Artificial Analysis", html)

    def test_no_attribution_block_when_no_source_data_present(self) -> None:
        primary = _row()
        html = render.model_sources_section(self.SOURCES, [primary])
        self.assertEqual(html, "")

    def test_deepswe_attribution_rendered_when_model_has_a_deepswe_result(self) -> None:
        sources = dict(
            self.SOURCES,
            deepswe={
                "available": True,
                "attribution": "DeepSWE / Datacurve (https://deepswe.datacurve.ai/)",
                "url": "https://example.com/deepswe",
            },
        )
        primary = _row(deepswe_pass_at_1=0.736)
        html = render.model_sources_section(sources, [primary])
        self.assertIn("DeepSWE / Datacurve (https://deepswe.datacurve.ai/)", html)
        self.assertIn("https://example.com/deepswe", html)

    def test_deepswe_attribution_omitted_when_model_has_no_deepswe_result(self) -> None:
        sources = dict(
            self.SOURCES,
            deepswe={"available": True, "attribution": "DeepSWE / Datacurve", "url": "https://example.com/deepswe"},
        )
        primary = _row(aa_coding_index=76.5)  # no deepswe_pass_at_1
        html = render.model_sources_section(sources, [primary])
        self.assertNotIn("DeepSWE", html)

    def test_first_party_only_model_keeps_its_announcement_provenance(self) -> None:
        sources = {
            "first_party": {
                "available": True,
                "attribution": "First-party model announcements",
                "url": "https://research.meta.ai/sitemap.xml",
            }
        }
        primary = _row(
            official_url="https://research.meta.ai/blog/introducing-muse-spark-1-3",
            joined_sources=["first_party"],
        )
        html = render.model_sources_section(sources, [primary])
        self.assertIn("First-party model announcements", html)
        self.assertIn("https://research.meta.ai/sitemap.xml", html)
        self.assertIn("https://research.meta.ai/blog/introducing-muse-spark-1-3", html)
        self.assertIn("Read the announcement", html)


class ModelPageRenderingTest(unittest.TestCase):
    """Full render_model_pages() coverage - one HTML file per distinct
    url_slug, and stale-page pruning when a model drops out of the artifact
    (mirrors render_topic_pages/render_foundation_pages's pattern)."""

    def setUp(self) -> None:
        self._tmp = Path(tempfile.mkdtemp())
        self._patcher = mock.patch.object(render, "WEB_DIR", self._tmp)
        self._patcher.start()

    def tearDown(self) -> None:
        self._patcher.stop()
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _artifact(self, models: list[dict]) -> dict:
        return {
            "generated_at": "2026-08-16T09:07:26+00:00",
            "sources": ModelAttributionTest.SOURCES,
            "models": models,
        }

    def test_one_page_written_per_distinct_url_slug(self) -> None:
        models = [
            _row(slug="a-high", url_slug="model-a", variant_label="high", display_name="Model A"),
            _row(slug="a-low", url_slug="model-a", variant_label="low", display_name="Model A"),
            _row(slug="b1", url_slug="model-b", display_name="Model B"),
        ]
        entries = render.render_model_pages("https://example.com", self._artifact(models))
        out_dir = self._tmp / "models"
        written = {p.name for p in out_dir.glob("*.html")}
        self.assertEqual(written, {"model-a.html", "model-b.html"})
        self.assertEqual(sorted(slug for slug, _lastmod in entries), ["model-a", "model-b"])

    def test_stale_model_page_is_pruned_when_it_drops_out_of_the_artifact(self) -> None:
        models = [
            _row(slug="a1", url_slug="model-a", display_name="Model A"),
            _row(slug="b1", url_slug="model-b", display_name="Model B"),
        ]
        render.render_model_pages("https://example.com", self._artifact(models))
        out_dir = self._tmp / "models"
        self.assertTrue((out_dir / "model-a.html").exists())
        self.assertTrue((out_dir / "model-b.html").exists())

        # model-b is retired from the next collector run.
        render.render_model_pages("https://example.com", self._artifact(models[:1]))
        self.assertTrue((out_dir / "model-a.html").exists())
        self.assertFalse((out_dir / "model-b.html").exists())

    def test_rendered_page_has_title_and_canonical_and_no_em_dash(self) -> None:
        models = [_row(slug="a1", url_slug="model-a", display_name="Model A")]
        render.render_model_pages("https://example.com", self._artifact(models))
        html = (self._tmp / "models" / "model-a.html").read_text(encoding="utf-8")
        self.assertIn("<title>Model A - Model Release Radar | LLM Digest</title>", html)
        self.assertIn('href="https://example.com/models/model-a"', html)
        # Scoped to the model page's own markup: the shared site chrome
        # injected into EVERY generated page carries a pre-existing em dash in
        # a CSS comment, so asserting over the whole document would fail on
        # something this page does not author. Rewriting that comment is a
        # one-character change that rewrites all ~2,400 generated pages, which
        # is not worth the diff.
        body = html.split("</style>")[-1]
        self.assertNotIn("—", body)


if __name__ == "__main__":
    unittest.main()


class ModelChartCollapsesVariantsTest(unittest.TestCase):
    """Guards a real rendering bug, not a style preference.

    Both sources publish one catalog row per reasoning-effort variant, and all
    variants of a model share a price. Plotting rows drew a vertical stack of
    points at a single X, and since frontier membership is a MODEL-level fact,
    every variant in that stack rendered as "on frontier" - including ones a
    sibling at the same price strictly beat (GPT-5.6 Luna showed max 71.4 and
    non-reasoning 39.3 both as frontier points at $0.45). The chart must plot
    one point per model, like every other surface.
    """

    def test_chart_js_collapses_to_one_point_per_url_slug(self) -> None:
        js = render.MODEL_CHART_JS
        self.assertIn("bestBySlug", js)
        # Points must come from the per-model map, never straight off the rows.
        self.assertIn("Object.keys(bestBySlug)", js)
        self.assertNotIn("priced.map(function (m) {", js)

    def test_chart_js_keeps_the_best_variant_on_the_active_metric(self) -> None:
        self.assertIn("m[capField] > cur[capField]", render.MODEL_CHART_JS)


class ModelDeepSWEChartAxesTest(unittest.TestCase):
    """WORK ITEM 3: the detail-page chart's default axes are DeepSWE pass@1
    (Y) vs. measured cost per task (X, log scale) - never the old per-token
    blended price."""

    def test_chart_js_uses_deepswe_fields_as_the_fixed_axes(self) -> None:
        js = render.MODEL_CHART_JS
        self.assertIn("capField = 'deepswe_pass_at_1'", js)
        self.assertIn("costField = 'deepswe_cost_per_task_usd'", js)
        self.assertNotIn("price_blended_per_1m", js)

    def test_chart_js_caption_states_measured_cost_not_per_token_estimate(self) -> None:
        js = render.MODEL_CHART_JS
        self.assertIn("Measured cost per task, DeepSWE", js)
        self.assertIn("not a per-token price estimate", js)

    def test_chart_section_renders_root_when_deepswe_data_present(self) -> None:
        primary = _row(
            url_slug="model-a",
            deepswe_pass_at_1=0.736,
            deepswe_cost_per_task_usd=11.84,
        )
        html = render.model_chart_section(primary)
        self.assertIn('id="modelChartRoot"', html)
        self.assertIn('data-url-slug="model-a"', html)
        self.assertIn("Cost vs. capability", html)

    def test_chart_section_states_plainly_and_never_draws_a_chart_without_deepswe_data(self) -> None:
        primary = _row(deepswe_pass_at_1=None, deepswe_cost_per_task_usd=None)
        html = render.model_chart_section(primary)
        self.assertNotIn('id="modelChartRoot"', html)
        self.assertIn("has not been measured on DeepSWE", html)
        self.assertIn("Artificial Analysis benchmark scores are listed below", html)

    def test_chart_section_requires_both_pass_at_1_and_cost_never_half_a_chart(self) -> None:
        # A model could theoretically carry a pass_at_1 with no cost (or vice
        # versa) if the DeepSWE join ever partially failed - still no chart.
        primary = _row(deepswe_pass_at_1=0.5, deepswe_cost_per_task_usd=None)
        html = render.model_chart_section(primary)
        self.assertNotIn('id="modelChartRoot"', html)


class ModelDeepSweEffortDisclosureTest(unittest.TestCase):
    """The measured effort must be visible next to the score.

    Effort changes measured cost several-fold on one model, so a pass@1 shown
    without its configuration reads as the model's only behavior.
    """

    def test_measured_effort_is_rendered_with_the_score(self) -> None:
        primary = _row(
            deepswe_pass_at_1=0.699,
            deepswe_cost_per_task_usd=13.41,
            deepswe_effort="xhigh",
        )
        html = render.model_scores_section(primary)
        self.assertIn("xhigh effort", html)

    def test_absent_effort_does_not_render_an_empty_qualifier(self) -> None:
        primary = _row(
            deepswe_pass_at_1=0.5, deepswe_cost_per_task_usd=1.0, deepswe_effort=None
        )
        html = render.model_scores_section(primary)
        self.assertNotIn(" effort", html)
