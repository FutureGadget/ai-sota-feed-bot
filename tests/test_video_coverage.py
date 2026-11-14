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
    "highlights": ["h0", "h1", "h2", "h3"],
    "categories": [{"slug": "a"}, {"slug": "b"}, {"slug": "c"}],
}
NARRATION = [{"id": "s1", "text": "x"}, {"id": "s2", "text": "y"}, {"id": "s3", "text": "z"}]


def full() -> dict:
    return {
        "lead": 0,
        "highlights": [{"i": 0, "scene": "s1"}, {"i": 1, "scene": "s2"}, {"i": 2, "scene": "s2"}, {"i": 3, "scene": "s3"}],
        "categories": [{"slug": "a", "scene": "s1"}, {"slug": "b", "scene": "s2"}, {"slug": "c", "scene": "s3"}],
    }


class VideoCoverageTest(unittest.TestCase):
    def test_complete_mapping_passes(self):
        self.assertEqual(cc.check(RECAP, NARRATION, full()), [])

    def test_unmapped_highlight_and_category_fail(self):
        cov = full()
        cov["highlights"].pop()
        cov["categories"].pop()
        errors = cc.check(RECAP, NARRATION, cov)
        self.assertTrue(any("highlights: i 3" in e for e in errors))
        self.assertTrue(any("categories: slug 'c'" in e for e in errors))

    def test_cut_needs_reason_and_is_capped(self):
        cov = full()
        cov["highlights"][1] = {"i": 1, "cut": ""}
        self.assertTrue(any("needs a scene or a cut reason" in e for e in cc.check(RECAP, NARRATION, cov)))
        cov = full()
        for i in (1, 2, 3):
            cov["highlights"][i] = {"i": i, "cut": "no mechanism"}
        self.assertTrue(any("3 cut" in e for e in cc.check(RECAP, NARRATION, cov)))

    def test_scene_must_exist_and_lead_cannot_be_cut(self):
        cov = full()
        cov["highlights"][0] = {"i": 0, "scene": "s9"}
        self.assertTrue(any("'s9'" in e for e in cc.check(RECAP, NARRATION, cov)))
        cov = full()
        cov["highlights"][0] = {"i": 0, "cut": "skip"}
        self.assertTrue(any("lead highlight cannot be cut" in e for e in cc.check(RECAP, NARRATION, cov)))

    def test_latest_published_recaps_have_highlights_and_slugs(self):
        for kind in ("daily", "weekly"):
            recap = json.loads((ROOT / "data" / kind / "latest.json").read_text(encoding="utf-8"))
            self.assertTrue(recap.get("highlights"))
            self.assertTrue(all(c.get("slug") for c in recap["categories"]))


if __name__ == "__main__":
    unittest.main()
