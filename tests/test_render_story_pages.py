from __future__ import annotations

import unittest

from pipeline import render_static_pages as render


class StoryPageRenderingTest(unittest.TestCase):
    def test_story_body_prefers_brief_over_flattened_rss_body(self) -> None:
        rec = {
            "sid": "c9ab8f8aa14fe295",
            "title": "Claude Fable is relentlessly proactive",
            "url": "https://example.com/story",
            "summary": "Raw article paragraph. " * 100,
            "summary_1line": "A concise account of an agent autonomously debugging a browser issue.",
            "why_it_matters": "Matches feed focus: agent, claude code.",
            "image_url": "https://example.com/screenshot.jpg",
            "matched_topics": ["agent", "claude code"],
            "published": "2026-06-11T23:35:17+00:00",
        }

        body = render.render_story_body(rec, {rec["sid"]: rec})

        self.assertIn("In brief", body)
        self.assertIn("A concise account of an agent", body)
        self.assertNotIn("Raw article paragraph", body)
        self.assertNotIn("Why it matters", body)
        self.assertNotIn("Matches feed focus", body)
        self.assertIn('class="story-lead"', body)
        self.assertIn('class="story-img"', body)

    def test_story_brief_caps_raw_summary_fallback(self) -> None:
        rec = {
            "title": "A useful story",
            "summary": "word " * 200,
            "summary_1line": "",
        }

        brief = render.story_brief(rec)

        self.assertLessEqual(len(brief), render.STORY_BRIEF_MAX_CHARS)
        self.assertTrue(brief.endswith("…"))


if __name__ == "__main__":
    unittest.main()
