"""The Python builder and the JS /api/updates overlay must agree on an item's source hash.

The builder stores a hash of each English desk item beside its Korean text; the
API overlays that text only when its own hash of the live item is equal. A
disagreement silently shows English, so both implementations run on the same
fixtures here.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))

import build_localized_updates as updates  # noqa: E402

CASES: dict[str, dict] = {
    "plain": {"title": "Activation Steering", "summary": "A Nov 19 paper argues RL is steering."},
    "empty": {},
    "title_only": {"title": "Agent token costs run away"},
    "null_fields": {"title": None, "summary": None},
    "whitespace_runs_and_edges": {"title": "  Spaced \t out\n title  ", "summary": "Line one.\n\nLine two."},
    "unicode_spaces": {"title": "nbsp and em space　ideographic", "summary": "x"},
    "korean_and_emoji": {"title": "딥시크 \U0001f680", "summary": "é combining accent, é precomposed — dash “quotes”"},
    "json_escapes": {"title": 'Quote " backslash \\ slash / <tag> & amp', "summary": "tab\there"},
    "ellipsis_excerpt": {"title": "Daily", "summary": "A long summary that was cut at a word…"},
    "extra_fields_ignored": {"id": "storylines:a", "version": "a" * 24, "title": "t", "summary": "s", "href": "/x"},
}

_NODE = """
import { updateHash } from './lib/update-translations.js';
const cases = JSON.parse(process.env.CASES);
console.log(JSON.stringify(Object.fromEntries(
  Object.entries(cases).map(([name, item]) => [name, updateHash(item)]))));
"""


class UpdatesHashParityTest(unittest.TestCase):
    def test_python_and_js_hash_every_fixture_identically(self) -> None:
        res = subprocess.run(
            ["node", "--input-type=module", "-e", _NODE],
            cwd=ROOT, env={"PATH": os.environ["PATH"], "CASES": json.dumps(CASES)},
            capture_output=True, text=True, check=True,
        )
        js = json.loads(res.stdout)
        py = {name: updates.source_hash(item) for name, item in CASES.items()}
        self.assertEqual(js, py)

    def test_the_fixtures_are_not_all_one_hash(self) -> None:
        self.assertGreater(len({updates.source_hash(item) for item in CASES.values()}), 7)


if __name__ == "__main__":
    unittest.main()
