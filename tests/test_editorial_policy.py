from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from pipeline import editorial
from pipeline.ranking import global_merge, stage_c_score_and_select
from unittest.mock import patch


def _item(title: str, source: str = "search_cn_open_weight_labs", **extra) -> dict:
    payload = {
        "id": f"{source}:{title}",
        "title": title,
        "source": source,
        "url": f"https://example.com/{abs(hash((source, title)))}",
        "published": "2026-10-24T00:00:00Z",
    }
    payload.update(extra)
    return payload


class SourceRoleTest(unittest.TestCase):
    def test_explicit_role_wins(self) -> None:
        cfg = editorial.load_config()
        self.assertEqual(editorial.source_role("anthropic_engineering", cfg), "first_party")
        self.assertEqual(editorial.source_role("search_cn_open_weight_labs", cfg), "search")

    def test_prefix_and_suffix_fallbacks(self) -> None:
        cfg = editorial.load_config()
        self.assertEqual(editorial.source_role("search_brand_new_query", cfg), "search")
        self.assertEqual(editorial.source_role("arxiv_new_category", cfg), "research")
        self.assertEqual(editorial.source_role("some_new_releases", cfg), "release")

    def test_unknown_source_is_default(self) -> None:
        cfg = editorial.load_config()
        self.assertEqual(editorial.source_role("brand_new_blog", cfg), "default")


