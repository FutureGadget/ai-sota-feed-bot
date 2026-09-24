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


def test_email_reader_sets_keep_only_email_attributed_rows():
    rows = [
        ("2026-06-15", "alice", 1),
        ("2026-06-15", "bob", 0),
        ("2026-06-15", "carol", "false"),
        ("2026-06-22", "alice", True),
    ]
    assert nsm.weekly_email_reader_sets(rows) == {
        "2026-06-15": {"alice"},
        "2026-06-22": {"alice"},
    }


def test_compute_weeks_adds_email_counts_without_changing_headline():
    sets = {
        "2026-06-08": {"alice", "bob"},
        "2026-06-15": {"alice", "bob", "carol"},
    }
    email_sets = {"2026-06-15": {"alice", "carol"}}
    plain = nsm.compute_weeks(sets)[0]
    row = nsm.compute_weeks(sets, email_sets)[0]
    assert {k: row[k] for k in plain} == plain
    assert row["email_readers"] == 2
    assert row["email_returning_readers"] == 1


def test_compute_weeks_without_email_sets_keeps_legacy_shape():
    sets = {"2026-06-08": {"alice"}, "2026-06-15": {"alice"}}
    row = nsm.compute_weeks(sets)[0]
    assert "email_readers" not in row
