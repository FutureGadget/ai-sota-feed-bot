"""Stability and admission scorecard for the served Brief.

Pure functions used by ``scripts/feed_replay.py``. No network, no writes.

The scorecard answers three questions:

1. **Admission coverage:** how many of the day's judge keeps reached the served
   Brief, and why the rest did not.
2. **Stability:** across production run times, how much did the visible Brief
   change, and did any story leave while still inside its 24-hour window?
3. **Mix:** what roles, sources and admission lag does the served pool hold?

The ledger is append-only, so the only legitimate way for a story to leave the
visible window is age (its admission crossed 24 hours). Any removal before
that is an eviction and is reported as ``unexpected_removals``.
"""

from __future__ import annotations

import json
import statistics
from collections import Counter
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
BRIEF_DIR = ROOT / "data" / "brief"
POOL_DIR = ROOT / "data" / "quality" / "pool"
PROCESSED_DIR = ROOT / "data" / "processed"


def parse_ts(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        ts = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)


def utc_day(value: Any) -> str | None:
    ts = parse_ts(value)
    return ts.astimezone(timezone.utc).date().isoformat() if ts else None


def story_key(row: dict[str, Any]) -> str:
    key = str(row.get("story_key") or "").strip()
    if key:
        return key
    url = str(row.get("url") or "").strip()
    if url:
        return f"url:{url}"
    return str(row.get("title") or "").strip()


