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

    def test_related_stories_reject_same_source_and_one_broad_topic(self) -> None:
        current = {
            "sid": "aaaaaaaaaaaaaaaa",
            "title": "Claude Fable is relentlessly proactive",
            "source": "example",
            "type": "news",
            "matched_topics": ["agent", "claude code"],
            "published": "2026-06-11T12:00:00+00:00",
        }
        unrelated = {
            "sid": "bbbbbbbbbbbbbbbb",
            "title": "Evaluate agents with a generic benchmark",
            "source": "example",
            "type": "news",
            "matched_topics": ["agent", "claude code"],
            "published": "2026-06-10T12:00:00+00:00",
        }

        related = render.related_stories(
            current,
            {current["sid"]: current, unrelated["sid"]: unrelated},
        )

        self.assertEqual(related, [])

    def test_storyline_related_stories_only_show_thread_history(self) -> None:
        current = {
            "sid": "aaaaaaaaaaaaaaaa",
            "title": "Claude Fable is relentlessly proactive",
            "source": "source_a",
            "type": "news",
            "published": "2026-06-11T12:00:00+00:00",
        }
        anchor_match = {
            "sid": "bbbbbbbbbbbbbbbb",
            "title": "Initial impressions of Claude Fable 5",
            "source": "source_b",
            "type": "news",
            "published": "2026-06-10T12:00:00+00:00",
        }
        thread_match = {
            "sid": "cccccccccccccccc",
            "title": "Access changes after the model launch",
            "source": "source_c",
            "type": "news",
            "published": "2026-06-09T12:00:00+00:00",
        }
        storyline_of = {
            current["sid"]: ("claude-fable", "Claude Fable"),
            thread_match["sid"]: ("claude-fable", "Claude Fable"),
        }

        related = render.related_stories(
            current,
            {
                current["sid"]: current,
                anchor_match["sid"]: anchor_match,
                thread_match["sid"]: thread_match,
            },
            storyline_of,
        )

        self.assertEqual([item["sid"] for item in related], [thread_match["sid"]])

    def test_non_storyline_related_stories_keep_specific_anchor(self) -> None:
        current = {
            "sid": "aaaaaaaaaaaaaaaa",
            "title": "Claude Fable is relentlessly proactive",
            "source": "source_a",
            "type": "news",
            "published": "2026-06-11T12:00:00+00:00",
        }
        anchor_match = {
            "sid": "bbbbbbbbbbbbbbbb",
            "title": "Initial impressions of Claude Fable 5",
            "source": "source_b",
            "type": "news",
            "published": "2026-06-10T12:00:00+00:00",
        }

        related = render.related_stories(
            current,
            {current["sid"]: current, anchor_match["sid"]: anchor_match},
        )

        self.assertEqual([item["sid"] for item in related], [anchor_match["sid"]])

    def test_storyline_body_prioritizes_latest_change_and_builder_action(self) -> None:
        storyline = {
            "slug": "claude-fable",
            "label": "Claude Fable",
            "editorial": {
                "status": {
                    "state": "Available with data sharing",
                    "tone": "now",
                    "changed": "2026-06-20",
                    "detail": "Access returned under changed data terms.",
                },
                "whats_new": "Access returned on Bedrock with data sharing required.",
                "tldr": "The model launched, was suspended, and later returned.",
                "take_for_builders": "Review retention terms before restoring traffic.",
                "beats": [
                    {
                        "kicker": "NOW",
                        "tone": "now",
                        "headline": "Access returns with changed terms",
                        "sids": ["aaaaaaaaaaaaaaaa"],
                    }
                ],
                "open_questions": ["Will private inference return?"],
            },
            "days": [
                {
                    "date": "2026-06-20",
                    "items": [
                        {
                            "sid": "aaaaaaaaaaaaaaaa",
                            "title": "Access returns",
                            "url": "https://example.com/access",
                            "published": "2026-06-20T10:00:00+00:00",
                            "source": "example",
                        }
                    ],
                }
            ],
        }

        body = render.render_storyline_body(storyline, set())

        self.assertLess(body.index("Latest change"), body.index("Background — the story so far"))
        self.assertLess(body.index("For builders"), body.index("The Arc"))
        self.assertIn('role="tablist"', body)
        self.assertIn('role="tabpanel"', body)
        self.assertIn("<details class=\"sl-background\">", body)
        self.assertIn("<details class=\"sl-agents\">", body)
        self.assertEqual(body.count("Review retention terms before restoring traffic."), 1)
        self.assertNotIn("Access returned under changed data terms.", body)

    def test_storyline_access_track_explains_every_phase_on_small_screens(self) -> None:
        status = {
            "track": [
                {"label": "available", "detail": "Jun 9–13", "tone": "launch", "weight": 40},
                {"label": "suspended", "detail": "Jun 13–20", "tone": "alert", "weight": 38},
                {"label": "returned", "detail": "Jun 20 → now", "tone": "now", "weight": 22},
            ]
        }

        html = render._sl_access_track(status)

        self.assertIn("sl-track-legend", html)
        self.assertIn("available", html)
        self.assertIn("suspended", html)
        self.assertIn("returned", html)


if __name__ == "__main__":
    unittest.main()
