#!/usr/bin/env python3
"""Weekly returning readers — the one metric this project is judged against.

Decision (docs/design-docs/decision-log.md, 2026-07-02): for a fixed 60-day
window, every change is evaluated against this single number and nothing
else. Features shipped, sources added, and recap quality are off the
scoreboard until the window ends.

Definition: for a completed ISO week W (Monday 00:00 UTC through the
following Monday 00:00 UTC), a *returning reader* is a `distinct_id` seen in
a pageview event during week W that was also seen in a pageview event
during week W-1. Pageviews are the standard posthog-js `$pageview`. The query
also matches the legacy custom `page_view` (dual-emitted until 2026-07-13, then
removed) so weeks recorded before the removal still count with no gap.
`returning_rate = returning / total_readers` for week W.

A *reader* needs `MIN_PAGEVIEWS_PER_WEEK` pageviews inside the week, not one.
A single pageview is what a JS-rendering crawler produces: it fires
`$identify` then `$pageview` in a fresh browser profile, gets a new
`distinct_id` on every run, and can never be "returning". Counting those as
readers inflated `total_readers` from 100 (2026-09-21) to 1,576 (2026-10-19)
while the returning count sat still at 5-7, so the rate collapsed for
arithmetic reasons and not because readers left (see the 2026-10-31 ADR). `single_page_readers`
records the excluded cohort so the crawler volume stays visible instead of
disappearing from the artifact.

Email attribution (secondary, diagnostic only): an *email reader* is a reader
with at least one pageview in week W that landed from a digest link
(`utm_source = 'email'`). Email links also carry the subscriber's reader id
(`rid=`, adopted by web/posthog-client.js), so a subscriber reading from a mail
app's in-app browser stays one reader across weeks. `email_readers` and
`email_returning_readers` (returning readers who were email readers in W) are
recorded next to the headline numbers; they never change them.
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

# A reader loads more than one page in a week; a crawler loads one and leaves.
# Raise this to 3 to also exclude feed-then-one-story readers.
MIN_PAGEVIEWS_PER_WEEK = 2

# Recorded in the artifact so a reader of the JSON knows which definition
# produced the numbers.
READER_DEFINITION = (
    f"distinct_id with >= {MIN_PAGEVIEWS_PER_WEEK} pageviews in the week "
    "('$pageview' or legacy 'page_view')"
)


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
    payload = {
        "generated_at": utc_now().isoformat(),
        "reader_definition": READER_DEFINITION,
        "weeks": weeks,
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _as_count(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _shift_week(week_start: str, days: int) -> str | None:
    """The ISO date `days` away from a week-start key, or None if unparseable."""
    dt = parse_ts(week_start)
    if dt is None:
        return None
    return (dt + timedelta(days=days)).strftime("%Y-%m-%d")


def weekly_reader_sets(rows: list[tuple[str, str]]) -> dict[str, set[str]]:
    """Group (week_start_iso, distinct_id) pairs into per-week reader sets."""
    by_week: dict[str, set[str]] = {}
    for week_start, distinct_id in rows:
        if not week_start or not distinct_id:
            continue
        by_week.setdefault(str(week_start), set()).add(str(distinct_id))
    return by_week


def split_reader_sets(
    rows: list[tuple[str, str, int]],
    min_pageviews: int = MIN_PAGEVIEWS_PER_WEEK,
) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """Split (week_start, distinct_id, pageviews) rows into readers and single-page hits.

    Returns `(reader_sets, single_page_sets)`. Only the first feeds the
    headline numbers; the second is recorded so a crawler wave is visible in
    the artifact instead of silently vanishing from the denominator.
    """
    readers: dict[str, set[str]] = {}
    single_page: dict[str, set[str]] = {}
    for week_start, distinct_id, pageviews in rows:
        if not week_start or not distinct_id:
            continue
        target = readers if _as_count(pageviews) >= min_pageviews else single_page
        target.setdefault(str(week_start), set()).add(str(distinct_id))
    return readers, single_page


def weekly_email_reader_sets(rows: list[tuple[str, str, object]]) -> dict[str, set[str]]:
    """Per-week sets of readers with an email-attributed pageview, from
    (week_start_iso, distinct_id, via_email) triples."""
    by_week: dict[str, set[str]] = {}
    for week_start, distinct_id, via_email in rows:
        if not week_start or not distinct_id or not via_email or str(via_email).lower() in ("0", "false"):
            continue
        by_week.setdefault(str(week_start), set()).add(str(distinct_id))
    return by_week


def compute_weeks(
    reader_sets: dict[str, set[str]],
    email_sets: dict[str, set[str]] | None = None,
    single_page_sets: dict[str, set[str]] | None = None,
) -> list[dict]:
    """Turn per-week reader sets into returning-reader rows.

    A week needs the prior week's set to classify readers, so a week with no
    week exactly 7 days before it is dropped (no baseline to compare against).
    Comparing against the nearest present key instead of the calendar week
    would silently span a gap. With `email_sets`, each row also carries the
    email-attribution counts; with `single_page_sets`, the excluded cohort.
    """
    known = set(reader_sets) | set(single_page_sets or ())
    ordered = sorted(known)
    out = []
    for week in ordered:
        prev_week = _shift_week(week, -7)
        if prev_week not in known:
            continue
        readers = reader_sets.get(week, set())
        prev_readers = reader_sets.get(prev_week, set())
        returning = readers & prev_readers
        total = len(readers)
        row = {
            "week_start": week,
            "total_readers": total,
            "returning_readers": len(returning),
            "new_readers": total - len(returning),
            "returning_rate": round(len(returning) / total, 4) if total else 0.0,
        }
        if single_page_sets is not None:
            row["single_page_readers"] = len(single_page_sets.get(week, set()))
        if email_sets is not None:
            email_readers = email_sets.get(week, set()) & readers
            row["email_readers"] = len(email_readers)
            row["email_returning_readers"] = len(email_readers & returning)
        out.append(row)
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
        "SELECT toStartOfWeek(timestamp, 1) AS week_start, distinct_id, "
        "max(properties.utm_source = 'email') AS via_email, count() AS pageviews "
        "FROM events "
        # `$pageview` is the standard posthog-js pageview and the only pageview
        # the web client emits today. `page_view` is the legacy custom event
        # (removed 2026-07-13); keep it in the filter so weeks captured before
        # the removal still count and the rollup bridges the rename with no gap.
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

    rows = [
        (
            r[0],
            r[1],
            r[2] if len(r) > 2 else 0,
            _as_count(r[3]) if len(r) > 3 else 0,
        )
        for r in results
    ]
    reader_sets, single_page_sets = split_reader_sets(
        [(week_start, distinct_id, pageviews) for week_start, distinct_id, _email, pageviews in rows]
    )
    email_sets = weekly_email_reader_sets(
        [(week_start, distinct_id, via_email) for week_start, distinct_id, via_email, _pv in rows]
    )
    current_week = monday_of(utc_now()).strftime("%Y-%m-%d")
    reader_sets = {w: ids for w, ids in reader_sets.items() if w[:10] < current_week}
    single_page_sets = {w: ids for w, ids in single_page_sets.items() if w[:10] < current_week}
    computed = {
        row["week_start"][:10]: row
        for row in compute_weeks(reader_sets, email_sets, single_page_sets)
    }

    history = load_history()
    history.update(computed)
    save_history(history)

    latest = history[max(history)] if history else None
    print(
        "north_star_sync_done "
        f"min_pageviews={MIN_PAGEVIEWS_PER_WEEK} "
        f"weeks_computed={len(computed)} weeks_tracked={len(history)} "
        f"latest_week={latest['week_start'] if latest else None} "
        f"latest_readers={latest['total_readers'] if latest else None} "
        f"latest_returning={latest['returning_readers'] if latest else None} "
        f"latest_single_page={latest.get('single_page_readers') if latest else None} "
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

    print(
        f"{'week_start':<12} {'readers':>7} {'returning':>10} {'new':>7} {'rate':>7} "
        f"{'single':>7} {'email':>6} {'email_ret':>10}"
    )
    for row in weeks:
        # Optional columns only exist for weeks synced after each shipped.
        email = row.get("email_readers", "-")
        email_ret = row.get("email_returning_readers", "-")
        single = row.get("single_page_readers", "-")
        print(
            f"{row['week_start']:<12} {row['total_readers']:>7} {row['returning_readers']:>10} "
            f"{row['new_readers']:>7} {row['returning_rate']:>7.2%} {single:>7} {email:>6} {email_ret:>10}"
        )

    latest = weeks[-1]
    print(
        "north_star "
        f"week={latest['week_start']} returning_readers={latest['returning_readers']} "
        f"total_readers={latest['total_readers']} returning_rate={latest['returning_rate']} "
        f"single_page_readers={latest.get('single_page_readers')} "
        f"email_readers={latest.get('email_readers')} "
        f"email_returning_readers={latest.get('email_returning_readers')}"
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
