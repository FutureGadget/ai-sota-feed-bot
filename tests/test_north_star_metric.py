"""Unit tests for the weekly-returning-readers rollup (pipeline/north_star_metric.py).

Covers only the pure grouping/classification logic — the PostHog HTTP call
is exercised manually against real credentials, not in CI.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))

import north_star_metric as nsm  # noqa: E402


def test_weekly_reader_sets_groups_by_week():
    rows = [
        ("2026-06-15", "alice"),
        ("2026-06-15", "bob"),
        ("2026-06-22", "alice"),
        ("2026-06-22", "carol"),
    ]
    sets = nsm.weekly_reader_sets(rows)
    assert sets == {
        "2026-06-15": {"alice", "bob"},
        "2026-06-22": {"alice", "carol"},
    }


def test_weekly_reader_sets_skips_blank_ids():
    rows = [("2026-06-15", "alice"), ("", "bob"), ("2026-06-15", "")]
    sets = nsm.weekly_reader_sets(rows)
    assert sets == {"2026-06-15": {"alice"}}


def test_compute_weeks_drops_first_week_as_baseline():
    sets = {
        "2026-06-08": {"alice", "bob"},
        "2026-06-15": {"alice", "carol"},
    }
    rows = nsm.compute_weeks(sets)
    assert len(rows) == 1
    assert rows[0]["week_start"] == "2026-06-15"


def test_compute_weeks_classifies_returning_vs_new():
    sets = {
        "2026-06-08": {"alice", "bob"},
        "2026-06-15": {"alice", "carol", "dave"},
        "2026-06-22": {"alice", "bob", "carol"},
    }
    rows = {r["week_start"]: r for r in nsm.compute_weeks(sets)}

    week2 = rows["2026-06-15"]
    assert week2["total_readers"] == 3
    assert week2["returning_readers"] == 1  # alice only
    assert week2["new_readers"] == 2  # carol, dave
    assert week2["returning_rate"] == round(1 / 3, 4)

    week3 = rows["2026-06-22"]
    assert week3["total_readers"] == 3
    assert week3["returning_readers"] == 2  # alice, carol (bob returns from wk1, not wk2)
    assert week3["new_readers"] == 1


def test_compute_weeks_handles_zero_readers():
    sets = {"2026-06-08": set(), "2026-06-15": set()}
    rows = nsm.compute_weeks(sets)
    assert rows[0]["returning_rate"] == 0.0


def test_history_round_trip(tmp_path):
    path = tmp_path / "weekly_returning_readers.json"
    nsm.save_history(
        {
            "2026-06-15": {
                "week_start": "2026-06-15",
                "total_readers": 3,
                "returning_readers": 1,
                "new_readers": 2,
                "returning_rate": 0.3333,
            }
        },
        path=path,
    )
    loaded = nsm.load_history(path=path)
    assert loaded["2026-06-15"]["total_readers"] == 3


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-v"]))
