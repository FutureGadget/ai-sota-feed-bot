"""Skill Radar static surface (`/skills`, family pages, static payloads).

Covers the failure modes that are invisible locally but fatal in production:

- page routes live in the Worker table, and an unmatched path has no asset
  fallback (`html_handling: none`), so a missing route 404s silently;
- practitioner lane rows carry `family` instead of `id`, which rendered a
  literal "None" link before this test existed.

Run by `python -m unittest discover` in CI, so this file must not import pytest.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))

import render_static_pages as rsp  # noqa: E402


def _entry(entry_id: str = "michael-denyer-pstack-claude", **overrides) -> dict:
    entry = {
        "id": entry_id,
        "lead": "michael-denyer/pstack-claude",
        "practitioner": "michael-denyer",
        "members": ["michael-denyer/pstack-claude", "backnotprop/pstack"],
        "member_count": 2,
        "ports": 1,
        "stars": 7050,
        "forks": 578,
        "fork_ratio": 0.082,
        "unique_skills": 40,
        "capabilities": ["code-review", "testing"],
        "layouts": ["skills"],
        "age_days": 159,
        "idle_days": 3,
        "velocity_7d": 120,
        "recent_ports": 0,
        "first_seen": "2026-06-01",
        "aggregated": False,
        "no_license": False,
        "stale": False,
        "practitioner_setups": 1,
        "score": 0.81,
        "lane": "shelf",
        "reason": "1 independent port · 7,050 stars combined",
        "lens": "core",
        "dominant_capability": "code-review",
        "flagship_skill": "requesting-code-review",
    }
    entry.update(overrides)
    return entry


def _artifact() -> dict:
    artifact = {
        "generated_at": "2026-11-02T00:00:00+00:00",
        "counts": {
            "records": 12,
            "capabilities": 1,
            "shelf": 1,
            "rising": 1,
            "off_lens_excluded": 40,
        },
        "lanes": {
            "rising": [_entry("new-rising", lead="new/rising", lane="rising", reason="+900 stars in 7d")],
            "shelf": [_entry()],
            "practitioners": [
                {
                    "practitioner": "poteto",
                    "setup": "michael-denyer/pstack-claude",
                    "family": "michael-denyer-pstack-claude",
                    "ports": 1,
                    "stars": 7050,
                    "unique_skills": 40,
                    "score": 0.8,
                },
                {
                    "practitioner": "garrytan",
                    "setup": "garrytan/gstack",
                    "family": "garrytan-gstack",
                    "ports": 2,
                    "stars": 138587,
                    "unique_skills": 68,
                    "score": 0.7,
                },
            ],
        },
        "capabilities": [],
    }
    representative = _entry()
    representative["skill"] = {"name": "requesting-code-review"}
    artifact["capabilities"] = [
        {
            "capability": "code-review",
            "lens": "core",
            "representative": representative,
            "alternates": [_entry("other-family", lead="other/family")],
        }
    ]
    return artifact


@contextmanager
def _web_dir():
    """Point the renderer's WEB_DIR at a scratch directory and restore it."""
    previous = rsp.WEB_DIR
    with tempfile.TemporaryDirectory() as tmp:
        rsp.WEB_DIR = Path(tmp)
        try:
            yield Path(tmp)
        finally:
            rsp.WEB_DIR = previous


class SkillsPagesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.artifact = _artifact()

    def test_board_body_renders_every_lane_and_links_families(self) -> None:
        body = rsp.skills_board_body(self.artifact)
        self.assertIsNotNone(body)
        self.assertIn("Proven setups", body)
        self.assertIn("Browse by capability", body)
        self.assertIn("Rising this week", body)
        self.assertIn("Practitioners", body)
        self.assertIn('href="/skills/michael-denyer-pstack-claude"', body)
        self.assertIn('href="/skills/new-rising"', body)

    def test_board_is_proven_first_and_long_lists_are_collapsed(self) -> None:
        body = rsp.skills_board_body(self.artifact)
        # Proven cards come before the capability browse and the rising list.
        self.assertLess(body.index("Proven setups"), body.index("Browse by capability"))
        self.assertLess(body.index("Browse by capability"), body.index("Rising this week"))
        # The full shelf and the practitioner table live behind disclosure, not
        # in the default reading path.
        self.assertIn("<summary>All 1 setups, side by side</summary>", body)
        self.assertIn("<summary>Practitioners ranked by ports (2)</summary>", body)
        # Rising is a compact list, not another card grid.
        self.assertIn('<ul class="skills-rise">', body)

    def test_practitioner_lane_is_hidden_without_real_ports(self) -> None:
        flat = json.loads(json.dumps(self.artifact))
        for row in flat["lanes"]["practitioners"]:
            row["ports"] = 0
        body = rsp.skills_board_body(flat)
        self.assertNotIn("Practitioners", body, "a lane of all-zero ports just repeats the shelf")

    def test_practitioner_rows_link_the_family_not_none(self) -> None:
        body = rsp.skills_board_body(self.artifact)
        self.assertNotIn("None", body)
        self.assertNotIn("/skills/unknown", body)
        self.assertIn(">michael-denyer/pstack-claude</a>", body)

    def test_board_body_is_none_without_data(self) -> None:
        self.assertIsNone(rsp.skills_board_body({"lanes": {}, "capabilities": []}))

    def test_capability_groups_are_explained_without_a_per_group_caveat(self) -> None:
        body = rsp.skills_board_body(self.artifact)
        # The gate (two name-matching skills) makes a per-group "provisional"
        # badge unnecessary; the rule is disclosed once in the methodology block.
        self.assertIn("at least two skills", body)
        self.assertIn("Core means", body)
        self.assertNotIn("still being reviewed", body)
        self.assertNotIn("provisional", body.lower())

    def test_static_payloads_are_lean_and_ordered(self) -> None:
        with _web_dir() as tmp:
            full_size, top_size = rsp.write_skills_static_json(self.artifact)
            self.assertGreater(full_size, 0)
            self.assertGreater(top_size, 0)

            full = json.loads((tmp / "skills-data.json").read_text())
            self.assertNotIn(
                "members", full["lanes"]["shelf"][0], "audit lists stay out of the client payload"
            )
            self.assertEqual(full["counts"]["shelf"], 1)

            top = json.loads((tmp / "skills-top.json").read_text())
            self.assertEqual(top["rising"][0]["id"], "new-rising")
            self.assertEqual(
                set(top["rising"][0]),
                {
                    "id", "lead", "practitioner", "stars", "unique_skills",
                    "fork_ratio", "velocity_7d", "ports", "reason", "capability_label",
                },
            )

    def test_feed_shell_hosts_the_strip(self) -> None:
        shell = (ROOT / "web" / "index.html").read_text()
        self.assertIn('id="skillsStrip"', shell)
        self.assertIn("/skills-strip.css", shell)
        self.assertIn("/skills-strip.js", shell)
        self.assertIn('href="/skills"', shell)
        # The band must start hidden: a missing artifact should cost no empty box.
        self.assertIn('aria-label="Skill Radar" hidden', shell)

    def test_skills_routes_exist_in_the_worker_table(self) -> None:
        """An unmatched path has no asset fallback, so a missing route 404s silently."""
        worker = (ROOT / "worker" / "src" / "index.js").read_text()
        self.assertIn("/web/skills/index.html", worker)
        self.assertIn("/web/skills/${m[1]}.html", worker)
        self.assertLess(
            worker.index("/web/skills/index.html"),
            worker.index("/web/skills/${m[1]}.html"),
        )

    def test_sitemap_includes_the_board_and_family_pages(self) -> None:
        with _web_dir() as tmp:
            rsp.write_sitemap(
                "https://example.com",
                [],
                [],
                skills=[("/skills/michael-denyer-pstack-claude", "2026-11-02")],
            )
            xml = (tmp / "sitemap.xml").read_text()
            self.assertIn("<loc>https://example.com/skills</loc>", xml)
            self.assertIn("<loc>https://example.com/skills/michael-denyer-pstack-claude</loc>", xml)


if __name__ == "__main__":
    unittest.main()
