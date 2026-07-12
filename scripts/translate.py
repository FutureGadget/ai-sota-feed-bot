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
import google_translate  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_LOCALE = "ko"
MODEL_NAME = "google-translate-v2"


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


# ---------------------------------------------------------------------------
# Main translation loop
# ---------------------------------------------------------------------------

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

        # Call Google Cloud Translation API
        print(f"  Translating via {MODEL_NAME}...", end="", flush=True)
        start = time.monotonic()
        try:
            translated = google_translate.translate_fields(
                candidate["source"],
                contract["translated_fields"],
                locale,
            )
            elapsed = time.monotonic() - start
            print(f" done ({elapsed:.1f}s)")
        except Exception as exc:
            elapsed = time.monotonic() - start
            print(f" FAILED ({elapsed:.1f}s)")
            print(f"  Error: {exc}", file=sys.stderr)
            failures += 1
            continue

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
    print(f"Done: {successes} translated, {failures} failed, {len(items)} total")

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
