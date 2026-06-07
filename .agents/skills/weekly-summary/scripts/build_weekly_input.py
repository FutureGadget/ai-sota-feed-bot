"""Build the weekly recap *input bundle* for an agent to summarize.

Aggregates the unique articles that appeared in the feed over an ISO week and
writes them to ``data/weekly/input/<week>.json`` (+ ``input/latest.json``).

A Claude Code routine reads this bundle, summarizes/categorizes the articles,
and writes the published recap to ``data/weekly/<week>.json``.

Usage:
    python pipeline/build_weekly_input.py                 # ISO week containing today
    python pipeline/build_weekly_input.py --week 2026-W23
    python pipeline/build_weekly_input.py --end 2026-06-07 --days 7
"""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, time, timedelta, timezone

from weekly_common import (
    CATEGORY_ORDER,
    WEEKLY_DIR,
    WEEKLY_INPUT_DIR,
    collect_week_articles,
    fmt_range,
    iso_week_id,
    recap_article_urls,
    week_bounds,
    write_json,
)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--week", help="ISO week id, e.g. 2026-W23 (default: week containing --end/today)")
    ap.add_argument("--end", help="End date YYYY-MM-DD (used when --week is omitted)")
    ap.add_argument("--days", type=int, default=7, help="Lookback window in days when using --end (default 7)")
    ap.add_argument(
        "--types",
        default="news",
        help="Comma-separated item types to include, or 'all' (default: news). "
        "Other types (paper/release/research) are better served by the live feed.",
    )
    ap.add_argument(
        "--keep-carryover",
        action="store_true",
        help="Keep articles still in the feed this week but published in an "
        "earlier week (default: drop them — only include articles published "
        "within the window).",
    )
    ap.add_argument(
        "--no-prior-dedup",
        action="store_true",
        help="Do not exclude articles already published in an earlier week's "
        "recap (default: exclude them to avoid cross-week duplicates).",
    )
    args = ap.parse_args()

    types_raw = args.types.strip().lower()
    include_types = None if types_raw in ("", "all", "*") else {t.strip() for t in types_raw.split(",") if t.strip()}

    if args.week:
        week = args.week
        start_d, end_d = week_bounds(week)
    else:
        end_d = date.fromisoformat(args.end) if args.end else datetime.now(timezone.utc).date()
        week = iso_week_id(end_d)
        start_d = end_d - timedelta(days=args.days - 1)

    start_dt = datetime.combine(start_d, time.min, tzinfo=timezone.utc)
    end_dt = datetime.combine(end_d, time.max, tzinfo=timezone.utc)

    # #2: don't re-surface articles a prior week's recap already covered.
    exclude_urls = set() if args.no_prior_dedup else recap_article_urls(exclude_week=week)

    articles = collect_week_articles(
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
        "week": week,
        "start": start_d.isoformat(),
        "end": end_d.isoformat(),
        "range_label": fmt_range(start_d, end_d),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "included_types": sorted(include_types) if include_types is not None else "all",
        "published_window": not args.keep_carryover,
        "prior_recap_dedup": not args.no_prior_dedup,
        "prior_recap_urls": len(exclude_urls),
        "article_count": len(articles),
        "category_hint": category_hint,
        "articles": articles,
    }

    write_json(WEEKLY_INPUT_DIR / f"{week}.json", bundle)
    write_json(WEEKLY_INPUT_DIR / "latest.json", bundle)

    # Dedup signal: a recap for this week is keyed by its ISO week id (the
    # filename below). If it already exists, the routine should NOT re-write it.
    already_published = (WEEKLY_DIR / f"{week}.json").exists()

    print(
        json.dumps(
            {
                "week": week,
                "range": bundle["range_label"],
                "included_types": bundle["included_types"],
                "published_window": bundle["published_window"],
                "prior_recap_dedup": bundle["prior_recap_dedup"],
                "prior_recap_urls": bundle["prior_recap_urls"],
                "article_count": len(articles),
                "categories": category_hint,
                "input_path": f"data/weekly/input/{week}.json",
                "recap_path": f"data/weekly/{week}.json",
                "already_published": already_published,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