class StoryClusterTest(unittest.TestCase):
    def test_deepseek_release_titles_collapse(self) -> None:
        titles = [
            "DeepSeek Ships a Faster Flash Model and Its Own Search API",
            "DeepSeek Makes V4.1-Flash-1017 Official With MIT-Licensed Weights and Stronger Agentic Coding",
            "DeepSeek Releases V4.1-Flash-1017 Update, Says It's Faster and Leaner",
            "Deepseek V4.1 Flash 1017 beats larger rivals in agentic tasks",
        ]
        out, diag = editorial.cluster_items([_item(t) for t in titles], editorial.load_config())
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["story_cluster_size"], 4)
        self.assertEqual(diag["collapsed"], 3)

    def test_different_events_about_the_same_company_stay_apart(self) -> None:
        titles = [
            "DeepSeek Releases V4.1-Flash-1017 Update",
            "DeepSeek Suffers Nearly 5-Hour Outage as China’s AI Boom Fuels Chip Shortage",
            "DeepSeek Raises $12 Billion in New Funding",
            "Teen Prodigy Behind Kimi Breakthrough Leaves Moonshot AI for U.S.",
        ]
        out, _ = editorial.cluster_items([_item(t) for t in titles], editorial.load_config())
        self.assertEqual(len(out), 4)

    def test_release_feed_patch_versions_stay_apart(self) -> None:
        titles = [
            "Claude Code v2.1.296",
            "Claude Code v2.1.302",
        ]
        out, _ = editorial.cluster_items(
            [
                _item(t, source="claude_code_releases", url=f"https://github.com/anthropics/claude-code/releases/tag/{t.rsplit(' ', 1)[-1]}")
                for t in titles
            ],
            editorial.load_config(),
        )
        self.assertEqual(len(out), 2)


    def test_model_less_release_versions_stay_apart(self) -> None:
        titles = [
            "Release 2.64.0 corresponding to NGC container 25.12",
            "Release 2.73.0 corresponding to NGC container 26.09",
        ]
        out, _ = editorial.cluster_items(
            [
                _item(
                    title,
                    source="triton_releases",
                    url=f"https://github.com/triton-inference-server/server/releases/tag/v{title.split()[1]}",
                )
                for title in titles
            ],
            editorial.load_config(),
        )
        self.assertEqual(len(out), 2)

    def test_prerelease_versions_stay_apart(self) -> None:
        titles = [
            "codex 0.164.0-alpha.8",
            "codex 0.164.0-alpha.9",
            "codex 0.164.0-alpha.12",
            "codex 0.164.0",
        ]
        out, _ = editorial.cluster_items(
            [
                _item(
                    title,
                    source="openai_codex_releases",
                    url=f"https://github.com/openai/codex/releases/tag/rust-v{title.split()[-1]}",
                )
                for title in titles
            ],
            editorial.load_config(),
        )
        self.assertEqual(len(out), 4)

    def test_unrelated_posts_about_the_same_product_stay_apart(self) -> None:
        titles = [
            "Getting started with Claude Code hooks",
            "Claude Code hooks: five mistakes to avoid",
            "Using subagents in Claude Code",
            "Claude Code subagents: a practical review",
        ]
        out, _ = editorial.cluster_items(
            [_item(title, source="claude_dev_blog") for title in titles],
            editorial.load_config(),
        )
        self.assertEqual(len(out), 4)

    def test_huggingface_org_releases_do_not_collapse_across_models(self) -> None:
        titles = [
            "moonshotai/Kimi-K2.7-Code released on Hugging Face",
            "moonshotai/Kimi-K3 released on Hugging Face",
            "moonshotai/Kimi-K2-Base released on Hugging Face",
        ]
        out, _ = editorial.cluster_items(
            [
                _item(title, source="hf_moonshotai_releases", url=f"https://huggingface.co/{title.split()[0]}")
                for title in titles
            ],
            editorial.load_config(),
        )
        self.assertEqual(len(out), 3)

    def test_huggingface_org_release_sizes_stay_apart(self) -> None:
        titles = [
            "Qwen/Qwen3.8-2.4T-A95B released on Hugging Face",
            "Qwen/Qwen3.8-2.8T-A95B released on Hugging Face",
        ]
        out, _ = editorial.cluster_items(
            [
                _item(title, source="hf_qwen_releases", url=f"https://huggingface.co/{title.split()[0]}")
                for title in titles
            ],
            editorial.load_config(),
        )
        self.assertEqual(len(out), 2)

    def test_old_coverage_does_not_merge_into_a_current_story(self) -> None:
        now = datetime.now(timezone.utc)
        old = _item(
            "Gemini 4 Argon available on Google Cloud",
            source="google_cloud_blog",
            published=(now - timedelta(days=20)).isoformat(),
        )
        fresh = _item(
            "Google optimizes the Agent Development Kit with Gemini 4 Argon",
            source="infoq_ai_ml",
            published=(now - timedelta(hours=2)).isoformat(),
        )
        out, _ = editorial.cluster_items([old, fresh], editorial.load_config())
        self.assertEqual(len(out), 2)

    def test_fresh_member_becomes_the_card_when_the_original_is_stale(self) -> None:
        now = datetime.now(timezone.utc)
        stale = _item(
            "Gemini 4 Argon available on Google Cloud",
            source="google_cloud_blog",
            published=(now - timedelta(days=11)).isoformat(),
        )
        fresh = _item(
            "Google Optimizes the Agent Development Kit with Gemini 4 Argon",
            source="infoq_ai_ml",
            published=(now - timedelta(hours=2)).isoformat(),
        )
        out, _ = editorial.cluster_items([stale, fresh], editorial.load_config())
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["source"], "infoq_ai_ml")
        self.assertEqual(out[0]["also_covered"][0]["source"], "google_cloud_blog")

    def test_first_party_original_beats_search_echo(self) -> None:
        original = _item(
            "Redesigning source control at Anthropic",
            source="anthropic_engineering",
            published="2026-10-23T00:00:00Z",
        )
        echo = _item(
            "Redesigning source control at Anthropic",
            source="search_agent_engineering_news",
            published="2026-10-24T00:00:00Z",
        )
        out, _ = editorial.cluster_items([echo, original], editorial.load_config())
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["source"], "anthropic_engineering")
        self.assertEqual(out[0]["also_covered"][0]["source"], "search_agent_engineering_news")


