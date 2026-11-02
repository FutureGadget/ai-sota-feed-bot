"""Regression coverage for the Skill Radar collector (docs/ideas/agent-skill-radar.md).

The cases here encode the measured failures from the 2026-11-01 probes, so the
mistakes cannot come back silently:

- ``path.endswith("skill.md")`` matched docs like ``verification-skill.md``
- per-harness vendoring inflated one skill into 15 rows
- description text was useless for family detection, skill-name overlap was not
- harness names made every skill look on-lens
- the shelf needs hysteresis or it flaps week to week
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))

import collect_skills as cs  # noqa: E402

NOW = datetime(2026, 11, 1, 12, 0, 0, tzinfo=timezone.utc)


def _repo(name, stars=1000, forks=100, age_days=120, skills=(), description="", license="MIT", **extra):
    created = (NOW - timedelta(days=age_days)).isoformat()
    record = {
        "full_name": name,
        "owner": name.split("/")[0],
        "id": extra.pop("id", abs(hash(name)) % 10**8),
        "stars": stars,
        "forks": forks,
        "created_at": created,
        "pushed_at": extra.pop("pushed_at", NOW.isoformat()),
        "archived": False,
        "fork": False,
        "license": license,
        "description": description,
        "skills": [{"name": skill, "path": f"skills/{skill}/SKILL.md"} for skill in skills],
        "unique_skills": len(skills),
        "layouts": ["skills"],
        "first_seen": extra.pop("first_seen", (NOW - timedelta(days=age_days)).date().isoformat()),
        "default_branch": "main",
    }
    record.update(extra)
    return record


# --------------------------------------------------------------------------- #
# skill files
# --------------------------------------------------------------------------- #


def test_is_skill_path_requires_exact_basename():
    assert cs.is_skill_path("skills/architect/SKILL.md")
    assert cs.is_skill_path("SKILL.md")
    assert cs.is_skill_path("plugins/pstack/.codex-plugin/prompts/create-verification-skill.md") is False
    assert cs.is_skill_path("docs/skills.md") is False
    assert cs.is_skill_path("") is False


def test_parse_frontmatter_expands_block_scalars():
    text = (
        "---\n"
        "name: report-writer\n"
        "description: |-\n"
        "  Write the weekly report.\n"
        "  Mention every risk.\n"
        "---\n"
        "\n# Report writer\n"
    )
    parsed = cs.parse_frontmatter(text)
    assert parsed is not None
    assert parsed["name"] == "report-writer"
    assert "weekly report" in parsed["description"]
    assert "every risk" in parsed["description"]


def test_parse_frontmatter_rejects_missing_frontmatter():
    assert cs.parse_frontmatter("# just markdown\n") is None
    assert cs.parse_frontmatter("") is None


def test_dedupe_collapses_harness_vendored_copies():
    entries = [
        {"path": ".cursor/skills/impeccable/SKILL.md", "sha": "a"},
        {"path": ".claude/skills/impeccable/SKILL.md", "sha": "a"},
        {"path": "skills/impeccable/SKILL.md", "sha": "a"},
        {"path": "docs/ja-JP/skills/impeccable/SKILL.md", "sha": "a"},
        {"path": "skills/other/SKILL.md", "sha": "b"},
    ]
    records = cs.dedupe_skills(entries, "pbakaus/impeccable")
    assert [record["name"] for record in records] == ["impeccable", "other"]
    impeccable = records[0]
    assert impeccable["copies"] == 4
    # Committed census is metadata only: a name and a copy count. Paths, shas
    # and per-copy layouts were most of the artifact size and are not read.
    assert set(impeccable) == {"name", "copies"}


def test_layout_and_locale_detection():
    assert cs.layout_of("skills/x/SKILL.md") == "skills"
    assert cs.layout_of(".agents/skills/x/SKILL.md") == ".agents"
    assert cs.layout_of("SKILL.md") == "root"
    assert cs.locale_of("docs/zh-CN/skills/x/SKILL.md") == "zh-CN"
    assert cs.locale_of("skills/x/SKILL.md") is None


def test_inventory_from_tree_ignores_skill_md_suffix_docs():
    tree = [
        {"path": "skills/architect/SKILL.md", "sha": "1"},
        {"path": "plugins/pstack/.codex-plugin/prompts/create-verification-skill.md", "sha": "2"},
        {"path": "README.md", "sha": "3"},
    ]
    skills, meta = cs.inventory_from_tree(tree, "a/pstack", max_skills=400)
    assert [skill["name"] for skill in skills] == ["architect"]
    assert meta["skill_files"] == 1
    assert meta["layouts"] == ["skills"]


# --------------------------------------------------------------------------- #
# families
# --------------------------------------------------------------------------- #


def test_containment_does_not_punish_added_skills():
    base = {"architect", "arena", "automate-me", "blast-radius"}
    port = set(base) | {"extra-one", "extra-two"}
    assert cs.containment(base, port) == 1.0, "a port that adds skills is still the same line"
    # Containment is always 1.0 for a subset, so it cannot be the only guard:
    # a tiny inventory is 'contained' by anything. build_families requires a
    # minimum absolute overlap and comparable inventory sizes for exactly that.
    assert cs.containment(base, {"architect"}) == 1.0


def test_build_families_does_not_fold_small_repos_into_mega_collections():
    mega = [f"skill-{index}" for index in range(200)]
    repos = {
        "aggregator/all-skills": _repo("aggregator/all-skills", stars=9000, skills=mega),
        "solo/tiny-set": _repo("solo/tiny-set", stars=50, skills=["skill-1", "skill-2", "skill-3"]),
    }
    families = cs.build_families(repos)
    tiny = next(family for family in families.values() if "solo/tiny-set" in family["members"])
    assert tiny["members"] == ["solo/tiny-set"]


def test_build_families_clusters_ports_but_not_name_collisions():
    skills = ["architect", "arena", "automate-me", "benchmark-checklist"]
    repos = {
        "backnotprop/pstack": _repo("backnotprop/pstack", stars=3315, skills=skills),
        "michael-denyer/pstack-claude": _repo("michael-denyer/pstack-claude", stars=3725, skills=skills),
        # Same name, different concept, shipped no skills at all.
        "peadar/pstack": _repo("peadar/pstack", stars=273, age_days=5000, skills=[], description="Print stack traces from running processes"),
        # Same word in the name, no relationship.
        "nutlope/hallmark": _repo("nutlope/hallmark", stars=44561, skills=["hallmark"], description="Anti-AI-slop design skill"),
        "banquets/hallmark-banquets": _repo("banquets/hallmark-banquets", stars=0, skills=[], description="Hallmark Banquets venue site"),
    }
    families = cs.build_families(repos)
    pstack = next(family for family in families.values() if "backnotprop/pstack" in family["members"])
    assert pstack["lead"] == "michael-denyer/pstack-claude"
    assert set(pstack["members"]) == {"backnotprop/pstack", "michael-denyer/pstack-claude"}
    # An unrelated repo with the same word in its name stays a singleton.
    banquets = next(family for family in families.values() if "banquets/hallmark-banquets" in family["members"])
    assert banquets["members"] == ["banquets/hallmark-banquets"]
    assert not any("peadar/pstack" in family["members"] and len(family["members"]) > 1
                   for family in families.values())


def test_build_families_joins_explicit_port_without_skill_overlap():
    repos = {
        "garrytan/gstack": _repo("garrytan/gstack", stars=138559, skills=["brainstorm", "plan", "ship", "review"]),
        # A wrapper ships no skill files but says where it came from.
        "ahacad/gstack": _repo("ahacad/gstack", stars=54, skills=[], description="Claude Code plugin wrapper for garrytan/gstack"),
        # Renamed inventory, explicit derivation.
        "thanh/gstack-windows": _repo("thanh/gstack-windows", stars=37, skills=["w-1", "w-2"], description="Hardened Windows port of gstack"),
        # Unrelated repo that happens to mention a stack.
        "someone/stack-tool": _repo("someone/stack-tool", stars=900, skills=[], description="A stack trace viewer"),
    }
    families = cs.build_families(repos)
    gstack = next(family for family in families.values() if family["lead"] == "garrytan/gstack")
    assert "ahacad/gstack" in gstack["members"]
    assert "thanh/gstack-windows" in gstack["members"]
    assert "someone/stack-tool" not in gstack["members"]


def test_unique_skill_count_is_not_copy_count():
    repos = {
        "pbakaus/impeccable": _repo(
            "pbakaus/impeccable",
            skills=["impeccable"],
            unique_skills=1,
            skill_files=15,
        )
    }
    families = cs.build_families(repos)
    assert next(iter(families.values()))["unique_skills"] == 1


# --------------------------------------------------------------------------- #
# capability + lens
# --------------------------------------------------------------------------- #


def _taxonomy():
    cfg = cs.load_config()
    return cfg


def test_harness_names_do_not_make_a_design_skill_on_lens():
    cfg = _taxonomy()
    taxonomy = cfg["capabilities"]["taxonomy"]
    harness = cfg["capabilities"]["harness_tokens"]
    slug, hits = cs.classify_capability(
        "hallmark",
        "Anti-AI-slop design skill for Claude Code, Cursor, and Codex.",
        taxonomy,
        harness,
    )
    assert slug == "frontend-design", "a design skill stays a design skill after harness stripping"
    assert cs.lens_tier(cs.capability_weight(cfg, slug), cfg["capabilities"]["lens"]) == "off"


def test_code_review_skill_stays_on_lens_even_when_it_names_a_harness():
    cfg = _taxonomy()
    slug, _ = cs.classify_capability(
        "requesting-code-review",
        "Use when completing tasks before merging to verify the work: request a code review of the diff in Claude Code.",
        cfg["capabilities"]["taxonomy"],
        cfg["capabilities"]["harness_tokens"],
    )
    assert slug == "code-review"
    assert cs.lens_tier(cs.capability_weight(cfg, slug), cfg["capabilities"]["lens"]) == "core"


def test_assign_capabilities_uses_cache_and_llm_fallback():
    cfg = _taxonomy()
    skills = [
        {"name": "hallmark", "description": "Anti-AI-slop design skill for Claude Code"},
        {"name": "mystery", "description": "Does a thing"},
    ]
    # `hallmark` classifies by keyword, so only `mystery` should reach the LLM.
    calls = []

    def fake_llm(pending):
        calls.append([item["skill"]["name"] for item in pending])
        return {item["key"]: "tooling-mcp" for item in pending}

    counts, cache = cs.assign_capabilities(skills, cfg, cache={}, llm_assigner=fake_llm)
    assert calls == [["mystery"]]
    assert skills[1]["capability"] == "tooling-mcp"
    assert skills[1]["capability_source"] == "llm"
    assert counts["uncategorized"] == 0
    assert cache

    # Second pass: cache hit, no second LLM call.
    again = [{"name": "mystery", "description": "Does a thing"}]
    _, _ = cs.assign_capabilities(again, cfg, cache=cache, llm_assigner=fake_llm)
    assert again[0]["capability"] == "tooling-mcp"
    assert len(calls) == 1


def test_openrouter_assigner_is_off_without_model_or_key():
    cfg = _taxonomy()
    cfg["capabilities"]["llm"]["model"] = ""
    assert cs.openrouter_assigner(cfg) is None
    cfg["capabilities"]["llm"]["model"] = "some/model"
    previous = os.environ.pop("OPENROUTER_API_KEY", None)
    try:
        assert cs.openrouter_assigner(cfg) is None
    finally:
        if previous is not None:
            os.environ["OPENROUTER_API_KEY"] = previous


# --------------------------------------------------------------------------- #
# ranking
# --------------------------------------------------------------------------- #

class BoardTest(unittest.TestCase):
    """Ranking tests that write artifacts; needs an isolated DATA_DIR."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.board_dir = Path(self._tmp.name)
        (self.board_dir / "history").mkdir(parents=True, exist_ok=True)
        history = {
            "2026-10-25": {"new/rising": {"stars": 100, "forks": 4, "skills": 3}},
            "2026-11-01": {
                "new/rising": {"stars": 1900, "forks": 60, "skills": 3},
                "backnotprop/pstack": {"stars": 3315, "forks": 235, "skills": 40},
                "nutlope/hallmark": {"stars": 44561, "forks": 2361, "skills": 1},
            },
        }
        cs.write_json(self.board_dir / "history" / "2026-11-01.json", history)
        self._previous = (cs.DATA_DIR, cs.HISTORY_DIR)
        cs.DATA_DIR = self.board_dir
        cs.HISTORY_DIR = self.board_dir / "history"

    def tearDown(self) -> None:
        cs.DATA_DIR, cs.HISTORY_DIR = self._previous
        self._tmp.cleanup()

    def test_rank_board_writes_lanes_with_separate_models(self) -> None:
        board = cs.rank_board(_artifacts(), cs.load_config(), now=NOW)

        rising = {entry["id"] for entry in board["lanes"]["rising"]}
        shelf = {entry["id"] for entry in board["lanes"]["shelf"]}

        assert "new-rising" in rising
        assert "new-rising" not in shelf, "a 5-day-old repo is not a reference"
        assert "michael-denyer-pstack-claude" in shelf
        assert "nutlope-hallmark" not in shelf, "an off-lens design skill is not admitted"
        assert board["counts"]["off_lens_excluded"] == 1
        assert shelf.isdisjoint(rising), "rising and shelf must not share entries"
        assert any(entry["reason"] for entry in board["lanes"]["rising"])

        assert board["lanes"]["practitioners"]
        assert board["counts"]["capabilities"] >= 1
        assert json.loads((self.board_dir / "latest.json").read_text())["schema_version"] == cs.SCHEMA_VERSION

    def test_capability_board_picks_one_representative_per_capability(self) -> None:
        board = cs.rank_board(_artifacts(), cs.load_config(), now=NOW)
        by_capability = {entry["capability"]: entry for entry in board["capabilities"]}
        assert "code-review" in by_capability
        representative = by_capability["code-review"]["representative"]
        assert representative["id"] == "michael-denyer-pstack-claude"
        assert representative["skill"]["name"] == "code-review"
        # One family may not represent two capabilities on the same board.
        families_used = [entry["representative"]["id"] for entry in board["capabilities"]]
        assert len(families_used) == len(set(families_used))
        assert "frontend-design" not in by_capability, "off-lens capabilities are not board groups"
        # One representative plus at most two alternates, never the whole inventory.
        assert len(by_capability["code-review"]["alternates"]) <= 2

    def test_rank_board_is_idempotent_and_persists_shelf_state(self) -> None:
        cfg = cs.load_config()
        first = cs.rank_board(_artifacts(), cfg, now=NOW)
        first_shelf = {entry["id"] for entry in first["lanes"]["shelf"]}

        second = cs.rank_board(_artifacts(), cfg, now=NOW)
        assert first_shelf == {entry["id"] for entry in second["lanes"]["shelf"]}

        state = json.loads((self.board_dir / "state.json").read_text())
        assert set(state["shelf"]) == first_shelf


    # --------------------------------------------------------------------------- #
    # discovery
    # --------------------------------------------------------------------------- #

    def test_one_stray_skill_cannot_create_a_capability_group(self) -> None:
        """A marketing bundle with a single "onboarding" skill must not claim
        codebase-navigation; the gate needs two name-matching skills."""
        artifacts = _artifacts()
        artifacts["repos"]["solo/marketing"] = _repo(
            "solo/marketing", stars=50000, forks=5000, age_days=200,
            skills=["onboarding", "campaign-copy"],
            description="Marketing skills for growth teams",
        )
        artifacts["families"] = cs.build_families(artifacts["repos"])
        board = cs.rank_board(artifacts, cs.load_config(), now=NOW)
        groups = {entry["capability"]: entry for entry in board["capabilities"]}
        assert "codebase-navigation" not in groups or groups["codebase-navigation"]["representative"]["lead"] != "solo/marketing"

    def test_capability_group_needs_two_name_matching_skills(self) -> None:
        artifacts = _artifacts()
        board = cs.rank_board(artifacts, cs.load_config(), now=NOW)
        assert board["capabilities"], "the fixture setup has two code-review skills"
        for entry in board["capabilities"]:
            assert "provisional" not in entry



