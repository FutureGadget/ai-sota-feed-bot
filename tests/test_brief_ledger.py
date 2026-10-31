"""Admission ledger: gates, quotas, story collapse, and append-only updates."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))

import brief_ledger as bl  # noqa: E402
import ops_daily_summary  # noqa: E402
import story_store  # noqa: E402

DAY = "2026-10-27"
RUN_AT = f"{DAY}T12:00:00+00:00"


def _write(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _row(
    url: str,
    *,
    source: str,
    role: str,
    title: str,
    score: float | None = 0.9,
    verdict: str = "keep",
    category: str = "agent_engineering",
    story_key: str | None = None,
    first_seen: str = f"{DAY}T09:00:00+00:00",
    published: str = f"{DAY}T08:00:00+00:00",
    type: str = "news",
    release_tier: str | None = None,
    evidence: int | None = 900,
    also_covered=None,
    **extra,
):
    return {
        "title": title,
        "url": url,
        "source": source,
        "source_role": role,
        "type": type,
        "published": published,
        "story_key": story_key or f"story:{url}",
        "judge_score": score,
        "judge_verdict": verdict,
        "judge_category": category,
        "judge_evidence_chars": evidence,
        "judge_signals": {"platform_relevant": 0.8},
        "release_tier": release_tier,
        "first_seen_run": first_seen,
        "last_seen_run": first_seen,
        "runs_seen": 1,
        "edition_runs": 0,
        "summary": f"{title} summary",
        "also_covered": also_covered or [],
        "source_count": 1,
        **extra,
    }


class BriefLedgerTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        self.brief = root / "brief"
        self.pool = root / "pool"
        self.processed = root / "processed"
        self.stories = root / "stories"
        self.config = root / "brief.yaml"
        _write(
            self.config,
            {
                "enabled": True,
                "exclude_categories": ["off_topic"],
                "min_admit_score": 0.35,
                "min_evidence_chars": 300,
                "release": {"major": 0.55, "minor": 0.2, "unknown": 0.3},
                "unjudged": {
                    "scale": 0.9,
                    "fallback": 0.35,
                    "platform_relevant": 0.5,
                    "corporate_marketing": 0.2,
                },
                "weights": {
                    "judge_keep": 1.0,
                    "platform_relevant": 0.3,
                    "coverage": 0.25,
                    "source_tune": 0.5,
                    "in_edition": 0.05,
                    "corporate_marketing": 0.3,
                    "freshness": 0.2,
                    "must_cover": 1.0,
                },
                "freshness": {"half_life_hours": 36, "floor": 0.25},
                "quotas": {
                    "global_per_day": 10,
                    "per_source_per_6h": 2,
                    "roles": {
                        "first_party": 5,
                        "practitioner": 5,
                        "community": 5,
                        "research": 5,
                        "release": 5,
                        "search": 5,
                        "aggregator": 5,
                        "default": 5,
                    },
                },
            },
        )

    def tearDown(self):
        self._tmp.cleanup()

    def write_pool(self, rows: list[dict], day: str = DAY):
        _write(
            self.pool / f"{day}.json",
            {
                "date": day,
                "updated_at": f"{day}T12:00:00+00:00",
                "items": {row["url"]: row for row in rows},
            },
        )

    def run_record(self, run_at: str = RUN_AT, rebuild: bool = False):
        return bl.record_run(
            None,
            None,
            run_at=run_at,
            brief_dir=self.brief,
            pool_dir=self.pool,
            config_path=self.config,
            rebuild=rebuild,
        )

    def ledger(self, day: str = DAY) -> dict:
        return json.loads((self.brief / f"{day}.json").read_text(encoding="utf-8"))

    def test_gate_admits_keeps_reviews_unjudged_with_evidence_and_releases(self):
        self.write_pool(
            [
                _row("https://a.com/keep", source="simon_willison", role="practitioner", title="Keep", score=0.9),
                _row("https://a.com/review", source="latent_space", role="practitioner", title="Keep band", score=0.4, verdict="keep"),
                _row("https://a.com/review-low", source="latent_space", role="practitioner", title="Review band", score=0.2, verdict="review"),
                _row("https://a.com/drop", source="openai_blog", role="first_party", title="Drop", score=0.05, verdict="drop"),
                _row("https://a.com/drop-high", source="openai_blog", role="first_party", title="High-score drop", score=0.9, verdict="drop"),
                _row("https://a.com/offtopic", source="openai_blog", role="first_party", title="Off topic", score=0.9, category="off_topic"),
                _row("https://a.com/thin", source="arxiv_cs_ai", role="research", title="Thin evidence", score=None, verdict="unjudged", evidence=100),
                _row("https://a.com/unjudged", source="arxiv_cs_ai", role="research", title="Enough evidence", score=None, verdict="unjudged", evidence=900),
                _row(
                    "https://a.com/release",
                    source="vllm_releases",
                    role="release",
                    title="vLLM 1.0",
                    score=0.02,
                    verdict="drop",
                    category="release_note",
                    type="release",
                    release_tier="major",
                ),
            ]
        )
        diag = self.run_record()
        self.assertTrue(diag["written"])
        items = self.ledger()["items"]
        urls = {item["url"] for item in items.values()}
        self.assertEqual(
            urls,
            {
                "https://a.com/keep",
                "https://a.com/review",
                "https://a.com/unjudged",
                "https://a.com/release",
            },
        )
        self.assertEqual(diag["rejected_gate"].get("judge_drop"), 2)
        self.assertEqual(diag["rejected_gate"].get("score_low"), 1)
        self.assertEqual(diag["rejected_gate"].get("off_topic"), 1)
        self.assertEqual(diag["rejected_gate"].get("insufficient_evidence"), 1)

    def test_story_collapse_keeps_one_card_and_records_the_other(self):
        self.write_pool(
            [
                _row(
                    "https://a.com/kimi-a",
                    source="openai_blog",
                    role="first_party",
                    title="Kimi K3.1 Pro launches",
                    story_key="story:kimi",
                ),
                _row(
                    "https://a.com/kimi-b",
                    source="simon_willison",
                    role="practitioner",
                    title="Moonshot releases Kimi K3.1 Pro",
                    story_key="story:kimi",
                    also_covered=[
                        {
                            "source": "latent_space",
                            "url": "https://a.com/kimi-c",
                            "title": "Kimi K3.1 Pro analysis",
                        }
                    ],
                ),
            ]
        )
        self.run_record()
        items = self.ledger()["items"]
        self.assertEqual(len(items), 1)
        item = next(iter(items.values()))
        self.assertIn(item["url"], {"https://a.com/kimi-a", "https://a.com/kimi-b"})
        self.assertEqual(len(item["also_covered"]), 2)
        self.assertEqual(
            {entry["source"] for entry in item["also_covered"]},
            {"simon_willison", "latent_space"},
        )

    def test_late_judgment_clears_the_stale_judge_error(self):
        self.write_pool(
            [
                _row(
                    "https://a.com/late",
                    source="simon_willison",
                    role="practitioner",
                    title="Late judgment",
                    score=None,
                    verdict="unjudged",
                    evidence=None,
                    judge_error="judge_timeout",
                )
            ]
        )
        self.run_record()
        item = next(iter(self.ledger()["items"].values()))
        self.assertEqual(item["judge_error"], "judge_timeout")

        self.write_pool(
            [
                _row(
                    "https://a.com/late",
                    source="simon_willison",
                    role="practitioner",
                    title="Late judgment",
                    score=0.8,
                    verdict="keep",
                    evidence=900,
                )
            ]
        )
        self.run_record(run_at=f"{DAY}T13:00:00+00:00")
        item = next(iter(self.ledger()["items"].values()))
        self.assertEqual(item["judge_score"], 0.8)
        self.assertEqual(item["judge_verdict"], "keep")
        self.assertNotIn("judge_error", item)

    def test_append_only_and_last_seen_update(self):
        self.write_pool([_row("https://a.com/first", source="simon_willison", role="practitioner", title="First")])
        self.run_record()
        first = self.ledger()
        admitted_at = first["items"]["story:https://a.com/first"]["admitted_at"]
        # Normal builds anchor the 24h window at the moment of admission, not
        # the earlier pool sighting.
        self.assertEqual(admitted_at, RUN_AT)

        self.write_pool(
            [
                _row(
                    "https://a.com/first",
                    source="simon_willison",
                    role="practitioner",
                    title="First",
                    first_seen=f"{DAY}T09:00:00+00:00",
                ),
                _row("https://a.com/second", source="latent_space", role="practitioner", title="Second"),
            ]
        )
        # Move the first story's last sighting forward.
        pool = json.loads((self.pool / f"{DAY}.json").read_text())
        pool["items"]["https://a.com/first"]["last_seen_run"] = f"{DAY}T11:00:00+00:00"
        _write(self.pool / f"{DAY}.json", pool)
        diag = self.run_record(run_at=f"{DAY}T12:30:00+00:00")
        self.assertTrue(diag["written"])
        items = self.ledger()["items"]
        self.assertEqual(len(items), 2)
        self.assertEqual(items["story:https://a.com/first"]["admitted_at"], admitted_at)
        self.assertEqual(items["story:https://a.com/first"]["last_seen"], f"{DAY}T11:00:00+00:00")

        # A no-change run must not rewrite the ledger.
        diag = self.run_record(run_at=f"{DAY}T13:00:00+00:00")
        self.assertFalse(diag["written"])
        self.assertEqual(diag["reason"], "no_change")

    def test_per_source_quota_is_a_flood_guard(self):
        rows = [
            _row(f"https://news.ycombinator.com/item?id={i}", source="hackernews_ai", role="community", title=f"HN {i}")
            for i in range(4)
        ]
        self.write_pool(rows)
        diag = self.run_record()
        self.assertEqual(diag["admitted"], 2)
        self.assertGreaterEqual(diag["rejected_quota"].get("source_quota", 0), 2)

    def test_ops_summary_reads_latest_ledger(self):
        self.write_pool([_row("https://a.com/keep", source="simon_willison", role="practitioner", title="Keep")])
        self.run_record()
        summary = ops_daily_summary.brief_ledger_summary(self.brief)
        self.assertIsNotNone(summary)
        self.assertEqual(summary["date"], DAY)
        self.assertEqual(summary["items"], 1)
        self.assertEqual(summary["role_counts"], {"practitioner": 1})
        self.assertEqual(summary["top_sources"], {"simon_willison": 1})

    def test_source_quota_counts_previous_day_items_crossing_midnight(self):
        prior = {
            "date": "2026-10-26",
            "updated_at": "2026-10-26T23:30:00+00:00",
            "items": {
                "story:https://hn/1": {
                    "story_key": "story:https://hn/1",
                    "url": "https://hn/1",
                    "source": "hackernews_ai",
                    "source_role": "community",
                    "type": "news",
                    "title": "HN 1",
                    "admitted_at": "2026-10-26T23:00:00+00:00",
                    "first_seen": "2026-10-26T23:00:00+00:00",
                    "last_seen": "2026-10-26T23:00:00+00:00",
                },
                "story:https://hn/2": {
                    "story_key": "story:https://hn/2",
                    "url": "https://hn/2",
                    "source": "hackernews_ai",
                    "source_role": "community",
                    "type": "news",
                    "title": "HN 2",
                    "admitted_at": "2026-10-26T23:30:00+00:00",
                    "first_seen": "2026-10-26T23:30:00+00:00",
                    "last_seen": "2026-10-26T23:30:00+00:00",
                },
            },
        }
        _write(self.brief / "2026-10-26.json", prior)
        self.write_pool(
            [
                _row(
                    "https://hn/3",
                    source="hackernews_ai",
                    role="community",
                    title="HN 3",
                    first_seen=f"{DAY}T01:00:00+00:00",
                )
            ]
        )
        diag = self.run_record(run_at=f"{DAY}T01:10:00+00:00")
        self.assertEqual(diag["rejected_quota"].get("source_quota"), 1)
        # The first build of the day writes the empty ledger with diagnostics,
        # so the API serves the admitted-empty day rather than falling back.
        self.assertTrue(diag["written"])
        self.assertEqual(diag["items"], 0)

    def test_backfill_uses_first_seen_for_admission_time(self):
        self.write_pool([_row("https://a.com/first", source="simon_willison", role="practitioner", title="First")])
        diag = bl.record_run(
            None,
            None,
            run_at=f"{DAY}T23:59:00+00:00",
            brief_dir=self.brief,
            pool_dir=self.pool,
            config_path=self.config,
            rebuild=True,
            admission_time_mode="first_seen",
        )
        self.assertTrue(diag["written"])
        item = self.ledger()["items"]["story:https://a.com/first"]
        self.assertEqual(item["admitted_at"], f"{DAY}T09:00:00+00:00")

    def test_story_store_captures_ledger_only_stories(self):
        self.write_pool([_row("https://a.com/ledger-only", source="simon_willison", role="practitioner", title="Ledger only")])
        self.run_record()
        saved = (story_store.BRIEF_DIR, story_store.PROCESSED_DIR, story_store.STORE_DIR)
        story_store.BRIEF_DIR = self.brief
        story_store.PROCESSED_DIR = self.processed
        story_store.STORE_DIR = self.stories
        try:
            new, total = story_store.sync()
        finally:
            story_store.BRIEF_DIR, story_store.PROCESSED_DIR, story_store.STORE_DIR = saved
        self.assertEqual(new, 1)
        self.assertEqual(total, 1)
        index = json.loads((self.stories / "index.json").read_text(encoding="utf-8"))
        self.assertEqual(len(index), 1)
        self.assertEqual(next(iter(index.values()))["title"], "Ledger only")

    def test_prior_day_story_within_24h_is_not_readmitted(self):
        prior = {
            "date": "2026-10-26",
            "updated_at": "2026-10-26T23:00:00+00:00",
            "items": {
                "story:https://a.com/kimi": {
                    "story_key": "story:https://a.com/kimi",
                    "url": "https://a.com/kimi",
                    "source": "openai_blog",
                    "source_role": "first_party",
                    "type": "news",
                    "title": "Kimi",
                    "admitted_at": "2026-10-26T23:00:00+00:00",
                    "first_seen": "2026-10-26T23:00:00+00:00",
                    "last_seen": "2026-10-26T23:00:00+00:00",
                }
            },
        }
        _write(self.brief / "2026-10-26.json", prior)
        self.write_pool(
            [
                _row(
                    "https://a.com/kimi",
                    source="openai_blog",
                    role="first_party",
                    title="Kimi",
                    story_key="story:https://a.com/kimi",
                    first_seen=f"{DAY}T01:00:00+00:00",
                )
            ]
        )
        diag = self.run_record(run_at=f"{DAY}T02:00:00+00:00")
        self.assertEqual(diag["prior_story"], 1)
        # The first run of the day writes an empty ledger with diagnostics so
        # the API can serve the admitted-empty day instead of falling back to
        # the run pool.
        self.assertTrue(diag["written"])
        self.assertEqual(diag["items"], 0)


if __name__ == "__main__":
    unittest.main()
