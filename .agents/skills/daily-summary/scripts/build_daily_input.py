"""Build the daily recap *input bundle* for an agent to summarize.

Aggregates the unique articles that appeared in the feed over a single calendar
day and writes them to ``data/daily/input/<date>.json`` (+ ``input/latest.json``).

A Claude Code routine reads this bundle, summarizes/categorizes the articles,
and writes the published recap to ``data/daily/<date>.json``.

Usage:
    python build_daily_input.py                 # next unprocessed UTC day
    python build_daily_input.py --date 2026-06-07
    python build_daily_input.py --date 2026-06-07 --days 1
"""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, time, timedelta, timezone

from daily_common import (
    CATEGORY_ORDER,
    DAILY_DIR,
    DAILY_INPUT_DIR,
    collect_day_articles,
    date_id,
    fmt_day,
    next_target_date,
    recap_article_urls,
    record_skipped_date,
    write_json,
)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--date",
        help="Calendar date YYYY-MM-DD (default: the next unprocessed UTC day - "
        "one day past the latest published recap or confirmed-empty day)",
    )
    ap.add_argument(
        "--days",
        type=int,
        default=1,
        help="Lookback window in days ending on --date (default 1 = just that day)",
    )
    ap.add_argument(
        "--types",
        default="news",
        help="Comma-separated item types to include, or 'all' (default: news). "
        "Other types (paper/release/research) are better served by the live feed.",
    )
    ap.add_argument(
        "--keep-carryover",
        action="store_true",
        help="Keep articles still in the feed today but published on an earlier "
        "day (default: drop them — only include articles published within the "
        "window).",
    )
    ap.add_argument(
        "--no-prior-dedup",
        action="store_true",
        help="Do not exclude articles already published in an earlier day's "
        "recap (default: exclude them to avoid cross-day duplicates).",
    )
    args = ap.parse_args()

    types_raw = args.types.strip().lower()
    include_types = None if types_raw in ("", "all", "*") else {t.strip() for t in types_raw.split(",") if t.strip()}

    today = datetime.now(timezone.utc).date()
    if args.date:
        end_d = date.fromisoformat(args.date)
    else:
        end_d = next_target_date(today)
        if end_d >= today:
            print(
                json.dumps(
                    {
                        "due": False,
                        "target_date": date_id(end_d),
                        "today_utc": date_id(today),
                        "reason": "target date is not a complete UTC day yet",
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return

    day = date_id(end_d)
    start_d = end_d - timedelta(days=args.days - 1)

    start_dt = datetime.combine(start_d, time.min, tzinfo=timezone.utc)
    end_dt = datetime.combine(end_d, time.max, tzinfo=timezone.utc)

    # #2: don't re-surface articles a prior day's recap already covered.
    exclude_urls = set() if args.no_prior_dedup else recap_article_urls(exclude_date=day)

    articles = collect_day_articles(
        start_dt,
        end_dt,
        require_published_in_window=not args.keep_carryover,  # #1
        exclude_urls=exclude_urls,
    )
    if include_types is not None:
        articles = [a for a in articles if a.get("type") in include_types]

    # Pre-group by deterministic category so the agent has a starting structure.
    grouped: dict[str, list] = {}
    for a in articles:
        grouped.setdefault(a["category"], []).append(a)
    category_hint = [
        {"name": name, "count": len(grouped.get(name, []))}
        for _, name in CATEGORY_ORDER
        if grouped.get(name)
    ]

    bundle = {
        "date": day,
        "range_label": fmt_day(end_d),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "included_types": sorted(include_types) if include_types is not None else "all",
        "lookback_days": args.days,
        "published_window": not args.keep_carryover,
        "prior_recap_dedup": not args.no_prior_dedup,
        "prior_recap_urls": len(exclude_urls),
        "article_count": len(articles),
        "category_hint": category_hint,
        "articles": articles,
    }

    write_json(DAILY_INPUT_DIR / f"{day}.json", bundle)
    write_json(DAILY_INPUT_DIR / "latest.json", bundle)

    # Dedup signal: a recap for this day is keyed by its date id (the filename
    # below). If it already exists, the routine should NOT re-write it.
    already_published = (DAILY_DIR / f"{day}.json").exists()

    empty = len(articles) == 0
    if empty and not args.date:
        # Automatic mode found nothing to publish for the target day. Advance
        # the state cursor past it so the next run doesn't recompute this same
        # empty target forever - an explicit --date call never mutates it.
        record_skipped_date(day)

    print(
        json.dumps(
            {
                "due": True,
                "empty": empty,
                "date": day,
                "range": bundle["range_label"],
                "included_types": bundle["included_types"],
                "published_window": bundle["published_window"],
                "prior_recap_dedup": bundle["prior_recap_dedup"],
                "prior_recap_urls": bundle["prior_recap_urls"],
                "article_count": len(articles),
                "categories": category_hint,
                "input_path": f"data/daily/input/{day}.json",
                "recap_path": f"data/daily/{day}.json",
                "already_published": already_published,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
