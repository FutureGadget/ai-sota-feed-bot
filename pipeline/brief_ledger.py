"""Daily admission ledger for the served Brief.

The feed build already captures the whole post-judge Stage A pool in
``data/quality/pool/<day>.json``. That pool is the right recall set for the
editor decks, but it is offline and much larger than a reader can finish. This
module decides which of those stories are admitted to the reader-facing
24-hour Brief and writes the durable result to ``data/brief/<day>.json``.

Two rules make the served Brief stable:

1. **Admission is once per story.** A story is admitted on the UTC day it first
   appears in the pool. Later builds can add new stories and update coverage,
   but they never remove or re-rank an admitted one.
2. **Caps are flood guards, not a per-day ceiling.** Global, per-role and
   per-source quotas decide admission; the API's display caps only order the
   top of the admitted pool and fold the rest.

The ledger is committed by ``run_full.sh`` and bundled into ``/api/feed`` via
``vercel.json``. It is not read by the static build.
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from collections import Counter
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

import yaml

try:
    import deck_select
    import editorial
    import judged_pool
except Exception:  # pragma: no cover - package-style import
    from pipeline import deck_select, editorial, judged_pool

ROOT = Path(__file__).resolve().parents[1]
BRIEF_DIR = ROOT / "data" / "brief"
POOL_DIR = ROOT / "data" / "quality" / "pool"
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
CONFIG_PATH = ROOT / "config" / "brief.yaml"
SCHEMA_VERSION = 1

# Diagnostics that describe the current pool composition. They are the useful
# signal when nothing new was admitted (all candidates were rejected), so a
# change in these counters still rewrites the file while `items` stays intact.
STABLE_DIAG_KEYS = (
    "candidates",
    "stories",
    "keeps",
    "reviews",
    "unjudged",
    "releases",
    "off_topic",
    "rejected_gate",
    "rejected_quota",
    "prior_story",
)

DISPLAY_FIELDS = (
    "title",
    "published",
    "source",
    "source_role",
    "type",
    "story_key",
    "story_cluster_id",
    "summary_1line",
    "why_it_matters",
    "llm_category",
    "matched_topics",
    "content_excerpt",
    "image_url",
    "time_decay_factor",
    "slot",
    "also_covered",
)

EMPTY = (None, "", [], {})


def load_config(path: Path | None = None) -> dict[str, Any]:
    data = yaml.safe_load((path or CONFIG_PATH).read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def parse_ts(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        ts = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        try:
            from dateutil import parser as dt_parser

            ts = dt_parser.parse(str(value))
        except Exception:
            return None
    return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)


def utc_day(value: Any) -> date | None:
    ts = parse_ts(value)
    return ts.astimezone(timezone.utc).date() if ts else None


def normalize_url(value: Any) -> str:
    return judged_pool.normalize_url(value)


def story_id(row: dict[str, Any]) -> str:
    key = str(row.get("story_key") or "").strip()
    if key:
        return key
    url = normalize_url(row.get("url"))
    if url:
        return f"url:{url}"
    title = " ".join(str(row.get("title") or "").split()).lower()
    return f"title:{title}" if title else ""


def _read(path: Path, fallback: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return fallback


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".brief-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
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


def _compact_coverage(entries: Any) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for entry in entries if isinstance(entries, list) else []:
        if not isinstance(entry, dict):
            continue
        source = str(entry.get("source") or "").strip()
        url = str(entry.get("url") or "").strip()
        title = " ".join(str(entry.get("title") or "").split())[:160]
        key = f"{source}|{normalize_url(url)}"
        if not (source or url or title) or key in seen:
            continue
        seen.add(key)
        out.append({"source": source, "url": url, "title": title})
        if len(out) >= 4:
            break
    return out


def _merge_coverage(base: Any, extra: Any) -> list[dict[str, str]]:
    return _compact_coverage(list(base or []) + list(extra or []))


def _strip_self_coverage(entries: list[dict[str, str]], source: Any, url: Any) -> list[dict[str, str]]:
    self_source = str(source or "")
    self_url = normalize_url(url)
    return [
        entry
        for entry in entries
        if str(entry.get("source") or "") != self_source
        and normalize_url(entry.get("url")) != self_url
    ]


def _display_row(item: dict[str, Any]) -> dict[str, Any]:
    row: dict[str, Any] = {}
    for field in DISPLAY_FIELDS:
        value = item.get(field)
        if value not in EMPTY:
            row[field] = value
    return row


def _merge_display(base: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for field, value in extra.items():
        if value not in EMPTY:
            out[field] = value
    return out


def load_display(day: str, *, processed_dir: Path | None = None, raw_dir: Path | None = None) -> dict[str, dict[str, Any]]:
    """Display fields for the day's URLs from raw items and run snapshots.

    The judged pool carries the judge fields and a squeezed summary. The run
    snapshots carry the enriched ``why_it_matters`` and ``also_covered`` the
    feed card uses; raw items are the fallback for stories that never won a
    run. A run snapshot wins over a raw item.
    """
    processed_dir = processed_dir or PROCESSED_DIR
    raw_dir = raw_dir or RAW_DIR
    out: dict[str, dict[str, Any]] = {}

    raw_path = raw_dir / day / "items.json"
    raw = _read(raw_path, [])
    raw_items = raw.get("items", []) if isinstance(raw, dict) else raw
    for item in raw_items or []:
        if not isinstance(item, dict):
            continue
        key = normalize_url(item.get("url"))
        if key:
            out[key] = _merge_display(out.get(key, {}), _display_row(item))

    wants = day
    index = _read(processed_dir / "runs_index.json", [])
    run_paths: list[str] = []
    if isinstance(index, list):
        for entry in index:
            if not isinstance(entry, dict):
                continue
            entry_day = utc_day(entry.get("run_at"))
            if entry_day is None or entry_day.isoformat() != wants:
                continue
            rel = entry.get("path") or entry.get("file")
            if rel:
                run_paths.append(str(rel))
    if not run_paths:
        runs_root = processed_dir / "runs" / day[:4] / day[5:7]
        if runs_root.is_dir():
            run_paths = [str(p.relative_to(processed_dir / "runs")) for p in sorted(runs_root.glob("*.json"))]

    for rel in run_paths:
        run = _read(processed_dir / "runs" / rel, {})
        items = run.get("items") if isinstance(run, dict) else run
        for item in items or []:
            if not isinstance(item, dict):
                continue
            key = normalize_url(item.get("url"))
            if key:
                out[key] = _merge_display(out.get(key, {}), _display_row(item))
    return out


def freshness_at(
    published: Any,
    admitted_at: Any,
    config: dict[str, Any],
) -> float:
    cfg = config.get("freshness") or {}
    half_life = float(cfg.get("half_life_hours", 36) or 36)
    floor = float(cfg.get("floor", 0.25) or 0.25)
    pub, admitted = parse_ts(published), parse_ts(admitted_at)
    if pub is None or admitted is None:
        return 0.5
    age_hours = max(0.0, (admitted - pub).total_seconds() / 3600.0)
    return max(floor, 0.5 ** (age_hours / half_life))


def utility_for(
    row: dict[str, Any],
    config: dict[str, Any],
    priors: dict[str, float],
) -> tuple[float, dict[str, Any], float]:
    selection_cfg = {
        "weights": config.get("weights") or {},
        "release": config.get("release") or {},
        "unjudged": config.get("unjudged") or {},
    }
    total, parts = deck_select.utility(row, selection_cfg, priors)
    weights = config.get("weights") or {}
    admitted_at = row.get("first_seen_run") or row.get("admitted_at")
    fresh = freshness_at(row.get("published"), admitted_at, config)
    total += float(weights.get("freshness", 0.0) or 0.0) * fresh
    must = 1.0 if str(row.get("release_tier") or "") == "major" else 0.0
    total += float(weights.get("must_cover", 0.0) or 0.0) * must
    parts = dict(parts)
    parts["freshness"] = round(float(weights.get("freshness", 0.0) or 0.0) * fresh, 4)
    parts["must_cover"] = round(float(weights.get("must_cover", 0.0) or 0.0) * must, 4)
    parts["freshness_value"] = round(fresh, 4)
    return round(total, 4), parts, fresh


def gate_reason(row: dict[str, Any], config: dict[str, Any]) -> str | None:
    category = str(row.get("judge_category") or "").strip()
    if category in {str(v) for v in (config.get("exclude_categories") or [])}:
        return "off_topic"
    if deck_select.is_release(row):
        return None

    # A verdict is one unit: a row marked drop is rejected even if a stale or
    # inconsistent score happens to be high. The score threshold only orders
    # keep/review within the admissible band.
    if str(row.get("judge_verdict") or "") == "drop":
        return "judge_drop"

    score = row.get("judge_score")
    if score is not None:
        try:
            value = float(score)
        except (TypeError, ValueError):
            value = None
        if value is not None:
            if value >= float(config.get("min_admit_score", config.get("review_min_score", 0.35)) or 0.35):
                return None
            return "score_low"

    # Missing evidence is the judge-unavailable fail-open path. Present but
    # thin evidence is rejected; the feed should not empty when Jev is down.
    evidence = row.get("judge_evidence_chars")
    if evidence is not None:
        try:
            if int(evidence) < int(config.get("min_evidence_chars", 300) or 300):
                return "insufficient_evidence"
        except (TypeError, ValueError):
            pass
    return None


def _source_role(row: dict[str, Any], editorial_cfg: dict[str, Any]) -> str:
    role = str(row.get("source_role") or "").strip()
    if role:
        return role
    try:
        return str(editorial.source_role(str(row.get("source") or ""), editorial_cfg) or "default")
    except Exception:
        return "default"


def _render_item(
    row: dict[str, Any],
    display: dict[str, Any],
    *,
    utility: float,
    parts: dict[str, Any],
    freshness: float,
    admitted_at: str,
    rank: int,
    editorial_cfg: dict[str, Any],
) -> dict[str, Any]:
    merged = dict(display)
    merged.update({key: value for key, value in row.items() if value not in EMPTY})
    coverage = _merge_coverage(row.get("also_covered"), display.get("also_covered"))
    coverage = _strip_self_coverage(coverage, merged.get("source"), merged.get("url"))
    sources = {entry.get("source") for entry in coverage if entry.get("source")}
    sources.add(str(merged.get("source") or ""))
    sources.discard("")
    type_value = str(merged.get("type") or "news").strip().lower()
    slot_value = str(merged.get("slot") or "").strip()
    llm_category = str(merged.get("llm_category") or merged.get("judge_category") or "")
    if type_value in {"paper", "research"} or slot_value == "research_watch":
        llm_category = "research"
    elif type_value == "release":
        llm_category = "release"
    item = {
        "story_key": story_id(merged),
        "id": merged.get("id") or normalize_url(merged.get("url")),
        "url": merged.get("url") or "",
        "title": merged.get("title") or "",
        "source": merged.get("source") or "",
        "source_role": _source_role(merged, editorial_cfg),
        "type": merged.get("type") or "news",
        "published": merged.get("published"),
        "summary_1line": merged.get("summary_1line") or merged.get("summary") or "",
        "why_it_matters": merged.get("why_it_matters") or "",
        "content_excerpt": merged.get("content_excerpt") or merged.get("excerpt") or "",
        "llm_category": llm_category,
        "v2_slot": merged.get("slot") or "",
        "slot": merged.get("slot") or "",
        "release_tier": merged.get("release_tier"),
        "source_tune": merged.get("source_tune"),
        "matched_topics": merged.get("matched_topics") or [],
        "image_url": merged.get("image_url"),
        "time_decay_factor": merged.get("time_decay_factor"),
        "also_covered": coverage,
        "source_count": len(sources) or 1,
        "admitted_at": admitted_at,
        "first_seen": admitted_at,
        "last_seen": merged.get("last_seen_run") or admitted_at,
        "seen_count": int(merged.get("runs_seen") or 1),
        "utility": utility,
        "utility_basis": str(parts.get("basis") or ""),
        "freshness_at_admission": round(freshness, 4),
        "admission_rank": rank,
        "score_at_first_seen": utility,
        "rank_at_first_seen": rank,
    }
    for field in (
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
        "story_cluster_id",
    ):
        if merged.get(field) not in EMPTY:
            item[field] = merged[field]
    return item


def _update_item(item: dict[str, Any], row: dict[str, Any], display: dict[str, Any]) -> bool:
    merged = dict(display)
    merged.update({key: value for key, value in row.items() if value not in EMPTY})
    changed = False

    last_seen = merged.get("last_seen_run") or item.get("last_seen")
    if last_seen and str(last_seen) > str(item.get("last_seen") or ""):
        item["last_seen"] = last_seen
        changed = True
    seen = int(merged.get("runs_seen") or 1)
    if seen > int(item.get("seen_count") or 0):
        item["seen_count"] = seen
        changed = True

    coverage = _merge_coverage(item.get("also_covered"), row.get("also_covered"))
    coverage = _merge_coverage(coverage, display.get("also_covered"))
    coverage = _merge_coverage(coverage, [{
        "source": row.get("source"),
        "url": row.get("url"),
        "title": row.get("title"),
    }])
    coverage = _strip_self_coverage(coverage, item.get("source"), item.get("url"))
    if coverage != (item.get("also_covered") or []):
        item["also_covered"] = coverage
        sources = {entry.get("source") for entry in coverage if entry.get("source")}
        sources.add(str(item.get("source") or ""))
        sources.discard("")
        item["source_count"] = len(sources) or 1
        changed = True

    for field in ("summary_1line", "why_it_matters", "content_excerpt", "llm_category", "release_tier", "image_url"):
        if item.get(field) in EMPTY and merged.get(field) not in EMPTY:
            item[field] = merged.get(field)
            changed = True

    # A story admitted while unjudged can gain a real judgment later; the
    # admission decision and seat do not change.
    if item.get("judge_score") is None and merged.get("judge_score") is not None:
        for field in (
            "judge_score",
            "judge_verdict",
            "judge_category",
            "judge_category_confidence",
            "judge_signals",
            "judge_evidence_chars",
            "judge_model",
            "judge_rubric_version",
            "judge_judged_at",
        ):
            if merged.get(field) not in EMPTY:
                item[field] = merged[field]
        item.pop("judge_error", None)
        changed = True
    return changed


def _within_six_hours(items: Iterable[dict[str, Any]], source: str, ts: datetime) -> int:
    """Same-source admissions within six hours of this candidate's arrival.

    Symmetric on purpose: a candidate can be considered after a later one on
    the same day (global utility order), and the cap must still hold.
    """
    window = timedelta(hours=6)
    count = 0
    for item in items:
        if str(item.get("source") or "") != source:
            continue
        at = parse_ts(item.get("admitted_at"))
        if at is not None and abs(at - ts) < window:
            count += 1
    return count


def _quota_reason(
    row: dict[str, Any],
    admitted_at: datetime,
    existing: dict[str, dict[str, Any]],
    new_items: dict[str, dict[str, Any]],
    config: dict[str, Any],
    prior_items: list[dict[str, Any]] | None = None,
) -> str | None:
    quotas = config.get("quotas") or {}
    source = str(row.get("source") or "")
    role = str(row.get("source_role") or "default")
    all_items = list(existing.values()) + list(new_items.values()) + list(prior_items or [])
    per_source = int(quotas.get("per_source_per_6h", 0) or 0)
    if per_source > 0 and _within_six_hours(all_items, source, admitted_at) >= per_source:
        return "source_quota"
    roles = quotas.get("roles") or {}
    role_cap = int(roles.get(role, roles.get("default", 0)) or 0)
    role_count = sum(1 for item in existing.values() if str(item.get("source_role") or "") == role)
    role_count += sum(1 for item in new_items.values() if str(item.get("source_role") or "") == role)
    if role_cap > 0 and role_count >= role_cap:
        return "role_quota"
    global_cap = int(quotas.get("global_per_day", 0) or 0)
    if global_cap > 0 and len(existing) + len(new_items) >= global_cap:
        return "global_quota"
    return None


def _admit(
    rows: dict[str, dict[str, Any]],
    existing: dict[str, dict[str, Any]],
    run_at: str,
    config: dict[str, Any],
    editorial_cfg: dict[str, Any],
    display: dict[str, dict[str, Any]],
    prior_stories: dict[str, str] | None = None,
    prior_items: list[dict[str, Any]] | None = None,
    admission_time_mode: str = "run",
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    priors = deck_select.score_priors(list(rows.values()), config)
    diag: dict[str, Any] = {
        "candidates": len(rows),
        "stories": 0,
        "keeps": 0,
        "reviews": 0,
        "unjudged": 0,
        "releases": 0,
        "off_topic": 0,
        "rejected_gate": Counter(),
        "rejected_quota": Counter(),
        "prior_story": 0,
    }
    # One card per story. The pool is keyed by URL, so two outlets reporting
    # the same event can still be two rows with one story_key; keep the best
    # candidate as the representative and roll the other into also_covered.
    best: dict[str, tuple[float, datetime, str, dict[str, Any], dict[str, Any], float]] = {}
    for key, row in rows.items():
        verdict = str(row.get("judge_verdict") or "")
        if verdict == "keep":
            diag["keeps"] += 1
        elif verdict == "review":
            diag["reviews"] += 1
        elif verdict == "unjudged" or row.get("judge_score") is None:
            diag["unjudged"] += 1
        if deck_select.is_release(row):
            diag["releases"] += 1
        if str(row.get("judge_category") or "") in {str(v) for v in (config.get("exclude_categories") or [])}:
            diag["off_topic"] += 1

        first_seen = parse_ts(row.get("first_seen_run")) or parse_ts(run_at)
        if first_seen is None:
            first_seen = parse_ts(run_at) or datetime.now(timezone.utc)
        reason = gate_reason(row, config)
        if reason:
            diag["rejected_gate"][reason] += 1
            continue
        total, parts, fresh = utility_for(row, config, priors)
        sid = story_id(row)
        if not sid:
            continue
        prev = best.get(sid)
        if prev is None or (-total, first_seen, key) < (-prev[0], prev[1], prev[2]):
            coverage = _merge_coverage(row.get("also_covered"), prev[3].get("also_covered") if prev else [])
            if prev is not None:
                coverage = _merge_coverage(coverage, [{
                    "source": prev[3].get("source"),
                    "url": prev[3].get("url"),
                    "title": prev[3].get("title"),
                }])
            row = {**row, "also_covered": coverage}
            best[sid] = (total, first_seen, key, row, parts, fresh)
        else:
            coverage = _merge_coverage(prev[3].get("also_covered"), row.get("also_covered"))
            coverage = _merge_coverage(coverage, [{
                "source": row.get("source"),
                "url": row.get("url"),
                "title": row.get("title"),
            }])
            prev[3]["also_covered"] = coverage
    diag["stories"] = len(best)

    scored = sorted(best.values(), key=lambda pair: (-pair[0], pair[1], pair[2]))
    new_items: dict[str, dict[str, Any]] = {}
    prior_stories = prior_stories or {}
    run_time = parse_ts(run_at)
    use_first_seen = str(admission_time_mode) == "first_seen"
    for utility, first_seen, key, row, parts, fresh in scored:
        sid = story_id(row)
        if sid in existing:
            continue
        prior_at = parse_ts(prior_stories.get(sid))
        if prior_at is not None and abs(first_seen - prior_at) < timedelta(hours=24):
            diag["prior_story"] += 1
            continue
        role = _source_role(row, editorial_cfg)
        row_for_quota = {**row, "source_role": role}
        # A story admitted late in the day gets a full 24-hour window from the
        # moment it entered the ledger, not from its first pool sighting. The
        # backfill intentionally uses first_seen to reconstruct a past day.
        admitted_time = first_seen if use_first_seen or run_time is None else run_time
        reason = _quota_reason(
            row_for_quota,
            admitted_time,
            existing,
            new_items,
            config,
            prior_items=prior_items,
        )
        if reason:
            diag["rejected_quota"][reason] += 1
            continue
        item = _render_item(
            row_for_quota,
            display.get(normalize_url(row.get("url")), {}),
            utility=utility,
            parts=parts,
            freshness=fresh,
            admitted_at=admitted_time.isoformat(),
            rank=len(existing) + len(new_items) + 1,
            editorial_cfg=editorial_cfg,
        )
        if not item.get("story_key"):
            continue
        new_items[sid] = item

    diag["rejected_gate"] = dict(diag["rejected_gate"])
    diag["rejected_quota"] = dict(diag["rejected_quota"])
    diag["admitted"] = len(new_items)
    diag["role_counts"] = dict(Counter(str(item.get("source_role") or "default") for item in new_items.values()))
    return new_items, diag


def record_run(
    candidates: list[dict[str, Any]] | None = None,
    edition: list[dict[str, Any]] | None = None,
    run_at: str | None = None,
    *,
    brief_dir: Path | None = None,
    pool_dir: Path | None = None,
    config_path: Path | None = None,
    rebuild: bool = False,
    admission_time_mode: str = "run",
) -> dict[str, Any]:
    """Append this build's candidates to the day's Brief ledger.

    Never raises; the feed build must not fail on ledger bookkeeping.
    """
    diag: dict[str, Any] = {"written": False}
    try:
        config = load_config(config_path)
        if not config.get("enabled", True):
            diag["reason"] = "disabled"
            return diag
        stamp = run_at or datetime.now(timezone.utc).isoformat()
        day = (utc_day(stamp) or datetime.now(timezone.utc).date()).isoformat()
        directory = brief_dir or BRIEF_DIR
        path = directory / f"{day}.json"

        pool_rows = judged_pool.load_pool_days([day], pool_dir=pool_dir)
        if not pool_rows and (candidates or edition):
            seed: dict[str, Any] = {}
            judged_pool.merge_run(seed, candidates or [], edition or [], stamp)
            pool_rows = seed.get("items") or {}
        # Safety net: if the pool write failed or was skipped, the current
        # build's candidates must still reach the admission gate.
        for item in list(candidates or []) + list(edition or []):
            if not isinstance(item, dict):
                continue
            key = normalize_url(item.get("url"))
            if not key:
                continue
            row = judged_pool._row_from_item(item)
            pool_rows[key] = judged_pool.merge_rows(pool_rows.get(key, {}), row)
        if not pool_rows:
            diag["reason"] = "empty"
            return diag

        display = load_display(day)
        for item in list(candidates or []) + list(edition or []):
            if not isinstance(item, dict):
                continue
            key = normalize_url(item.get("url"))
            if key:
                display[key] = _merge_display(display.get(key, {}), _display_row(item))

        existing_payload = {} if rebuild else _read(path, {})
        existing = dict(existing_payload.get("items") or {})
        prior_stories: dict[str, str] = {}
        prior_items: list[dict[str, Any]] = []
        day_date = date.fromisoformat(day)
        for offset in (1, 2):
            prior_day = (day_date - timedelta(days=offset)).isoformat()
            prior_payload = _read(directory / f"{prior_day}.json", {})
            for pid, pitem in (prior_payload.get("items") or {}).items():
                if not isinstance(pitem, dict):
                    continue
                prior_items.append(pitem)
                if pitem.get("admitted_at"):
                    prior_stories[pid] = str(pitem["admitted_at"])
        updated = 0
        pool_by_story: dict[str, list[dict[str, Any]]] = {}
        for row in pool_rows.values():
            sid = story_id(row)
            if sid:
                pool_by_story.setdefault(sid, []).append(row)
        for key, item in list(existing.items()):
            for row in pool_by_story.get(key, []):
                if _update_item(item, row, display.get(normalize_url(row.get("url")), {})):
                    updated += 1

        editorial_cfg = editorial.load_config()
        new_items, admit_diag = _admit(
            pool_rows,
            existing,
            stamp,
            config,
            editorial_cfg,
            display,
            prior_stories=prior_stories,
            prior_items=prior_items,
            admission_time_mode=admission_time_mode,
        )
        items = {**existing, **new_items}
        previous_diag = existing_payload.get("diagnostics") or {}
        diag_changed = any(
            admit_diag.get(key) != previous_diag.get(key)
            for key in STABLE_DIAG_KEYS
        )
        changed = bool(new_items) or updated > 0 or diag_changed
        diag.update(admit_diag)
        diag.update(
            {
                "written": changed,
                "path": str(path),
                "items": len(items),
                "new": len(new_items),
                "updated": updated,
                "run_candidates": len(candidates or []),
            }
        )
        if not changed:
            diag["reason"] = "no_change"
            return diag

        payload = {
            "schema_version": SCHEMA_VERSION,
            "date": day,
            "timezone": "UTC",
            "updated_at": stamp,
            "items": items,
            "diagnostics": {key: value for key, value in diag.items() if key not in {"path"}},
        }
        _atomic_write(path, payload)
        return diag
    except Exception as exc:  # the feed build must never fail on this
        diag["reason"] = f"error:{exc}"
        return diag


def backfill(
    days: int = 3,
    *,
    brief_dir: Path | None = None,
    pool_dir: Path | None = None,
    config_path: Path | None = None,
    force: bool = False,
    today: date | None = None,
) -> list[dict[str, Any]]:
    """Rebuild ledgers for the last ``days`` UTC days from committed pools.

    Days with an existing ledger are skipped unless ``force`` is set, so the
    normal append-only writer is never rewound by a routine backfill.
    """
    directory = brief_dir or BRIEF_DIR
    end = today or datetime.now(timezone.utc).date()
    out: list[dict[str, Any]] = []
    for offset in range(max(1, days) - 1, -1, -1):
        day = (end - timedelta(days=offset)).isoformat()
        path = directory / f"{day}.json"
        if path.exists() and not force:
            out.append({"date": day, "skipped": True, "reason": "exists"})
            continue
        if path.exists():
            path.unlink()
        pool = _read((pool_dir or POOL_DIR) / f"{day}.json", {})
        run_at = pool.get("updated_at") or datetime.combine(
            date.fromisoformat(day), time(23, 59, 59), tzinfo=timezone.utc
        ).isoformat()
        diag = record_run(
            None,
            None,
            run_at=run_at,
            brief_dir=directory,
            pool_dir=pool_dir,
            config_path=config_path,
            rebuild=True,
            admission_time_mode="first_seen",
        )
        out.append({"date": day, **diag})
    return out


def prune(days: int | None = None, *, brief_dir: Path | None = None, today: date | None = None) -> dict[str, int]:
    directory = brief_dir or BRIEF_DIR
    if days is None:
        days = int(load_config().get("retention_days", 3) or 3)
    end = today or datetime.now(timezone.utc).date()
    cutoff = end - timedelta(days=max(0, days))
    deleted = kept = 0
    if days <= 0 or not directory.is_dir():
        return {"deleted": 0, "kept": 0}
    for path in sorted(directory.glob("*.json")):
        try:
            stamp = date.fromisoformat(path.stem)
        except ValueError:
            continue
        if stamp < cutoff:
            path.unlink()
            deleted += 1
        else:
            kept += 1
    return {"deleted": deleted, "kept": kept}


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the served Brief admission ledger.")
    sub = parser.add_subparsers(dest="command")
    back = sub.add_parser("backfill", help="Rebuild recent ledgers from data/quality/pool.")
    back.add_argument("--days", type=int, default=3)
    back.add_argument("--force", action="store_true")
    pr = sub.add_parser("prune", help="Delete ledgers older than the retention window.")
    pr.add_argument("--days", type=int, default=None, help="Defaults to config/brief.yaml retention_days.")
    show = sub.add_parser("show", help="Print one day's ledger diagnostics.")
    show.add_argument("--date", default=datetime.now(timezone.utc).date().isoformat())
    args = parser.parse_args()

    if args.command == "backfill":
        for row in backfill(days=args.days, force=args.force):
            print(json.dumps(row, ensure_ascii=False, sort_keys=True))
    elif args.command == "prune":
        print(json.dumps(prune(days=args.days), sort_keys=True))
    elif args.command == "show":
        path = BRIEF_DIR / f"{args.date}.json"
        data = _read(path, {})
        print(json.dumps({
            "date": args.date,
            "exists": bool(data),
            "items": len((data.get("items") or {})),
            "updated_at": data.get("updated_at"),
            "diagnostics": data.get("diagnostics"),
        }, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