def test_percentile_map_spans_zero_to_one():
    assert cs.percentile_map({"a": 1, "b": 2, "c": 3}) == {"a": 0.0, "b": 0.5, "c": 1.0}
    assert cs.percentile_map({}) == {}


def test_velocity_uses_the_baseline_seven_days_back():
    history = {
        "2026-10-20": {"a/x": {"stars": 100}},
        "2026-10-25": {"a/x": {"stars": 150}},
        "2026-11-01": {"a/x": {"stars": 400}},
    }
    assert cs.velocity(history, "a/x", NOW) == 250
    assert cs.velocity(history, "a/missing", NOW) is None


def test_novelty_decays():
    assert cs.novelty_score(NOW.date().isoformat(), NOW) == 1.0
    assert cs.novelty_score((NOW - timedelta(days=9)).date().isoformat(), NOW) < 0.2
    assert cs.novelty_score(None, NOW) == 0.0


def _artifacts():
    repos = {
        "new/rising": _repo(
            "new/rising", stars=1900, forks=60, age_days=5,
            skills=["code-review", "testing", "eval-benchmark"],
            description="Agent orchestration and evaluation harness",
        ),
        "backnotprop/pstack": _repo(
            "backnotprop/pstack", stars=3315, forks=235, age_days=159,
            skills=["architect", "arena", "code-review", "requesting-code-review",
                    "unit-test", "test-suite"],
            description="Skills and principles for rigorous engineering",
        ),
        "michael-denyer/pstack-claude": _repo(
            "michael-denyer/pstack-claude", stars=3725, forks=343, age_days=159,
            skills=["architect", "arena", "code-review", "requesting-code-review",
                    "unit-test", "test-suite"],
            description="Port of pstack for other harnesses",
        ),
        "nutlope/hallmark": _repo(
            "nutlope/hallmark", stars=44561, forks=2361, age_days=187,
            skills=["hallmark"], description="Anti-AI-slop design skill",
        ),
    }
    families = cs.build_families(repos)
    return {"repos": repos, "families": families}


