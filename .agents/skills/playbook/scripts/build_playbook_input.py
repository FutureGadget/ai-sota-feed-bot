"""Build the Playbook *input bundle* for an agent to mine for actionable cards.

Aggregates the unique articles that appeared in the feed over a recent lookback
window and writes them to ``data/playbook/input/<date>.json`` (+
``input/latest.json``).

A Claude Code routine reads this bundle and writes the published edition to
``data/playbook/<date>.json`` — a batch of actionable cards (problem -> apply ->
result). Editions are curated less often than the daily recap, so the default
window is several days and includes papers/releases (where most applicable
agent-engineering learnings live), not just news.

Usage:
    python build_playbook_input.py                 # window ending today (UTC)
    python build_playbook_input.py --date 2026-06-21
    python build_playbook_input.py --days 5 --types all
"""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, time, timedelta, timezone

from playbook_common import (
    AREAS,
    PLAYBOOK_DIR,
    PLAYBOOK_INPUT_DIR,
    collect_articles,
    date_id,
    edition_card_urls,
    fmt_day,
    write_json,
)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--date", help="End date YYYY-MM-DD (default: today, UTC)")
    ap.add_argument(
        "--days",
        type=int,
        default=3,
        help="Lookback window in days ending on --date (default 3)",
    )
    ap.add_argument(
        "--types",
        default="news,release,research,paper",
        help="Comma-separated item types to include, or 'all' "
        "(default: news,release,research,paper)",
    )
    ap.add_argument(
        "--keep-carryover",
        action="store_true",
        help="Keep articles still in the feed but published before the window "
        "(default: drop them — only include articles published within it).",
    )
    ap.add_argument(
        "--no-prior-dedup",
        action="store_true",
        help="Do not exclude articles already cited in an earlier edition "
        "(default: exclude them to avoid cross-edition duplicates).",
    )
    args = ap.parse_args()

    types_raw = args.types.strip().lower()
    include_types = (
        None if types_raw in ("", "all", "*") else {t.strip() for t in types_raw.split(",") if t.strip()}
    )

    end_d = date.fromisoformat(args.date) if args.date else datetime.now(timezone.utc).date()
    day = date_id(end_d)
    start_d = end_d - timedelta(days=max(args.days - 1, 0))

    start_dt = datetime.combine(start_d, time.min, tzinfo=timezone.utc)
    end_dt = datetime.combine(end_d, time.max, tzinfo=timezone.utc)

    exclude_urls = set() if args.no_prior_dedup else edition_card_urls(exclude_date=day)

    articles = collect_articles(
        start_dt,
        end_dt,
        require_published_in_window=not args.keep_carryover,
        exclude_urls=exclude_urls,
    )
    if include_types is not None:
        articles = [a for a in articles if a.get("type") in include_types]

    bundle = {
        "date": day,
        "range_label": (
            fmt_day(end_d)
            if start_d == end_d
            else f"{fmt_day(start_d)} – {fmt_day(end_d)}"
        ),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "included_types": sorted(include_types) if include_types is not None else "all",
        "lookback_days": args.days,
        "published_window": not args.keep_carryover,
        "prior_edition_dedup": not args.no_prior_dedup,
        "prior_edition_urls": len(exclude_urls),
        "area_hints": AREAS,
        "article_count": len(articles),
        "articles": articles,
    }

    write_json(PLAYBOOK_INPUT_DIR / f"{day}.json", bundle)
    write_json(PLAYBOOK_INPUT_DIR / "latest.json", bundle)

    already_published = (PLAYBOOK_DIR / f"{day}.json").exists()

    print(
        json.dumps(
            {
                "date": day,
                "range": bundle["range_label"],
                "included_types": bundle["included_types"],
                "lookback_days": bundle["lookback_days"],
                "prior_edition_urls": bundle["prior_edition_urls"],
                "article_count": len(articles),
                "input_path": f"data/playbook/input/{day}.json",
                "edition_path": f"data/playbook/{day}.json",
                "already_published": already_published,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
