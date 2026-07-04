from __future__ import annotations

import unittest
from pathlib import Path

from pipeline import render_static_pages as render


ROOT = Path(__file__).resolve().parents[1]


class StorylineIndexSurfaceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = (ROOT / "web" / "storyline.html").read_text(encoding="utf-8")

    def test_index_uses_story_trace_hierarchy(self) -> None:
        self.assertIn("Stories do not end at launch.", self.html)
        self.assertIn("Latest change", self.html)
        self.assertIn("Builder action:", self.html)
        self.assertIn("Open evidence trace", self.html)
        self.assertIn("sl-mini-track", self.html)

    def test_index_keeps_following_filter_and_local_preview_fallback(self) -> None:
        self.assertIn('data-list-mode="following"', self.html)
        self.assertIn("ai_feed_storyline_follows_v1", self.html)
        self.assertIn("'/data/storylines/index.json'", self.html)

    def test_index_has_responsive_and_reduced_motion_rules(self) -> None:
        self.assertIn("@media (max-width: 560px)", self.html)
        self.assertIn("@media (prefers-reduced-motion:reduce)", self.html)

    def test_storyline_detail_registers_translation_surface_and_blocks(self) -> None:
        storyline = {
            "slug": "agent-memory",
            "label": "Agent memory moves from demos to production",
            "first_seen": "2026-06-20T00:00:00+00:00",
            "last_updated": "2026-06-22T00:00:00+00:00",
            "item_count": 2,
            "source_count": 2,
            "day_count": 2,
            "latest_title": "Memory systems get production guardrails",
            "editorial": {
                "whats_new": "A production rollout added retention controls.",
                "take_for_builders": "Treat memory as an operational dependency.",
                "tldr": "Agent memory is shifting from demo state to production infrastructure.",
                "beats": [
                    {
                        "kicker": "Launch",
                        "tone": "launch",
                        "headline": "A memory feature launched",
                        "summary": "The first release made session recall available.",
                        "sids": ["story-one"],
                    }
                ],
            },
            "days": [
                {
                    "date": "2026-06-20",
                    "items": [
                        {
                            "sid": "story-one",
                            "url": "https://example.com/memory",
                            "title": "A memory feature launched",
                            "source": "example",
                            "published": "2026-06-20T00:00:00+00:00",
                            "editor_note": "Session recall became configurable.",
                        }
                    ],
                }
            ],
        }
        body = render.render_storyline_body(storyline, set())
        self.assertIn('class="sl-latest" aria-labelledby="latestChangeLabel" data-translate-block', body)
        self.assertIn('class="sl-builder-take" data-translate-block', body)
        self.assertIn('class="sl-background-body" data-translate-block', body)
        self.assertIn('class="sl-spine" data-translate-block', body)

        html = render.render_page(
            title="Agent memory moves from demos to production — AI storyline",
            description="Agent memory is shifting from demo state to production infrastructure.",
            canonical="https://www.llm-digest.com/storyline/agent-memory",
            published="2026-06-20T00:00:00+00:00",
            h1="AI Storyline",
            meta_line="2 items · 2 sources · 2 days",
            json_href="/api/storylines?slug=agent-memory",
            archive="",
            recap_title="Agent memory moves from demos to production",
            recap_range="",
            title_html=render.storyline_hero(storyline),
            intro_html="",
            body_html=body,
            extra_js=render.STORYLINE_FOLLOW_JS + render.STORYLINE_ARC_JS,
            extra_css=render.STORYLINE_ARC_CSS,
        )
        self.assertIn('data-local-translate-surface="storylines"', html)
        self.assertIn('data-translate-ui-slot', html)


if __name__ == "__main__":
    unittest.main()
