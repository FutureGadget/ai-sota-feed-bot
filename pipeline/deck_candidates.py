"""Candidate pool for the editor-deck selector.

The decks used to read only the ranked feed editions. This module builds the
judged candidate set for a published-date window from two sources and merges
them, pool fields winning:

- ``data/quality/pool/<run-date>.json`` (``pipeline/judged_pool.py``): the
  whole post-judge Stage A pool, recorded by every edition build.
- A backfill from the committed artifacts that predate the pool:
  ``data/processed/judgments.json`` (every judged Stage A item, 14-day TTL),
  the run snapshots (edition membership, type, slot, cluster echoes) and
  ``data/raw`` (published date, summary for items outside the editions).

The backfill misses unjudged Stage A items that never reached an edition
(their verdict is not stored); the pool covers them going forward.

Filters mirror the recap bundle builders: published inside the window, item
type, URLs already used by an earlier recap, and known judge drops (release
items exempt, unjudged items pass).
"""

from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from dateutil import parser as dt_parser

try:
    import deck_quality
    import judged_pool
except Exception:  # pragma: no cover - package-style import
    from pipeline import deck_quality, judged_pool

ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"
RAW_DIR = ROOT / "data" / "raw"
BRIEF_DIR = ROOT / "data" / "brief"
SOURCE_ADJUSTMENTS = ROOT / "data" / "feedback" / "source_adjustments.json"

# Run snapshots and pool files are keyed by when the build ran. An article
# published on day D can first be collected on D+1 or D+2.
RUN_LAG_DAYS = 2

JUDGE_FIELDS = (
    "judge_score",
    "judge_verdict",
    "judge_category",
    "judge_category_confidence",
    "judge_signals",
    "judge_evidence_chars",
    "judge_model",
    "judge_rubric_version",
    "judge_judged_at",
)

EMPTY = (None, "", [], {})


def normalize_url(value: Any) -> str:
    return judged_pool.normalize_url(value)


def parse_ts(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        ts = dt_parser.parse(str(value))
    except (ValueError, TypeError, OverflowError):
        return None
    return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)


def window_bounds(start: date, end: date) -> tuple[datetime, datetime]:
    return (
        datetime.combine(start, time.min, tzinfo=timezone.utc),
        datetime.combine(end, time.max, tzinfo=timezone.utc),
    )


def _days(start: date, end: date) -> list[str]:
    out = []
    day = start
    while day <= end:
        out.append(day.isoformat())
        day += timedelta(days=1)
    return out


