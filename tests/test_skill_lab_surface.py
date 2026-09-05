from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SkillLabSurfaceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = (ROOT / "web" / "playbook-lab.html").read_text(encoding="utf-8")
        cls.vercel = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))

    def test_nested_route_precedes_generic_playbook_date_route(self) -> None:
        sources = [row["source"] for row in self.vercel["rewrites"]]
        self.assertIn("/playbook/lab/:slug([a-z0-9-]+)", sources)
        self.assertLess(
            sources.index("/playbook/lab/:slug([a-z0-9-]+)"),
            sources.index("/playbook/:date"),
        )

    def test_inherits_playbook_navigation_without_new_destination(self) -> None:
        self.assertIn('data-site-section="/playbook"', self.html)
        nav = self.html.split('<nav class="site-nav-fallback"', 1)[1].split("</nav>", 1)[0]
        self.assertIn('href="/playbook"', nav)
        self.assertNotIn('/playbook/lab/', nav)

    def test_fetches_validated_slug_and_has_local_visual_fallback(self) -> None:
        self.assertIn("/api/playbook?lab=${encodeURIComponent(slug)}", self.html)
        self.assertIn("/data/playbook/lab/${encodeURIComponent(slug)}.json", self.html)
        self.assertIn("const LAB_SLUG_RE = /^[a-z0-9][a-z0-9-]{0,79}$/;", self.html)

    def test_protocol_and_published_results_have_distinct_honest_states(self) -> None:
        self.assertIn("Protocol · no results yet", self.html)
        self.assertIn("60-second verdict", self.html)
        self.assertIn("No winner is shown before all ${plannedRunCount} runs pass review.", self.html)
        self.assertIn("const plannedRunCount = 3 *", self.html)
        self.assertIn("conditionStats", self.html)
        self.assertIn("median", self.html)

    def test_result_comparison_is_semantic_and_derived_from_runs(self) -> None:
        self.assertIn('<table class="lab-results">', self.html)
        self.assertIn('<th scope="col">Condition</th>', self.html)
        self.assertIn("run.success === true", self.html)
        self.assertIn("quality_score", self.html)
        self.assertIn("duration_ms", self.html)
        self.assertIn("cost_usd", self.html)
        self.assertIn("input_tokens", self.html)
        self.assertIn("output_tokens", self.html)
        self.assertIn("interventions", self.html)
        self.assertIn("recovery_events", self.html)
        self.assertIn("unnecessary_actions", self.html)
        self.assertIn("trajectory_summary", self.html)
        self.assertIn("Run receipts", self.html)

    def test_artifacts_are_allowlisted_and_open_safely(self) -> None:
        self.assertIn("function safePublicUrl", self.html)
        self.assertIn("url.protocol !== 'https:'", self.html)
        self.assertIn("raw.startsWith('/lab-artifacts/')", self.html)
        self.assertIn('target="_blank" rel="noopener"', self.html)
        self.assertIn("skill_lab_artifact_open", self.html)

    def test_measurement_and_finishability_are_explicit(self) -> None:
        self.assertIn("skill_lab_detail_view", self.html)
        self.assertIn("skill_lab_verdict_view", self.html)
        self.assertIn("skill_lab_complete", self.html)
        self.assertIn('id="labFinish"', self.html)
        self.assertIn("That's the Lab record", self.html)
        self.assertIn("skillLabMeetsVisibility(entries, threshold)", self.html)

    def test_loading_is_bounded_and_errors_replace_loading_metadata(self) -> None:
        self.assertIn("function fetchWithTimeout", self.html)
        self.assertIn("AbortController", self.html)
        self.assertIn("fetchWithTimeout(`/api/playbook?lab=", self.html)
        self.assertIn("meta.textContent = 'Lab record unavailable'", self.html)

    def test_restricted_storage_cannot_block_record_loading(self) -> None:
        apply_theme = self.html.split("function applyTheme(theme)", 1)[1].split(
            "function initThemeToggle", 1
        )[0]
        self.assertIn("try {", apply_theme)
        self.assertIn("localStorage.setItem('theme', theme)", apply_theme)

    def test_pinned_experimental_variable_is_visible(self) -> None:
        self.assertIn("<dt>Reasoning effort</dt>", self.html)
        self.assertIn("<dt>Skill</dt>", self.html)
        self.assertIn("skill.revision", self.html)
        self.assertIn("skill.sha256", self.html)

    def test_subscription_cta_is_attributed_without_collecting_email(self) -> None:
        self.assertIn("/subscribe?ref=skill_lab&lab_id=", self.html)
        self.assertIn('data-subscribe-placement="skill_lab_end"', self.html)
        self.assertNotIn("email:", self.html)

    def test_mobile_layout_and_actions_meet_floor(self) -> None:
        self.assertIn("@media (max-width:620px)", self.html)
        self.assertIn("grid-template-columns:1fr;", self.html)
        self.assertIn("min-height:44px", self.html)
        self.assertIn("overflow-x:auto", self.html)


if __name__ == "__main__":
    unittest.main()