def test_shelf_hysteresis_stops_flapping():
    previous = ["kept", "decayed"]
    scores = {"kept": 0.31, "decayed": 0.10, "newcomer": 0.40, "nearly": 0.34}
    members = cs.apply_shelf_hysteresis(
        previous, scores, ["kept", "decayed", "newcomer", "nearly"], entry=0.35, margin=0.05
    )
    assert members == {"kept", "newcomer"}
    assert "decayed" not in members, "an existing entry leaves once it decays past the margin"
    assert "nearly" not in members, "a new entry needs the full entry score"


def test_discovery_queries_cover_every_channel():
    cfg = cs.load_config()
    queries = cs.discovery_queries(cfg, ["pstack"])
    channels = {channel for channel, _ in queries}
    assert channels == {"momentum", "topic", "family"}
    momentum = [query for channel, query in queries if channel == "momentum"]
    assert all("created:>" in query and "stars:" in query for query in momentum), "bands keep each query under the 1000-result cap"
    assert any("topic:agent-skills" in query for _, query in queries)
    assert any("pstack in:name" in query for _, query in queries)


def test_discovery_bands_do_not_overlap():
    cfg = cs.load_config()
    bands = (cfg["discovery"]["momentum"]["bands"])
    assert len(bands) == len(set(bands))
    assert any(">=" in band for band in bands), "the top band must be open-ended"