def _read(path: Path, fallback: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return fallback


def load_ledger_files(brief_dir: Path | None = None) -> list[dict[str, Any]]:
    directory = brief_dir or BRIEF_DIR
    out: list[dict[str, Any]] = []
    if not directory.is_dir():
        return out
    for path in sorted(directory.glob("*.json")):
        data = _read(path, {})
        if not isinstance(data, dict) or not data.get("items"):
            continue
        rows = data.get("items")
        items = list(rows.values()) if isinstance(rows, dict) else list(rows)
        out.append(
            {
                "date": data.get("date") or path.stem,
                "updated_at": data.get("updated_at"),
                "items": [item for item in items if isinstance(item, dict)],
                "diagnostics": data.get("diagnostics") or {},
            }
        )
    return out


def flatten_entries(files: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [item for file in files for item in file.get("items") or []]


def load_pool_day(day: str, pool_dir: Path | None = None) -> dict[str, dict[str, Any]]:
    data = _read((pool_dir or POOL_DIR) / f"{day}.json", {})
    rows = data.get("items") if isinstance(data, dict) else None
    if isinstance(rows, dict):
        return {str(key): row for key, row in rows.items() if isinstance(row, dict)}
    return {}


def load_run_times(
    *,
    processed_dir: Path | None = None,
    days: int = 3,
    end: datetime | None = None,
) -> list[datetime]:
    directory = processed_dir or PROCESSED_DIR
    index = _read(directory / "runs_index.json", [])
    if not isinstance(index, list):
        return []
    end = end or datetime.now(timezone.utc)
    cutoff = end - timedelta(days=max(1, days))
    times = []
    for row in index:
        if not isinstance(row, dict):
            continue
        ts = parse_ts(row.get("run_at"))
        if ts is not None and cutoff <= ts <= end + timedelta(hours=1):
            times.append(ts.astimezone(timezone.utc))
    return sorted(set(times))


def brief_order(items: Iterable[dict[str, Any]], top_n: int = 5, max_per_source: int = 3) -> list[dict[str, Any]]:
    """Sort by admission utility, then apply the API's top-band source cap."""
    ordered = sorted(
        [item for item in items if isinstance(item, dict)],
        key=lambda row: (
            -float(row.get("utility") or 0.0),
            str(row.get("admitted_at") or row.get("first_seen") or ""),
            str(row.get("url") or ""),
        ),
    )
    if len(ordered) <= max_per_source:
        return ordered
    head = ordered[:top_n]
    tail = ordered[top_n:]
    counts: Counter[str] = Counter()
    out: list[dict[str, Any]] = []
    for item in head:
        source = str(item.get("source") or "unknown")
        if counts[source] < max_per_source or not tail:
            out.append(item)
            counts[source] += 1
            continue
        replacement_index = next(
            (
                index
                for index, candidate in enumerate(tail)
                if counts[str(candidate.get("source") or "unknown")] < max_per_source
            ),
            None,
        )
        if replacement_index is None:
            out.append(item)
            counts[source] += 1
            continue
        replacement = tail[replacement_index]
        tail[replacement_index] = item
        out.append(replacement)
        counts[str(replacement.get("source") or "unknown")] += 1
    return out + tail


def active_window(entries: Iterable[dict[str, Any]], at: datetime, hours: int = 24) -> list[dict[str, Any]]:
    """The visible Brief at ``at``: admissions in the last 24h, latest per story.

    A story re-admitted after its previous admission aged out is represented by
    the latest active admission, matching ``api/feed.js``.
    """
    lo = at - timedelta(hours=hours)
    by_story: dict[str, tuple[datetime, dict[str, Any]]] = {}
    for row in entries:
        admitted = parse_ts(row.get("admitted_at") or row.get("first_seen"))
        if admitted is None or admitted > at or admitted < lo:
            continue
        sid = story_key(row)
        if not sid:
            continue
        previous = by_story.get(sid)
        if previous is None or admitted > previous[0]:
            by_story[sid] = (admitted, row)
    return brief_order([row for _, row in by_story.values()])


def top_keys(items: Iterable[dict[str, Any]], n: int = 10) -> list[str]:
    return [story_key(item) for item in list(items)[: max(0, n)]]


def jaccard(a: Iterable[str], b: Iterable[str]) -> float | None:
    left = {value for value in a if value}
    right = {value for value in b if value}
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    return round(len(left & right) / len(left | right), 4)


def rank_displacement(a: Iterable[str], b: Iterable[str]) -> float | None:
    left = {value: index for index, value in enumerate(a) if value}
    right = {value: index for index, value in enumerate(b) if value}
    common = set(left) & set(right)
    if not common:
        return None
    return round(statistics.mean(abs(left[key] - right[key]) for key in common), 2)


def window_removals(
    previous: Iterable[dict[str, Any]],
    current: Iterable[dict[str, Any]],
    at_next: datetime,
    *,
    hours: int = 24,
) -> dict[str, Any]:
    """Removed story keys, splitting age expiry from unexpected eviction."""
    previous_by_key = {story_key(item): item for item in previous if story_key(item)}
    current_keys = {story_key(item) for item in current if story_key(item)}
    removed = set(previous_by_key) - current_keys
    lo = at_next - timedelta(hours=hours)
    unexpected = []
    expired = 0
    for key in sorted(removed):
        admitted = parse_ts(previous_by_key[key].get("admitted_at") or previous_by_key[key].get("first_seen"))
        if admitted is not None and admitted >= lo:
            unexpected.append(key)
        else:
            expired += 1
    return {
        "removed": len(removed),
        "expired": expired,
        "unexpected_removals": len(unexpected),
        "unexpected_keys": unexpected,
    }


def day_summary(
    day: str,
    ledger_file: dict[str, Any],
    pool_rows: dict[str, dict[str, Any]],
    served_ids: set[str] | None = None,
) -> dict[str, Any]:
    items = ledger_file.get("items") or []
    admitted_ids = {story_key(item) for item in items if story_key(item)}
    served_ids = set(served_ids) if served_ids is not None else set(admitted_ids)
    keeps: set[str] = set()
    for row in pool_rows.values():
        if utc_day(row.get("first_seen_run")) != day:
            continue
        if str(row.get("judge_verdict") or "") == "keep":
            keeps.add(story_key(row))
    keeps_admitted = len(keeps & admitted_ids)
    keeps_served = len(keeps & served_ids)
    roles = Counter(str(item.get("source_role") or "default") for item in items)
    sources = Counter(str(item.get("source") or "unknown") for item in items)
    lags = []
    for item in items:
        admitted = parse_ts(item.get("admitted_at") or item.get("first_seen"))
        published = parse_ts(item.get("published"))
        if admitted is not None and published is not None and admitted >= published:
            lags.append((admitted - published).total_seconds() / 3600.0)
    diagnostics = ledger_file.get("diagnostics") or {}
    return {
        "date": day,
        "admitted": len(items),
        "admitted_keeps": sum(1 for item in items if str(item.get("judge_verdict") or "") == "keep"),
        "admitted_reviews": sum(1 for item in items if str(item.get("judge_verdict") or "") == "review"),
        "admitted_releases": sum(1 for item in items if str(item.get("type") or "") == "release"),
        "served": len(served_ids),
        "keeps_total": len(keeps),
        "keeps_admitted": keeps_admitted,
        "keeps_served": keeps_served,
        "keeps_admission_rate": round(keeps_served / len(keeps), 4) if keeps else None,
        "rejected_gate": diagnostics.get("rejected_gate") or {},
        "rejected_quota": diagnostics.get("rejected_quota") or {},
        "prior_story": int(diagnostics.get("prior_story") or 0),
        "role_counts": dict(sorted(roles.items(), key=lambda kv: (-kv[1], kv[0]))),
        "top_sources": dict(sources.most_common(8)),
        "published_lag_median_hours": round(statistics.median(lags), 2) if lags else None,
    }


def stability(
    entries: Iterable[dict[str, Any]],
    run_times: Iterable[datetime],
    *,
    top_n: int = 10,
    min_visible: int = 5,
) -> dict[str, Any]:
    times = sorted(run_times)
    pairs = []
    for previous_at, current_at in zip(times, times[1:]):
        previous = active_window(entries, previous_at)
        current = active_window(entries, current_at)
        if not previous and not current:
            continue
        previous_top = top_keys(previous, top_n)
        current_top = top_keys(current, top_n)
        removals = window_removals(previous, current, current_at)
        pairs.append(
            {
                "from": previous_at.isoformat(),
                "to": current_at.isoformat(),
                "visible_previous": len(previous),
                "visible_current": len(current),
                "added": len({story_key(item) for item in current} - {story_key(item) for item in previous}),
                "top_jaccard": jaccard(previous_top, current_top),
                "rank_displacement": rank_displacement(previous_top, current_top),
                **removals,
            }
        )
    if not pairs:
        return {
            "pairs": 0,
            "rated_pairs": 0,
            "min_visible": min_visible,
            "top10_jaccard_mean": None,
            "top10_jaccard_min": None,
            "rank_displacement_mean": None,
            "unexpected_removals": 0,
            "removed_total": 0,
            "expired_total": 0,
            "per_pair": [],
        }
    rated = [
        pair
        for pair in pairs
        if pair["visible_previous"] >= min_visible and pair["visible_current"] >= min_visible
    ]
    jaccards = [p["top_jaccard"] for p in rated if p["top_jaccard"] is not None]
    displacements = [p["rank_displacement"] for p in rated if p["rank_displacement"] is not None]
    return {
        "pairs": len(pairs),
        "rated_pairs": len(rated),
        "min_visible": min_visible,
        "top10_jaccard_mean": round(statistics.mean(jaccards), 4) if jaccards else None,
        "top10_jaccard_min": min(jaccards) if jaccards else None,
        "rank_displacement_mean": round(statistics.mean(displacements), 2) if displacements else None,
        "unexpected_removals": sum(p["unexpected_removals"] for p in pairs),
        "removed_total": sum(p["removed"] for p in pairs),
        "expired_total": sum(p["expired"] for p in pairs),
        "per_pair": pairs,
    }


def scorecard(
    *,
    days: int = 3,
    brief_dir: Path | None = None,
    pool_dir: Path | None = None,
    processed_dir: Path | None = None,
    end: datetime | None = None,
) -> dict[str, Any]:
    files = load_ledger_files(brief_dir)
    if end is not None:
        cutoff = end.astimezone(timezone.utc).date().isoformat()
        files = [file for file in files if str(file.get("date") or "") <= cutoff]
    entries = flatten_entries(files)
    summaries = []
    for file in files:
        day_end = datetime.combine(
            date.fromisoformat(str(file["date"])), time(23, 59, 59), tzinfo=timezone.utc
        )
        served_ids = {story_key(item) for item in active_window(entries, day_end)}
        summaries.append(day_summary(file["date"], file, load_pool_day(file["date"], pool_dir), served_ids=served_ids))
    run_times = load_run_times(processed_dir=processed_dir, days=days, end=end)
    stability_block = stability(entries, run_times)
    total_keeps = sum(row["keeps_total"] for row in summaries)
    total_keeps_admitted = sum(row["keeps_served"] for row in summaries)
    return {
        "days": days,
        "ledgers": len(files),
        "runs": len(run_times),
        "admitted": sum(row["admitted"] for row in summaries),
        "served": sum(row["served"] for row in summaries),
        "keeps_total": total_keeps,
        "keeps_admitted": total_keeps_admitted,
        "keeps_admission_rate": round(total_keeps_admitted / total_keeps, 4) if total_keeps else None,
        "day_summaries": summaries,
        "stability": stability_block,
    }
