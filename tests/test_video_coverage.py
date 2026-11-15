from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "check_coverage", ROOT / ".agents" / "skills" / "video-common" / "scripts" / "check_coverage.py"
)
cc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cc)

RECAP = {
    "highlights": ["h0", "h1", "h2", "h3", "h4"],
    "categories": [{"slug": "a"}, {"slug": "b"}, {"slug": "c"}],
}
NARRATION = [{"id": f"s{n}", "text": "x"} for n in range(1, 7)]


def full() -> dict:
    return {
        "highlights": [
            {"i": 0, "scene": "s2", "tier": "lead"},
            {"i": 1, "scene": "s3", "tier": "deep"},
            {"i": 2, "scene": "s4", "tier": "deep"},
            {"i": 3, "scene": "s5", "tier": "quick"},
            {"i": 4, "scene": "s5", "tier": "quick"},
        ],
        "categories": [{"slug": "a", "scene": "s2"}, {"slug": "b", "scene": "s3"}, {"slug": "c", "scene": "s5"}],
    }


def has(errors: list[str], text: str) -> bool:
    return any(text in e for e in errors)


class VideoCoverageTest(unittest.TestCase):
    def test_complete_mapping_passes(self):
        self.assertEqual(cc.check(RECAP, NARRATION, full(), "daily"), [])

    def test_unmapped_highlight_and_category_fail(self):
        cov = full()
        cov["highlights"].pop()
        cov["categories"].pop()
        errors = cc.check(RECAP, NARRATION, cov)
        self.assertTrue(has(errors, "highlights: i 4"))
        self.assertTrue(has(errors, "categories: slug 'c'"))

    def test_cut_needs_reason_and_is_capped(self):
        cov = full()
        cov["highlights"][4] = {"i": 4, "cut": ""}
        self.assertTrue(has(cc.check(RECAP, NARRATION, cov), "needs a scene or a cut reason"))
        cov = full()
        for i in (3, 4):
            cov["highlights"][i] = {"i": i, "cut": "no room"}
        self.assertTrue(has(cc.check(RECAP, NARRATION, cov), "2 cut"))

    def test_scene_must_exist(self):
        cov = full()
        cov["highlights"][3]["scene"] = "s9"
        self.assertTrue(has(cc.check(RECAP, NARRATION, cov), "'s9'"))

    def test_depth_follows_priority_order(self):
        cov = full()
        cov["highlights"][2]["tier"], cov["highlights"][3]["tier"] = "quick", "deep"
        cov["highlights"][3]["scene"] = "s4"
        cov["highlights"][2]["scene"] = "s5"
        self.assertTrue(has(cc.check(RECAP, NARRATION, cov), "deep must be highlights [1, 2]"))
        cov = full()
        cov["highlights"][0]["tier"], cov["highlights"][1]["tier"] = "deep", "lead"
        self.assertTrue(has(cc.check(RECAP, NARRATION, cov), "lead must be highlight 0"))

    def test_swap_with_reason_promotes_the_next_highlight(self):
        cov = full()
        cov["highlights"][1] = {"i": 1, "scene": "s5", "tier": "quick", "swap": "announcement only"}
        cov["highlights"][3] = {"i": 3, "scene": "s3", "tier": "deep"}
        self.assertEqual(cc.check(RECAP, NARRATION, cov), [])
        cov["highlights"][1]["swap"] = " "
        self.assertTrue(has(cc.check(RECAP, NARRATION, cov), "swap needs tier quick and a reason"))

    def test_weekly_needs_three_deep_and_one_scene_each(self):
        self.assertTrue(has(cc.check(RECAP, NARRATION, full(), "weekly"), "deep must be highlights [1, 2, 3]"))
        cov = full()
        cov["highlights"][2]["scene"] = "s3"
        self.assertTrue(has(cc.check(RECAP, NARRATION, cov), "one scene each"))

    def test_few_highlights_still_pass(self):
        recap = {"highlights": ["h0", "h1", "h2"], "categories": [{"slug": "a"}]}
        cov = {
            "highlights": [
                {"i": 0, "scene": "s2", "tier": "lead"},
                {"i": 1, "scene": "s3", "tier": "deep"},
                {"i": 2, "scene": "s4", "tier": "deep"},
            ],
            "categories": [{"slug": "a", "scene": "s2"}],
        }
        self.assertEqual(cc.check(recap, NARRATION, cov, "weekly"), [])

    def test_latest_published_recaps_have_highlights_and_slugs(self):
        for kind in ("daily", "weekly"):
            recap = json.loads((ROOT / "data" / kind / "latest.json").read_text(encoding="utf-8"))
            self.assertGreaterEqual(len(recap.get("highlights") or []), 3)
            self.assertTrue(all(c.get("slug") for c in recap["categories"]))


if __name__ == "__main__":
    unittest.main()