# --------------------------------------------------------------------------- #
# path hygiene and family sweep names
# --------------------------------------------------------------------------- #


def test_test_fixtures_are_not_inventory():
    assert cs.is_excluded_path("test/fixtures/context-bill/tree-a/alpha/SKILL.md", ["test", "fixtures"])
    assert cs.is_excluded_path("node_modules/pkg/SKILL.md", ["node_modules"]) is True
    assert cs.is_excluded_path("skills/alpha/SKILL.md", ["test", "fixtures"]) is False
    # Excluding a part must not exclude a skill that merely has it in the name.
    assert cs.is_excluded_path("skills/fixtures-guide/SKILL.md", ["fixtures"]) is False
    assert cs.is_excluded_path("fixtures-guide/SKILL.md", ["fixtures"]) is False


def test_root_level_skills_report_root_layout():
    assert cs.layout_of("autoplan/SKILL.md") == "root"
    assert cs.layout_of("SKILL.md") == "root"
    assert cs.layout_of("skills/x/SKILL.md") == "skills"


def test_family_sweep_uses_whole_names_and_strips_harness_suffix():
    cfg = cs.load_config()
    repos = {
        "michael-denyer/pstack-claude": _repo("michael-denyer/pstack-claude", stars=3725, skills=["a", "b", "c"]),
        "backnotprop/pstack": _repo("backnotprop/pstack", stars=3315, skills=["a", "b", "c"]),
        "Egonex-AI/Understand-Anything": _repo("Egonex-AI/Understand-Anything", stars=89620, skills=["a", "b"]),
        "someone/skills": _repo("someone/skills", stars=9000, skills=["a"]),
    }
    names = cs.family_sweep_names(repos, cfg)
    assert "pstack-claude" not in names
    assert names.count("pstack") == 1
    assert "understand" not in names, "generic words must not consume a sweep"
    assert "anything" not in names
    assert "skills" not in names


