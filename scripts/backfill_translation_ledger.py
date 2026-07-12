#!/usr/bin/env python3
"""Estimate a month's Google Translate spend from git history.

Read-only: never writes data/i18n/<locale>/feed/budget.json. Use this as the
no-console-access fallback for seeding the ledger, or as a periodic sanity
check against the live ledger's chars_used.

For each commit touching data/i18n/<locale>/feed/latest.json within the given
month, diffs which translation_keys got a new source_hash (exactly the items
sent to the API that run), pulls the English source fields for those keys from
data/processed/latest.json at the same commit, and sums input chars.
"""

import argparse
import json
import subprocess
from calendar import monthrange
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent


def _norm_url(url: Any) -> str:
    s = str(url or "").strip()
    return s[:-1] if s.endswith("/") and len(s) > 1 else s


def _translation_key(it: dict[str, Any]) -> str:
    url = _norm_url(it.get("url"))
    return url or str(it.get("id") or it.get("title") or "").strip()


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)


def _commits_in_month(latest_path: str, month_start: datetime, month_end: datetime) -> list[str]:
    res = _git(
        "log", "--reverse", "--format=%H",
        f"--since={month_start.isoformat()}", f"--until={month_end.isoformat()}",
        "--", latest_path,
    )
    if res.returncode != 0:
        return []
    return [line.strip() for line in res.stdout.splitlines() if line.strip()]


def _baseline_commit(latest_path: str, month_start: datetime) -> str | None:
    res = _git("log", "-1", "--format=%H", f"--until={month_start.isoformat()}", "--", latest_path)
    if res.returncode != 0:
        return None
    out = res.stdout.strip()
    return out or None


def _show_json(commit: str | None, path: str) -> Any:
    if not commit:
        return None
    res = _git("show", f"{commit}:{path}")
    if res.returncode != 0:
        return None
    try:
        return json.loads(res.stdout)
    except json.JSONDecodeError:
        return None


def _translation_key_map(snapshot: dict[str, Any] | None) -> dict[str, str]:
    if not snapshot:
        return {}
    out = {}
    for it in snapshot.get("items", []):
        key = it.get("translation_key")
        if key:
            out[key] = it.get("source_hash")
    return out


def _processed_items(processed_snapshot: Any) -> list[dict[str, Any]]:
    """data/processed/latest.json is a bare list of items in some snapshots and
    {"items": [...]} in others; accept both shapes."""
    if isinstance(processed_snapshot, list):
        return processed_snapshot
    if isinstance(processed_snapshot, dict):
        items = processed_snapshot.get("items")
        if isinstance(items, list):
            return items
    return []


def _input_chars_for_key(processed_snapshot: Any, key: str) -> int:
    for it in _processed_items(processed_snapshot):
        if _translation_key(it) == key:
            texts = [it.get("title") or "", it.get("summary_1line") or "", it.get("why_it_matters") or ""]
            for ac in it.get("also_covered") or []:
                if isinstance(ac, dict):
                    texts.append(ac.get("title") or "")
            return sum(len(str(t)) for t in texts if str(t).strip())
    return 0


def estimate_month(month: str, locale: str = "ko") -> dict[str, Any]:
    year, mon = (int(x) for x in month.split("-"))
    month_start = datetime(year, mon, 1, tzinfo=timezone.utc)
    days = monthrange(year, mon)[1]
    month_end = datetime(year, mon, days, 23, 59, 59, tzinfo=timezone.utc)

    latest_path = f"data/i18n/{locale}/feed/latest.json"
    processed_path = "data/processed/latest.json"

    commits = _commits_in_month(latest_path, month_start, month_end)
    baseline = _baseline_commit(latest_path, month_start)
    prev_map = _translation_key_map(_show_json(baseline, latest_path))

    total_chars = 0
    changed_items = 0
    missing_source_items = 0

    for commit in commits:
        current_map = _translation_key_map(_show_json(commit, latest_path))
        changed_keys = [k for k, h in current_map.items() if prev_map.get(k) != h]
        if changed_keys:
            processed = _show_json(commit, processed_path)
            for key in changed_keys:
                chars = _input_chars_for_key(processed, key)
                if chars == 0:
                    missing_source_items += 1
                total_chars += chars
                changed_items += 1
        prev_map = current_map

    return {
        "month": month,
        "locale": locale,
        "commits_scanned": len(commits),
        "changed_items": changed_items,
        "missing_source_items": missing_source_items,
        "estimated_chars": total_chars,
        "suggested_seed_chars": int(total_chars * 1.15),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Estimate a month's Google Translate spend from git history. Read-only; never writes the ledger."
    )
    parser.add_argument("--month", required=True, help="UTC calendar month to estimate, YYYY-MM.")
    parser.add_argument("--locale", default="ko")
    args = parser.parse_args()

    result = estimate_month(args.month, args.locale)
    print(f"Scanned {result['commits_scanned']} commits touching data/i18n/{args.locale}/feed/latest.json in {result['month']}")
    print(f"Changed/translated items: {result['changed_items']} (missing English source: {result['missing_source_items']})")
    print(f"Estimated input chars sent: {result['estimated_chars']}")
    print(f"Suggested --seed-chars (with 15% safety margin): {result['suggested_seed_chars']}")
    print("Read-only: the ledger was not modified. To apply this estimate, run:")
    print(
        f"  python3 pipeline/build_localized_feed.py --locale {args.locale} "
        f"--seed-chars {result['suggested_seed_chars']} --seed-note \"backfill estimate {result['month']}\""
    )


if __name__ == "__main__":
    main()
