#!/usr/bin/env python3
"""Translate i18n candidates with Claude (pipeline/translator.py).

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
    - Anthropic credentials in the environment (workload identity in CI)

Spend is metered in USD by the ledger shared with the live feed
(data/i18n/translation_spend.json). Each page is saved as soon as it is
translated, so a stop at the monthly cap keeps everything done so far.
"""

from __future__ import annotations

import argparse
import hashlib
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

import export_i18n_candidates as exporter  # noqa: E402
import locales  # noqa: E402
import translator  # noqa: E402
import persist_static_i18n as persistence  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_LOCALE = "ko"
# Surfaces whose Korean version the agent routine writes in the same run as
# the English one (.agents/skills/daily-summary, weekly-summary).
AGENT_TRANSLATED_SURFACES = {"daily", "weekly"}


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

def _parse_path(path: str) -> list[str]:
    """Parse 'categories[].articles[].title' into ['categories', '[]', 'articles', '[]', 'title']."""
    segments: list[str] = []
    for part in path.split("."):
        if part.endswith("[]"):
            segments.append(part[:-2])
            segments.append("[]")
        else:
            segments.append(part)
    return segments


def _collect_strings(
    obj: Any,
    path_segments: list[str],
    address: list[Any],
    out: list[tuple[list[Any], str]],
) -> None:
    """Recursively collect string values at the given path."""
    if not path_segments:
        if isinstance(obj, str) and obj.strip():
            out.append((list(address), obj))
        return

    seg = path_segments[0]
    rest = path_segments[1:]

    if seg == "[]":
        if not isinstance(obj, list):
            return
        for i, item in enumerate(obj):
            _collect_strings(item, rest, address + [i], out)
    else:
        if not isinstance(obj, dict) or seg not in obj:
            return
        _collect_strings(obj[seg], rest, address + [seg], out)


def _set_at_address(root: dict[str, Any], address: list[Any], value: Any) -> None:
    """Set a value in a nested dict/list structure, creating containers as needed."""
    current: Any = root
    for i, key in enumerate(address[:-1]):
        next_key = address[i + 1]
        if isinstance(key, int):
            while len(current) <= key:
                current.append({} if isinstance(next_key, str) else [])
            current = current[key]
        else:
            if key not in current:
                current[key] = [] if isinstance(next_key, int) else {}
            current = current[key]

    last_key = address[-1]
    if isinstance(last_key, int):
        while len(current) <= last_key:
            current.append(None)
        current[last_key] = value
    else:
        current[last_key] = value


def _candidate_entries(candidate: dict[str, Any]) -> list[tuple[list[Any], str]]:
    """The exact translated strings and addresses, excluding source metadata."""
    entries: list[tuple[list[Any], str]] = []
    for path in candidate["contract"]["translated_fields"]:
        _collect_strings(candidate.get("source", {}), _parse_path(path), [], entries)
    return entries


