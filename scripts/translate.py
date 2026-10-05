#!/usr/bin/env python3
"""Translate i18n candidates using Google Cloud Translation API v2.

Usage:
    # Translate all missing/stale daily pages for Korean:
    python scripts/translate.py --locale ko --surface daily

    # Translate a specific page:
    python scripts/translate.py --locale ko --surface daily --id 2026-07-05

    # Translate up to 5 candidates across all surfaces:
    python scripts/translate.py --locale ko --limit 5

    # Dry run (show what would be translated without calling the API):
    python scripts/translate.py --locale ko --surface daily --dry-run

Prerequisites:
    - GOOGLE_TRANSLATE_API_KEY set in the environment
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Allow importing from pipeline/
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))

import build_localized_feed as ledger_lib  # noqa: E402
import export_i18n_candidates as exporter  # noqa: E402
import google_translate  # noqa: E402
import translation_guard  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_LOCALE = "ko"
MODEL_NAME = "google-translate-v2"

# Static pages get their own monthly character allowance, separate from the live
# feed ledger (data/i18n/<locale>/feed/budget.json). Google's free tier is
# 500,000 chars/month per billing account; feed cap (400,000) + this (100,000)
# add up to the whole allowance.
DEFAULT_STATIC_MONTHLY_CAP = 100_000


def _static_cap_from_env() -> int:
    raw = os.environ.get("GOOGLE_TRANSLATE_STATIC_MONTHLY_CHAR_CAP")
    if not raw:
        return DEFAULT_STATIC_MONTHLY_CAP
    try:
        return max(0, int(raw))
    except ValueError:
        return DEFAULT_STATIC_MONTHLY_CAP


# ---------------------------------------------------------------------------
# Merge & validation helpers
# ---------------------------------------------------------------------------

def _deep_merge(source: Any, translated: Any) -> Any:
    """Recursively merge translated fields on top of the original source."""
    if isinstance(source, dict) and isinstance(translated, dict):
        result = source.copy()
        for k, v in translated.items():
            if k in result:
                result[k] = _deep_merge(result[k], v)
            else:
                result[k] = v
        return result
    elif isinstance(source, list) and isinstance(translated, list):
        result = []
        for idx, item in enumerate(source):
            if idx < len(translated):
                result.append(_deep_merge(item, translated[idx]))
            else:
                result.append(item)
        return result
    else:
        return translated


def _validate_translation(
    translated: dict[str, Any],
    contract: dict[str, Any],
    surface: str,
) -> list[str]:
    """Perform basic schema validations on the translated JSON."""
    warnings = []
    # Ensure all target top-level keys exist
    for field_path in contract["translated_fields"]:
        top_key = field_path.split("[")[0].split(".")[0]
        if top_key not in translated:
            warnings.append(f"Missing translated field: {top_key}")

    # Basic content checks
    if surface in ("daily", "weekly"):
        cats = translated.get("categories", [])
        if not isinstance(cats, list) or len(cats) == 0:
            warnings.append("categories array is empty or missing")
        for i, cat in enumerate(cats):
            if not isinstance(cat, dict):
                continue
            if not cat.get("name"):
                warnings.append(f"categories[{i}].name is empty")
            articles = cat.get("articles", [])
            if not isinstance(articles, list) or len(articles) == 0:
                warnings.append(f"categories[{i}].articles is empty")

    return warnings


# ---------------------------------------------------------------------------
# Artifact assembly
# ---------------------------------------------------------------------------

def _assemble_artifact(
    candidate: dict[str, Any],
    translated: dict[str, Any],
    model_name: str,
) -> dict[str, Any]:
    """Build the final translation artifact JSON."""
    artifact: dict[str, Any] = {
        "locale": candidate["locale"],
        "source_path": candidate["source_path"],
        "source_hash": candidate["source_hash"],
        "translated_at": datetime.now(timezone.utc).isoformat(),
        "model": model_name,
        "review_status": "machine",
    }
    # Merge translated fields recursively on top of the original source
    merged = _deep_merge(candidate.get("source", {}), translated)
    artifact.update(merged)
    return artifact


def _rebuild_playbook_i18n_index(locale: str) -> None:
    """Rebuild index.json, latest.json for localized playbook."""
    import shutil
    i18n_playbook_dir = ROOT / "data" / "i18n" / locale / "playbook"
    if not i18n_playbook_dir.is_dir():
        return

    edition_files = sorted(
        p for p in i18n_playbook_dir.glob("*.json")
        if p.name not in ("index.json", "latest.json", "source-index.json")
    )

    entries = []
    for path in edition_files:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            cards = data.get("cards", [])
            entries.append({
                "date": data["date"],
                "title": data["title"],
                "generated_at": data.get("generated_at"),
                "card_count": len(cards),
                "path": path.name,
            })
        except Exception as e:
            print(f"  Error indexing localized playbook {path.name}: {e}")

    entries.sort(key=lambda e: str(e.get("date")), reverse=True)

    # Write index.json
    index_path = i18n_playbook_dir / "index.json"
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)
        f.write("\n")

    # Write latest.json
    if entries:
        latest_src_path = i18n_playbook_dir / entries[0]["path"]
        latest_dest_path = i18n_playbook_dir / "latest.json"
        try:
            shutil.copy2(latest_src_path, latest_dest_path)
            print(f"  Rebuilt localized playbook index and latest.json at {i18n_playbook_dir.relative_to(ROOT)}")
        except Exception as e:
            print(f"  Error copying latest localized playbook: {e}")


# ---------------------------------------------------------------------------
# Main translation loop
# ---------------------------------------------------------------------------

# Google Cloud Console "characters per day" quota (v2 and v3 are set separately;
# the project uses v2). The live feed shares it and has priority: static pages
# only spend what is left after the feed's usage so far today plus a reserve for
# the rest of the Pacific day (the quota resets at Pacific midnight).
DEFAULT_DAILY_QUOTA = 16_000
DEFAULT_FEED_RESERVE = 6_000


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        return max(0, int(raw))
    except ValueError:
        return default


def _chars_today(ledger: dict[str, Any], now: datetime) -> int:
    """Characters recorded in this ledger's history during the current Pacific day."""
    pacific = ledger_lib.PACIFIC_TZ
    today = now.astimezone(pacific).date()
    total = 0
    for entry in ledger.get("history") or []:
        try:
            at = datetime.fromisoformat(str(entry["at"]).replace("Z", "+00:00"))
            if at.astimezone(pacific).date() == today:
                total += int(entry.get("chars") or 0)
        except (KeyError, ValueError, TypeError):
            continue
    return total


