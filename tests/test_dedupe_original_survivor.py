from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))

import build_digest  # noqa: E402


def _iso(hours_ago: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).isoformat()


ORIGINAL = {
    "source": "anthropic_engineering",
    "title": "Redesigning source control at Anthropic",
    "url": "https://www.anthropic.com/engineering/redesigning-source-control",
    "published": _iso(23),
}
ECHO = {
    "source": "simon_willison",
    "title": "Redesigning source control at Anthropic",
    "url": "https://simonwillison.net/2026/Oct/13/redesigning-source-control-at-anthropic/",
    "published": _iso(0.5),
}


class DedupeOriginalSurvivorTest(unittest.TestCase):
    def _check(self, dedupe) -> None:
        for order in ([dict(ORIGINAL), dict(ECHO)], [dict(ECHO), dict(ORIGINAL)]):
            out = dedupe(order)
            self.assertEqual(len(out), 1)
            self.assertEqual(out[0]["source"], "anthropic_engineering")
            self.assertEqual(
                [c["source"] for c in out[0].get("also_covered", [])],
                ["simon_willison"],
            )

    def test_tier0_keeps_earliest_publication(self) -> None:
        self._check(build_digest.dedupe)


if __name__ == "__main__":
    unittest.main()
