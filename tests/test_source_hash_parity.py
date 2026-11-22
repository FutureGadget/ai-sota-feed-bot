"""The Python builder and the JS feed API must agree on a card's source hash.

The builder stores a hash of each English card beside its translation; the API
overlays the translation only when its own hash of the live card is equal. A
disagreement silently shows English, so both implementations are run on the
same fixtures here.
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))

import build_localized_feed as localized  # noqa: E402

CASES: dict[str, dict] = {
    "plain": {
        "title": "Agent tracing patterns",
        "summary_1line": "A concise explanation.",
        "why_it_matters": "Teams debug faster.",
    },
    "empty": {},
    "missing_fields": {"title": "Only a title"},
    "null_fields": {"title": None, "summary_1line": None, "why_it_matters": None, "also_covered": None},
    "whitespace_runs_and_edges": {
        "title": "  Spaced \t out\n title  ",
        "summary_1line": "Line one.\n\nLine two.",
        "why_it_matters": " nbsp and em space　ideographic",
    },
    "korean_and_emoji": {
        "title": "딥시크, 추론 모델 요금 인하 \U0001f680",
        "summary_1line": "한국어 요약 “quotes” — dash",
        "why_it_matters": "é combining accent, é precomposed",
    },
    "json_escapes": {
        "title": 'Quote " backslash \\ slash / and <tag> & amp',
        "summary_1line": "tab\there",
        "why_it_matters": "line separator and  paragraph",
    },
    "also_covered": {
        "title": "Story",
        "also_covered": [
            {"url": "https://a.example/x/", "title": "  Spaced   title "},
            {"url": "https://b.example/y", "title": "Plain"},
            {"url": "", "title": "Title only"},
            {"url": "https://c.example/z", "title": ""},
            {"url": "", "title": ""},
            {"url": None, "title": None},
            {"url": "  https://d.example/w/  ", "title": "Padded url"},
            "not a dict",
            None,
        ],
    },
    "also_covered_not_a_list": {"title": "Story", "also_covered": "nope"},
    "url_root_slash_kept": {"title": "t", "also_covered": [{"url": "/", "title": "root"}]},
    "extra_fields_ignored": {
        "title": "t",
        "id": "x",
        "url": "https://example.com/p",
        "v2_final_score": 9.9,
        "reader_adjustment": 0.2,
        "also_covered": [{"url": "https://o.example", "title": "o", "source": "bloomberg"}],
    },
}

_NODE = """
import { sourceHash } from './api/feed.js';
const cases = JSON.parse(process.env.CASES);
console.log(JSON.stringify(Object.fromEntries(
  Object.entries(cases).map(([name, item]) => [name, sourceHash(item)]))));
"""


class SourceHashParityTest(unittest.TestCase):
    def test_python_and_js_hash_every_fixture_identically(self) -> None:
        res = subprocess.run(
            ["node", "--input-type=module", "-e", _NODE],
            cwd=ROOT,
            env={"PATH": __import__("os").environ["PATH"], "CASES": json.dumps(CASES)},
            capture_output=True,
            text=True,
            check=True,
        )
        js = json.loads(res.stdout)
        py = {name: localized._source_hash(item) for name, item in CASES.items()}
        self.assertEqual(js, py)

    def test_the_fixtures_are_not_all_one_hash(self) -> None:
        self.assertGreater(len({localized._source_hash(item) for item in CASES.values()}), 8)


if __name__ == "__main__":
    unittest.main()