def _daily_headroom(feed_ledger_path: Path, static_ledger: dict[str, Any], now: datetime) -> int:
    """Characters static translation may still spend today without starving the feed."""
    feed_ledger = ledger_lib._read_json(feed_ledger_path) or {}
    quota = _int_env("GOOGLE_TRANSLATE_DAILY_CHAR_QUOTA", DEFAULT_DAILY_QUOTA)
    reserve = _int_env("GOOGLE_TRANSLATE_STATIC_FEED_RESERVE", DEFAULT_FEED_RESERVE)
    used = _chars_today(feed_ledger, now) + _chars_today(static_ledger, now)
    return quota - reserve - used


def _estimate_candidate_chars(candidate: dict[str, Any]) -> int:
    """Billed characters for one candidate (same fields translate_fields sends)."""
    entries: list[tuple[list[Any], str]] = []
    for path in candidate["contract"]["translated_fields"]:
        google_translate._collect_strings(
            candidate["source"], google_translate._parse_path(path), [], entries
        )
    return google_translate.estimate_billed_chars([v for _, v in entries])


def _record_spend(
    ledger_path: Path, ledger: dict[str, Any], stats: dict[str, int], run_id: str
) -> None:
    chars = int(stats.get("chars_sent", 0))
    if chars <= 0:
        return
    now = datetime.now(timezone.utc)
    ledger_lib.record_usage(ledger, chars, run_id, now)
    ledger_lib.save_ledger(ledger_path, ledger, now)


