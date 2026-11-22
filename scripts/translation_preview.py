#!/usr/bin/env python3
"""Preview Claude translations of the committed /ko/ feed cards.

Builds one job per card in data/i18n/ko/feed/latest.json (English source from
data/processed/latest.json, matched by translation key), translates them with
the `feed` surface, and prints a Markdown table of English, committed, and
Claude text. Writes no data file: spend goes to --ledger, a temp file by default.

    python3 scripts/translation_preview.py --limit 5
    python3 scripts/translation_preview.py --limit 2 --dry-run   # no API call
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))

import build_localized_feed as feed  # noqa: E402
import translator  # noqa: E402


def build_jobs(locale: str, limit: int) -> tuple[list[translator.Job], dict[str, dict], int]:
    """Jobs for the cards the /ko/ builder would translate now: the top `limit`
    Brief items from the same /api/feed selector build_localized_feed.py uses.
    Committed Korean text comes from the snapshot, when it has the card."""
    snapshot = json.loads((ROOT / "data" / "i18n" / locale / "feed" / "latest.json").read_text(encoding="utf-8"))
    by_key = {card["translation_key"]: card for card in snapshot["items"]}
    params = feed.snapshot_params("brief", max(100, limit * 2), datetime.now(timezone.utc))
    english = feed._fetch_english_feed(params).get("items", [])[:limit]
    jobs, current = [], {}
    for src in english:
        job = feed.item_job(src)
        jobs.append(job)
        current[job.key] = by_key.get(job.key, {})
    return jobs, current, len(english)


def cell(text: str) -> str:
    return " ".join(str(text or "").split()).replace("|", "\\|")


def table(jobs, current, results, field: str, header: str) -> str:
    rows = [f"| English {header} | Committed | Claude |", "| --- | --- | --- |"]
    for job, res in zip(jobs, results):
        if field in job.fields:
            committed = current[job.key].get(field)
            rows.append(f"| {cell(job.fields[field])} | {cell(committed)} | {cell(res.fields[field])} |")
    return "\n".join(rows)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--locale", default="ko")
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--ledger", type=Path, default=None, help="spend ledger path (default: a temp file)")
    p.add_argument("--dry-run", action="store_true", help="print the jobs and exit without calling the API")
    args = p.parse_args()

    jobs, current, _ = build_jobs(args.locale, args.limit)
    print(f"Previewing {len(jobs)} Brief cards (the set build_localized_feed.py translates).\n")

    if args.dry_run:
        for job in jobs:
            print(f"- {job.key}")
            for name, text in job.fields.items():
                print(f"    {name}: {text}")
            print(f"    context: {len(job.context)} chars" + (f" ({cell(job.context[:70])}...)" if job.context else ""))
        return

    ledger_path = args.ledger or Path(tempfile.mkdtemp(prefix="translation-preview-")) / "spend.json"
    ledger = translator.Ledger(ledger_path)
    results = translator.translate(jobs, args.locale, "feed", ledger=ledger)

    total = sum(r.cost_usd for r in results)
    out = "\n\n".join(
        [
            "## Titles",
            table(jobs, current, results, "title", "title"),
            "## One-line summaries",
            table(jobs, current, results, "summary_1line", "summary"),
            f"Total cost: ${total:.4f} for {len(results)} cards.",
        ]
    )
    print(out)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write(out + "\n")


if __name__ == "__main__":
    main()