class SearchQuarantineTest(unittest.TestCase):
    def test_gossip_and_business_tail_is_dropped(self) -> None:
        items = [
            _item("Teen Prodigy Behind Kimi Breakthrough Leaves Moonshot AI for U.S."),
            _item("DeepSeek Suffers Nearly 5-Hour Outage as China’s AI Boom Fuels Chip Shortage"),
            _item("DeepSeek Raises $12 Billion in New Funding"),
            _item("Claude Code vs Codex vs Copilot: 2026 Comparison"),
            _item("DeepSeek Releases V4.1-Flash-1017 Update"),
            _item("DeepSeek Harness v0.2.1 Pre-Release Adds Reasoning Translation"),
        ]
        out, diag = editorial.apply_pre_ranking(items, use_seen=False)
        titles = [it["title"] for it in out]
        self.assertIn("DeepSeek Releases V4.1-Flash-1017 Update", titles)
        self.assertIn("DeepSeek Harness v0.2.1 Pre-Release Adds Reasoning Translation", titles)
        self.assertNotIn("Teen Prodigy Behind Kimi Breakthrough Leaves Moonshot AI for U.S.", titles)
        self.assertNotIn("DeepSeek Suffers Nearly 5-Hour Outage as China’s AI Boom Fuels Chip Shortage", titles)
        self.assertNotIn("DeepSeek Raises $12 Billion in New Funding", titles)
        self.assertNotIn("Claude Code vs Codex vs Copilot: 2026 Comparison", titles)
        self.assertGreaterEqual(diag["search_dropped_low_quality"], 4)

    def test_search_source_candidate_cap(self) -> None:
        items = [
            _item(f"Kimi K3.1 release note {i}", published=f"2026-10-24T0{i}:00:00Z")
            for i in range(1, 6)
        ]
        _out, diag = editorial.apply_pre_ranking(items, use_seen=False)
        self.assertEqual(diag["search_dropped_over_cap"], 3)


class FirstPartyQuarantineTest(unittest.TestCase):
    def test_marketing_is_dropped_but_engineering_is_kept(self) -> None:
        items = [
            _item("ChatGPT Ads expands to 26 new countries as over 100,000 advertisers have used the platform", "openai_blog"),
            _item("Broad access through consistent standards", "openai_blog"),
            _item("How AT&T is rethinking in-house legal work with OpenAI", "openai_blog"),
            _item("Patch the Planet: global response coordination as agents uncover critical vulnerabilities", "openai_blog"),
            _item("Securing our frontier model training environment", "openai_blog"),
        ]
        out, diag = editorial.apply_pre_ranking(items, use_seen=False)
        titles = {it["title"] for it in out}
        self.assertNotIn("ChatGPT Ads expands to 26 new countries as over 100,000 advertisers have used the platform", titles)
        self.assertNotIn("Broad access through consistent standards", titles)
        self.assertNotIn("How AT&T is rethinking in-house legal work with OpenAI", titles)
        self.assertIn("Patch the Planet: global response coordination as agents uncover critical vulnerabilities", titles)
        self.assertIn("Securing our frontier model training environment", titles)
        self.assertGreaterEqual(diag["first_party_dropped_low_value"], 3)


class HistoryAliasTest(unittest.TestCase):
    def test_one_item_counts_once_despite_multiple_lookup_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runs_dir = root / "runs"
            runs_dir.mkdir()
            item = {
                "title": "A repeated agent story",
                "url": "https://example.com/agent-story",
                "story_key": "model:agent|title:a repeated agent story",
                "published": "2026-10-24T00:00:00Z",
            }
            (runs_dir / "run.json").write_text(
                json.dumps({"run_at": "2026-10-24T01:00:00Z", "items": [item]}),
                encoding="utf-8",
            )
            index = root / "runs_index.json"
            index.write_text(json.dumps([{"path": "run.json"}]), encoding="utf-8")
            with (
                patch.object(editorial, "RUNS_DIR", runs_dir),
                patch.object(editorial, "RUNS_INDEX", index),
            ):
                history = editorial.load_recent_history(editorial.load_config())
            self.assertEqual(history[item["story_key"]]["count"], 1)
            self.assertEqual(history[item["url"]]["count"], 1)
            self.assertEqual(history[editorial.normalize_title(item["title"])]["count"], 1)


