"""Skill Radar static surface (`/skills`, family pages, static payloads).

Covers the failure modes that are invisible locally but fatal in production:

- page routes live in the Worker table, and an unmatched path has no asset
  fallback (`html_handling: none`), so a missing route 404s silently;
- practitioner lane rows carry `family` instead of `id`, which rendered a
  literal "None" link before this test existed.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

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
    }
    entry.update(overrides)
    return entry


@pytest.fixture()
def artifact() -> dict:
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
            "provisional": True,
            "representative": representative,
            "alternates": [_entry("other-family", lead="other/family")],
        }
    ]
    return artifact


def test_board_body_renders_every_lane_and_links_families(artifact):
    body = rsp.skills_board_body(artifact)
    assert body is not None
    assert "Rising this week" in body
    assert "Reference shelf" in body
    assert "Practitioners" in body
    assert "By capability" in body
    assert 'href="/skills/michael-denyer-pstack-claude"' in body
    assert 'href="/skills/new-rising"' in body


def test_practitioner_lane_is_hidden_without_real_ports(artifact):
    flat = json.loads(json.dumps(artifact))
    for row in flat["lanes"]["practitioners"]:
        row["ports"] = 0
    body = rsp.skills_board_body(flat)
    assert "Practitioners" not in body, "a lane of all-zero ports just repeats the shelf"


def test_practitioner_rows_link_the_family_not_none(artifact):
    body = rsp.skills_board_body(artifact)
    assert "None" not in body
    assert "/skills/unknown" not in body
    assert ">michael-denyer/pstack-claude</a>" in body


def test_feed_shell_hosts_the_strip():
    shell = (ROOT / "web" / "index.html").read_text()
    assert 'id="skillsStrip"' in shell
    assert "/skills-strip.css" in shell
    assert "/skills-strip.js" in shell
    assert 'href="/skills"' in shell
    # The band must start hidden: a missing artifact should cost no empty box.
    assert 'id="skillsStrip"' in shell and 'aria-label="Skill Radar" hidden' in shell


def test_capability_groups_are_explained_without_a_per_group_caveat(artifact):
    body = rsp.skills_board_body(artifact)
    # The gate (two name-matching skills) makes a per-group "provisional" badge
    # unnecessary; the rule is disclosed once in the methodology block.
    assert "at least two skills" in body
    assert "Core means" in body
    assert "still being reviewed" not in body
    assert "provisional" not in body.lower()


def test_board_body_is_none_without_data():
    assert rsp.skills_board_body({"lanes": {}, "capabilities": []}) is None


def test_static_payloads_are_lean_and_ordered(artifact, tmp_path, monkeypatch):
    monkeypatch.setattr(rsp, "WEB_DIR", tmp_path)
    full_size, top_size = rsp.write_skills_static_json(artifact)
    assert full_size > 0 and top_size > 0

    full = json.loads((tmp_path / "skills-data.json").read_text())
    assert "members" not in full["lanes"]["shelf"][0], "audit lists stay out of the client payload"
    assert full["counts"]["shelf"] == 1

    top = json.loads((tmp_path / "skills-top.json").read_text())
    assert top["rising"][0]["id"] == "new-rising"
    assert set(top["rising"][0]) == {
        "id", "lead", "practitioner", "stars", "unique_skills",
        "fork_ratio", "velocity_7d", "ports", "reason", "capability_label",
    }


def test_skills_routes_exist_in_the_worker_table():
    """An unmatched path has no asset fallback, so a missing route 404s silently."""
    worker = (ROOT / "worker" / "src" / "index.js").read_text()
    assert "/web/skills/index.html" in worker
    assert "/web/skills/${m[1]}.html" in worker
    assert worker.index("/web/skills/index.html") < worker.index("/web/skills/${m[1]}.html")


def test_sitemap_includes_the_board_and_family_pages(tmp_path, monkeypatch):
    monkeypatch.setattr(rsp, "WEB_DIR", tmp_path)
    rsp.write_sitemap(
        "https://example.com",
        [],
        [],
        skills=[("/skills/michael-denyer-pstack-claude", "2026-11-02")],
    )
    xml = (tmp_path / "sitemap.xml").read_text()
    assert "<loc>https://example.com/skills</loc>" in xml
    assert "<loc>https://example.com/skills/michael-denyer-pstack-claude</loc>" in xml
