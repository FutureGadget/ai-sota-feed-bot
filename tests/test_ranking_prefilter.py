from __future__ import annotations

import unittest
from datetime import datetime, timezone
from unittest.mock import patch

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


if __name__ == "__main__":
    unittest.main()
