from __future__ import annotations

import json
import math
import os
import re
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from dateutil import parser as dt_parser

from brief_ledger import record_run as record_brief_ledger
from content_fetch import build_content_map
from editorial import apply_pre_ranking, write_editorial_artifact
from editorial_judge import apply_judge
from judged_pool import record_run as record_judged_pool
from enrich import enrich_items, record_duplicate
from llm_label import label_items, load_cfg as load_llm_cfg
from llm_rerank import rerank_candidates

# Optional server-side operational telemetry. Never fatal.
try:
    import telemetry
except Exception:
    telemetry = None

ROOT = Path(__file__).resolve().parents[1]

# Keep the on-disk run snapshots bounded to the same window the index retains.
# The index was already capped, but the snapshot files themselves used to
# accumulate forever, bloating the repo and the deployed function bundle.
PROCESSED_RUNS_KEEP = 500


def prune_orphan_runs(runs_dir: Path, kept_rel_paths: set[str]) -> int:
    """Delete run snapshot files under runs_dir not present in kept_rel_paths."""
    if not runs_dir.exists():
        return 0
    removed = 0
    for p in runs_dir.glob("**/*.json"):
        rel = str(p.relative_to(runs_dir))
        if rel in kept_rel_paths:
            continue
        try:
            p.unlink()
            removed += 1
        except OSError:
            pass
    return removed


def atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass


def write_run_snapshot(items: list[dict[str, Any]], run_at: datetime | None = None) -> tuple[str, str]:
    """Persist per-run snapshot so web/API can accumulate historical runs.

    Returns: (iso_timestamp, filename)
    """
    ts = run_at or datetime.now(timezone.utc)
    run_at_iso = ts.isoformat()
    run_id = ts.strftime("%Y%m%d-%H%M%S")
    year = ts.strftime("%Y")
    month = ts.strftime("%m")

    processed_dir = ROOT / "data" / "processed"
    runs_dir = processed_dir / "runs" / year / month
    runs_dir.mkdir(parents=True, exist_ok=True)

    run_payload = {
        "run_at": run_at_iso,
        "item_count": len(items),
        "items": items,
    }

    run_file = runs_dir / f"{run_id}.json"
    run_rel_path = f"{year}/{month}/{run_file.name}"
    atomic_write_json(run_file, run_payload)

    index_file = processed_dir / "runs_index.json"
    try:
        index = json.loads(index_file.read_text(encoding="utf-8")) if index_file.exists() else []
        if not isinstance(index, list):
            index = []
    except Exception:
        index = []

    by_path: dict[str, dict[str, Any]] = {}
    for row in index:
        if not isinstance(row, dict):
            continue
        rel_path = row.get("path") or row.get("file")
        if rel_path:
            row["path"] = rel_path
            by_path[rel_path] = row

    # Backfill from runs directory recursively so index self-heals if truncated/corrupted.
    for p in sorted((processed_dir / "runs").glob("**/*.json")):
        rel_path = str(p.relative_to(processed_dir / "runs"))
        if rel_path in by_path:
            continue
        try:
            payload = json.loads(p.read_text(encoding="utf-8"))
            by_path[rel_path] = {
                "run_at": payload.get("run_at") or "",
                "path": rel_path,
                "item_count": int(payload.get("item_count", len(payload.get("items", []) or []))),
            }
        except Exception:
            continue

    by_path[run_rel_path] = {"run_at": run_at_iso, "path": run_rel_path, "item_count": len(items)}
    merged_index = sorted(by_path.values(), key=lambda x: x.get("run_at", ""), reverse=True)[:PROCESSED_RUNS_KEEP]
    atomic_write_json(index_file, merged_index)
    prune_orphan_runs(processed_dir / "runs", {row["path"] for row in merged_index if row.get("path")})

    return run_at_iso, run_rel_path


