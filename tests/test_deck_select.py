"""Deck selector: min-cost-flow optimality, constraints, scoring, collapse."""
from __future__ import annotations

import itertools
import random
import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))

import deck_select as ds  # noqa: E402
from mincostflow import MinCostFlow  # noqa: E402

CFG = {
    "weights": {"judge_keep": 1.0, "platform_relevant": 0.0, "coverage": 0.25, "source_tune": 0.0, "in_edition": 0.0, "corporate_marketing": 0.0},
    "unjudged": {"scale": 0.9, "fallback": 0.35, "platform_relevant": 0.5, "corporate_marketing": 0.2},
    "release": {"major": 0.55, "minor": 0.2, "unknown": 0.3},
    "decks": {},
}


def story(i, utility, source, category, **extra):
    return {"story_id": f"s{i}", "utility": utility, "source": source, "judge_category": category, **extra}


def brute_force(stories, deck, budget):
    """Best total utility under the same constraints (no floors)."""
    best = 0.0
    eligible = [s for s in stories if s["utility"] >= deck.get("min_utility", 0) and s["utility"] > 0]
    for k in range(0, min(budget, len(eligible)) + 1):
        for combo in itertools.combinations(eligible, k):
            by_src = Counter(s["source"] for s in combo)
            by_cat = Counter(ds.category_of(s) for s in combo)
            if any(n > ds._source_cap(deck, src) for src, n in by_src.items()):
                continue
            role_of = ds.source_roles(stories)
            by_role = Counter(role_of.get(s["source"], "") for s in combo)
            if any(n > ds._role_cap(deck, role) for role, n in by_role.items()):
                continue
            if any(n > ds._category_bounds(deck, cat)[1] for cat, n in by_cat.items()):
                continue
            best = max(best, sum(s["utility"] for s in combo))
    return best


class MinCostFlowTest(unittest.TestCase):
    def test_stops_when_next_path_does_not_help(self):
        mcf = MinCostFlow(4)
        a = mcf.add_edge(0, 2, 1, -5)
        b = mcf.add_edge(0, 3, 1, 3)
        mcf.add_edge(2, 1, 1, 0)
        mcf.add_edge(3, 1, 1, 0)
        flow, cost = mcf.solve(0, 1, 5)
        self.assertEqual((flow, cost), (1, -5))
        self.assertEqual((mcf.flow_on(a), mcf.flow_on(b)), (1, 0))


class SolveTest(unittest.TestCase):
    def test_matches_brute_force_on_random_instances(self):
        rng = random.Random(7)
        roles = {"a": "research", "b": "research", "c": "community", "d": "first_party"}
        for trial in range(80):
            n = rng.randint(1, 9)
            stories = [
                story(i, round(rng.uniform(0.0, 1.5), 3), src, rng.choice(["agent_engineering", "inference_serving", "research_method"]), source_role=roles[src])
                for i in range(n)
                for src in [rng.choice("abcd")]
            ]
            deck = {
                "budget": rng.randint(1, 6),
                "min_utility": rng.choice([0.0, 0.4]),
                "max_per_source": rng.randint(1, 3),
                "roles": {"research": {"max": rng.randint(0, 3)}},
                "categories": {"default": {"max": rng.randint(1, 3)}, "research_method": {"max": rng.randint(0, 2)}},
            }
            chosen = set(ds.solve(stories, deck))
            got = sum(s["utility"] for s in stories if s["story_id"] in chosen)
            want = brute_force(stories, deck, deck["budget"])
            self.assertAlmostEqual(got, want, places=2, msg=f"trial {trial}: {stories} {deck}")

    def test_greedy_would_fail_but_flow_is_optimal(self):
        # Greedy takes s0 (1.0, source a, cat X) and then can take nothing else:
        # source a is capped at 1 and category X at 1. Flow takes s1 + s2.
        stories = [
            story(0, 1.0, "a", "agent_engineering"),
            story(1, 0.9, "a", "inference_serving"),
            story(2, 0.8, "b", "agent_engineering"),
        ]
        deck = {"budget": 2, "max_per_source": 1, "categories": {"default": {"max": 1}}}
        self.assertEqual(set(ds.solve(stories, deck)), {"s1", "s2"})

    def test_floor_pulls_in_an_eligible_lower_utility_story(self):
        stories = [story(0, 1.0, "a", "agent_engineering"), story(1, 0.9, "b", "agent_engineering"), story(2, 0.6, "c", "evaluation_reliability")]
        deck = {"budget": 2, "categories": {"default": {"max": 5}, "evaluation_reliability": {"min": 1}}}
        self.assertEqual(set(ds.solve(stories, deck)), {"s0", "s2"})

    def test_quiet_window_returns_fewer_than_budget(self):
        stories = [story(0, 0.9, "a", "agent_engineering"), story(1, 0.3, "b", "agent_engineering")]
        deck = {"budget": 10, "min_utility": 0.5}
        self.assertEqual(ds.solve(stories, deck), ["s0"])

    def test_zero_cap_category_is_excluded(self):
        stories = [story(0, 2.0, "a", "off_topic"), story(1, 0.6, "b", "agent_engineering")]
        deck = {"budget": 5, "categories": {"off_topic": {"max": 0}}}
        self.assertEqual(ds.solve(stories, deck), ["s1"])


