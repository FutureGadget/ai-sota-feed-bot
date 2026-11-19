from __future__ import annotations

import copy
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
sys.path.insert(0, str(ROOT))

import community  # noqa: E402

RECAP = {
    "date": "2026-01-02",
    "categories": [
        {"name": "A", "articles": [{"title": "Item <one>", "url": "https://example.com/a"}]}
    ],
}
POST = {
    "kind": "daily",
    "edition": "2026-01-02",
    "threads": {
        "en": {
            "style": "reddit",
            "board": "r/llmdigest",
            "title": "Today",
            "author": "u/the_feed_agent",
            "score": 10,
            "body": ["Line one", "Line two"],
            "refs": ["https://example.com/a"],
            "comments": [
                {
                    "author": "u/x",
                    "score": 3,
                    "body": "hi <b>",
                    "replies": [{"author": "u/the_feed_agent", "is_op": True, "score": 1, "body": "yo"}],
                },
                {"author": "u/y", "score": 9, "body": "top comment"},
            ],
        },
        "ko": {
            "style": "dcinside",
            "board": "갤",
            "title": "제목",
            "author": "피드요약봇",
            "tag": "(고닉)",
            "body": "본문",
            "refs": ["https://example.com/a"],
            "comments": [],
        },
    },
}


class CommunityValidationTest(unittest.TestCase):
    def test_valid_post_passes(self):
        self.assertEqual(community.validate(POST, RECAP, "daily", "2026-01-02"), [])

    def test_ref_outside_recap_fails(self):
        bad = copy.deepcopy(POST)
        bad["threads"]["en"]["refs"] = ["https://evil.example/x"]
        errs = community.validate(bad, RECAP, "daily", "2026-01-02")
        self.assertTrue(any("ref not in recap" in e for e in errs))

    def test_wrong_style_deep_replies_and_kind_mismatch_fail(self):
        bad = copy.deepcopy(POST)
        bad["threads"]["ko"]["style"] = "reddit"
        bad["threads"]["en"]["comments"][0]["replies"][0]["replies"] = [{"author": "u/y", "body": "z"}]
        bad["kind"] = "weekly"
        errs = community.validate(bad, RECAP, "daily", "2026-01-02")
        self.assertTrue(any("style must be" in e for e in errs))
        self.assertTrue(any("nested deeper" in e for e in errs))
        self.assertTrue(any("kind" in e for e in errs))

    def test_missing_recap_fails(self):
        self.assertTrue(community.validate(POST, None, "daily", "2026-01-02"))

    def test_committed_posts_validate(self):
        self.assertEqual(community.main(["--check"]), 0)


class CommunityRenderTest(unittest.TestCase):
    def test_post_body_escapes_counts_and_labels_fiction(self):
        html = community.render_post_body(POST, RECAP, "daily", "2026-01-02", "en")
        self.assertIn("hi &lt;b&gt;", html)
        self.assertIn("Item &lt;one&gt;", html)
        self.assertIn("Fictional thread", html)
        self.assertIn("Comments (3)", html)
        self.assertIn('href="/daily/2026-01-02"', html)

    def test_teaser_links_to_post_and_quotes_top_comment(self):
        html = community.render_teaser(POST, "daily", "2026-01-02", "en")
        self.assertIn('href="/community/daily/2026-01-02"', html)
        self.assertIn("top comment", html)
        self.assertIn("3 comments", html)
        ko_body = community.render_post_body(POST, RECAP, "daily", "2026-01-02", "ko")
        self.assertIn('href="/daily/2026-01-02"', ko_body)
        ko = community.render_teaser(POST, "daily", "2026-01-02", "ko")
        self.assertIn('href="/ko/community/daily/2026-01-02"', ko)

    def test_missing_post_or_locale_renders_nothing(self):
        self.assertEqual(community.render_teaser(None, "daily", "2026-01-02", "en"), "")
        only_en = copy.deepcopy(POST)
        del only_en["threads"]["ko"]
        self.assertEqual(community.render_post_body(only_en, RECAP, "daily", "2026-01-02", "ko"), "")

    def test_index_lists_posts(self):
        rows = [{"kind": "daily", "edition": "2026-01-02", "post": POST, "recap": RECAP}]
        html = community.render_index_list(rows, "en")
        self.assertIn("Daily recap thread · Jan 2, 2026", html)
        self.assertIn("/community/daily/2026-01-02", html)
        self.assertIn("2026년 1월 2일", community.render_index_list(rows, "ko"))

    def test_weekly_edition_label(self):
        recap = {"week": "2026-W46", "start": "2026-11-07", "end": "2026-11-13"}
        self.assertEqual(community.edition_label("weekly", recap, "en"), "Nov 7–13, 2026")
        self.assertEqual(community.edition_label("weekly", recap, "ko"), "2026년 11월 7일–11월 13일")


class CommunitySurfaceTest(unittest.TestCase):
    def test_routes_exist_in_the_worker_table(self):
        worker = (ROOT / "worker" / "src" / "index.js").read_text(encoding="utf-8")
        table = worker[worker.index("const STATIC_REWRITES") :]
        table = table[: table.index("];")]
        patterns = [re.compile(p) for p in re.findall(r"\[/(.+?)/,", table)]
        for path in (
            "/community",
            "/community/daily/2026-11-18",
            "/community/weekly/2026-W46",
            "/ko/community",
            "/ko/community/daily/2026-11-18",
            "/ko/community/weekly/2026-W46",
        ):
            with self.subTest(path=path):
                self.assertTrue(any(p.search(path) for p in patterns), path)

    def test_email_block_links_to_the_thread(self):
        import publish.publish_email as email

        cfg = email.load_config()
        rows = community.iter_posts()
        self.assertTrue(rows, "expected at least one committed community post")
        row = rows[0]
        block = email.render_community_email(cfg, row["kind"], row["edition"])
        self.assertIn("From the community", block)
        self.assertIn(f"/community/{row['kind']}/{row['edition']}?utm_source=", block)
        self.assertEqual(email.render_community_email(cfg, "daily", "1999-01-01"), "")

    def test_recap_skills_run_the_community_step(self):
        for kind in ("daily", "weekly"):
            skill = (ROOT / ".agents" / "skills" / f"{kind}-summary" / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn(".agents/skills/community-thread/SKILL.md", skill)
            self.assertLess(skill.index("community-thread"), skill.index("Validate + rebuild the index"))
            routine = (ROOT / ".agents" / "routines" / f"{kind}-recap" / "prompt.md").read_text(encoding="utf-8")
            self.assertIn("data/community/", routine)


if __name__ == "__main__":
    unittest.main()