def _read(path: Path, fallback: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return fallback


def _merge(base: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in extra.items():
        if value not in EMPTY:
            out[key] = value
    return out


def load_source_tune(path: Path | None = None) -> dict[str, float]:
    data = _read(path or SOURCE_ADJUSTMENTS, {})
    out: dict[str, float] = {}
    for source, delta in ((data or {}).get("adjustments") or {}).items():
        try:
            out[str(source)] = float(delta)
        except (TypeError, ValueError):
            continue
    return out


# --- backfill -------------------------------------------------------------


def _raw_items(days: Iterable[str], raw_dir: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for day in days:
        data = _read(raw_dir / day / "items.json", [])
        items = data.get("items", []) if isinstance(data, dict) else data
        for item in items or []:
            if not isinstance(item, dict):
                continue
            key = normalize_url(item.get("url"))
            if key and key not in out:
                out[key] = item
    return out


def _run_rows(start: datetime, end: datetime, processed_dir: Path) -> dict[str, dict[str, Any]]:
    """Edition rows in [start, end] keyed by URL, with edition counters."""
    index = _read(processed_dir / "runs_index.json", [])
    out: dict[str, dict[str, Any]] = {}
    for entry in index if isinstance(index, list) else []:
        run_at = parse_ts(entry.get("run_at"))
        if run_at is None or run_at < start or run_at > end:
            continue
        rel = entry.get("path") or entry.get("file")
        run = _read(processed_dir / "runs" / str(rel), {}) if rel else {}
        items = run.get("items") if isinstance(run, dict) else run
        for rank, item in enumerate(items or [], start=1):
            if not isinstance(item, dict):
                continue
            key = normalize_url(item.get("url"))
            if not key:
                continue
            row = out.get(key) or {"edition_runs": 0}
            row = _merge(row, judged_pool._row_from_item(item))
            row["edition_runs"] = int(row.get("edition_runs") or 0) + 1
            best = row.get("best_edition_rank")
            row["best_edition_rank"] = rank if best is None else min(int(best), rank)
            if item.get("source_tune") is not None:
                row["source_tune"] = item.get("source_tune")
            out[key] = row
    return out


def backfill_rows(
    start: date,
    end: date,
    *,
    processed_dir: Path | None = None,
    raw_dir: Path | None = None,
) -> dict[str, dict[str, Any]]:
    """Reconstruct pool-like rows for a published window from committed data."""
    processed_dir = processed_dir or PROCESSED_DIR
    raw_dir = raw_dir or RAW_DIR
    lo, hi = window_bounds(start - timedelta(days=1), end + timedelta(days=RUN_LAG_DAYS))
    runs = _run_rows(lo, hi, processed_dir)
    raw = _raw_items(_days(start - timedelta(days=2), end + timedelta(days=RUN_LAG_DAYS)), raw_dir)

    rows: dict[str, dict[str, Any]] = {key: dict(row) for key, row in runs.items()}
    store = _read(processed_dir / "judgments.json", {})
    for entry in ((store or {}).get("entries") or {}).values():
        if not isinstance(entry, dict):
            continue
        key = normalize_url(entry.get("url"))
        if not key:
            continue
        judged = {field: entry.get(field) for field in JUDGE_FIELDS}
        for field in ("title", "source", "source_role", "story_key"):
            judged[field] = entry.get(field)
        row = rows.get(key)
        if row is None:
            base = raw.get(key)
            if base is None:
                continue  # judged outside the window
            row = judged_pool._row_from_item({**base, "slot": _slot_for(base.get("source"))})
            row["edition_runs"] = 0
        # The store holds the latest judgment for this identity; prefer it to
        # the copy frozen into an older run snapshot.
        rows[key] = _merge(row, judged)
        rows[key]["url"] = rows[key].get("url") or entry.get("url")

    for key, row in rows.items():
        base = raw.get(key)
        if base:
            if row.get("published") in EMPTY and base.get("published"):
                row["published"] = base["published"]
            if row.get("summary") in EMPTY:
                summary = " ".join(str(base.get("summary") or "").split())[: judged_pool.SUMMARY_CHARS]
                if summary:
                    row["summary"] = summary
        row["backfill"] = True
    return rows


_SLOT_MAP: dict[str, str] | None = None


def load_brief_rows(
    start: date,
    end: date,
    *,
    brief_dir: Path | None = None,
) -> dict[str, dict[str, Any]]:
    """Admitted Brief rows in the published window, keyed by normalized URL.

    The ledger is the served subset of the judged pool. It is a recall check and
    an ``in_brief`` signal for the selector, not a replacement for the pool:
    the pool remains the superset (and the only source older than the ledger
    retention window).
    """
    directory = brief_dir or BRIEF_DIR
    out: dict[str, dict[str, Any]] = {}
    if not directory.is_dir():
        return out
    lo, hi = window_bounds(start, end)
    for path in sorted(directory.glob("*.json")):
        data = _read(path, {})
        rows = data.get("items") if isinstance(data, dict) else data
        if isinstance(rows, dict):
            rows = rows.values()
        for row in rows or []:
            if not isinstance(row, dict):
                continue
            published = parse_ts(row.get("published"))
            if published is None or published < lo or published > hi:
                continue
            key = normalize_url(row.get("url"))
            if not key:
                continue
            prev = out.get(key, {})
            out[key] = {
                **prev,
                **row,
                "in_brief": True,
                "brief_admitted_at": row.get("admitted_at") or prev.get("brief_admitted_at"),
            }
    return out


def _slot_for(source: Any) -> str:
    global _SLOT_MAP
    if _SLOT_MAP is None:
        try:
            try:
                import ranking
            except Exception:  # pragma: no cover
                from pipeline import ranking
            _SLOT_MAP = ranking._build_source_slot_map(ranking.load_ranking_config())
        except Exception:
            _SLOT_MAP = {}
    return _SLOT_MAP.get(str(source or ""), "overflow")


# --- public API -----------------------------------------------------------


def load_rows(
    start: date,
    end: date,
    *,
    pool_dir: Path | None = None,
    processed_dir: Path | None = None,
    raw_dir: Path | None = None,
    brief_dir: Path | None = None,
    use_backfill: bool = True,
) -> dict[str, dict[str, Any]]:
    """Union of backfill, pool and admitted-Brief rows for a published window."""
    rows = backfill_rows(start, end, processed_dir=processed_dir, raw_dir=raw_dir) if use_backfill else {}
    pool = judged_pool.load_pool_days(_days(start, end + timedelta(days=RUN_LAG_DAYS)), pool_dir=pool_dir)
    for key, row in pool.items():
        merged = judged_pool.merge_rows(rows.get(key, {}), row)
        merged["from_pool"] = True
        rows[key] = merged

    brief = load_brief_rows(start, end, brief_dir=brief_dir)
    for key, row in brief.items():
        existing = rows.get(key)
        if existing is None:
            # Defensive recall: a ledger row the pool/backfill missed still
            # reaches the selector. The story grouping collapses it if the
            # same event is already present under another URL.
            existing = dict(row)
            existing["edition_runs"] = 0
            existing["from_ledger"] = True
            rows[key] = existing
        existing["in_brief"] = True
        existing["brief_admitted_at"] = row.get("admitted_at")
    return rows


def is_dropped(row: dict[str, Any], *, exempt_releases: bool = True) -> bool:
    return deck_quality.QualityIndex().is_dropped(row, exempt_releases=exempt_releases)


def filter_rows(
    rows: dict[str, dict[str, Any]],
    start: date,
    end: date,
    *,
    types: set[str] | None = None,
    exclude_urls: set[str] | None = None,
    include_dropped: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Apply the bundle builders' filters. Returns (candidates, reject counts)."""
    lo, hi = window_bounds(start, end)
    exclude = {normalize_url(url) for url in (exclude_urls or set())}
    rejects = {"published_window": 0, "type": 0, "prior_recap": 0, "judge_drop": 0}
    out = []
    for key, row in rows.items():
        published = parse_ts(row.get("published"))
        if published is None or published < lo or published > hi:
            rejects["published_window"] += 1
            continue
        if types is not None and str(row.get("type") or "news") not in types:
            rejects["type"] += 1
            continue
        if key in exclude:
            rejects["prior_recap"] += 1
            continue
        if not include_dropped and is_dropped(row):
            rejects["judge_drop"] += 1
            continue
        out.append({**row, "key": key, "url": row.get("url") or key})
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    out.sort(key=lambda r: (parse_ts(r.get("published")) or epoch, r["key"]), reverse=True)
    return out, rejects


def load_candidates(
    start: date,
    end: date,
    *,
    types: set[str] | None = None,
    exclude_urls: set[str] | None = None,
    include_dropped: bool = False,
    pool_dir: Path | None = None,
    processed_dir: Path | None = None,
    raw_dir: Path | None = None,
    brief_dir: Path | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = load_rows(start, end, pool_dir=pool_dir, processed_dir=processed_dir, raw_dir=raw_dir, brief_dir=brief_dir)
    candidates, rejects = filter_rows(
        rows, start, end, types=types, exclude_urls=exclude_urls, include_dropped=include_dropped
    )
    diag = {
        "rows": len(rows),
        "candidates": len(candidates),
        "from_pool": sum(1 for c in candidates if c.get("from_pool")),
        "from_ledger": sum(1 for c in candidates if c.get("from_ledger")),
        "in_brief": sum(1 for c in candidates if c.get("in_brief")),
        "backfill_only": sum(1 for c in candidates if c.get("backfill") and not c.get("from_pool")),
        "judged": sum(1 for c in candidates if c.get("judge_score") is not None),
        "rejects": rejects,
    }
    return candidates, diag
