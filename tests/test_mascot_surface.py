from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MascotSurfaceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = (ROOT / "web" / "mascot" / "mascot.js").read_text(encoding="utf-8")

    def test_right_anchor_keeps_css_safe_area_expression(self) -> None:
        self.assertIn(
            "calc(100% - ${opts.width}px - ${cssLen(opts.offsetX)})",
            self.source,
        )
        self.assertNotIn("const offsetXPx", self.source)


if __name__ == "__main__":
    unittest.main()
