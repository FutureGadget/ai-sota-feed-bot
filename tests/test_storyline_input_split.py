from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = (
    Path(__file__).resolve().parents[1]
    / ".agents"
    / "skills"
    / "storyline-editor"
    / "scripts"
)
sys.path.insert(0, str(SCRIPTS))

import build_storyline_input as bsi  # noqa: E402
import storyline_common as sc  # noqa: E402


def _detail(slug: str, sids: list[str]) -> dict:
    return {
        "slug": slug,
        "days": [
            {
                "date": "2026-07-01",
                "items": [
                    {
                        "sid": sid,
                        "title": f"title {sid}",
                        "url": f"https://example.com/{sid}",
                        "source": "example",
                        "summary_1line": "one line",
                        "published": "2026-07-01T00:00:00+00:00",
                    }
                    for sid in sids
                ],
            }
        ],
    }


class StorylineInputSplitTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name) / "storylines"
        (root / "narratives").mkdir(parents=True)
        self.root = root

        self._orig = (bsi.STORYLINES_INDEX, bsi.INPUT_DIR, sc.NARRATIVE_DIR)
        bsi.STORYLINES_INDEX = root / "index.json"
        bsi.INPUT_DIR = root / "input"
        sc.NARRATIVE_DIR = root / "narratives"

        index = {
            "window_days": 21,
            "storylines": [
                {
                    "slug": "alpha",
                    "label": "Alpha",
                    "item_count": 2,
                    "source_count": 2,
                    "day_count": 1,
                    "last_updated": "2026-07-01T00:00:00+00:00",
                    "member_sids": ["a1", "a2"],
                },
                {
                    "slug": "beta",
                    "label": "Beta",
                    "item_count": 1,
                    "source_count": 1,
                    "day_count": 1,
                    "last_updated": "2026-07-01T00:00:00+00:00",
                    "member_sids": ["b1"],
                },
            ],
        }
        (root / "index.json").write_text(json.dumps(index), encoding="utf-8")
        (root / "alpha.json").write_text(
            json.dumps(_detail("alpha", ["a1", "a2"])), encoding="utf-8"
        )
        (root / "beta.json").write_text(
            json.dumps(_detail("beta", ["b1"])), encoding="utf-8"
        )
        # beta already has a *fresh* narrative — it must not need work.
        (root / "narratives" / "beta.json").write_text(
            json.dumps(
                {
                    "slug": "beta",
                    "generated_at": "2026-07-01T01:00:00+00:00",
                    "covers_last_updated": "2026-07-01T00:00:00+00:00",
                    "covers_member_sids": ["b1"],
                    "tldr": "Beta background.",
                }
            ),
            encoding="utf-8",
        )
        # A leftover work item for a slug that no longer needs work.
        leftover = root / "input" / "by-slug" / "gone.json"
        leftover.parent.mkdir(parents=True)
        leftover.write_text("{}", encoding="utf-8")

    def tearDown(self) -> None:
        bsi.STORYLINES_INDEX, bsi.INPUT_DIR, sc.NARRATIVE_DIR = self._orig
        self._tmp.cleanup()

    def _load(self, *parts: str) -> dict:
        return json.loads((self.root / "input").joinpath(*parts).read_text(encoding="utf-8"))

    def test_writes_manifest_and_per_slug_work_items(self) -> None:
        bsi.main([])

        latest = self._load("latest.json")
        self.assertEqual(latest["needs_narrative_count"], 1)
        self.assertEqual([s["slug"] for s in latest["storylines"]], ["alpha"])
        self.assertTrue(latest["storylines"][0]["timeline"])

        manifest = self._load("manifest.json")
        row = manifest["storylines"][0]
        self.assertEqual(row["slug"], "alpha")
        self.assertNotIn("timeline", row)
        self.assertNotIn("prior_narrative", row)
        self.assertEqual(row["input_path"], "data/storylines/input/by-slug/alpha.json")

        work = self._load("by-slug", "alpha.json")
        self.assertEqual(work["window_days"], 21)
        self.assertEqual(work["storyline"]["slug"], "alpha")
        self.assertTrue(work["storyline"]["timeline"])

        by_slug = sorted(p.name for p in (self.root / "input" / "by-slug").glob("*.json"))
        self.assertEqual(by_slug, ["alpha.json"])  # gone.json removed, beta not needed

    def test_stale_narrative_gets_work_item_with_prior(self) -> None:
        index = json.loads((self.root / "index.json").read_text(encoding="utf-8"))
        index["storylines"][1]["last_updated"] = "2026-07-02T00:00:00+00:00"
        (self.root / "index.json").write_text(json.dumps(index), encoding="utf-8")

        bsi.main([])

        manifest = self._load("manifest.json")
        rows = {r["slug"]: r for r in manifest["storylines"]}
        self.assertEqual(rows["beta"]["reason"], "stale")
        self.assertTrue(rows["beta"]["has_prior_narrative"])

        work = self._load("by-slug", "beta.json")
        self.assertEqual(work["storyline"]["prior_narrative"]["tldr"], "Beta background.")


if __name__ == "__main__":
    unittest.main()