def translate_candidates(
    *,
    locale: str,
    surfaces: set[str] | None,
    target_id: str | None,
    limit: int,
    dry_run: bool,
    include_fresh: bool,
    days: int | None = None,
) -> int:
    """Translate candidates and write artifact files. Return exit code."""
    # Build the candidate list via the existing exporter
    payload = exporter.build_export(
        locale=locale,
        surfaces=surfaces,
        include_fresh=include_fresh,
        include_source=True,  # We need the source to translate
        limit=limit if target_id is None else 500,
        days=days,
    )
    items = payload.get("items", [])

    # Filter to specific ID if requested
    if target_id is not None:
        items = [it for it in items if it["id"] == target_id]
        if not items:
            print(f"ERROR: No candidate found with id '{target_id}'", file=sys.stderr)
            return 1

    if not items:
        print("No candidates to translate (all fresh).")
        return 0

    print(f"Found {len(items)} candidate(s) to translate\n")

    if dry_run:
        print("DRY RUN — would translate:\n")
        for it in items:
            print(f"  [{it['status']:>7}] {it['surface']:>12} / {it['id']}")
            print(f"           {it['title'][:80]}")
        return 0

    successes = 0
    failures = 0
    budget_skipped = 0

    # Character budget: every candidate is estimated before the API call and
    # skipped when it would push the month past the cap. Spend is persisted after
    # each candidate so a crash or cancelled run never loses metering.
    now = datetime.now(timezone.utc)
    ledger_path = ROOT / "data" / "i18n" / locale / "feed" / "static_budget.json"
    ledger = ledger_lib.load_ledger(ledger_path, _static_cap_from_env(), now)
    feed_ledger_path = ROOT / "data" / "i18n" / locale / "feed" / "budget.json"
    run_id = now.strftime("%Y%m%d-%H%M%S") + "-static"
    print(
        f"translate_static_budget chars_used={ledger['chars_used']} "
        f"cap={ledger['monthly_cap']} month={ledger['month']}"
    )

    for i, candidate in enumerate(items, 1):
        surface = candidate["surface"]
        ident = candidate["id"]
        status = candidate["status"]
        contract = candidate["contract"]
        title = candidate.get("title", "")[:60]

        print(f"\n[{i}/{len(items)}] {surface}/{ident} ({status})")
        print(f"  Title: {title}")

        if not candidate.get("source"):
            print("  SKIP: No source data available")
            failures += 1
            continue

        # Budget pre-flight: estimate billed characters for this candidate.
        estimate = _estimate_candidate_chars(candidate)
        remaining = int(ledger["monthly_cap"]) - int(ledger["chars_used"])
        if estimate > remaining:
            print(
                f"  SKIP: budget (needs ~{estimate} chars, {max(remaining, 0)} left "
                f"of {ledger['monthly_cap']} this month)"
            )
            budget_skipped += 1
            continue
        headroom = _daily_headroom(feed_ledger_path, ledger, datetime.now(timezone.utc))
        if estimate > headroom:
            print(
                f"  SKIP: daily quota (needs ~{estimate} chars, {max(headroom, 0)} "
                "left after the feed's share today)"
            )
            budget_skipped += 1
            continue

        # Call Google Cloud Translation API
        print(f"  Translating via {MODEL_NAME}...", end="", flush=True)
        start = time.monotonic()
        stats: dict[str, int] = {}
        try:
            translated = google_translate.translate_fields(
                candidate["source"],
                contract["translated_fields"],
                locale,
                stats=stats,
            )
            elapsed = time.monotonic() - start
            print(f" done ({elapsed:.1f}s)")
        except Exception as exc:
            elapsed = time.monotonic() - start
            print(f" FAILED ({elapsed:.1f}s)")
            print(f"  Error: {exc}", file=sys.stderr)
            failures += 1
            # Batches that succeeded before the failure were still billed.
            _record_spend(ledger_path, ledger, stats, run_id)
            if isinstance(exc, google_translate.QuotaExceededError):
                # Spend guard or provider quota: every later candidate would fail too.
                print("  STOP: quota exhausted, not trying remaining candidates")
                break
            continue
        _record_spend(ledger_path, ledger, stats, run_id)

        warnings = _validate_translation(translated, contract, surface)
        for w in warnings:
            print(f"  WARNING: {w}")

        # Assemble and write artifact
        artifact = _assemble_artifact(candidate, translated, MODEL_NAME)
        artifact_path = ROOT / candidate["artifact_path"]
        artifact_path.parent.mkdir(parents=True, exist_ok=True)

        text = json.dumps(artifact, ensure_ascii=False, indent=2) + "\n"
        artifact_path.write_text(text, encoding="utf-8")
        print(f"  Written: {artifact_path.relative_to(ROOT)}")
        successes += 1

    print(f"\n{'='*50}")
    print(
        f"Done: {successes} translated, {failures} failed, "
        f"{budget_skipped} skipped (budget), {len(items)} total"
    )
    print(
        f"translate_static_budget_done chars_used={ledger['chars_used']} "
        f"cap={ledger['monthly_cap']} month={ledger['month']}"
    )

    if successes > 0 and not dry_run:
        _rebuild_playbook_i18n_index(locale)

    return 0 if failures == 0 else 1


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Translate i18n candidates using Google Cloud Translation API.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--locale", default=DEFAULT_LOCALE,
        help=f"Target locale (default: {DEFAULT_LOCALE})",
    )
    parser.add_argument(
        "--surface", action="append",
        choices=sorted(exporter.SURFACE_ORDER),
        help="Limit to surface type; repeat for multiple (default: all)",
    )
    parser.add_argument(
        "--id", dest="target_id",
        help="Translate only the candidate with this exact id (date, slug, sid)",
    )
    parser.add_argument(
        "--limit", type=int, default=10,
        help="Max candidates to translate (default: 10)",
    )
    parser.add_argument(
        "--days", type=int,
        help="Limit candidates to those modified within N days from today",
    )
    parser.add_argument(
        "--include-fresh", action="store_true",
        help="Re-translate already fresh artifacts",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show candidates without translating",
    )
    return parser.parse_args()


def main() -> int:
    # Gate on API key before doing any work
    if google_translate.get_api_key() is None:
        print(
            "ERROR: GOOGLE_TRANSLATE_API_KEY is not set.\n"
            "Set the environment variable and retry.",
            file=sys.stderr,
        )
        return 1

    args = parse_args()
    if not args.dry_run:
        # Hard, fail-closed spend ceiling in front of every API request.
        translation_guard.install_default()
    return translate_candidates(
        locale=args.locale,
        surfaces=set(args.surface or []) or None,
        target_id=args.target_id,
        limit=args.limit,
        dry_run=args.dry_run,
        include_fresh=args.include_fresh,
        days=args.days,
    )


if __name__ == "__main__":
    raise SystemExit(main())