class SeenMemoryTest(unittest.TestCase):
    def _history(self, key: str, count: int) -> dict:
        return {key: {"count": count, "first_seen": "2026-10-23T00:00:00Z", "last_seen": "2026-10-24T00:00:00Z"}}

    def test_retires_a_story_after_its_edition_cap(self) -> None:
        cfg = editorial.load_config()
        done = _item("Old corporate policy update", source="anthropic_newsroom")
        done["story_key"] = "story:old-corporate"
        fresh = [
            _item(f"Fresh story {i}", source="openai_blog", published=f"2026-10-24T0{i}:00:00Z")
            for i in range(1, 13)
        ]
        history = self._history("story:old-corporate", 10)
        out, diag = editorial._apply_seen_memory([done] + fresh, cfg, history)
        self.assertEqual(diag["seen_dropped"], 1)
        self.assertNotIn(done["title"], [it["title"] for it in out])

    def test_quiet_day_keeps_repeats_with_a_penalty(self) -> None:
        cfg = editorial.load_config()
        seen = _item("Seen but still the only story", source="openai_blog")
        seen["story_key"] = "story:quiet"
        history = self._history("story:quiet", 4)
        out, diag = editorial._apply_seen_memory([seen], cfg, history)
        self.assertEqual(diag["seen_dropped"], 0)
        self.assertEqual(len(out), 1)
        self.assertGreater(out[0]["editorial_penalty"], 0)

    def test_source_override_is_shorter_than_the_role_cap(self) -> None:
        cfg = editorial.load_config()
        corporate = _item("Anthropic corporate item", source="anthropic_newsroom")
        corporate["story_key"] = "story:corporate-override"
        fresh = [
            _item(f"Fresh story {i}", source="openai_blog", published=f"2026-10-24T0{i}:00:00Z")
            for i in range(1, 13)
        ]
        history = self._history("story:corporate-override", 7)
        out, diag = editorial._apply_seen_memory([corporate] + fresh, cfg, history)
        self.assertEqual(diag["seen_dropped"], 1)
        self.assertNotIn(corporate["title"], [it["title"] for it in out])