class ScoringTest(unittest.TestCase):
    def test_unjudged_items_take_the_role_prior_not_zero(self):
        rows = [
            {"key": "a", "source_role": "community", "judge_score": 0.8},
            {"key": "b", "source_role": "community", "judge_score": 0.6},
            {"key": "c", "source_role": "community"},
        ]
        priors = ds.score_priors(rows, CFG)
        score, basis = ds.base_score(rows[2], CFG, priors)
        self.assertAlmostEqual(score, 0.9 * 0.7)
        self.assertEqual(basis, "prior:community")

    def test_release_items_use_the_release_tier(self):
        row = {"key": "r", "type": "release", "release_tier": "major", "judge_score": 0.02}
        self.assertEqual(ds.base_score(row, CFG, {"*": 0.5}), (0.55, "release:major"))
        self.assertEqual(ds.category_of(row), "release_note")

    def test_collapse_keeps_best_member_and_counts_sources(self):
        rows = [
            {"key": "u1", "url": "u1", "story_key": "k", "source": "hn", "judge_score": 0.4},
            {"key": "u2", "url": "u2", "story_key": "k", "source": "blog", "judge_score": 0.9, "edition_runs": 0},
            {"key": "u3", "url": "u3", "story_key": "k", "source": "search", "judge_score": 0.5, "edition_runs": 3},
            {"key": "u4", "url": "u4", "source": "hn", "judge_score": 0.7},
        ]
        stories = ds.score_stories(rows, CFG)
        self.assertEqual(len(stories), 2)
        top = stories[0]
        self.assertEqual(top["key"], "u2")
        self.assertEqual(top["source_count"], 3)
        self.assertEqual(top["edition_runs"], 3)
        self.assertEqual(sorted(top["member_urls"]), ["u1", "u2", "u3"])
        self.assertAlmostEqual(top["utility"], 0.9 + 0.25 * __import__("math").log1p(2), places=3)

    def test_same_model_version_headlines_merge_into_one_story(self):
        rows = [
            {"key": "u1", "url": "u1", "story_key": "model:moonshot|ver:3.1|title:a", "title": "Moonshot AI resets Kimi K3.1 Pro quotas", "source": "search_x", "judge_score": 0.5},
            {"key": "u2", "url": "u2", "story_key": "model:kimi|ver:3.1|title:b", "title": "Kimi K3.1 Pro: open weights, 1M context", "source": "latent_space", "judge_score": 0.8},
            {"key": "u3", "url": "u3", "title": "Introducing Kimi K3.1 Pro", "source": "simon_willison"},
            {"key": "u4", "url": "u4", "title": "Kimi K3 on AMD MI355X", "source": "vllm_blog", "judge_score": 0.7},
            {"key": "u5", "url": "u5", "title": "Claude Code adds hooks", "source": "hn", "judge_score": 0.6},
            {"key": "u6", "url": "u6", "title": "Claude Code sandbox write-up", "source": "blog", "judge_score": 0.6},
        ]
        stories = {s["key"]: s for s in ds.score_stories(rows, CFG)}
        self.assertEqual(set(stories), {"u2", "u4", "u5", "u6"})
        self.assertEqual(sorted(stories["u2"]["member_urls"]), ["u1", "u2", "u3"])
        self.assertEqual(stories["u2"]["source_count"], 3)
        off = ds.score_stories(rows, {**CFG, "collapse": {"merge_model_version_events": False}})
        self.assertEqual(len(off), 6)

    def test_select_reports_shortlist_and_bench_reasons(self):
        cfg = {**CFG, "decks": {"t": {"budget": 2, "bench": 5, "min_utility": 0.3, "max_per_source": 1, "categories": {"default": {"max": 5}}}}}
        rows = [
            {"key": "a1", "url": "a1", "source": "a", "judge_score": 0.9, "judge_category": "agent_engineering"},
            {"key": "a2", "url": "a2", "source": "a", "judge_score": 0.8, "judge_category": "agent_engineering"},
            {"key": "b1", "url": "b1", "source": "b", "judge_score": 0.7, "judge_category": "agent_engineering"},
            {"key": "c1", "url": "c1", "source": "c", "judge_score": 0.6, "judge_category": "agent_engineering"},
            {"key": "d1", "url": "d1", "source": "d", "judge_score": 0.1, "judge_category": "agent_engineering"},
        ]
        out = ds.select(rows, "t", cfg=cfg)
        self.assertEqual([c["key"] for c in out["shortlist"]], ["a1", "b1"])
        reasons = {c["key"]: c["bench_reason"] for c in out["bench"]}
        self.assertEqual(reasons, {"a2": "source_cap:a", "c1": "budget", "d1": "below_min_utility"})


class ConfigTest(unittest.TestCase):
    def test_shipped_config_has_daily_and_weekly(self):
        cfg = ds.load_config()
        for deck in ("daily", "weekly"):
            spec = ds.deck_config(deck, cfg)
            self.assertGreater(spec["budget"], 0)
            self.assertEqual(ds._category_bounds(spec, "off_topic")[1], 0)


if __name__ == "__main__":
    unittest.main()
