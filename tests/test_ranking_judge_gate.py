from __future__ import annotations

import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from pipeline.ranking import enforce_top_band_constraints, stage_a_prefilter, stage_c_score_and_select


def _item(item_id: str, **extra):
    payload = {
        "id": item_id,
        "source": "openai_blog",
        "title": f"Agent platform update {item_id}",
        "summary": "A concrete agent platform update with serving details.",
        "url": f"https://example.com/{item_id}",
        "published": "2026-10-24T09:00:00+00:00",
    }
    payload.update(extra)
    return payload


class JudgeGatePrefilterTest(unittest.TestCase):
    def test_gate_drops_high_confidence_verdict(self) -> None:
        now = datetime(2026, 10, 24, 12, 0, tzinfo=timezone.utc)
        items = [
            _item("keep", judge_verdict="keep", judge_score=0.8),
            _item("drop", judge_verdict="drop", judge_score=0.05),
        ]
        cfg = {
            "candidate_pool_cap": 10,
            "judge_gate": {"enabled": True, "drop_verdicts": ["drop"]},
            "slots": {
                "frontier_official": {
                    "sources": ["openai_blog"],
                    "freshness_hours": 240,
                    "max_per_source": 2,
                }
            },
        }
        profile = {"selection": {"exclude_title_regex": []}, "off_topic": {"enabled": False}}
        with patch("pipeline.ranking._now_utc", return_value=now):
            out, diag = stage_a_prefilter(items, cfg, profile, {"openai_blog": 1.0})
        self.assertEqual([item["id"] for item in out], ["keep"])
        self.assertEqual(diag["prefilter_reasons"]["judge_drop"], 1)

    def test_release_role_is_exempt_from_hard_drop(self) -> None:
        now = datetime(2026, 10, 24, 12, 0, tzinfo=timezone.utc)
        items = [
            _item(
                "release",
                source="claude_code_releases",
                source_role="release",
                judge_verdict="drop",
                judge_score=0.1,
                judge_category="release_note",
            )
        ]
        cfg = {
            "candidate_pool_cap": 10,
            "judge_gate": {
                "enabled": True,
                "drop_verdicts": ["drop"],
                "exempt_source_roles": ["release"],
                "exempt_categories": ["release_note"],
            },
            "slots": {
                "agent_tooling_releases": {
                    "sources": ["claude_code_releases"],
                    "freshness_hours": 240,
                    "max_per_source": 2,
                }
            },
        }
        profile = {"selection": {"exclude_title_regex": []}, "off_topic": {"enabled": False}}
        with patch("pipeline.ranking._now_utc", return_value=now):
            out, _diag = stage_a_prefilter(items, cfg, profile, {"claude_code_releases": 1.0})
        self.assertEqual([item["id"] for item in out], ["release"])

    def test_gate_disabled_keeps_drop_verdict(self) -> None:
        now = datetime(2026, 10, 24, 12, 0, tzinfo=timezone.utc)
        items = [_item("drop", judge_verdict="drop", judge_score=0.05)]
        cfg = {
            "candidate_pool_cap": 10,
            "judge_gate": {"enabled": False},
            "slots": {
                "frontier_official": {
                    "sources": ["openai_blog"],
                    "freshness_hours": 240,
                    "max_per_source": 2,
                }
            },
        }
        profile = {"selection": {"exclude_title_regex": []}, "off_topic": {"enabled": False}}
        with patch("pipeline.ranking._now_utc", return_value=now):
            out, _diag = stage_a_prefilter(items, cfg, profile, {"openai_blog": 1.0})
        self.assertEqual([item["id"] for item in out], ["drop"])


class JudgeAdjustmentStageCTest(unittest.TestCase):
    def test_judge_adjustment_changes_the_slot_score(self) -> None:
        cfg = {
            "judge_ranking": {"weight": 1.2},
            "slots": {
                "frontier_official": {
                    "max_items": 2,
                    "max_per_source": 2,
                    "blend": {"alpha": 1.0, "beta": 0.0},
                }
            },
            "time_decay": {"enabled": False},
        }
        boosted = _item("boosted", slot="frontier_official", freshness=1.0, judge_score=0.9, judge_verdict="keep")
        plain = _item("plain", slot="frontier_official", freshness=1.0, judge_score=0.1, judge_verdict="review")
        labels = {
            "boosted": {"fit_agentic_platform": 4, "actionability": 4, "novelty": 3, "evidence_quality": 3, "hype_risk": 1},
            "plain": {"fit_agentic_platform": 4, "actionability": 4, "novelty": 3, "evidence_quality": 3, "hype_risk": 1},
        }
        with patch("pipeline.ranking.label_items", return_value=(labels, {"llm_called": 0, "cache_hits": 0})):
            selected, _diag = stage_c_score_and_select({"frontier_official": [plain, boosted]}, cfg, llm_budget=0)
        out = selected["frontier_official"]
        self.assertEqual([item["id"] for item in out], ["boosted", "plain"])
        self.assertGreater(out[0]["pre_decay_score"], out[1]["pre_decay_score"])


class JudgeTopBandTest(unittest.TestCase):
    def test_drop_verdict_is_not_promoted(self) -> None:
        cfg = {
            "top_band_constraints": {
                "enabled": True,
                "top_n": 2,
                "min_frontier_official": 1,
                "min_anthropic_frontier": 0,
                "max_research_in_top_n": 3,
            }
        }
        items = [
            _item("practitioner", slot="practitioner_analysis", global_score=3.0),
            _item("other", slot="practitioner_analysis", global_score=2.9),
            _item("drop-frontier", slot="frontier_official", global_score=1.0, judge_verdict="drop"),
        ]
        out, _diag = enforce_top_band_constraints(items, cfg)
        self.assertNotIn("drop-frontier", [item["id"] for item in out[:2]])


if __name__ == "__main__":
    unittest.main()
