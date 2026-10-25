from __future__ import annotations

import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import yaml

from pipeline.ranking import stage_a_prefilter


class RankingPrefilterTest(unittest.TestCase):
    def test_pool_coverage_handles_items_without_ids(self) -> None:
        now = datetime(2026, 8, 28, 12, 0, tzinfo=timezone.utc)
        items = [
            {
                "source": "claude_blog",
                "title": "Older Claude agent engineering update",
                "summary": "A practical agent update.",
                "url": "https://claude.com/blog/older-agent-update",
                "published": "2026-08-28T10:00:00+00:00",
            },
            {
                "source": "openai_blog",
                "title": "Fresh platform update",
                "summary": "A platform update.",
                "url": "https://openai.com/index/platform-update",
                "published": "2026-08-28T12:00:00+00:00",
            },
        ]
        cfg = {
            "candidate_pool_cap": 1,
            "slots": {
                "frontier_official": {
                    "sources": ["claude_blog", "openai_blog"],
                    "freshness_hours": 240,
                    "max_per_source": 1,
                }
            },
        }
        profile = {
            "selection": {"exclude_title_regex": []},
            "off_topic": {"enabled": False},
        }

        with patch("pipeline.ranking._now_utc", return_value=now):
            candidates, _diag = stage_a_prefilter(
                items,
                cfg,
                profile,
                {"claude_blog": 1.0, "openai_blog": 1.0},
            )

        self.assertEqual(
            {item["url"] for item in candidates},
            {item["url"] for item in items},
        )

    def test_pool_coverage_keeps_source_item_for_later_slot_scoring(self) -> None:
        now = datetime(2026, 8, 28, 12, 0, tzinfo=timezone.utc)
        target_url = "https://claude.com/blog/how-warp-builds-self-improving-agents-on-claude"
        items = [
            {
                "id": "claude-target",
                "source": "claude_blog",
                "title": "How Warp builds self-improving agents on Claude",
                "summary": "A development pattern for self-improving agents.",
                "url": target_url,
                "published": "2026-08-28T10:00:00+00:00",
            },
            {
                "id": "claude-sibling",
                "source": "claude_blog",
                "title": "A newer Claude agent engineering update",
                "summary": "A practical agent update.",
                "url": "https://claude.com/blog/newer-agent-update",
                "published": "2026-08-28T11:00:00+00:00",
            },
            {
                "id": "openai-1",
                "source": "openai_blog",
                "title": "Fresh platform update one",
                "summary": "A platform update.",
                "url": "https://openai.com/index/platform-update-one",
                "published": "2026-08-28T12:00:00+00:00",
            },
            {
                "id": "openai-2",
                "source": "openai_blog",
                "title": "Fresh platform update two",
                "summary": "Another platform update.",
                "url": "https://openai.com/index/platform-update-two",
                "published": "2026-08-28T11:30:00+00:00",
            },
            {
                "id": "openai-3",
                "source": "openai_blog",
                "title": "Fresh platform update three",
                "summary": "Yet another platform update.",
                "url": "https://openai.com/index/platform-update-three",
                "published": "2026-08-28T11:15:00+00:00",
            },
        ]
        cfg = {
            "candidate_pool_cap": 4,
            "slots": {
                "frontier_official": {
                    "sources": ["claude_blog", "openai_blog"],
                    "freshness_hours": 240,
                    "max_per_source": 2,
                }
            },
        }
        profile = {
            "selection": {"exclude_title_regex": []},
            "off_topic": {"enabled": False},
        }

        with patch("pipeline.ranking._now_utc", return_value=now):
            candidates, _diag = stage_a_prefilter(
                items,
                cfg,
                profile,
                {"claude_blog": 1.0, "openai_blog": 1.0},
            )

        self.assertIn(target_url, {item["url"] for item in candidates})


class OffTopicGateTest(unittest.TestCase):
    def _profile(self) -> dict:
        path = Path(__file__).resolve().parents[1] / "config" / "profile.yaml"
        return yaml.safe_load(path.read_text(encoding="utf-8"))

    def test_eval_signal_rescues_a_healthcare_phrase(self) -> None:
        now = datetime(2026, 10, 24, 17, 3, tzinfo=timezone.utc)
        items = [
            {
                "id": "eval-post",
                "source": "hamel_husain",
                "title": "“It’s Hard to Eval” Is a Product Smell",
                "summary": "Examples include a medical records agent and a patient support workflow.",
                "url": "https://hamel.dev/blog/posts/eval-smell/",
                "published": "2026-10-24T12:00:00+00:00",
            },
            {
                "id": "game-post",
                "source": "simon_willison",
                "title": "battledrones v14: Compass Rose, a four player map",
                "summary": "Claude Opus 4.5 added a new map with AI players for the WebSocket multiplayer mode.",
                "url": "https://simonwillison.net/2026/Oct/24/battledrones/",
                "published": "2026-10-24T03:59:57+00:00",
            },
            {
                "id": "game-post-two",
                "source": "simon_willison",
                "title": "Battle Drones - a vibe coded RTS with audio-based multiplayer",
                "summary": "A side project with AI-controlled units and a Claude-generated map editor.",
                "url": "https://simonwillison.net/2026/Oct/23/battle-drones/",
                "published": "2026-10-23T03:59:57+00:00",
            },
        ]
        cfg = {
            "candidate_pool_cap": 10,
            "slots": {
                "practitioner_analysis": {
                    "sources": ["hamel_husain", "simon_willison"],
                    "freshness_hours": 240,
                    "max_per_source": 2,
                }
            },
        }
        with patch("pipeline.ranking._now_utc", return_value=now):
            candidates, diag = stage_a_prefilter(items, cfg, self._profile(), {})
        titles = {item["title"] for item in candidates}
        self.assertIn("“It’s Hard to Eval” Is a Product Smell", titles)
        self.assertNotIn("battledrones v14: Compass Rose, a four player map", titles)
        self.assertNotIn("Battle Drones - a vibe coded RTS with audio-based multiplayer", titles)
        self.assertEqual(diag["prefilter_reasons"].get("off_topic", 0), 0)
        self.assertEqual(diag["prefilter_reasons"]["hard_exclude"], 2)


if __name__ == "__main__":
    unittest.main()
