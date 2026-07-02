#!/usr/bin/env python3
"""Weekly returning readers — the one metric this project is judged against.

Decision (docs/design-docs/decision-log.md, 2026-07-02): for a fixed 60-day
window, every change is evaluated against this single number and nothing
else. Features shipped, sources added, and recap quality are off the
scoreboard until the window ends.

Definition: for a completed ISO week W (Monday 00:00 UTC through the
following Monday 00:00 UTC), a *returning reader* is a `distinct_id` seen in
a pageview event during week W that was also seen in a pageview event
during week W-1. Pageviews are the standard posthog-js `$pageview` plus the
legacy custom `page_view` (bridged so the rename leaves no gap).
`returning_rate = returning / total_readers` for week W.
The in-progress (current) week is never scored — only completed weeks.

data/metrics/weekly_returning_readers.json holds the durable history, one
row per completed week, merged forward on every sync (never rewritten from
scratch beyond the query lookback window).

Commands:
  sync     pull pageview events from PostHog and recompute recent weeks
  summary  print the tracked history as a table (most recent last)

sync reads POSTHOG_PERSONAL_API_KEY, POSTHOG_PROJECT_ID and optional
POSTHOG_API_HOST (default https://us.posthog.com) from the environment and
exits cleanly (no-op) when they are missing.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HISTORY_PATH = ROOT / "data" / "metrics" / "weekly_returning_readers.json"

WEEKS_LOOKBACK = 16
SYNC_LIMIT = 200000


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_ts(value) -> datetime | None:
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def monday_of(dt: datetime) -> datetime:
    d = dt.astimezone(timezone.utc)
    d = d.replace(hour=0, minute=0, second=0, microsecond=0)
    return d - timedelta(days=d.weekday())


def load_history(path: Path = HISTORY_PATH) -> dict[str, dict]:
    if not path.exists():
        return {}
    try:
        rows = json.loads(path.read_text(encoding="utf-8")).get("weeks") or []
    except (json.JSONDecodeError, OSError):
        return {}
    return {str(r["week_start"]): r for r in rows if isinstance(r, dict) and r.get("week_start")}


def save_history(by_week: dict[str, dict], path: Path = HISTORY_PATH) -> None:
    weeks = sorted(by_week.values(), key=lambda r: str(r["week_start"]))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"generated_at": utc_now().isoformat(), "weeks": weeks}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def weekly_reader_sets(rows: list[tuple[str, str]]) -> dict[str, set[str]]:
    """Group (week_start_iso, distinct_id) pairs into per-week reader sets."""
    by_week: dict[str, set[str]] = {}
    for week_start, distinct_id in rows:
        if not week_start or not distinct_id:
            continue
        by_week.setdefault(str(week_start), set()).add(str(distinct_id))
    return by_week


def compute_weeks(reader_sets: dict[str, set[str]]) -> list[dict]:
    """Turn per-week reader sets into returning-reader rows.

    A week needs the prior week's set to classify readers, so the earliest
    week in `reader_sets` is dropped (no baseline to compare against).
    """
    ordered = sorted(reader_sets)
    out = []
    for i in range(1, len(ordered)):
        week, prev_week = ordered[i], ordered[i - 1]
        readers = reader_sets[week]
        prev_readers = reader_sets[prev_week]
        returning = readers & prev_readers
        total = len(readers)
        out.append({
            "week_start": week,
            "total_readers": total,
            "returning_readers": len(returning),
            "new_readers": total - len(returning),
            "returning_rate": round(len(returning) / total, 4) if total else 0.0,
        })
    return out


def cmd_sync(args: argparse.Namespace) -> int:
    api_key = os.environ.get("POSTHOG_PERSONAL_API_KEY", "").strip()
    project_id = os.environ.get("POSTHOG_PROJECT_ID", "").strip()
    host = (os.environ.get("POSTHOG_API_HOST", "").strip() or "https://us.posthog.com").rstrip("/")
    if not api_key or not project_id:
        print("north_star_sync_skipped reason=missing_credentials")
        return 0

    import requests

    since = monday_of(utc_now()) - timedelta(weeks=WEEKS_LOOKBACK)
    hogql = (
        "SELECT toStartOfWeek(timestamp, 1) AS week_start, distinct_id FROM events "
        # `$pageview` is the standard posthog-js pageview (now emitted by the web
        # client so Web Analytics activates); `page_view` is the legacy custom
        # event. Match both so the rollup bridges the rename with no gap.
        "WHERE event IN ('$pageview', 'page_view') "
        f"AND timestamp >= toDateTime('{since.strftime('%Y-%m-%d %H:%M:%S')}') "
        "GROUP BY week_start, distinct_id "
        f"ORDER BY week_start LIMIT {SYNC_LIMIT}"
    )
    resp = requests.post(
        f"{host}/api/projects/{project_id}/query",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"query": {"kind": "HogQLQuery", "query": hogql}},
        timeout=60,
    )
    resp.raise_for_status()
    results = resp.json().get("results") or []

    reader_sets = weekly_reader_sets([(week_start, distinct_id) for week_start, distinct_id in results])
    current_week = monday_of(utc_now()).strftime("%Y-%m-%d")
    reader_sets = {w: ids for w, ids in reader_sets.items() if w[:10] < current_week}
    computed = {row["week_start"][:10]: row for row in compute_weeks(reader_sets)}

    history = load_history()
    history.update(computed)
    save_history(history)

    latest = history[max(history)] if history else None
    print(
        "north_star_sync_done "
        f"weeks_computed={len(computed)} weeks_tracked={len(history)} "
        f"latest_week={latest['week_start'] if latest else None} "
        f"latest_returning={latest['returning_readers'] if latest else None} "
        f"latest_rate={latest['returning_rate'] if latest else None}"
    )
    return 0


def cmd_summary(args: argparse.Namespace) -> int:
    history = load_history()
    if not history:
        print("No weekly returning-reader history yet — run `sync` with PostHog credentials first.")
        return 0

    weeks = sorted(history.values(), key=lambda r: str(r["week_start"]))
    if args.weeks:
        weeks = weeks[-args.weeks:]

    print(f"{'week_start':<12} {'total':>7} {'returning':>10} {'new':>7} {'rate':>7}")
    for row in weeks:
        print(
            f"{row['week_start']:<12} {row['total_readers']:>7} {row['returning_readers']:>10} "
            f"{row['new_readers']:>7} {row['returning_rate']:>7.2%}"
        )

    latest = weeks[-1]
    print(
        "north_star "
        f"week={latest['week_start']} returning_readers={latest['returning_readers']} "
        f"total_readers={latest['total_readers']} returning_rate={latest['returning_rate']}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    p_sync = sub.add_parser("sync", help="pull pageview events from PostHog and recompute recent weeks")
    p_sync.set_defaults(func=cmd_sync)

    p_summary = sub.add_parser("summary", help="print tracked weekly history")
    p_summary.add_argument("--weeks", type=int, default=None, help="only show the last N weeks")
    p_summary.set_defaults(func=cmd_summary)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
