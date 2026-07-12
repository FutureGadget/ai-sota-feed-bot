from __future__ import annotations

import unittest
from unittest.mock import patch

from pipeline.ranking import _infer_item_type, stage_c_score_and_select


class RankingReleaseClassificationTest(unittest.TestCase):
    def test_opening_release_marker_classifies_practitioner_post_as_release(self) -> None:
        item = {
            "source": "simon_willison",
            "title": "sqlite-utils 4.1",
            "summary": "<p><strong>Release:</strong> sqlite-utils 4.1</p><p>Minor new features.</p>",
            "url": "https://example.com/sqlite-utils-4-1",
        }

        self.assertEqual(_infer_item_type(item, "practitioner_analysis"), "release")

    def test_incidental_release_mention_does_not_reclassify_analysis(self) -> None:
        item = {
            "source": "simon_willison",
            "title": "The new GPT-5.6 family: Luna, Terra, Sol",
            "summary": "Analysis of the model family, including its release schedule and pricing.",
            "url": "https://example.com/gpt-5-6-family",
        }

        self.assertEqual(_infer_item_type(item, "practitioner_analysis"), "news")

    def test_inferred_release_type_is_authoritative_for_served_category(self) -> None:
        item = {
            "id": "sqlite-utils-4-1",
            "source": "simon_willison",
            "slot": "practitioner_analysis",
            "title": "sqlite-utils 4.1",
            "summary": "<p><strong>Release:</strong> sqlite-utils 4.1</p>",
            "published": "2026-07-11T23:50:20Z",
            "freshness": 1.0,
            "url": "https://example.com/sqlite-utils-4-1",
        }
        cfg = {
            "slots": {
                "practitioner_analysis": {
                    "max_items": 1,
                    "max_per_source": 1,
                    "blend": {"alpha": 1.0, "beta": 0.0},
                }
            },
            "time_decay": {"enabled": False},
        }
        labels = {
            item["id"]: {
                "category": "platform",
                "fit_agentic_platform": 3,
                "actionability": 3,
                "novelty": 3,
                "evidence_quality": 3,
                "hype_risk": 1,
            }
        }

        with patch(
            "pipeline.ranking.label_items",
            return_value=(labels, {"llm_called": 0, "cache_hits": 0}),
        ):
            selected, _diag = stage_c_score_and_select(
                {"practitioner_analysis": [item]}, cfg, llm_budget=0
            )

        output = selected["practitioner_analysis"][0]
        self.assertEqual(output["type"], "release")
        self.assertEqual(output["llm_category"], "release")


if __name__ == "__main__":
    unittest.main()
