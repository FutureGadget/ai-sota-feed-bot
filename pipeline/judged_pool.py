"""Durable per-day judged candidate pool for the editor decks.

Every edition build judges a Stage A candidate pool (up to
``candidate_pool_cap`` items) and then keeps about 24 of them for the feed.
The daily/weekly recap bundles read only those 24-item editions, so anything
the judge kept but the feed layout did not place is invisible to the decks.

This module records the whole post-judge pool, one row per item, in
``data/quality/pool/<run-date>.json``. Each build merges into the file for
its UTC run date: the latest judge fields win, and run counters accumulate.
Unjudged items are recorded too, so the decks can fail open the same way the
feed does.

The pool is an offline input for deck selection and funnel measurement. It
is not read by any API (``data/quality`` is excluded from the deployment) and
never changes the feed. See
``docs/exec-plans/active/2026-10-29-deck-candidate-selector.md``.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
POOL_DIR = ROOT / "data" / "quality" / "pool"
SCHEMA_VERSION = 1

EXCERPT_CHARS = 400
SUMMARY_CHARS = 280

# Copied from the latest observation of an item. ``None``/empty values never
# overwrite a stored value, so a later run that fails open (judge timeout,
# missing key) does not erase an earlier judgment.
ITEM_FIELDS = (
    "id",
    "title",
    "url",
    "source",
    "source_role",
    "type",
    "published",
    "story_key",
    "story_cluster_id",
    "judge_score",
    "judge_verdict",
    "judge_category",
    "judge_category_confidence",
    "judge_signals",
    "judge_evidence_chars",
    "judge_error",
    "judge_model",
    "judge_rubric_version",
    "judge_judged_at",
    "prefilter_score",
    "source_tune",
)

EMPTY = (None, "", [], {})


def normalize_url(value: Any) -> str:
    url = str(value or "").split("#")[0].strip()
    return url[:-1] if url.endswith("/") and len(url) > 1 else url


def item_key(item: dict[str, Any]) -> str:
    """Stable row key: normalized URL, falling back to id, then title."""
    return normalize_url(item.get("url")) or str(item.get("id") or "").strip() or str(item.get("title") or "").strip()


def _squeeze(value: Any, limit: int) -> str:
    return " ".join(str(value or "").split())[:limit]


def _row_from_item(item: dict[str, Any]) -> dict[str, Any]:
    row: dict[str, Any] = {}
    for field in ITEM_FIELDS:
        value = item.get(field)
        if value not in EMPTY:
            row[field] = value
    excerpt = _squeeze(item.get("content_excerpt"), EXCERPT_CHARS)
    if excerpt:
        row["excerpt"] = excerpt
    summary = _squeeze(item.get("summary_1line") or item.get("summary"), SUMMARY_CHARS)
    if summary:
        row["summary"] = summary
    also_covered = item.get("also_covered")
    if isinstance(also_covered, list) and also_covered:
        row["echo_count"] = len(also_covered)
        sources = {str(entry.get("source")) for entry in also_covered if isinstance(entry, dict) and entry.get("source")}
        sources.add(str(item.get("source") or ""))
        sources.discard("")
        row["source_count"] = len(sources)
    if item.get("slot"):
        row["slot"] = item["slot"]
    return row


def _read(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".pool-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            # One key per line keeps the bi-hourly git diffs small.
            json.dump(payload, handle, ensure_ascii=False, indent=1, sort_keys=True)
            handle.write("\n")
        os.chmod(tmp, 0o644)  # mkstemp creates 0600
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def merge_run(
    pool: dict[str, Any],
    candidates: list[dict[str, Any]],
    edition: list[dict[str, Any]],
    run_at: str,
) -> dict[str, Any]:
    """Merge one build's judged pool and its edition into ``pool`` in place.

    ``candidates`` is the post-judge Stage A pool. ``edition`` is the final
    ranked list; its items mark ``edition_runs`` and ``best_edition_rank``.
    An edition item missing from the candidate pool is still recorded.
    """
    items = pool.setdefault("items", {})
    edition_rank = {}
    for rank, item in enumerate(edition, start=1):
        key = item_key(item)
        if key and key not in edition_rank:
            edition_rank[key] = (rank, item)

    seen_this_run: set[str] = set()
    for item in list(candidates) + [pair[1] for pair in edition_rank.values()]:
        key = item_key(item)
        if not key or key in seen_this_run:
            continue
        seen_this_run.add(key)
        row = items.get(key) or {}
        for field, value in _row_from_item(item).items():
            row[field] = value
        row.setdefault("first_seen_run", run_at)
        row["last_seen_run"] = run_at
        row["runs_seen"] = int(row.get("runs_seen") or 0) + 1
        if key in edition_rank:
            rank, edition_item = edition_rank[key]
            row["edition_runs"] = int(row.get("edition_runs") or 0) + 1
            previous = row.get("best_edition_rank")
            row["best_edition_rank"] = rank if previous is None else min(int(previous), rank)
            if edition_item.get("slot"):
                row["edition_slot"] = edition_item["slot"]
        else:
            row.setdefault("edition_runs", 0)
        items[key] = row

    pool["schema_version"] = SCHEMA_VERSION
    pool["runs"] = int(pool.get("runs") or 0) + 1
    pool["updated_at"] = run_at
    pool["item_count"] = len(items)
    return pool


def record_run(
    candidates: list[dict[str, Any]] | None,
    edition: list[dict[str, Any]],
    run_at: str | None = None,
    pool_dir: Path | None = None,
) -> dict[str, Any]:
    """Merge a build into today's pool file. Never raises; returns diagnostics."""
    diag: dict[str, Any] = {"written": False}
    if not candidates and not edition:
        diag["reason"] = "empty"
        return diag
    try:
        stamp = run_at or datetime.now(timezone.utc).isoformat()
        try:
            day = datetime.fromisoformat(stamp.replace("Z", "+00:00")).astimezone(timezone.utc).date().isoformat()
        except ValueError:
            day = datetime.now(timezone.utc).date().isoformat()
        directory = pool_dir or POOL_DIR
        path = directory / f"{day}.json"
        pool = _read(path)
        pool.setdefault("date", day)
        merge_run(pool, candidates or [], edition, stamp)
        _atomic_write(path, pool)
        rows = pool["items"].values()
        diag.update(
            {
                "written": True,
                "path": str(path),
                "items": len(pool["items"]),
                "run_candidates": len(candidates or []),
                "in_edition": sum(1 for row in rows if row.get("edition_runs")),
                "judged": sum(1 for row in rows if row.get("judge_score") is not None),
            }
        )
    except Exception as exc:  # the feed build must never fail on this
        diag["reason"] = f"error:{exc}"
    return diag


def load_pool_days(days: list[str], pool_dir: Path | None = None) -> dict[str, dict[str, Any]]:
    """Union of pool rows over several run dates, latest observation wins."""
    directory = pool_dir or POOL_DIR
    merged: dict[str, dict[str, Any]] = {}
    for day in sorted(days):
        pool = _read(directory / f"{day}.json")
        for key, row in (pool.get("items") or {}).items():
            if not isinstance(row, dict):
                continue
            previous = merged.get(key)
            if previous is None:
                merged[key] = dict(row)
                continue
            combined = dict(previous)
            for field, value in row.items():
                if value not in EMPTY:
                    combined[field] = value
            combined["first_seen_run"] = min(str(previous.get("first_seen_run") or "~"), str(row.get("first_seen_run") or "~"))
            combined["runs_seen"] = int(previous.get("runs_seen") or 0) + int(row.get("runs_seen") or 0)
            combined["edition_runs"] = int(previous.get("edition_runs") or 0) + int(row.get("edition_runs") or 0)
            ranks = [r for r in (previous.get("best_edition_rank"), row.get("best_edition_rank")) if r is not None]
            if ranks:
                combined["best_edition_rank"] = min(int(r) for r in ranks)
            merged[key] = combined
    return merged