def test_generic_shared_skill_names_do_not_merge_unrelated_repos():
    generic = ["plan", "review", "test", "ship", "spec"]
    repos = {
        "morluto/rea": _repo("morluto/rea", stars=418500, skills=generic),
        "anthropics/skills": _repo("anthropics/skills", stars=186334, skills=generic),
        "other/harness": _repo("other/harness", stars=90000, skills=generic),
    }
    families = cs.build_families(repos, stopwords=["skills", "claude"])
    assert len(families) == 3, "skill names alone must never prove a family"
    assert all(len(family["members"]) == 1 for family in families.values())


def test_explicit_reference_matching_is_word_bounded_and_ignores_generic_names():
    repos = {
        "morluto/rea": _repo("morluto/rea", stars=418500, skills=["a", "b", "c"]),
        "someone/create-things": _repo(
            "someone/create-things", stars=900, skills=["x", "y", "z"],
            description="Derived from creative work already in progress",
        ),
        "other/skills": _repo("other/skills", stars=5000, skills=["p", "q", "r"]),
        "port/maker": _repo(
            "port/maker", stars=10, skills=["d", "e", "f"],
            description="Port of rea for other harnesses",
        ),
    }
    families = cs.build_families(repos, stopwords=["skills"])

    def members_of(name):
        family = next(item for item in families.values() if name in item["members"])
        return set(family["members"])

    assert "morluto/rea" in members_of("port/maker"), "an explicit 'port of <name>' is a real pointer"
    assert "morluto/rea" not in members_of("someone/create-things"), "'already' must not match 'rea'"
    assert members_of("other/skills") == {"other/skills"}, "a generic name is not a pointer"


