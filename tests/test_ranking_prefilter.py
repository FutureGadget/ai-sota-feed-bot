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

    def test_pool_reserve_sends_every_fresh_video_to_the_judge(self) -> None:
        """A single-source lane must not be starved down to its freshest item.

        Regression: video_watch is the only lane with one source and
        max_per_source 1, so the per-source reserve admitted exactly one video
        and the news pool cap swallowed the rest. Only the newest video was ever
        judged, so a promo could take the lane's single seat while the real
        episode was never scored.
        """
        now = datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc)
        videos = [
            {
                "id": f"video-{index}",
                "source": "ai_native_dev",
                "title": f"Episode {index}: running agents in production",
                "summary": "A long-form episode about agent infrastructure.",
                "url": f"https://youtu.be/video{index}",
                "published": f"2026-10-{25 + index:02d}T12:00:00+00:00",
                "type": "video",
            }
            for index in range(5)
        ]
        # A full news pool of fresher, higher-scoring items that would otherwise
        # take every seat after the reserve.
        news = [
            {
                "id": f"news-{index}",
                "source": "openai_blog",
                "title": f"Fresh platform update {index}",
                "summary": "A platform update about agent infrastructure.",
                "url": f"https://openai.com/index/update-{index}",
                "published": "2026-10-31T11:00:00+00:00",
            }
            for index in range(20)
        ]
        slots = {
            "video_watch": {
                "sources": ["ai_native_dev"],
                "freshness_hours": 240,
                "max_items": 2,
                "max_per_source": 1,
            },
            "frontier_official": {
                "sources": ["openai_blog"],
                "freshness_hours": 240,
                "max_items": 7,
                "max_per_source": 3,
            },
        }
        profile = {"selection": {"exclude_title_regex": []}, "off_topic": {"enabled": False}}
        base = {"slots": slots, "candidate_pool_cap": 8}

        with patch("pipeline.ranking._now_utc", return_value=now):
            starved, _ = stage_a_prefilter(
                videos + news, base, profile, {"ai_native_dev": 1.0, "openai_blog": 1.0}
            )
            reserved, _ = stage_a_prefilter(
                videos + news,
                {**base, "slots": {**slots, "video_watch": {**slots["video_watch"], "pool_reserve": 5}}},
                profile,
                {"ai_native_dev": 1.0, "openai_blog": 1.0},
            )

        # Without a separate reserve the lane is capped at max_per_source.
        self.assertEqual(sum(1 for item in starved if item["source"] == "ai_native_dev"), 1)
        # With it, the whole fresh window reaches the judge.
        self.assertEqual(sum(1 for item in reserved if item["source"] == "ai_native_dev"), 5)

    def test_pool_reserve_defaults_to_max_per_source(self) -> None:
        """Every lane keeps its current reserve unless it opts out."""
        now = datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc)
        items = [
            {
                "id": f"openai-{index}",
                "source": "openai_blog",
                "title": f"Platform update {index}",
                "summary": "A platform update about agent infrastructure.",
                "url": f"https://openai.com/index/update-{index}",
                "published": f"2026-10-31T{10 - index:02d}:00:00+00:00",
            }
            for index in range(5)
        ]
        news = [
            {
                "id": f"other-{index}",
                "source": "simon_willison",
                "title": f"Practitioner note {index}",
                "summary": "A note about agent infrastructure.",
                "url": f"https://simonwillison.net/{index}",
                "published": "2026-10-31T11:30:00+00:00",
            }
            for index in range(20)
        ]
        # The cap equals the default reserve, so nothing else can fill a seat.
        cfg = {
            "candidate_pool_cap": 3,
            "slots": {
                "frontier_official": {
                    "sources": ["openai_blog"],
                    "freshness_hours": 240,
                    "max_per_source": 2,
                },
                "practitioner_analysis": {
                    "sources": ["simon_willison"],
                    "freshness_hours": 240,
                    "max_per_source": 1,
                },
            },
        }
        profile = {"selection": {"exclude_title_regex": []}, "off_topic": {"enabled": False}}
        with patch("pipeline.ranking._now_utc", return_value=now):
            candidates, _diag = stage_a_prefilter(
                items + news, cfg, profile, {"openai_blog": 1.0, "simon_willison": 1.0}
            )
        self.assertEqual(sum(1 for item in candidates if item["source"] == "openai_blog"), 2)
        self.assertEqual(sum(1 for item in candidates if item["source"] == "simon_willison"), 1)


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
