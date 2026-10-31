#!/usr/bin/env python3
"""Replay the served Brief and print the stability/admission scorecard.

Usage:
    python scripts/feed_replay.py
    python scripts/feed_replay.py --days 7
    python scripts/feed_replay.py --end 2026-10-31
    python scripts/feed_replay.py --no-write

The report is written under ``data/quality/feed_benchmark/runs/<stamp>/``
(gitignored) unless ``--no-write`` is set. The script reads only committed or
local runtime artifacts; it never calls the network and never changes feed
data.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, time, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))

import feed_metrics  # noqa: E402


def _parse_end(value: str | None) -> datetime | None:
    if not value:
        return None
    day = date.fromisoformat(value)
    return datetime.combine(day, time(23, 59, 59), tzinfo=timezone.utc)


def _day_lines(scorecard: dict) -> list[str]:
    lines = []
    for row in scorecard.get("day_summaries") or []:
        gate = row.get("rejected_gate") or {}
        quota = row.get("rejected_quota") or {}
        lines.append(
            "feed_day "
            f"date={row['date']} "
            f"admitted={row['admitted']} "
            f"admitted_keeps={row['admitted_keeps']} "
            f"admitted_reviews={row['admitted_reviews']} "
            f"admitted_releases={row['admitted_releases']} "
            f"keeps={row['keeps_total']} "
            f"keeps_admitted={row['keeps_admitted']} "
            f"keeps_rate={row['keeps_admission_rate']} "
            f"gate={gate} "
            f"quota={quota} "
            f"prior_story={row['prior_story']} "
            f"lag_median_h={row['published_lag_median_hours']}"
        )
    return lines


def _markdown(scorecard: dict) -> str:
    lines = [
        "# Served Brief replay",
        "",
        f"- Ledgers: {scorecard['ledgers']}",
        f"- Runs: {scorecard['runs']}",
        f"- Admitted: {scorecard['admitted']}",
        f"- Judge keeps: {scorecard['keeps_total']}",
        f"- Keeps admitted: {scorecard['keeps_admitted']} ({scorecard['keeps_admission_rate']})",
        "",
        "| day | admitted | keeps | keeps admitted | gate rejects | quota rejects | lag median (h) |",
        "|---|---:|---:|---:|---|---|---:|",
    ]
    for row in scorecard.get("day_summaries") or []:
        gate = ", ".join(f"{k}:{v}" for k, v in sorted((row.get("rejected_gate") or {}).items())) or "-"
        quota = ", ".join(f"{k}:{v}" for k, v in sorted((row.get("rejected_quota") or {}).items())) or "-"
        lines.append(
            f"| {row['date']} | {row['admitted']} | {row['keeps_total']} | "
            f"{row['keeps_admitted']} | {gate} | {quota} | {row['published_lag_median_hours']} |"
        )
    stability = scorecard.get("stability") or {}
    lines += [
        "",
        "## Stability",
        "",
        f"- Pairs: {stability.get('pairs')}",
        f"- Rated pairs (>= {stability.get('min_visible')} visible): {stability.get('rated_pairs')}",
        f"- Top-10 Jaccard mean: {stability.get('top10_jaccard_mean')}",
        f"- Top-10 Jaccard min: {stability.get('top10_jaccard_min')}",
        f"- Rank displacement mean: {stability.get('rank_displacement_mean')}",
        f"- Expired removals: {stability.get('expired_total')}",
        f"- Unexpected removals: {stability.get('unexpected_removals')}",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay the served Brief stability/admission scorecard.")
    parser.add_argument("--days", type=int, default=3)
    parser.add_argument("--end", default=None, help="UTC date to replay through (YYYY-MM-DD).")
    parser.add_argument("--out-dir", default=str(ROOT / "data" / "quality" / "feed_benchmark" / "runs"))
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()

    end = _parse_end(args.end)
    card = feed_metrics.scorecard(days=args.days, end=end)
    if not args.no_write:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        out_dir = Path(args.out_dir) / stamp
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "report.json").write_text(
            json.dumps({"generated_at": datetime.now(timezone.utc).isoformat(), **card}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (out_dir / "report.md").write_text(_markdown(card), encoding="utf-8")
        print(f"feed_replay_report={out_dir / 'report.md'}")

    stability = card.get("stability") or {}
    print(
        "feed_replay "
        f"days={card['days']} ledgers={card['ledgers']} runs={card['runs']} "
        f"admitted={card['admitted']} keeps={card['keeps_total']} "
        f"keeps_admitted={card['keeps_admitted']} keeps_rate={card['keeps_admission_rate']} "
        f"top10_jaccard_mean={stability.get('top10_jaccard_mean')} "
        f"top10_jaccard_min={stability.get('top10_jaccard_min')} "
        f"rank_displacement_mean={stability.get('rank_displacement_mean')} "
        f"unexpected_removals={stability.get('unexpected_removals')} "
        f"expired_removals={stability.get('expired_total')}"
    )
    for line in _day_lines(card):
        print(line)


if __name__ == "__main__":
    main()