def _candidate_payload_hash(candidate: dict[str, Any]) -> str:
    payload = json.dumps(
        [candidate["locale"], _candidate_entries(candidate)],
        ensure_ascii=False, separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def page_job(candidate: dict[str, Any], entries: list[tuple[list[Any], str]]) -> translator.Job:
    """One job per page: its collected strings keyed by their index in ``entries``."""
    return translator.Job(
        key=f"{candidate['surface']}/{candidate['id']}",
        fields={str(i): text for i, (_, text) in enumerate(entries)},
        context=candidate.get("title", ""),
    )


def _translated_fields(entries: list[tuple[list[Any], str]], result: translator.Result) -> dict[str, Any]:
    """The translated strings placed at their source addresses."""
    translated: dict[str, Any] = {}
    for i, (address, _) in enumerate(entries):
        _set_at_address(translated, address, result.fields[str(i)])
    return translated


def translate_candidates(
    *,
    locale: str,
    surfaces: set[str] | None,
    target_id: str | None,
    limit: int,
    dry_run: bool,
    include_fresh: bool,
    days: int | None = None,
    client=None,
) -> int:
    """Translate candidates and write artifact files. Return exit code."""
    if surfaces is None:
        # Recap routines write their own Korean recaps; only an explicit
        # --surface daily/weekly sends a recap to the translator.
        surfaces = set(exporter.SURFACE_ORDER) - AGENT_TRANSLATED_SURFACES
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
    unavailable_skipped = 0

    # The ledger reserves before every call and records after it, so a crash or
    # cancelled run never loses metering. Each page is written as soon as it is
    # translated: a failure or the cap never discards finished pages.
    ledger = translator.Ledger(ROOT / "data" / "i18n" / "translation_spend.json")
    print(f"translate_static_budget usd_spent={ledger.spent:.4f} cap={ledger.monthly_cap:.2f}")
    model = translator.model_for("static")
    client = client or translator.make_client()

    for i, candidate in enumerate(items, 1):
        surface = candidate["surface"]
        ident = candidate["id"]
        status = candidate["status"]
        title = candidate.get("title", "")[:60]

        print(f"\n[{i}/{len(items)}] {surface}/{ident} ({status})")
        print(f"  Title: {title}")

        # An acknowledged lost output was already paid for. A later scheduled run
        # must not silently buy the identical text after metadata-only rebuilds.
        try:
            lost_run = persistence.lost_output_run(
                ROOT, candidate["artifact_path"], candidate["source_hash"],
                _candidate_payload_hash(candidate),
            )
        except persistence.PersistenceError as exc:
            print(f"  STOP: unreadable persistence receipt: {exc}", file=sys.stderr)
            return 1
        if lost_run:
            print(f"  SKIP: paid output unavailable run={lost_run} source_hash={candidate['source_hash']}")
            unavailable_skipped += 1
            continue

        if not candidate.get("source"):
            print("  SKIP: No source data available")
            failures += 1
            continue

        entries = _candidate_entries(candidate)
        print(f"  Translating via {model}...", end="", flush=True)
        start = time.monotonic()
        try:
            [result] = translator.translate(
                [page_job(candidate, entries)], locale, "static", client=client, ledger=ledger
            )
        except translator.BudgetExceeded as exc:
            print(" STOPPED")
            print(f"  STOP: {exc}; not trying remaining candidates", file=sys.stderr)
            break
        except Exception as exc:
            print(f" FAILED ({time.monotonic() - start:.1f}s)")
            print(f"  Error: {exc}", file=sys.stderr)
            failures += 1
            continue
        print(f" done ({time.monotonic() - start:.1f}s)")

        translated = _translated_fields(entries, result)
        warnings = _validate_translation(translated, candidate["contract"], surface)
        for w in warnings:
            print(f"  WARNING: {w}")

        # Assemble and write artifact
        artifact = _assemble_artifact(candidate, translated, model)
        artifact_path = ROOT / candidate["artifact_path"]
        artifact_path.parent.mkdir(parents=True, exist_ok=True)

        text = json.dumps(artifact, ensure_ascii=False, indent=2) + "\n"
        temporary_path = artifact_path.with_name(artifact_path.name + ".tmp")
        temporary_path.write_text(text, encoding="utf-8")
        temporary_path.replace(artifact_path)
        print(f"  Written: {artifact_path.relative_to(ROOT)}")
        successes += 1

    not_tried = len(items) - successes - failures - unavailable_skipped
    print(f"\n{'='*50}")
    print(
        f"Done: {successes} translated, {failures} failed, "
        f"{unavailable_skipped} skipped (paid output unavailable), "
        f"{not_tried} not tried (monthly cap), {len(items)} total"
    )
    print(f"translate_static_budget_done usd_spent={ledger.spent:.4f} cap={ledger.monthly_cap:.2f}")

    if successes > 0 and not dry_run:
        _rebuild_playbook_i18n_index(locale)

    # Reaching the cap is a normal stop, not a failure: the finished pages are
    # committed and the rest wait for the next month.
    return 0 if failures == 0 else 1


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Translate i18n candidates with Claude.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--locale", default=DEFAULT_LOCALE, choices=locales.others(locales.DEFAULT),
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
    args = parse_args()
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
