"""The served Brief's top-band rules stay in step with the ranker's."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))

import editorial  # noqa: E402


class BriefTopBandConfigTest(unittest.TestCase):
    def setUp(self):
        self.brief = editorial.load_config().get("brief_top_band") or {}
        ranking = yaml.safe_load((ROOT / "config" / "ranking.yaml").read_text(encoding="utf-8"))
        self.ranker = ranking.get("top_band_constraints") or {}

    def test_serving_rules_match_the_ranker(self):
        # config/ranking.yaml governs each edition; config/editorial.yaml
        # governs the ledger-served Brief. They describe the same front page.
        self.assertTrue(self.brief.get("enabled"))
        self.assertEqual(self.brief.get("top_n"), self.ranker.get("top_n"))
        self.assertEqual(self.brief.get("max_research"), self.ranker.get("max_research_in_top_n"))
        self.assertEqual(
            bool(self.brief.get("lead_excludes_research")),
            bool(self.ranker.get("lead_excludes_research")),
        )
        self.assertEqual(
            bool(self.brief.get("lead_excludes_video")),
            bool(self.ranker.get("lead_excludes_video")),
        )

    def test_rules_reach_the_api_through_the_editorial_artifact(self):
        source = (ROOT / "pipeline" / "editorial.py").read_text(encoding="utf-8")
        self.assertIn('"brief_top_band": cfg.get("brief_top_band", {}) or {}', source)
        reader = (ROOT / "lib" / "editorial.js").read_text(encoding="utf-8")
        self.assertIn("brief_top_band", reader)


if __name__ == "__main__":
    unittest.main()