def load_profile() -> dict[str, Any]:
    with open(ROOT / "config" / "profile.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def latest_raw_file() -> Path:
    raw_root = ROOT / "data" / "raw"
    if not raw_root.exists():
        raise FileNotFoundError("No raw data found")
    days = sorted([p for p in raw_root.iterdir() if p.is_dir()])
    if not days:
        raise FileNotFoundError("No dated raw directories found")
    latest_day = days[-1]
    fp = latest_day / "items.json"
    if not fp.exists():
        raise FileNotFoundError(f"Missing {fp}")
    return fp


def load_items_for_tier0() -> tuple[list[dict[str, Any]], str, Path]:
    fp = latest_raw_file()
    return json.loads(fp.read_text(encoding="utf-8")), "raw", fp


def load_latest_processed_run_at() -> datetime | None:
    idx_file = ROOT / "data" / "processed" / "runs_index.json"
    if not idx_file.exists():
        return None
    try:
        idx = json.loads(idx_file.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(idx, list) or not idx:
        return None
    run_at = idx[0].get("run_at")
    if not run_at:
        return None
    try:
        d = datetime.fromisoformat(str(run_at).replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return d
    except Exception:
        return None


def parse_item_ts(it: dict[str, Any]) -> datetime | None:
    for k in ("collected_at", "published"):
        v = it.get(k)
        if not v:
            continue
        try:
            d = dt_parser.parse(str(v))
            if d.tzinfo is None:
                d = d.replace(tzinfo=timezone.utc)
            return d
        except Exception:
            continue
    return None


def load_source_health() -> dict[str, float]:
    p = ROOT / "data" / "health" / "source_health.json"
    if not p.exists():
        return {}
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    out = {}
    for src, row in payload.get("sources", {}).items():
        out[src] = float(row.get("reliability", 1.0))
    return out


def canonical_url(u: str) -> str:
    return u.split("?")[0].strip().lower()


def title_tokens(t: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", t.lower()))


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def dedupe(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_url: dict[str, dict[str, Any]] = {}
    for it in items:
        key = canonical_url(it["url"])
        prev = by_url.get(key)
        if prev is None:
            by_url[key] = it
        elif freshness_score(it.get("published", "")) > freshness_score(prev.get("published", "")):
            record_duplicate(it, prev)
            by_url[key] = it
        else:
            record_duplicate(prev, it)

    out: list[dict[str, Any]] = []
    signatures: list[set[str]] = []
    for it in sorted(by_url.values(), key=lambda x: freshness_score(x.get("published", "")), reverse=True):
        toks = title_tokens(it.get("title", ""))
        match_idx = next((i for i, prev_toks in enumerate(signatures) if jaccard(toks, prev_toks) >= 0.85), None)
        if match_idx is not None:
            # Same story under a near-identical title: keep the earliest
            # publication as the card (the original, e.g. a first-party post)
            # and list later echoes such as link-blog commentary as coverage.
            prev = out[match_idx]
            if freshness_score(it.get("published", "")) < freshness_score(prev.get("published", "")):
                record_duplicate(it, prev)
                out[match_idx] = it
            else:
                record_duplicate(prev, it)
            continue
        signatures.append(toks)
        out.append(it)
    return out


def freshness_score(published_str: str, decay_hours: float = 72.0) -> float:
    try:
        dt = dt_parser.parse(published_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    except Exception:
        dt = datetime.now(timezone.utc)
    age_hours = max((datetime.now(timezone.utc) - dt).total_seconds() / 3600.0, 0)
    return math.exp(-age_hours / decay_hours)


def keyword_hits(text: str, keywords: list[str]) -> int:
    t = text.lower()
    return sum(1 for k in keywords if re.search(rf"\b{re.escape(k.lower())}\b", t))


def maturity_label(text: str) -> str:
    t = text.lower()
    if any(x in t for x in ["benchmark", "production", "release", "ga", "stable"]):
        return "production-ready"
    if any(x in t for x in ["preview", "beta", "experimental", "prototype"]):
        return "emerging"
    return "research"


def signal_type(item: dict[str, Any]) -> str:
    s = item.get("source", "").lower()
    t = item.get("title", "").lower()
    if "arxiv" in s or "paper" in s or "paperswithcode" in s:
        return "paper"
    if "release" in s or "release" in t:
        return "release"
    return "news"


def why_it_matters(tags: list[str]) -> str:
    if not tags:
        return ""
    return f"Likely impact on {', '.join(tags[:3])} workflows and platform decisions."


def balanced_select(items: list[dict[str, Any]], max_items: int, diversity: dict[str, Any]) -> list[dict[str, Any]]:
    if not diversity.get("enabled", False):
        return items[:max_items]

    min_per_type = diversity.get("min_per_type", {})
    max_per_type = diversity.get("max_per_type", {})
    target_mix = diversity.get("target_mix", {"paper": 0.33, "news": 0.33, "release": 0.34})

    by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for it in items:
        by_type[it.get("type", "news")].append(it)

    selected: list[dict[str, Any]] = []
    counts = defaultdict(int)

    type_order = [k for k, _ in sorted(target_mix.items(), key=lambda kv: kv[1], reverse=True)]
    if not type_order:
        type_order = ["paper", "news", "release"]

    # Phase 1: enforce minimum per type (when enough candidates exist)
    for t in type_order:
        required = int(min_per_type.get(t, 0))
        cap = int(max_per_type.get(t, max_items))
        target = min(required, cap)
        while len(selected) < max_items and counts[t] < target and by_type.get(t):
            selected.append(by_type[t].pop(0))
            counts[t] += 1

    # Phase 2: round-robin by target mix while respecting caps
    while len(selected) < max_items:
        progressed = False
        for t in type_order:
            if len(selected) >= max_items:
                break
            cap = int(max_per_type.get(t, max_items))
            if counts[t] >= cap:
                continue
            if by_type.get(t):
                selected.append(by_type[t].pop(0))
                counts[t] += 1
                progressed = True
        if not progressed:
            break

    # Phase 3: fill by absolute top leftovers under caps
    if len(selected) < max_items:
        leftovers = []
        for t_items in by_type.values():
            leftovers.extend(t_items)
        leftovers.sort(key=lambda x: x["score"], reverse=True)
        for it in leftovers:
            if len(selected) >= max_items:
                break
            t = it.get("type", "news")
            cap = int(max_per_type.get(t, max_items))
            if counts[t] < cap:
                selected.append(it)
                counts[t] += 1

    return selected


def apply_source_cap(
    selected: list[dict[str, Any]],
    eligible: list[dict[str, Any]],
    max_items: int,
    max_per_source: int,
    max_per_type: dict[str, int] | None = None,
) -> list[dict[str, Any]]:
    if max_per_source <= 0:
        return selected[:max_items]

    out = []
    source_counts = defaultdict(int)
    type_counts = defaultdict(int)
    max_per_type = max_per_type or {}

    for it in selected:
        src = it.get("source", "")
        typ = it.get("type", "news")
        if source_counts[src] >= max_per_source:
            continue
        if max_per_type and type_counts[typ] >= int(max_per_type.get(typ, max_items)):
            continue
        out.append(it)
        source_counts[src] += 1
        type_counts[typ] += 1

    if len(out) < max_items:
        for it in eligible:
            if len(out) >= max_items:
                break
            if it in out:
                continue
            src = it.get("source", "")
            typ = it.get("type", "news")
            if source_counts[src] >= max_per_source:
                continue
            if max_per_type and type_counts[typ] >= int(max_per_type.get(typ, max_items)):
                continue
            out.append(it)
            source_counts[src] += 1
            type_counts[typ] += 1

    return out[:max_items]


def apply_preferred_source_slots(
    selected: list[dict[str, Any]],
    eligible: list[dict[str, Any]],
    preferred_sources: list[str],
    min_slots: int,
    max_items: int,
) -> list[dict[str, Any]]:
    if not preferred_sources or min_slots <= 0:
        return selected[:max_items]

    preferred_set = set(preferred_sources)
    out = list(selected[:max_items])
    have = sum(1 for it in out if it.get("source") in preferred_set)
    if have >= min_slots:
        return out

    candidates = [it for it in eligible if it.get("source") in preferred_set and it not in out]
    candidates.sort(key=lambda x: x.get("score", 0), reverse=True)

    for cand in candidates:
        if have >= min_slots:
            break
        if len(out) < max_items:
            out.append(cand)
            have += 1
            continue

        # Replace lowest-ranked non-preferred item
        replace_idx = None
        for i in range(len(out) - 1, -1, -1):
            if out[i].get("source") not in preferred_set:
                replace_idx = i
                break
        if replace_idx is None:
            break
        out[replace_idx] = cand
        have += 1

    # keep deterministic order by score after injection
    out.sort(key=lambda x: x.get("score", 0), reverse=True)
    return out[:max_items]


def apply_constrained_topk(
    selected: list[dict[str, Any]],
    eligible: list[dict[str, Any]],
    max_items: int,
    top_k: int,
    max_release_in_top_k: int,
    max_same_source_in_top_k: int,
    frontier_sources: list[str],
    min_frontier_slots: int,
    agent_release_sources: list[str],
    min_agent_release_slots: int,
    deprioritized_sources: list[str],
    max_deprioritized_slots: int,
) -> list[dict[str, Any]]:
    top_k = max(0, min(top_k, max_items))
    if top_k == 0:
        return selected[:max_items]

    pool = []
    for x in (selected + eligible):
        if x not in pool:
            pool.append(x)
    pool.sort(key=lambda x: x.get("score", 0), reverse=True)

    frontier = set(frontier_sources or [])
    agent_rel = set(agent_release_sources or [])
    depr = set(deprioritized_sources or [])

    top = []
    rel_count = 0
    src_count = defaultdict(int)

    def count(rows, src_set):
        return sum(1 for r in rows if r.get("source") in src_set)

    for cand in pool:
        if len(top) >= top_k:
            break
        src = cand.get("source", "")
        typ = cand.get("type", "news")
        if src_count[src] >= max_same_source_in_top_k:
            continue
        if typ == "release" and rel_count >= max_release_in_top_k:
            continue
        if src in depr and count(top, depr) >= max_deprioritized_slots:
            continue
        top.append(cand)
        src_count[src] += 1
        if typ == "release":
            rel_count += 1

    def enforce_floor(src_set: set[str], minimum: int):
        nonlocal top
        if minimum <= 0 or not src_set:
            return
        while count(top, src_set) < minimum:
            cand = next((x for x in pool if x.get("source") in src_set and x not in top), None)
            if cand is None:
                break
            idx = next((i for i in range(len(top)-1, -1, -1) if top[i].get("source") not in src_set), None)
            if idx is None:
                break
            top[idx] = cand

    enforce_floor(frontier, int(min_frontier_slots))
    enforce_floor(agent_rel, int(min_agent_release_slots))

    out = list(top)
    for x in selected:
        if len(out) >= max_items:
            break
        if x not in out:
            out.append(x)
    for x in pool:
        if len(out) >= max_items:
            break
        if x not in out:
            out.append(x)
    return out[:max_items]


def apply_top_guardrails(
    selected: list[dict[str, Any]],
    eligible: list[dict[str, Any]],
    top_k: int,
    max_release_in_top_k: int,
    max_same_source_in_top_k: int,
) -> list[dict[str, Any]]:
    if top_k <= 0:
        return selected

    # Candidate pool by score (selected first preference, then eligible)
    pool = []
    for x in (selected + eligible):
        if x not in pool:
            pool.append(x)
    pool.sort(key=lambda x: x.get("score", 0), reverse=True)

    top = []
    rel_count = 0
    src_count = defaultdict(int)

    for cand in pool:
        if len(top) >= top_k:
            break
        src = cand.get("source", "")
        typ = cand.get("type", "news")
        if src_count[src] >= max_same_source_in_top_k:
            continue
        if typ == "release" and rel_count >= max_release_in_top_k:
            continue
        top.append(cand)
        src_count[src] += 1
        if typ == "release":
            rel_count += 1

    # Fill any remaining top slots without constraints to avoid gaps
    if len(top) < top_k:
        for cand in pool:
            if len(top) >= top_k:
                break
            if cand in top:
                continue
            top.append(cand)

    # Rebuild remainder preserving selected order as much as possible, keep original length
    target_len = len(selected)
    merged = []
    for x in top + selected:
        if x not in merged:
            merged.append(x)
        if len(merged) >= target_len:
            break
    return merged


def enforce_source_floor(
    selected: list[dict[str, Any]],
    pool: list[dict[str, Any]],
    source_set: set[str],
    min_slots: int,
) -> list[dict[str, Any]]:
    if not source_set or min_slots <= 0:
        return selected

    out = list(selected)
    have = sum(1 for it in out if it.get("source") in source_set)
    if have >= min_slots:
        return out

    candidates = [x for x in pool if x.get("source") in source_set and x not in out]
    candidates.sort(key=lambda x: x.get("score", 0), reverse=True)

    for cand in candidates:
        if have >= min_slots:
            break
        # replace lowest-scored non-target
        replace_idx = None
        for i in range(len(out) - 1, -1, -1):
            if out[i].get("source") not in source_set:
                replace_idx = i
                break
        if replace_idx is None:
            break
        out[replace_idx] = cand
        have += 1

    return out


def apply_topk_source_mix(
    selected: list[dict[str, Any]],
    pool: list[dict[str, Any]],
    top_k: int,
    priority_sources: list[str],
    min_priority_slots: int,
    deprioritized_sources: list[str],
    max_deprioritized_slots: int,
) -> list[dict[str, Any]]:
    if top_k <= 0:
        return selected

    out = list(selected)
    top = out[:top_k]
    tail = out[top_k:]

    pri = set(priority_sources or [])
    dep = set(deprioritized_sources or [])

    def count_priority(rows):
        return sum(1 for x in rows if x.get("source") in pri)

    def count_deprioritized(rows):
        return sum(1 for x in rows if x.get("source") in dep)

    ranked_pool = sorted(pool, key=lambda x: x.get("score", 0), reverse=True)

    # enforce minimum priority slots in top-k
    while count_priority(top) < int(min_priority_slots):
        cand = next((x for x in ranked_pool if x.get("source") in pri and x not in top), None)
        if cand is None:
            break
        idx = next((i for i in range(len(top) - 1, -1, -1) if top[i].get("source") not in pri), None)
        if idx is None:
            break
        top[idx] = cand

    # cap deprioritized slots in top-k
    while count_deprioritized(top) > int(max_deprioritized_slots):
        idx = next((i for i in range(len(top) - 1, -1, -1) if top[i].get("source") in dep), None)
        if idx is None:
            break
        cand = next((x for x in ranked_pool if x.get("source") not in dep and x not in top), None)
        if cand is None:
            break
        top[idx] = cand

    return top + tail


def apply_category_allocation(
    selected: list[dict[str, Any]],
    pool: list[dict[str, Any]],
    max_items: int,
    alloc_cfg: dict[str, Any],
) -> list[dict[str, Any]]:
    if not alloc_cfg.get("enabled", False):
        return selected[:max_items]

    order = alloc_cfg.get("order", ["platform", "release", "research"])
    min_q = alloc_cfg.get("min", {})
    max_q = alloc_cfg.get("max", {})

    def cat(it: dict[str, Any]) -> str:
        c = (it.get("llm_category") or "").lower().strip()
        if c in {"platform", "release", "research"}:
            return c
        t = it.get("type", "news")
        if t == "release":
            return "release"
        if t == "paper":
            return "research"
        return "platform"

    ranked = []
    for x in (selected + pool):
        if x not in ranked:
            ranked.append(x)
    ranked.sort(key=lambda x: x.get("score", 0), reverse=True)

    by_cat = {"platform": [], "release": [], "research": []}
    for it in ranked:
        by_cat.setdefault(cat(it), []).append(it)

    out: list[dict[str, Any]] = []
    counts = {"platform": 0, "release": 0, "research": 0}

    # satisfy minimums first
    for c in order:
        need = int(min_q.get(c, 0))
        cap = int(max_q.get(c, max_items))
        target = min(need, cap)
        while counts.get(c, 0) < target and by_cat.get(c):
            it = by_cat[c].pop(0)
            if it in out:
                continue
            out.append(it)
            counts[c] = counts.get(c, 0) + 1
            if len(out) >= max_items:
                return out[:max_items]

    # fill remaining respecting max caps
    for it in ranked:
        if len(out) >= max_items:
            break
        if it in out:
            continue
        c = cat(it)
        cap = int(max_q.get(c, max_items))
        if counts.get(c, 0) >= cap:
            continue
        out.append(it)
        counts[c] = counts.get(c, 0) + 1

    return out[:max_items]


def run():
    profile = load_profile()
    items, input_mode, input_file = load_items_for_tier0()
    print(f"tier0_input_mode={input_mode} file={input_file}")

    incr_enabled = str(os.getenv("TIER0_INCREMENTAL", "1")).strip().lower() in {"1", "true", "yes"}
    skip_no_delta = str(os.getenv("TIER0_INCREMENTAL_SKIP_NO_DELTA", "0")).strip().lower() in {"1", "true", "yes"}
    if incr_enabled:
        prev_run_at = load_latest_processed_run_at()
        if prev_run_at is None:
            print("tier0_incremental prev_run_at=none delta_items=unknown")
        else:
            delta_count = 0
            for it in items:
                d = parse_item_ts(it)
                if d is not None and d > prev_run_at:
                    delta_count += 1
            print(f"tier0_incremental prev_run_at={prev_run_at.isoformat()} delta_items={delta_count} total_items={len(items)}")
            if skip_no_delta and delta_count == 0:
                print("tier0_incremental_skip=true reason=no_delta")
                if telemetry is not None:
                    telemetry.capture(
                        "feed_build_skipped",
                        {
                            "reason": "no_delta",
                            "delta_count": delta_count,
                            "total_items": len(items),
                            "input_mode": input_mode,
                        },
                    )
                return

    items = enrich_items(items)
    items = dedupe(items)
    items, editorial_diag = apply_pre_ranking(items)
    items_deduped = list(items)
    print(
        "editorial_stats "
        f"in={editorial_diag.get('input', 0)} out={editorial_diag.get('output', 0)} "
        f"search_in={editorial_diag.get('search_in', 0)} "
        f"search_low_quality={editorial_diag.get('search_dropped_low_quality', 0)} "
        f"search_non_latin={editorial_diag.get('search_dropped_non_latin', 0)} "
        f"search_over_cap={editorial_diag.get('search_dropped_over_cap', 0)} "
        f"first_party_low_value={editorial_diag.get('first_party_dropped_low_value', 0)} "
        f"clusters={editorial_diag.get('clusters', 0)} "
        f"collapsed={editorial_diag.get('collapsed', 0)} "
        f"seen_dropped={editorial_diag.get('seen_dropped', 0)} "
        f"seen_penalized={editorial_diag.get('seen_penalized', 0)}"
    )
    source_health = load_source_health()

    # Unified ranking pipeline (single canonical path).
    try:
        from ranking import run_ranking

        judged_pool_candidates: list[dict[str, Any]] = []
        ranked_items, ranking_diag = run_ranking(
            items_deduped,
            profile,
            load_llm_cfg(),
            source_health,
            judge_fn=apply_judge,
            pool_sink=judged_pool_candidates.extend,
        )
        ranking_diag["editorial"] = editorial_diag
        judge_diag = ranking_diag.get("judge", {}) or {}
        print(
            "judge_stats "
            f"enabled={int(bool(judge_diag.get('enabled')))} "
            f"selected={judge_diag.get('selected', 0)} "
            f"judged={judge_diag.get('judged', 0)} "
            f"cached={judge_diag.get('cached', 0)} "
            f"store_hits={judge_diag.get('store_hits', 0)} "
            f"store_misses={judge_diag.get('store_misses', 0)} "
            f"store_entries={judge_diag.get('store_entries', 0)} "
            f"content_fetched={judge_diag.get('content_fetched', 0)} "
            f"video_items={judge_diag.get('video_items', 0)} "
            f"transcript_fetched={judge_diag.get('transcript_fetched', 0)} "
            f"transcript_missing={judge_diag.get('transcript_missing', 0)} "
            f"insufficient_evidence={judge_diag.get('insufficient_evidence', 0)} "
            f"errors={judge_diag.get('errors', 0)} "
            f"downgraded={judge_diag.get('downgraded', 0)} "
            f"verdicts={judge_diag.get('verdicts', {})} "
            f"categories={judge_diag.get('categories', {})} "
            f"reason={judge_diag.get('reason', 'ok')}"
        )

        processed_dir = ROOT / "data" / "processed"
        processed_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_json(processed_dir / "latest.json", ranked_items)
        write_editorial_artifact(editorial_diag)

        date_str = datetime.now().strftime("%Y-%m-%d")
        diag_dir = ROOT / "data" / "diagnostics"
        diag_dir.mkdir(parents=True, exist_ok=True)
        with open(diag_dir / f"{date_str}_ranking.json", "w", encoding="utf-8") as f:
            json.dump(ranking_diag, f, ensure_ascii=False, indent=2)

        lines = [
            f"# Daily AI SOTA Digest - {date_str}",
            "",
            "Focus: AI Platform Engineering",
            "",
        ]
        for i, it in enumerate(ranked_items, start=1):
            lines += [
                f"## {i}. {it.get('title','')}",
                f"- Type: {it.get('type','news')} | Source: {it.get('source','unknown')}",
                f"- URL: {it.get('url','')}",
                f"- Score: {it.get('global_score', it.get('final_score', it.get('score', 0)))} | Reliability: {it.get('source_reliability', 1.0)}",
                f"- Why it matters: {it.get('why_it_matters', '')}",
                "",
            ]

        digest_dir = ROOT / "data" / "digest"
        digest_dir.mkdir(parents=True, exist_ok=True)
        out = digest_dir / f"{date_str}.md"
        with open(out, "w", encoding="utf-8") as f:
            f.write("\n".join(lines).strip() + "\n")
        with open(digest_dir / "latest.md", "w", encoding="utf-8") as f:
            f.write("\n".join(lines).strip() + "\n")

        run_at_iso, run_file = write_run_snapshot(ranked_items)
        print(f"digest_items={len(ranked_items)} file={out} run_at={run_at_iso} run_file={run_file}")
        pool_diag = record_judged_pool(judged_pool_candidates, ranked_items, run_at=run_at_iso)
        print(
            "judged_pool "
            f"written={int(bool(pool_diag.get('written')))} "
            f"items={pool_diag.get('items', 0)} "
            f"run_candidates={pool_diag.get('run_candidates', 0)} "
            f"in_edition={pool_diag.get('in_edition', 0)} "
            f"judged={pool_diag.get('judged', 0)} "
            f"reason={pool_diag.get('reason', 'ok')}"
        )
        ledger_diag = record_brief_ledger(judged_pool_candidates, ranked_items, run_at=run_at_iso)
        print(
            "brief_ledger "
            f"written={int(bool(ledger_diag.get('written')))} "
            f"items={ledger_diag.get('items', 0)} "
            f"new={ledger_diag.get('new', 0)} "
            f"updated={ledger_diag.get('updated', 0)} "
            f"candidates={ledger_diag.get('candidates', 0)} "
            f"stories={ledger_diag.get('stories', 0)} "
            f"rejected_gate={ledger_diag.get('rejected_gate', {})} "
            f"rejected_quota={ledger_diag.get('rejected_quota', {})} "
            f"reason={ledger_diag.get('reason', 'ok')}"
        )
        if telemetry is not None:
            telemetry.capture(
                "feed_build_completed",
                {
                    "digest_items": len(ranked_items),
                    "input_mode": input_mode,
                    "run_at": run_at_iso,
                    "date": date_str,
                    "ledger_items": int(ledger_diag.get("items", 0) or 0),
                    "ledger_new": int(ledger_diag.get("new", 0) or 0),
                    "ledger_updated": int(ledger_diag.get("updated", 0) or 0),
                    "ledger_written": bool(ledger_diag.get("written")),
                    "ledger_reason": str(ledger_diag.get("reason") or "ok"),
                    "ledger_rejected_gate": ledger_diag.get("rejected_gate") or {},
                    "ledger_rejected_quota": ledger_diag.get("rejected_quota") or {},
                    "ledger_role_counts": ledger_diag.get("role_counts") or {},
                },
            )
        return
    except Exception as e:
        print(f"ranking_pipeline_error err={e}")
        raise RuntimeError(f"ranking_pipeline_error err={e}")


if __name__ == "__main__":
    run()
