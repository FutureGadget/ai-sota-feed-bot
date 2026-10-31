"""The video lane: preserve the collector's medium and keep it off the lead."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))

from ranking import _infer_item_type, enforce_top_band_constraints  # noqa: E402


def _item(source: str, slot: str, score: float, **extra) -> dict:
    item = {
        "source": source,
        "slot": slot,
        "global_score": score,
        "url": f"https://example.com/{source}/{score}",
        "title": f"{source} {score}",
    }
    item.update(extra)
    return item


class InferVideoTypeTest(unittest.TestCase):
    def test_video_type_is_not_overwritten(self) -> None:
        self.assertEqual(
            _infer_item_type({"source": "ai_native_dev", "type": "video", "title": "A talk"}, "video_watch"),
            "video",
        )

    def test_regular_items_still_infer_news(self) -> None:
        self.assertEqual(
            _infer_item_type({"source": "simon_willison", "title": "A post"}, "practitioner_analysis"),
            "news",
        )


class LeadExcludesVideoTest(unittest.TestCase):
    CFG = {
        "top_band_constraints": {
            "enabled": True,
            "top_n": 10,
            "min_frontier_official": 0,
            "min_anthropic_frontier": 0,
            "max_research_in_top_n": 99,
            "lead_excludes_video": True,
        }
    }

    def test_lifts_the_best_non_video_to_the_lead(self) -> None:
        items = [
            _item("ai_native_dev", "video_watch", 3.20, type="video"),
            _item("simon_willison", "practitioner_analysis", 3.10),
            _item("arxiv_cs_ai", "research_watch", 2.90),
        ]
        out, diag = enforce_top_band_constraints(items, self.CFG)
        self.assertEqual(out[0]["source"], "simon_willison")
        self.assertEqual(diag["video_lead_lifted"], 1)

    def test_no_op_when_every_band_item_is_video(self) -> None:
        items = [
            _item("ai_native_dev", "video_watch", 3.20, type="video"),
            _item("another_channel", "video_watch", 3.00, type="video"),
        ]
        out, diag = enforce_top_band_constraints(items, self.CFG)
        self.assertEqual(out[0]["source"], "ai_native_dev")
        self.assertEqual(diag["video_lead_lifted"], 0)
