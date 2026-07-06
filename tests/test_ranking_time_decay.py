from __future__ import annotations

import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from pipeline.ranking import stage_c_score_and_select, time_decay_factor


NOW = datetime(2026, 7, 6, 12, 0, tzinfo=timezone.utc)


class RankingTimeDecayTest(unittest.TestCase):
    CFG = {
        "slots": {
            "frontier_official": {
                "max_items": 2,
                "max_per_source": 2,
                "blend": {"alpha": 1.0, "beta": 0.0},
            }
        },
        "time_decay": {
            "enabled": True,
            "half_life_hours": 24,
            "floor": 0.25,
        },
    }

    def test_factor_half_life_decays_smoothly_to_configured_floor(self) -> None:
        with patch("pipeline.ranking._now_utc", return_value=NOW):
            fresh = time_decay_factor("2026-07-06T12:00:00Z", self.CFG, "frontier_official")
            one_half_life = time_decay_factor("2026-07-05T12:00:00Z", self.CFG, "frontier_official")
            far_older = time_decay_factor("2026-06-29T12:00:00Z", self.CFG, "frontier_official")

        self.assertAlmostEqual(fresh, 1.0, places=6)
        self.assertAlmostEqual(one_half_life, 0.625, places=6)
        self.assertGreater(far_older, 0.25)
        self.assertLess(far_older, one_half_life)

    def test_stage_c_applies_decay_after_normal_slot_score(self) -> None:
        fresh = {
            "id": "fresh",
            "source": "openai_blog",
            "slot": "frontier_official",
            "title": "Fresh agent eval update",
            "summary": "agent eval benchmark",
            "published": "2026-07-06T12:00:00Z",
            "freshness": 1.0,
            "url": "https://example.com/fresh",
        }
        stale = {
            "id": "stale",
            "source": "openai_blog",
            "slot": "frontier_official",
            "title": "Older agent eval update",
            "summary": "agent eval benchmark",
            "published": "2026-07-02T12:00:00Z",
            "freshness": 1.0,
            "url": "https://example.com/stale",
        }
        labels = {
            "fresh": {"fit_agentic_platform": 4, "actionability": 4, "novelty": 3, "evidence_quality": 3, "hype_risk": 1},
            "stale": {"fit_agentic_platform": 4, "actionability": 4, "novelty": 3, "evidence_quality": 3, "hype_risk": 1},
        }

        with (
            patch("pipeline.ranking._now_utc", return_value=NOW),
            patch("pipeline.ranking.label_items", return_value=(labels, {"llm_called": 0, "cache_hits": 0})),
        ):
            selected, _diag = stage_c_score_and_select({"frontier_official": [stale, fresh]}, self.CFG, llm_budget=0)

        out = selected["frontier_official"]
        self.assertEqual([x["id"] for x in out], ["fresh", "stale"])
        self.assertAlmostEqual(out[0]["time_decay_factor"], 1.0, places=3)
        self.assertLess(out[1]["time_decay_factor"], 0.35)
        self.assertLess(out[1]["final_score"], out[1]["pre_decay_score"])

    def test_disabled_decay_keeps_factor_neutral(self) -> None:
        cfg = {"time_decay": {"enabled": False}}
        with patch("pipeline.ranking._now_utc", return_value=NOW):
            self.assertEqual(time_decay_factor("2026-07-02T12:00:00Z", cfg, "frontier_official"), 1.0)


if __name__ == "__main__":
    unittest.main()
