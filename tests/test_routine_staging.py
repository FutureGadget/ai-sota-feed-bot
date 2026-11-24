from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTINES = ROOT / ".agents" / "routines"


class RoutineStagingTest(unittest.TestCase):
    def test_routines_that_stage_english_recap_pages_also_stage_korean_ones(self) -> None:
        # The recap index builder re-renders /ko/ pages whenever it renders
        # the English ones (attach_video.py runs it too). A routine that commits
        # only web/daily/ leaves the Korean page behind on main until the next
        # feed run, and test_korean_pages_preserve_source_page_structure fails.
        checked = 0
        for prompt in sorted(ROUTINES.glob("*/prompt.md")):
            staged = {m.group(1) for m in re.finditer(r"^\s*(web/[\w/-]+/)\s*$", prompt.read_text(encoding="utf-8"), re.M)}
            for kind in ("daily", "weekly"):
                if f"web/{kind}/" in staged:
                    checked += 1
                    self.assertIn(f"web/ko/{kind}/", staged, f"{prompt.relative_to(ROOT)} stages web/{kind}/ without web/ko/{kind}/")
        self.assertGreaterEqual(checked, 4)


if __name__ == "__main__":
    unittest.main()
