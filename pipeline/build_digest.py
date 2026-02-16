from __future__ import annotations

import json
import math
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from dateutil import parser as dt_parser

from content_fetch import build_content_map
from llm_label import label_items, load_cfg as load_llm_cfg
from llm_rerank import rerank_candidates

ROOT = Path(__file__).resolve().parents[1]


def write_run_snapshot(items: list[dict[str, Any]], run_at: datetime | None = None) -> tuple[str, str]:
    """Persist per-run snapshot so web/API can accumulate historical runs.

    Returns: (iso_timestamp, filename)
    """
    ts = run_at or datetime.now(timezone.utc)
    run_at_iso = ts.isoformat()
    run_id = ts.strftime("%Y%m%d-%H%M%S")

    processed_dir = ROOT / "data" / "processed"
    runs_dir = processed_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    run_payload = {
        "run_at": run_at_iso,
        "item_count": len(items),
        "items": items,
    }

    run_file = runs_dir / f"{run_id}.json"
    with open(run_file, "w", encoding="utf-8") as f:
        json.dump(run_payload, f, ensure_ascii=False, indent=2)

    index_file = processed_dir / "runs_index.json"
    try:
        index = json.loads(index_file.read_text(encoding="utf-8")) if index_file.exists() else []
        if not isinstance(index, list):
            index = []
    except Exception:
        index = []

    index.append({"run_at": run_at_iso, "file": run_file.name, "item_count": len(items)})
    index = sorted(index, key=lambda x: x.get("run_at", ""), reverse=True)[:500]
    with open(index_file, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    return run_at_iso, run_file.name


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
        if prev is None or float(it.get("source_weight", 1.0)) > float(prev.get("source_weight", 1.0)):
            by_url[key] = it

    out: list[dict[str, Any]] = []
    signatures: list[set[str]] = []
    for it in sorted(by_url.values(), key=lambda x: float(x.get("source_weight", 1.0)), reverse=True):
        toks = title_tokens(it.get("title", ""))
        if any(jaccard(toks, prev_toks) >= 0.85 for prev_toks in signatures):
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
    raw_file = latest_raw_file()

    with open(raw_file, "r", encoding="utf-8") as f:
        items = json.load(f)

    items = dedupe(items)
    items_deduped = list(items)

    pkw = profile.get("platform_keywords", [])
    hkw = profile.get("hype_keywords", [])
    w = profile.get("weights", {})
    decay = float(w.get("freshness_hours_decay", 72))
    source_health = load_source_health()

    # v2 full switch path
    try:
        from ranking_v2 import load_v2_config, run_v2

        v2_cfg = load_v2_config()
        if bool(v2_cfg.get("enabled", False)):
            v2_items, v2_diag = run_v2(items_deduped, profile, load_llm_cfg(), source_health)

            processed_dir = ROOT / "data" / "processed"
            processed_dir.mkdir(parents=True, exist_ok=True)
            with open(processed_dir / "latest.json", "w", encoding="utf-8") as f:
                json.dump(v2_items, f, ensure_ascii=False, indent=2)

            with open(processed_dir / "latest_v2.json", "w", encoding="utf-8") as f:
                json.dump(v2_items, f, ensure_ascii=False, indent=2)

            date_str = datetime.now().strftime("%Y-%m-%d")
            diag_dir = ROOT / "data" / "diagnostics"
            diag_dir.mkdir(parents=True, exist_ok=True)
            with open(diag_dir / f"{date_str}_v2.json", "w", encoding="utf-8") as f:
                json.dump(v2_diag, f, ensure_ascii=False, indent=2)

            lines = [
                f"# Daily AI SOTA Digest - {date_str}",
                "",
                "Focus: AI Platform Engineering",
                "",
            ]
            for i, it in enumerate(v2_items, start=1):
                lines += [
                    f"## {i}. {it.get('title','')}",
                    f"- Type: {it.get('type','news')} | Source: {it.get('source','unknown')}",
                    f"- URL: {it.get('url','')}",
                    f"- Score: {it.get('v2_final_score', it.get('score', 0))} | Reliability: {it.get('source_reliability', 1.0)}",
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
            with open(digest_dir / f"{date_str}_v2.md", "w", encoding="utf-8") as f:
                f.write("\n".join(lines).strip() + "\n")
            with open(digest_dir / "latest_v2.md", "w", encoding="utf-8") as f:
                f.write("\n".join(lines).strip() + "\n")

            run_at_iso, run_file = write_run_snapshot(v2_items)
            print(f"digest_items={len(v2_items)} file={out} run_at={run_at_iso} run_file={run_file}")
            return
    except Exception as e:
        print(f"ranking_v2_switch_error err={e}")

    scored = []
    exclude_title_regex = profile.get("selection", {}).get("exclude_title_regex", [])
    type_bonus_cfg = profile.get("type_bonus", {})
    for it in items:
        title = it.get('title', '')
        if any(re.search(pat, title) for pat in exclude_title_regex):
            continue
        text = f"{title} {it.get('summary', '')}"
        platform_hits = keyword_hits(text, pkw)
        hype_hits = keyword_hits(text, hkw)
        fresh = freshness_score(it.get("published", ""), decay)

        item_type = signal_type(it)
        src_rel = float(source_health.get(it.get("source", ""), 1.0))
        # Heuristic keyword/type boosting removed; keep baseline score simple.
        score = (
            float(it.get("source_weight", 1.0)) * float(w.get("source_weight", 1.0))
            + fresh
            + src_rel * float(w.get("source_reliability", 1.0))
        )

        tags = [k for k in pkw if re.search(rf"\b{re.escape(k)}\b", text.lower())][:5]

        scored.append(
            {
                **it,
                "type": item_type,
                "score": round(score, 3),
                "source_reliability": round(src_rel, 3),
                "freshness": round(fresh, 3),
                "platform_hits": platform_hits,
                "hype_hits": hype_hits,
                "maturity": maturity_label(text),
                "tags": tags,
                "why_it_matters": why_it_matters(tags),
            }
        )

    llm_cfg = load_llm_cfg()
    label_top_n = int(llm_cfg.get("label_top_n", 20))
    pre_sorted = sorted(scored, key=lambda x: x["score"], reverse=True)

    if bool(llm_cfg.get("content_fetch_enabled", True)):
        fetch_n = int(llm_cfg.get("content_fetch_top_n", max(label_top_n, int(llm_cfg.get("rerank_top_n", 40)))))
        excerpt_chars = int(llm_cfg.get("content_excerpt_chars", 1200))
        fetch_timeout = int(llm_cfg.get("content_fetch_timeout_seconds", 10))
        fetch_budget = int(llm_cfg.get("content_fetch_time_budget_seconds", 25))
        content_map = build_content_map(
            pre_sorted,
            top_n=fetch_n,
            excerpt_chars=excerpt_chars,
            timeout=fetch_timeout,
            time_budget_seconds=fetch_budget,
        )
        for it in pre_sorted:
            u = (it.get("url", "") or "").split("#")[0].strip()
            if u in content_map:
                it["content_excerpt"] = content_map[u]

    label_budget = min(len(pre_sorted), max(label_top_n, int(profile.get("max_digest_items", 10))))
    labels = label_items(pre_sorted[:label_budget])

    llm_used = 0
    heuristic_used = 0

    for it in scored:
        key = it.get("id") or f"{it.get('source')}::{it.get('url')}"
        lb = labels.get(key, {})
        src = lb.get("__label_source", "heuristic")
        if src == "llm":
            llm_used += 1
        else:
            heuristic_used += 1

        it["llm_platform_relevant"] = bool(lb.get("platform_relevant", True))
        it["llm_novelty"] = int(lb.get("novelty", 3))
        it["llm_practicality"] = int(lb.get("practicality", 3))
        it["llm_hype"] = int(lb.get("hype", 2))
        llm_cat = str(lb.get("category", "")).strip().lower()
        if llm_cat not in {"platform", "release", "research"}:
            typ = (it.get("type") or "news").lower()
            llm_cat = "release" if typ == "release" else ("research" if typ == "paper" else "platform")
        it["llm_category"] = llm_cat
        it["llm_summary_1line"] = str(lb.get("summary_1line", "")).strip()
        it["llm_why_1line"] = lb.get("why_1line", "")
        it["llm_label_source"] = src

        it["score"] = round(
            float(it["score"])
            + (0.6 if it["llm_platform_relevant"] else -0.6)
            + (it["llm_practicality"] - 3) * 0.4
            + (it["llm_novelty"] - 3) * 0.2
            - max(0, it["llm_hype"] - 3) * 0.4,
            3,
        )
        if it["llm_summary_1line"]:
            it["summary_1line"] = it["llm_summary_1line"]
        else:
            s = str(it.get("summary", "") or "").strip()
            it["summary_1line"] = (s[:137].rstrip() + "...") if len(s) > 140 else s

        if it["llm_why_1line"] and src == "llm":
            it["why_it_matters"] = it["llm_why_1line"]

    scored.sort(key=lambda x: x["score"], reverse=True)
    print(f"label_stats llm={llm_used} heuristic={heuristic_used} label_top_n={label_top_n} label_budget={label_budget}")

    max_items = int(profile.get("max_digest_items", 10))
    min_score = float(profile.get("min_score", 1.0))
    eligible = [
        x
        for x in scored
        if x["score"] >= min_score and (x.get("llm_platform_relevant", True) or x["score"] >= (min_score + 1.5))
    ]
    diversity_cfg = profile.get("diversity", {})
    llm_cfg = load_llm_cfg()
    quotas = {
        "min": diversity_cfg.get("min_per_type", {}),
        "max": diversity_cfg.get("max_per_type", {}),
    }

    top = rerank_candidates(eligible, llm_cfg, max_items, quotas)
    if not top:
        top = balanced_select(eligible, max_items, diversity_cfg)

    sel_cfg = profile.get("selection", {})
    max_per_source = int(sel_cfg.get("max_per_source", 0))
    top = apply_source_cap(top, eligible, max_items, max_per_source, diversity_cfg.get("max_per_type", {}))

    top = apply_constrained_topk(
        top,
        eligible,
        max_items=max_items,
        top_k=int(sel_cfg.get("top_k_guardrail", 5)),
        max_release_in_top_k=int(sel_cfg.get("max_release_in_top_k", 1)),
        max_same_source_in_top_k=int(sel_cfg.get("max_same_source_in_top_k", 1)),
        frontier_sources=list(sel_cfg.get("frontier_blog_sources", [])),
        min_frontier_slots=int(sel_cfg.get("min_frontier_blog_slots", 0)),
        agent_release_sources=list(sel_cfg.get("agent_app_release_sources", [])),
        min_agent_release_slots=int(sel_cfg.get("min_agent_app_release_slots", 0)),
        deprioritized_sources=list(sel_cfg.get("top_k_deprioritized_sources", [])),
        max_deprioritized_slots=int(sel_cfg.get("max_top_k_deprioritized_slots", 99)),
    )

    top = enforce_source_floor(
        top,
        eligible,
        set(sel_cfg.get("anthropic_sources", [])),
        int(sel_cfg.get("min_anthropic_slots", 0)),
    )

    top = apply_category_allocation(
        top,
        eligible,
        max_items=max_items,
        alloc_cfg=sel_cfg.get("category_allocation", {}),
    )

    # Re-apply source cap after category allocation to avoid same-source pileups.
    top = apply_source_cap(top, eligible, max_items, max_per_source, diversity_cfg.get("max_per_type", {}))

    # v2 ranking path (feature-flagged). Shadow mode writes v2 artifacts without replacing publish path.
    v2_items = None
    v2_shadow_mode = True
    try:
        from ranking_v2 import load_v2_config, run_v2

        v2_cfg = load_v2_config()
        if bool(v2_cfg.get("enabled", False)):
            v2_shadow_mode = bool(v2_cfg.get("shadow_mode", True))
            v2_items, v2_diag = run_v2(items_deduped, profile, llm_cfg, source_health)

            processed_dir_v2 = ROOT / "data" / "processed"
            processed_dir_v2.mkdir(parents=True, exist_ok=True)
            with open(processed_dir_v2 / "latest_v2.json", "w", encoding="utf-8") as f:
                json.dump(v2_items, f, ensure_ascii=False, indent=2)

            date_str_v2 = datetime.now().strftime("%Y-%m-%d")
            diag_dir = ROOT / "data" / "diagnostics"
            diag_dir.mkdir(parents=True, exist_ok=True)
            with open(diag_dir / f"{date_str_v2}_v2.json", "w", encoding="utf-8") as f:
                json.dump(v2_diag, f, ensure_ascii=False, indent=2)

            if not bool(v2_cfg.get("shadow_mode", True)):
                top = v2_items
    except Exception as e:
        print(f"ranking_v2_error err={e}")

    processed_dir = ROOT / "data" / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    with open(processed_dir / "latest.json", "w", encoding="utf-8") as f:
        json.dump(top, f, ensure_ascii=False, indent=2)

    date_str = datetime.now().strftime("%Y-%m-%d")
    lines = [
        f"# Daily AI SOTA Digest - {date_str}",
        "",
        "Focus: AI Platform Engineering",
        "",
    ]

    for i, it in enumerate(top, start=1):
        lines += [
            f"## {i}. {it['title']}",
            f"- Type: {it['type']} | Source: {it['source']}",
            f"- URL: {it['url']}",
            f"- Score: {it['score']} | Reliability: {it['source_reliability']} | Maturity: {it['maturity']}",
            f"- Tags: {', '.join(it['tags']) if it['tags'] else 'n/a'}",
            f"- Why it matters: {it['why_it_matters']}",
            "",
        ]

    digest_dir = ROOT / "data" / "digest"
    digest_dir.mkdir(parents=True, exist_ok=True)
    out = digest_dir / f"{date_str}.md"
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines).strip() + "\n")
    with open(digest_dir / "latest.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines).strip() + "\n")

    if v2_items is not None and v2_shadow_mode:
        lines_v2 = [
            f"# Daily AI SOTA Digest (v2-shadow) - {date_str}",
            "",
            "Focus: AI Platform Engineering",
            "",
        ]
        for i, it in enumerate(v2_items, start=1):
            lines_v2 += [
                f"## {i}. {it.get('title','')}",
                f"- Type: {it.get('type','news')} | Source: {it.get('source','unknown')}",
                f"- URL: {it.get('url','')}",
                f"- Score: {it.get('v2_final_score', it.get('score', 0))} | Reliability: {it.get('source_reliability', 1.0)}",
                f"- Why it matters: {it.get('why_it_matters', '')}",
                "",
            ]
        with open(digest_dir / f"{date_str}_v2.md", "w", encoding="utf-8") as f:
            f.write("\n".join(lines_v2).strip() + "\n")
        with open(digest_dir / "latest_v2.md", "w", encoding="utf-8") as f:
            f.write("\n".join(lines_v2).strip() + "\n")

    run_at_iso, run_file = write_run_snapshot(top)
    print(f"digest_items={len(top)} file={out} run_at={run_at_iso} run_file={run_file}")


if __name__ == "__main__":
    run()
