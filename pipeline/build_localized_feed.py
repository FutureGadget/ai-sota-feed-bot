"""Build locale-specific live-feed snapshots.

The first supported surface is the Korean default Brief feed. This module keeps
the core contract deterministic and safe: it can select/hash feed items and
write explicit status even when no translation provider is configured.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
I18N_DIR = DATA_DIR / "i18n"
KST = timezone(timedelta(hours=9))
DEFAULT_LOCALE = "ko"
DEFAULT_LABEL = "brief"
DEFAULT_LIMIT = 20
DEFAULT_DAYS = 7
DEFAULT_TIER1_FRESH_CAP = 4
DEFAULT_TIER1_INSERT_AFTER = 3
DEFAULT_TIER1_MIN_QUICK_SCORE = 2.6
DEFAULT_TIER1_MAX_PER_SOURCE = 1
DEFAULT_TIER1_PRIORITY_MIN = 1
DEFAULT_TIER1_PRIORITY_SOURCES = [
    "openai_blog",
    "anthropic_newsroom",
    "anthropic_engineering",
    "anthropic_research",
    "claude_blog",
]


def load_json(path: Path, fallback: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def norm_url(value: Any) -> str:
    s = str(value or "").strip()
    if s.endswith("/") and len(s) > 1:
        s = s[:-1]
    return s


def translation_key(item: dict[str, Any]) -> str:
    url = norm_url(item.get("url"))
    if url:
        return url
    return str(item.get("id") or item.get("title") or "").strip()


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def source_hash_payload(item: dict[str, Any]) -> dict[str, Any]:
    also = []
    for entry in item.get("also_covered") or []:
        if not isinstance(entry, dict):
            continue
        url = norm_url(entry.get("url"))
        title = _clean_text(entry.get("title"))
        if url or title:
            also.append({"url": url, "title": title})
    return {
        "title": _clean_text(item.get("title")),
        "summary_1line": _clean_text(item.get("summary_1line")),
        "why_it_matters": _clean_text(item.get("why_it_matters")),
        "also_covered": also,
    }


def source_hash(item: dict[str, Any]) -> str:
    payload = json.dumps(
        source_hash_payload(item),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def parse_dt(value: Any) -> datetime | None:
    s = str(value or "").strip()
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def item_key(item: dict[str, Any]) -> str:
    return str(item.get("url") or item.get("title") or "").strip()


def kst_rolling_window(*, now: datetime | None = None, days: int = DEFAULT_DAYS) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    local_today = now.astimezone(KST).date()
    start_day = local_today - timedelta(days=max(1, int(days)) - 1)
    start = datetime.combine(start_day, time.min, tzinfo=KST)
    end = datetime.combine(local_today, time(23, 59, 59, 999000), tzinfo=KST)
    return {
        "days": max(1, int(days)),
        "from": start.isoformat(),
        "to": end.isoformat(),
    }


def is_current(source_run_at: Any, *, now: datetime | None = None, max_age_hours: int = 24) -> bool:
    source_dt = parse_dt(source_run_at)
    if not source_dt:
        return False
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return now.astimezone(timezone.utc) - source_dt <= timedelta(hours=max_age_hours)


def labels_from_item(item: dict[str, Any]) -> set[str]:
    labels: set[str] = set()
    for key in ("llm_category", "v2_slot", "type"):
        value = str(item.get(key) or "").strip().lower()
        if value:
            labels.add(value)
    return labels


def is_release_item(item: dict[str, Any]) -> bool:
    labels = labels_from_item(item)
    return "release" in labels


def select_brief_items(items: list[dict[str, Any]], *, limit: int = DEFAULT_LIMIT) -> list[dict[str, Any]]:
    selected = [it for it in items if isinstance(it, dict) and not is_release_item(it)]
    return selected[: max(1, int(limit))]


def feed_dir(locale: str) -> Path:
    return I18N_DIR / locale / "feed"


def status_payload(
    *,
    locale: str,
    status: str,
    reason: str,
    eligible_count: int = 0,
    translated_count: int = 0,
    source_run_at: str | None = None,
    translated_at: str | None = None,
) -> dict[str, Any]:
    expires_at = None
    source_dt = parse_dt(source_run_at)
    if source_dt:
        expires_at = (source_dt + timedelta(hours=24)).isoformat()
    return {
        "locale": locale,
        "surface": "feed",
        "status": status,
        "reason": reason,
        "source_run_at": source_run_at,
        "translated_at": translated_at,
        "expires_at": expires_at,
        "eligible_count": eligible_count,
        "translated_count": translated_count,
        "missing_count": max(0, eligible_count - translated_count),
    }


def write_status(locale: str, payload: dict[str, Any], *, dry_run: bool = False) -> None:
    log_key = {
        "current": "localized_feed_ok",
        "stale": "localized_feed_stale",
        "incomplete": "localized_feed_incomplete",
        "missing_credentials": "localized_feed_missing_credentials",
        "disabled": "localized_feed_disabled",
    }.get(str(payload.get("status")), "localized_feed_status")
    print(
        f"{log_key}=1 locale={locale} status={payload.get('status')} "
        f"eligible_count={payload.get('eligible_count', 0)} "
        f"translated_count={payload.get('translated_count', 0)} "
        f"reason={payload.get('reason')}"
    )
    if not dry_run:
        atomic_write_json(feed_dir(locale) / "status.json", payload)


def read_latest_feed_items() -> list[dict[str, Any]]:
    data = load_json(DATA_DIR / "processed" / "latest.json", [])
    return data if isinstance(data, list) else []


def read_latest_processed_run_at() -> str | None:
    index = load_json(DATA_DIR / "processed" / "runs_index.json", [])
    if isinstance(index, list) and index:
        first = index[0]
        if isinstance(first, dict) and first.get("run_at"):
            return str(first["run_at"])
    latest = DATA_DIR / "processed" / "latest.json"
    if latest.exists():
        return datetime.fromtimestamp(latest.stat().st_mtime, timezone.utc).isoformat()
    return None


def iter_json_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted((p for p in root.rglob("*.json") if p.is_file()), reverse=True)


def read_processed_runs() -> list[dict[str, Any]]:
    base = DATA_DIR / "processed"
    runs_dir = base / "runs"
    index = load_json(base / "runs_index.json", [])
    runs_by_path: dict[str, dict[str, Any]] = {}
    if isinstance(index, list):
        for row in index:
            if not isinstance(row, dict):
                continue
            rel = row.get("path") or row.get("file")
            if not rel:
                continue
            run = load_json(runs_dir / str(rel), None)
            if isinstance(run, dict) and isinstance(run.get("items"), list):
                runs_by_path[str(rel)] = run

    for path in iter_json_files(runs_dir):
        rel = str(path.relative_to(runs_dir))
        if rel in runs_by_path:
            continue
        run = load_json(path, None)
        if isinstance(run, dict) and isinstance(run.get("items"), list):
            runs_by_path[rel] = run

    return sorted(runs_by_path.values(), key=lambda r: str(r.get("run_at") or ""), reverse=True)


def filter_runs_by_date(runs: list[dict[str, Any]], from_iso: str | None, to_iso: str | None) -> list[dict[str, Any]]:
    start = parse_dt(from_iso)
    end = parse_dt(to_iso)
    out = []
    for run in runs:
        dt = parse_dt(run.get("run_at"))
        if not dt:
            continue
        if start and dt < start:
            continue
        if end and dt > end:
            continue
        out.append(run)
    return out


def filter_items_by_publish_window(
    items: list[dict[str, Any]],
    from_iso: str | None,
    to_iso: str | None,
) -> list[dict[str, Any]]:
    start = parse_dt(from_iso)
    end = parse_dt(to_iso)
    if not start and not end:
        return items
    out = []
    for item in items:
        dt = parse_dt(item.get("published") or item.get("first_seen") or item.get("last_seen"))
        if not dt:
            out.append(item)
            continue
        if start and dt < start:
            continue
        if end and dt > end:
            continue
        out.append(item)
    return out


def accumulate_items(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key: dict[str, dict[str, Any]] = {}
    for run_idx, run in enumerate(runs):
        run_at = run.get("run_at")
        for idx, item in enumerate(run.get("items") or []):
            if not isinstance(item, dict):
                continue
            key = item_key(item)
            if not key:
                continue
            rank = idx + 1
            prev = by_key.get(key)
            if not prev:
                by_key[key] = {
                    **item,
                    "first_seen": run_at,
                    "last_seen": run_at,
                    "seen_count": 1,
                    "last_seen_run_order": run_idx,
                    "rank_at_last_seen": rank,
                    "rank_prev_seen": None,
                    "score_at_last_seen": float(item.get("v2_final_score") or item.get("score") or 0),
                    "run_id": item.get("run_id") or item.get("ingest_batch_id") or run_at,
                }
                continue

            prev["seen_count"] = int(prev.get("seen_count") or 0) + 1
            if run_at and (not prev.get("first_seen") or str(run_at) < str(prev.get("first_seen"))):
                prev["first_seen"] = run_at
            is_newer = bool(run_at and (not prev.get("last_seen") or str(run_at) > str(prev.get("last_seen"))))
            if not is_newer and prev.get("rank_prev_seen") is None:
                prev["rank_prev_seen"] = rank
            if is_newer:
                prev["last_seen"] = run_at
                prev["last_seen_run_order"] = run_idx
                prev["rank_prev_seen"] = prev.get("rank_at_last_seen")
                prev["rank_at_last_seen"] = rank
                prev["score_at_last_seen"] = float(
                    item.get("v2_final_score")
                    or item.get("score")
                    or prev.get("score_at_last_seen")
                    or 0
                )
                for field in ("why_it_matters", "summary_1line", "also_covered", "score", "v2_final_score", "type", "source", "maturity"):
                    if item.get(field) is not None:
                        prev[field] = item.get(field)
                prev["run_id"] = item.get("run_id") or item.get("ingest_batch_id") or run_at or prev.get("run_id")

    return sorted(
        by_key.values(),
        key=lambda it: (
            int(it.get("last_seen_run_order") if it.get("last_seen_run_order") is not None else 9999),
            int(it.get("rank_at_last_seen") if it.get("rank_at_last_seen") is not None else 9999),
            -float(it.get("score_at_last_seen") or 0),
        ),
    )


def read_tier1_recent(*, lookback_hours: int = 24, max_runs: int = 12) -> list[dict[str, Any]]:
    base = DATA_DIR / "tier1"
    runs_dir = base / "runs"
    index = load_json(base / "runs_index.json", [])
    now = datetime.now(timezone.utc)
    selected = []
    if isinstance(index, list):
        for row in index:
            if not isinstance(row, dict):
                continue
            run_at = parse_dt(row.get("run_at"))
            if not run_at or now - run_at > timedelta(hours=max(1, lookback_hours)):
                continue
            selected.append(row)
    selected = sorted(selected, key=lambda r: str(r.get("run_at") or ""), reverse=True)[: max(1, max_runs)]

    by_key: dict[str, dict[str, Any]] = {}
    for row in selected:
        rel = row.get("path") or row.get("file")
        if not rel:
            continue
        run = load_json(runs_dir / str(rel), None)
        if not isinstance(run, dict) or not isinstance(run.get("items"), list):
            continue
        for item in run.get("items") or []:
            if not isinstance(item, dict):
                continue
            key = item_key(item)
            if key and key not in by_key:
                by_key[key] = {**item, "run_at": run.get("run_at")}
    if by_key:
        return list(by_key.values())

    latest = load_json(base / "latest.json", [])
    return latest if isinstance(latest, list) else []


def merge_tier1_fresh(
    base_items: list[dict[str, Any]],
    tier1_items: list[dict[str, Any]],
    deep_run_at_iso: str | None,
) -> tuple[list[dict[str, Any]], int]:
    deep_run_at = parse_dt(deep_run_at_iso)
    if not tier1_items or not deep_run_at:
        return base_items, 0

    by_key = {item_key(it) for it in base_items if item_key(it)}
    source_counts: dict[str, int] = {}
    now = datetime.now(timezone.utc)
    fresh = []
    for item in tier1_items:
        collected = parse_dt(item.get("collected_at"))
        published = parse_dt(item.get("published"))
        dt = collected or published
        quick = float(item.get("tier1_quick_score") or 0)
        title = str(item.get("title") or "")
        url = str(item.get("url") or "")
        if not dt or dt <= deep_run_at or quick < DEFAULT_TIER1_MIN_QUICK_SCORE:
            continue
        if published and now - published > timedelta(hours=24):
            continue
        if title.startswith(("v", "V")) and any(ch.isdigit() for ch in title[:8]):
            continue
        if "/releases/tag/" in url.lower() and any(ch.isdigit() for ch in title[:12]):
            continue
        fresh.append(item)
    fresh.sort(key=lambda it: float(it.get("tier1_quick_score") or 0), reverse=True)

    def pick(candidates: list[dict[str, Any]], *, priority_only: bool) -> list[dict[str, Any]]:
        picked: list[dict[str, Any]] = []
        priority = set(DEFAULT_TIER1_PRIORITY_SOURCES)
        for item in candidates:
            if len(picked) >= DEFAULT_TIER1_FRESH_CAP:
                break
            if priority_only and len(picked) >= DEFAULT_TIER1_PRIORITY_MIN:
                break
            src = str(item.get("source") or "unknown")
            if priority_only and src not in priority:
                continue
            key = item_key(item)
            if not key or key in by_key:
                continue
            if source_counts.get(src, 0) >= DEFAULT_TIER1_MAX_PER_SOURCE:
                continue
            by_key.add(key)
            source_counts[src] = source_counts.get(src, 0) + 1
            picked.append({
                **item,
                "first_seen": item.get("collected_at") or item.get("published"),
                "last_seen": item.get("collected_at") or item.get("published"),
                "seen_count": 1,
                "last_seen_run_order": -1,
                "rank_at_last_seen": None,
                "rank_prev_seen": None,
                "score_at_last_seen": float(item.get("tier1_quick_score") or item.get("score") or 0),
                "tier_hint": "tier1_fresh",
            })
        return picked

    picked = pick(fresh, priority_only=True)
    if len(picked) < DEFAULT_TIER1_FRESH_CAP:
        picked.extend(pick(fresh, priority_only=False))
    picked = picked[:DEFAULT_TIER1_FRESH_CAP]
    at = min(len(base_items), max(0, DEFAULT_TIER1_INSERT_AFTER))
    return [*base_items[:at], *picked, *base_items[at:]], len(picked)


def canonical_brief_feed(
    *,
    limit: int,
    days: int = DEFAULT_DAYS,
    now: datetime | None = None,
) -> dict[str, Any]:
    window = kst_rolling_window(days=days, now=now)
    runs = read_processed_runs()
    if not runs:
        all_items = read_latest_feed_items()
        filtered = filter_items_by_publish_window(select_brief_items(all_items, limit=500), window["from"], window["to"])
        return {
            "items": filtered[:limit],
            "total_items": len(filtered),
            "has_more": len(filtered) > limit,
            "source_run_at": read_latest_processed_run_at(),
            "selector": {
                "endpoint": "/api/feed",
                "label": DEFAULT_LABEL,
                "limit": limit,
                "days": days,
                "from": window["from"],
                "to": window["to"],
                "blend_tier1": True,
            },
        }

    filtered_runs = filter_runs_by_date(runs, window["from"], window["to"])
    deep_run_at = filtered_runs[0].get("run_at") if filtered_runs else None
    base_items = accumulate_items(runs)
    merged, fresh_added = merge_tier1_fresh(base_items, read_tier1_recent(), str(deep_run_at) if deep_run_at else None)
    label_filtered = select_brief_items(merged, limit=500)
    filtered = filter_items_by_publish_window(label_filtered, window["from"], window["to"])
    return {
        "items": filtered[:limit],
        "total_items": len(filtered),
        "has_more": len(filtered) > limit,
        "source_run_at": str(deep_run_at) if deep_run_at else read_latest_processed_run_at(),
        "selector": {
            "endpoint": "/api/feed",
            "label": DEFAULT_LABEL,
            "limit": limit,
            "days": days,
            "from": window["from"],
            "to": window["to"],
            "blend_tier1": True,
            "tier1": {
                "fresh_added": fresh_added,
                "fresh_cap": DEFAULT_TIER1_FRESH_CAP,
                "insert_after": DEFAULT_TIER1_INSERT_AFTER,
                "min_quick_score": DEFAULT_TIER1_MIN_QUICK_SCORE,
                "max_per_source": DEFAULT_TIER1_MAX_PER_SOURCE,
                "priority_min": DEFAULT_TIER1_PRIORITY_MIN,
                "priority_sources": DEFAULT_TIER1_PRIORITY_SOURCES,
            },
        },
    }


def load_existing_translations(locale: str) -> dict[str, dict[str, Any]]:
    latest = load_json(feed_dir(locale) / "latest.json", {})
    if not isinstance(latest, dict):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for row in latest.get("items") or []:
        if not isinstance(row, dict):
            continue
        key = str(row.get("translation_key") or row.get("key") or "").strip()
        if key:
            out[key] = row
    return out


def build_snapshot(*, locale: str, label: str, limit: int, dry_run: bool = False) -> dict[str, Any]:
    if os.environ.get("LOCALIZED_FEED_ENABLED", "1").strip().lower() in {"0", "false", "no", "off"}:
        payload = status_payload(
            locale=locale,
            status="disabled",
            reason="localized_feed_disabled",
        )
        write_status(locale, payload, dry_run=dry_run)
        return payload

    if label != DEFAULT_LABEL:
        payload = status_payload(
            locale=locale,
            status="disabled",
            reason="only_brief_supported",
        )
        write_status(locale, payload, dry_run=dry_run)
        return payload

    feed = canonical_brief_feed(limit=limit)
    items = feed["items"]
    existing = load_existing_translations(locale)
    translated_rows = []
    missing = []
    for item in items:
        key = translation_key(item)
        translated = existing.get(key)
        expected_hash = source_hash(item)
        if translated and str(translated.get("source_hash") or "") == expected_hash:
            translated_rows.append(translated)
        else:
            missing.append(key)

    source_run_at = feed.get("source_run_at")
    status = "current" if len(translated_rows) == len(items) else "missing_credentials"
    reason = "complete" if status == "current" else "no_translation_provider_configured"
    translated_at = datetime.now(timezone.utc).isoformat() if status == "current" else None
    payload = status_payload(
        locale=locale,
        status=status,
        reason=reason,
        eligible_count=len(items),
        translated_count=len(translated_rows),
        source_run_at=source_run_at or None,
        translated_at=translated_at,
    )
    if status == "current" and not dry_run:
        latest_payload = {
            "locale": locale,
            "surface": "feed",
            "source_path": "/",
            "target_path": f"/{locale}/",
            "snapshot_id": str(source_run_at or datetime.now(timezone.utc).isoformat()),
            "source_run_at": source_run_at,
            "translated_at": translated_at,
            "expires_at": payload.get("expires_at"),
            "eligible_label": label,
            "selector": feed.get("selector"),
            "max_items": limit,
            "source_item_count": feed.get("total_items"),
            "translated_item_count": len(translated_rows),
            "is_complete": True,
            "has_more": feed.get("has_more"),
            "items": translated_rows,
        }
        atomic_write_json(feed_dir(locale) / "latest.json", latest_payload)
    write_status(locale, payload, dry_run=dry_run)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build localized live-feed snapshot status.")
    parser.add_argument("--locale", default=DEFAULT_LOCALE)
    parser.add_argument("--label", default=DEFAULT_LABEL)
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    build_snapshot(locale=args.locale, label=args.label, limit=args.limit, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