def test_census_never_stores_skill_content():
    """The committed census is metadata. Bodies would be tens of thousands of
    files and would grow without bound."""
    tree = [{"path": "skills/architect/SKILL.md", "sha": "1"}]
    skills, _ = cs.inventory_from_tree(tree, "a/pstack", max_skills=400)
    assert skills == [{"name": "architect", "copies": 1}]


def test_slim_repo_skills_normalizes_cached_inventories():
    repos = {
        "a/x": {
            "skills": [
                {"name": "alpha", "copies": 2, "path": "skills/alpha/SKILL.md", "sha": "deadbeef",
                 "layouts": ["skills"], "locales": []}
            ]
        }
    }
    cs.slim_repo_skills(repos)
    assert repos["a/x"]["skills"] == [{"name": "alpha", "copies": 2}]


def test_prune_repos_drops_repos_unseen_inside_retention():
    cfg = cs.load_config()
    cfg["discovery"]["retention_days"] = 45
    repos = {
        "old/repo": {"last_seen": (NOW - timedelta(days=90)).date().isoformat()},
        "fresh/repo": {"last_seen": (NOW - timedelta(days=3)).date().isoformat()},
        "never/seen": {"first_seen": (NOW - timedelta(days=1)).date().isoformat()},
    }
    kept = cs.prune_repos(repos, NOW, cfg)
    assert set(kept) == {"fresh/repo", "never/seen"}


# --------------------------------------------------------------------------- #
# capability gate (replaces the per-group "provisional" label)
# --------------------------------------------------------------------------- #


def test_keyword_matching_is_word_bounded():
    cfg = _taxonomy()
    taxonomy, harness = cfg["capabilities"]["taxonomy"], cfg["capabilities"]["harness_tokens"]
    # "memo" must not match "memory", and "paper" must not match "paperclip".
    assert cs.classify_capability("memory-forensics", "", taxonomy, harness)[0] != "docs-files"
    assert cs.classify_capability("create-paperclip-bundled-skill", "", taxonomy, harness)[0] != "research"
    # Real matches still work, including across hyphen normalization.
    assert cs.classify_capability("pptx-deck-context", "", taxonomy, harness)[0] == "docs-files"
    assert cs.classify_capability("db-citation-fixer", "", taxonomy, harness)[0] == "research"


def test_percentile_map_gives_ties_the_same_rank():
    values = {"a": 0, "b": 0, "c": 0, "d": 5}
    result = cs.percentile_map(values)
    assert result["a"] == result["b"] == result["c"]
    assert result["d"] == 1.0
    assert result["a"] < result["d"]


def load_tests(loader, tests, pattern):
    """Run the plain-function tests under `unittest discover` (the CI runner)."""
    suite = unittest.TestSuite()
    suite.addTest(loader.loadTestsFromTestCase(BoardTest))
    for name, obj in sorted(globals().items()):
        if name.startswith("test_") and callable(obj) and not isinstance(obj, type):
            suite.addTest(unittest.FunctionTestCase(obj, description=name))
    return suite


if __name__ == "__main__":
    unittest.main()
