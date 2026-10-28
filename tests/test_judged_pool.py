"""Per-day judged candidate pool for the editor decks (pipeline/judged_pool.py)."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))

import judged_pool  # noqa: E402
import ranking  # noqa: E402

RUN1 = "2026-10-28T01:10:00+00:00"
RUN2 = "2026-10-28T03:10:00+00:00"


def _item(n: int, **extra) -> dict:
    base = {
        "id": f"item-{n}",
        "title": f"Item {n}",
        "url": f"https://example.com/post-{n}/",
        "source": "example_blog",
        "source_role": "practitioner",
        "type": "news",
        "published": "2026-10-28T00:00:00+00:00",
    }
    base.update(extra)
    return base


class JudgedPoolTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_merge_records_whole_pool_and_marks_edition_members(self):
        kept = _item(1, judge_score=0.8, judge_verdict="keep", judge_category="agent_engineering", slot="practitioner_analysis")
        left_out = _item(2, judge_score=0.7, judge_verdict="keep", content_excerpt="x " * 500)
        unjudged = _item(3, judge_score=None, judge_verdict="unjudged", judge_error="insufficient_evidence")

        pool = judged_pool.merge_run({}, [kept, left_out, unjudged], [kept], RUN1)

        rows = pool["items"]
        assert set(rows) == {f"https://example.com/post-{n}" for n in (1, 2, 3)}
        assert rows["https://example.com/post-1"]["edition_runs"] == 1
        assert rows["https://example.com/post-1"]["best_edition_rank"] == 1
        assert rows["https://example.com/post-1"]["edition_slot"] == "practitioner_analysis"
        # Judge-kept but not placed: the recall gap the decks cannot see today.
        assert rows["https://example.com/post-2"]["edition_runs"] == 0
        assert rows["https://example.com/post-2"]["judge_verdict"] == "keep"
        assert len(rows["https://example.com/post-2"]["excerpt"]) <= judged_pool.EXCERPT_CHARS
        # Fail-open: unjudged items are kept, with no fabricated score.
        assert rows["https://example.com/post-3"]["judge_verdict"] == "unjudged"
        assert "judge_score" not in rows["https://example.com/post-3"]
        assert pool["runs"] == 1 and pool["item_count"] == 3


    def test_later_fail_open_run_does_not_erase_judgment_and_counters_accumulate(self):
        first = _item(1, judge_score=0.62, judge_verdict="keep")
        pool = judged_pool.merge_run({}, [first], [], RUN1)

        # Second run: judge unavailable, item placed at rank 3 this time.
        second = _item(1, judge_score=None, judge_verdict=None)
        filler = [_item(10), _item(11)]
        pool = judged_pool.merge_run(pool, [second], filler + [second], RUN2)

        row = pool["items"]["https://example.com/post-1"]
        assert row["judge_score"] == 0.62
        assert row["judge_verdict"] == "keep"
        assert row["runs_seen"] == 2
        assert row["edition_runs"] == 1
        assert row["best_edition_rank"] == 3
        assert row["first_seen_run"] == RUN1 and row["last_seen_run"] == RUN2
        # Edition items absent from the candidate pool are still recorded.
        assert "https://example.com/post-10" in pool["items"]


    def test_cluster_echoes_become_coverage_signals(self):
        rep = _item(1, also_covered=[{"source": "hn"}, {"source": "search_x"}, {"source": "hn"}])
        row = judged_pool.merge_run({}, [rep], [], RUN1)["items"]["https://example.com/post-1"]
        assert row["echo_count"] == 3
        assert row["source_count"] == 3  # example_blog, hn, search_x


    def test_record_run_writes_by_utc_run_date_and_merges(self):
        diag = judged_pool.record_run([_item(1, judge_score=0.5)], [], run_at=RUN1, pool_dir=self.tmp_path)
        assert diag["written"] and diag["items"] == 1
        judged_pool.record_run([_item(2)], [_item(2)], run_at=RUN2, pool_dir=self.tmp_path)
        # 23:30 in KST on the 28th is still the 28th in UTC.
        judged_pool.record_run([_item(3)], [], run_at="2026-10-28T14:30:00+00:00", pool_dir=self.tmp_path)

        data = json.loads((self.tmp_path / "2026-10-28.json").read_text(encoding="utf-8"))
        assert data["date"] == "2026-10-28"
        assert data["runs"] == 3
        assert data["item_count"] == 3
        assert data["schema_version"] == judged_pool.SCHEMA_VERSION


    def test_record_run_never_raises(self):
        blocker = self.tmp_path / "not-a-dir"
        blocker.write_text("x")
        diag = judged_pool.record_run([_item(1)], [], run_at=RUN1, pool_dir=blocker)
        assert diag["written"] is False
        assert diag["reason"].startswith("error:")
        assert judged_pool.record_run([], [], run_at=RUN1, pool_dir=self.tmp_path)["reason"] == "empty"


    def test_load_pool_days_unions_run_dates(self):
        judged_pool.record_run([_item(1, judge_score=0.4)], [_item(1, judge_score=0.4)], run_at=RUN1, pool_dir=self.tmp_path)
        judged_pool.record_run([_item(1, judge_score=0.9)], [], run_at="2026-10-29T01:00:00+00:00", pool_dir=self.tmp_path)

        rows = judged_pool.load_pool_days(["2026-10-29", "2026-10-28", "2026-10-30"], pool_dir=self.tmp_path)
        row = rows["https://example.com/post-1"]
        assert row["judge_score"] == 0.9  # latest day wins
        assert row["runs_seen"] == 2
        assert row["edition_runs"] == 1
        assert row["best_edition_rank"] == 1
        assert row["first_seen_run"] == RUN1


    def test_run_ranking_hands_post_judge_pool_to_sink(self):
        patcher = patch.object(ranking, "_now_utc", lambda: datetime(2026, 9, 3, 12, 0, tzinfo=timezone.utc))
        patcher.start()
        self.addCleanup(patcher.stop)
        # Keep the heuristic label pass off the committed data/llm/labels.json.
        label_module = sys.modules[ranking.label_items.__module__]
        for name in ("CACHE_FILE", "CACHE_FILE_V2"):
            cache_patch = patch.object(label_module, name, self.tmp_path / "labels.json")
            cache_patch.start()
            self.addCleanup(cache_patch.stop)
        profile = yaml.safe_load((ROOT / "config" / "profile.yaml").read_text(encoding="utf-8"))
        source = "arxiv_agent_systems_research"
        paper = {
            "id": "pool-fixture",
            "source": source,
            "title": "Reflective prompt evolution for agent systems",
            "url": "https://arxiv.org/abs/2609.00002",
            "summary": "Prompt optimization improves agent trajectories, tool use, and evaluation efficiency.",
            "published": "2026-09-03T11:00:00+00:00",
        }

        def fake_judge(candidates):
            return [dict(c, judge_score=0.9, judge_verdict="keep") for c in candidates], {"enabled": True}

        seen: list[dict] = []
        top, _ = ranking.run_ranking([paper], profile, {"enabled": False}, {source: 1.0}, judge_fn=fake_judge, pool_sink=seen.extend)

        assert [item["id"] for item in seen] == ["pool-fixture"]
        assert seen[0]["judge_verdict"] == "keep"
        assert len(top) == 1


if __name__ == "__main__":
    unittest.main()
