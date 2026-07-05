from __future__ import annotations

import json
import unittest
from pathlib import Path

from pipeline import render_static_pages as render


ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "https://www.llm-digest.com"


class I18nStaticPagesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.stories = render.load_store()
        cls.storylines = {
            str(item.get("slug")): item
            for item in render.load_storyline_details()
            if isinstance(item, dict) and item.get("slug")
        }
        cls.wiki = render.load_wiki()
        cls.foundations = render.load_foundations()
        cls.artifact_paths = sorted((ROOT / "data" / "i18n" / "ko").glob("**/*.json"))
        cls.artifacts = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in cls.artifact_paths
            if path.name != "manifest.json"
        ]

    def test_korean_artifacts_are_fresh_for_their_sources(self) -> None:
        self.assertEqual(
            sorted(a["source_path"] for a in self.artifacts),
            [
                "/daily/2026-07-04",
                "/foundations/context-compaction-safety",
                "/story/ee2eab4f35a2124a",
                "/storyline/claude-fable",
                "/topic/agent-cost",
                "/weekly/2026-W27",
            ],
        )

        for artifact in self.artifacts:
            source = render.i18n_source_for_path(
                artifact["source_path"],
                self.stories,
                self.storylines,
                self.wiki,
                self.foundations,
            )
            self.assertIsNotNone(source, artifact["source_path"])
            self.assertEqual(artifact["source_hash"], render.i18n_source_hash(source))
            self.assertEqual(artifact["locale"], "ko")
            self.assertEqual(artifact["review_status"], "machine")

    def test_korean_pages_are_rendered_with_language_and_alternates(self) -> None:
        for artifact in self.artifacts:
            html_path = ROOT / "web" / "ko" / artifact["source_path"].strip("/")
            html_path = html_path.with_suffix(".html")
            html = html_path.read_text(encoding="utf-8")
            ko_url = f'{BASE_URL}/ko{artifact["source_path"]}'
            en_url = f'{BASE_URL}{artifact["source_path"]}'

            self.assertIn('<html lang="ko">', html)
            self.assertIn(f'<link rel="canonical" href="{ko_url}" />', html)
            self.assertIn(f'hreflang="ko" href="{ko_url}"', html)
            self.assertIn(f'hreflang="en" href="{en_url}"', html)
            self.assertIn(f'hreflang="x-default" href="{en_url}"', html)
            self.assertIn("English original", html)
            self.assertIn("기계 번역", html)

    def test_sitemap_and_vercel_rewrites_expose_korean_pages(self) -> None:
        sitemap = (ROOT / "web" / "sitemap.xml").read_text(encoding="utf-8")
        vercel = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
        rewrite_sources = {rewrite["source"] for rewrite in vercel["rewrites"]}

        for artifact in self.artifacts:
            self.assertIn(f"<loc>{BASE_URL}/ko{artifact['source_path']}</loc>", sitemap)

        self.assertIn("/ko/daily/:date(\\d{4}-\\d{2}-\\d{2})", rewrite_sources)
        self.assertIn("/ko/weekly/:week(\\d{4}-W\\d{2})", rewrite_sources)
        self.assertIn("/ko/story/:sid([0-9a-f]{16})", rewrite_sources)
        self.assertIn("/ko/storyline/:slug([a-z0-9-]+)", rewrite_sources)
        self.assertIn("/ko/topic/:slug([a-z0-9-]+)", rewrite_sources)
        self.assertIn("/ko/foundations/:slug([a-z0-9-]+)", rewrite_sources)


if __name__ == "__main__":
    unittest.main()
