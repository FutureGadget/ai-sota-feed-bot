from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

from pipeline import render_static_pages as render


ROOT = Path(__file__).resolve().parents[1]
PLAYBOOK_SCRIPTS = ROOT / ".agents" / "skills" / "playbook" / "scripts"
WEEKLY_SCRIPTS = ROOT / ".agents" / "skills" / "weekly-summary" / "scripts"


def load_playbook_common():
    path = PLAYBOOK_SCRIPTS / "playbook_common.py"
    spec = importlib.util.spec_from_file_location("playbook_common_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


pb = load_playbook_common()


def load_weekly_common():
    path = WEEKLY_SCRIPTS / "weekly_common.py"
    spec = importlib.util.spec_from_file_location("weekly_common_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


weekly = load_weekly_common()


def source_card(
    url: str = "https://example.com/paper",
    *,
    card_id: str = "pb-example",
    result: str = "Restore latency fell by 70% in the reported setup.",
    evidence_kind: str = "source-measured",
) -> dict:
    return {
        "id": card_id,
        "kind": "source-backed",
        "title": "Restore execution state on demand",
        "area": "Memory",
        "problem": "Reloading agent state creates high cold-start latency.",
        "apply": "Serialize execution state and memory-map it on restore.",
        "result": result,
        "effort": "medium",
        "source": "example",
        "source_url": url,
        "source_sid": pb.source_sid(url),
        "topic_url": "/topic/agent-memory",
        "evidence": {
            "kind": evidence_kind,
            "note": "Measured by the source in its benchmark setup.",
        },
    }


def edition(cards: list[dict]) -> dict:
    return {
        "date": "2026-06-22",
        "title": "Agent Builder's Playbook — Jun 22, 2026",
        "cards": cards,
    }


class PlaybookContractTest(unittest.TestCase):
    def test_input_article_carries_source_sid(self) -> None:
        url = "https://example.com/paper"
        article = pb.clean_article({"title": "Paper", "url": url})
        self.assertEqual(article["source_sid"], pb.source_sid(url))

    def test_source_backed_card_validates_with_matching_sid(self) -> None:
        self.assertEqual(pb.validate_edition(edition([source_card()])), [])

    def test_source_backed_card_rejects_mismatched_sid(self) -> None:
        card = source_card()
        card["source_sid"] = "0" * 16
        errors = pb.validate_edition(edition([card]))
        self.assertTrue(any("source_sid" in error for error in errors))

    def test_evergreen_card_needs_topic_url_but_not_source_provenance(self) -> None:
        card = {
            "id": "pb-evergreen",
            "kind": "evergreen",
            "title": "Compact long-running agent context",
            "problem": "Unbounded history degrades reasoning.",
            "apply": "Compact the working set on a token budget.",
            "result": "Context stays bounded across long tasks.",
            "topic_url": "/topic/context-compaction",
        }
        self.assertEqual(pb.validate_edition(edition([card])), [])

    def test_numeric_inference_is_rejected(self) -> None:
        card = source_card(evidence_kind="editorial-inference")
        errors = pb.validate_edition(edition([card]))
        self.assertTrue(any("numeric" in error for error in errors))

    def test_qualitative_inference_is_allowed(self) -> None:
        card = source_card(
            result="Restore latency should fall when less state is eagerly loaded.",
            evidence_kind="editorial-inference",
        )
        self.assertEqual(pb.validate_edition(edition([card])), [])

    def test_source_claim_must_be_worded_as_a_claim(self) -> None:
        card = source_card(
            result="Restore latency fell by 70%.",
            evidence_kind="source-claimed",
        )
        errors = pb.validate_edition(edition([card]))
        self.assertTrue(any("worded as a claim" in error for error in errors))

    def test_explicit_source_claim_is_allowed(self) -> None:
        card = source_card(
            result="The source reports a 70% latency reduction in its benchmark.",
            evidence_kind="source-claimed",
        )
        self.assertEqual(pb.validate_edition(edition([card])), [])

    def test_source_index_excludes_evergreen_cards(self) -> None:
        evergreen = {
            "id": "pb-evergreen",
            "kind": "evergreen",
            "title": "Compact context",
            "problem": "History grows.",
            "apply": "Compact it.",
            "result": "Bounded context.",
            "topic_url": "/topic/context-compaction",
        }
        index, errors = pb.build_source_index([edition([source_card(), evergreen])])
        self.assertEqual(errors, [])
        self.assertEqual(list(index), [pb.source_sid("https://example.com/paper")])

    def test_duplicate_source_cards_fail_index_build(self) -> None:
        first = source_card(card_id="pb-first")
        second = source_card(card_id="pb-second")
        index, errors = pb.build_source_index([edition([first, second])])
        self.assertEqual(index, {})
        self.assertTrue(any("duplicate" in error for error in errors))


class RecapPlaybookRenderingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.urls = [f"https://example.com/article-{n}" for n in range(1, 7)]
        self.recap = {
            "categories": [
                {
                    "name": "Research",
                    "slug": "research",
                    "articles": [
                        {"title": f"Article {n}", "url": url, "summary": "Summary"}
                        for n, url in enumerate(self.urls, 1)
                    ],
                }
            ]
        }
        self.index = {
            pb.source_sid(url): {
                **source_card(url, card_id=f"pb-{n}"),
                "edition_date": "2026-06-22",
            }
            for n, url in enumerate(self.urls, 1)
        }

    def test_exact_source_matches_render_with_weekly_cap(self) -> None:
        html = render.render_categories(
            self.recap,
            "weekly-link",
            playbook_index=self.index,
            playbook_cap=5,
        )
        self.assertEqual(html.count('class="playbook-takeaway"'), 5)
        self.assertIn("Playbook takeaway", html)
        self.assertIn("Serialize execution state", html)
        self.assertNotIn("pb-6", html)

    def test_similar_title_without_matching_url_does_not_render(self) -> None:
        recap = {
            "categories": [
                {
                    "name": "Research",
                    "articles": [
                        {
                            "title": "Restore execution state on demand",
                            "url": "https://different.example/paper",
                        }
                    ],
                }
            ]
        }
        html = render.render_categories(
            recap,
            "weekly-link",
            playbook_index=self.index,
            playbook_cap=5,
        )
        self.assertNotIn("playbook-takeaway", html)

    def test_missing_index_preserves_existing_recap_rendering(self) -> None:
        html = render.render_categories(
            self.recap,
            "daily-link",
            playbook_index=None,
            playbook_cap=3,
        )
        self.assertNotIn("playbook-takeaway", html)
        self.assertIn("Article 1", html)

    def test_takeaway_text_is_escaped(self) -> None:
        url = self.urls[0]
        index = {
            pb.source_sid(url): {
                **source_card(url),
                "apply": "<script>alert(1)</script>",
                "edition_date": "2026-06-22",
            }
        }
        html = render.render_categories(
            self.recap,
            "weekly-link",
            playbook_index=index,
            playbook_cap=5,
        )
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_same_source_renders_only_once_per_recap(self) -> None:
        url = self.urls[0]
        recap = {
            "categories": [
                {
                    "name": "One",
                    "articles": [
                        {"title": "First mention", "url": url},
                        {"title": "Duplicate mention", "url": url},
                    ],
                }
            ]
        }
        html = render.render_categories(
            recap,
            "weekly-link",
            playbook_index=self.index,
            playbook_cap=5,
        )
        self.assertEqual(html.count('class="playbook-takeaway"'), 1)


class WeeklyInputContractTest(unittest.TestCase):
    def test_clean_article_carries_story_sid(self) -> None:
        url = "https://example.com/release"
        article = weekly.clean_article({"title": "Release", "url": url, "type": "release"})
        self.assertEqual(article["source_sid"], pb.source_sid(url))

    def test_weekly_default_includes_engineering_content_types(self) -> None:
        script = (WEEKLY_SCRIPTS / "build_weekly_input.py").read_text(encoding="utf-8")
        self.assertIn('default="news,release,research,paper"', script)
        self.assertIn('"playbook_card_id"', script)


if __name__ == "__main__":
    unittest.main()