class RankingEditorialTest(unittest.TestCase):
    def test_editorial_penalty_lowers_the_slot_score(self) -> None:
        cfg = {
            "slots": {
                "frontier_official": {
                    "max_items": 2,
                    "max_per_source": 2,
                    "blend": {"alpha": 1.0, "beta": 0.0},
                }
            },
            "time_decay": {"enabled": False},
        }
        penalized = _item(
            "Penalized agent post",
            source="openai_blog",
            slot="frontier_official",
            freshness=1.0,
            editorial_penalty=0.5,
        )
        clean = _item(
            "Clean agent post",
            source="openai_blog",
            slot="frontier_official",
            freshness=1.0,
            editorial_penalty=0.0,
        )
        labels = {
            penalized["id"]: {"fit_agentic_platform": 4, "actionability": 4, "novelty": 3, "evidence_quality": 3, "hype_risk": 1},
            clean["id"]: {"fit_agentic_platform": 4, "actionability": 4, "novelty": 3, "evidence_quality": 3, "hype_risk": 1},
        }
        with patch("pipeline.ranking.label_items", return_value=(labels, {"llm_called": 0, "cache_hits": 0})):
            selected, _diag = stage_c_score_and_select(
                {"frontier_official": [penalized, clean]}, cfg, llm_budget=0
            )
        out = selected["frontier_official"]
        self.assertEqual([item["id"] for item in out], [clean["id"], penalized["id"]])
        self.assertAlmostEqual(out[1]["editorial_penalty"], 0.5)
        self.assertAlmostEqual(out[1]["pre_decay_score"], out[0]["pre_decay_score"] - 0.5, places=3)

    def test_floor_prefers_judged_ok_items_before_filling_below_the_bar(self) -> None:
        cfg = {
            "max_items": 4,
            "judge_ranking": {
                "headroom_min_score": 0.2,
                "headroom_drop_categories": ["off_topic"],
                "headroom_category_min_score": 0.6,
            },
            "judge_gate": {},
            "slots": {"practitioner_analysis": {"min_items": 2, "max_items": 2}},
            "dynamic_slot_rerank": {"enabled": False},
        }
        items = [
            _item("low-one", source="simon_willison", source_role="practitioner", slot="practitioner_analysis", final_score=3.0, judge_score=0.1, judge_verdict="review", judge_category="agent_engineering"),
            _item("low-two", source="simon_willison", source_role="practitioner", slot="practitioner_analysis", final_score=2.9, judge_score=0.15, judge_verdict="review", judge_category="agent_engineering"),
            _item("good-one", source="simon_willison", source_role="practitioner", slot="practitioner_analysis", final_score=2.8, judge_score=0.8, judge_verdict="keep", judge_category="agent_engineering"),
            _item("good-two", source="simon_willison", source_role="practitioner", slot="practitioner_analysis", final_score=2.7, judge_score=0.7, judge_verdict="keep", judge_category="agent_engineering"),
        ]
        out, _priority, diag = global_merge({"practitioner_analysis": items}, cfg)
        ids = [item["id"] for item in out]
        self.assertEqual(ids, ["simon_willison:good-one", "simon_willison:good-two"])
        self.assertEqual(diag["floor_selected"], 2)
        self.assertNotIn("low-one", ids)

    def test_floor_still_fills_when_all_candidates_are_below_the_bar(self) -> None:
        cfg = {
            "max_items": 2,
            "judge_ranking": {"headroom_min_score": 0.2},
            "judge_gate": {},
            "slots": {"practitioner_analysis": {"min_items": 2, "max_items": 2}},
            "dynamic_slot_rerank": {"enabled": False},
        }
        items = [
            _item("low-one", source="simon_willison", source_role="practitioner", slot="practitioner_analysis", final_score=3.0, judge_score=0.1, judge_verdict="review"),
            _item("low-two", source="simon_willison", source_role="practitioner", slot="practitioner_analysis", final_score=2.9, judge_score=0.15, judge_verdict="review"),
        ]
        out, _priority, diag = global_merge({"practitioner_analysis": items}, cfg)
        self.assertEqual(len(out), 2)
        self.assertEqual(diag["floor_selected"], 2)

    def test_global_merge_caps_search_items(self) -> None:
        cfg = {
            "max_items": 4,
            "editorial_caps": {"max_search_items": 1},
            "slots": {
                "community_signal": {"min_items": 1, "max_items": 4},
                "practitioner_analysis": {"min_items": 0, "max_items": 4},
            },
            "dynamic_slot_rerank": {"enabled": False},
        }
        search_items = [
            _item("Search story one", source="search_cn_open_weight_labs", source_role="search", final_score=3.0),
            _item("Search story two", source="search_llm_ops_news", source_role="search", final_score=2.9),
        ]
        practitioner = [
            _item("Practitioner story one", source="simon_willison", source_role="practitioner", final_score=2.8),
            _item("Practitioner story two", source="latent_space", source_role="practitioner", final_score=2.7),
        ]
        out, _priority, diag = global_merge(
            {"community_signal": search_items, "practitioner_analysis": practitioner}, cfg
        )
        self.assertEqual(len([it for it in out if it.get("source_role") == "search"]), 1)
        self.assertGreaterEqual(diag["skip_search_cap"], 1)


class EditorialCommunityCapConfigTest(unittest.TestCase):
    def test_api_community_caps_match_the_ranking_slot(self) -> None:
        cfg = editorial.load_config()
        self.assertEqual(cfg["caps"]["community"], 4)
        self.assertEqual(cfg["role_totals"]["community"], 4)


if __name__ == "__main__":
    unittest.main()
