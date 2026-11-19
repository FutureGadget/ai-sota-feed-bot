from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))

import recap_thread  # noqa: E402

RECAP = {
    "date": "2026-01-02",
    "categories": [
        {"name": "A", "articles": [{"title": "Item <one>", "url": "https://example.com/a"}]}
    ],
}
SIDECAR = {
    "date": "2026-01-02",
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
                    "replies": [{"author": "u/the_feed_agent", "is_op": True, "body": "yo"}],
                }
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


class RecapThreadTest(unittest.TestCase):
    def test_valid_sidecar_passes(self):
        self.assertEqual(recap_thread.validate(SIDECAR, RECAP), [])

    def test_ref_outside_recap_fails(self):
        bad = copy.deepcopy(SIDECAR)
        bad["threads"]["en"]["refs"] = ["https://evil.example/x"]
        self.assertTrue(any("ref not in recap" in e for e in recap_thread.validate(bad, RECAP)))

    def test_wrong_style_and_deep_replies_fail(self):
        bad = copy.deepcopy(SIDECAR)
        bad["threads"]["ko"]["style"] = "reddit"
        bad["threads"]["en"]["comments"][0]["replies"][0]["replies"] = [{"author": "u/y", "body": "z"}]
        errs = recap_thread.validate(bad, RECAP)
        self.assertTrue(any("style must be" in e for e in errs))
        self.assertTrue(any("nested deeper" in e for e in errs))

    def test_render_escapes_and_labels_fiction(self):
        html = recap_thread.render_thread(SIDECAR, RECAP, "en")
        self.assertIn('id="thread"', html)
        self.assertIn("hi &lt;b&gt;", html)
        self.assertIn("Item &lt;one&gt;", html)
        self.assertIn("Fictional thread", html)
        self.assertIn("2 comments", html)

    def test_render_ko_and_missing_locale(self):
        self.assertIn("가상 스레드", recap_thread.render_thread(SIDECAR, RECAP, "ko"))
        self.assertEqual(recap_thread.render_thread(None, RECAP, "en"), "")
        only_en = copy.deepcopy(SIDECAR)
        del only_en["threads"]["ko"]
        self.assertEqual(recap_thread.render_thread(only_en, RECAP, "ko"), "")

    def test_committed_sidecars_validate(self):
        self.assertEqual(recap_thread.main(["--check"]), 0)


if __name__ == "__main__":
    unittest.main()
