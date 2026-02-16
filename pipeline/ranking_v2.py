from __future__ import annotations

import json
import math
import re
import html
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from dateutil import parser as dt_parser

try:
    from llm_label import label_items_v2
except Exception:
    from pipeline.llm_label import label_items_v2

ROOT = Path(__file__).resolve().parents[1]
V2_CFG_FILE = ROOT / "config" / "ranking_v2.yaml"
PRESETS_DIR = ROOT / "config" / "presets"


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_v2_config() -> dict[str, Any]:
    if not V2_CFG_FILE.exists():
        return {"enabled": False}
    raw = yaml.safe_load(V2_CFG_FILE.read_text(encoding="utf-8")) or {"enabled": False}

    preset_name = raw.get("preset")
    if not preset_name:
        return raw

    preset_file = PRESETS_DIR / f"{preset_name}.yaml"
    if not preset_file.exists():
        print(f"ranking_v2_preset_missing name={preset_name}")
        return raw

    preset_cfg = yaml.safe_load(preset_file.read_text(encoding="utf-8")) or {}
    merged = _deep_merge(preset_cfg, raw)
    return merged


def _age_hours(published_str: str) -> float:
    try:
        dt = dt_parser.parse(published_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    except Exception:
        return 0.0
    return max((datetime.now(timezone.utc) - dt).total_seconds() / 3600.0, 0.0)


def _freshness_score(published_str: str, decay_hours: float = 24.0) -> float:
    age = _age_hours(published_str)
    return math.exp(-age / max(1.0, decay_hours))


def _build_source_slot_map(v2_cfg: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for slot, scfg in (v2_cfg.get("slots", {}) or {}).items():
        for s in scfg.get("sources", []) or []:
            out[s] = slot
    return out


def stage_a_prefilter(items: list[dict[str, Any]], v2_cfg: dict[str, Any], profile: dict[str, Any], source_health: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    src_to_slot = _build_source_slot_map(v2_cfg)
    slots = v2_cfg.get("slots", {}) or {}
    exclude_title_regex = profile.get("selection", {}).get("exclude_title_regex", [])
    cap = int(v2_cfg.get("candidate_pool_cap", 100))

    out: list[dict[str, Any]] = []
    reasons = defaultdict(int)

    for it in items:
        title = it.get("title", "")
        if any(re.search(pat, title) for pat in exclude_title_regex):
            reasons["hard_exclude"] += 1
            continue

        src = it.get("source", "")
        slot = src_to_slot.get(src, "overflow")
        scfg = slots.get(slot, {})
        fresh_h = float(scfg.get("freshness_hours", 72))
        if _age_hours(it.get("published", "")) > fresh_h:
            reasons["freshness_window"] += 1
            continue

        rel = float(source_health.get(src, 1.0))
        if rel < 0.3:
            reasons["health_floor"] += 1
            continue

        item = dict(it)
        item["v2_slot"] = slot
        item["freshness"] = round(_freshness_score(it.get("published", ""), decay_hours=max(12.0, fresh_h / 3)), 3)
        item["source_reliability"] = round(rel, 3)
        item["v2_prefilter_score"] = round(float(it.get("source_weight", 1.0)) + item["freshness"] + rel, 3)
        out.append(item)

    out.sort(key=lambda x: x.get("v2_prefilter_score", 0), reverse=True)
    if len(out) > cap:
        reasons["pool_cap"] += len(out) - cap
        out = out[:cap]

    diag = {
        "prefilter_in": len(items),
        "prefilter_out": len(out),
        "prefilter_reasons": dict(reasons),
    }
    return out, diag


def assign_slots(candidates: list[dict[str, Any]], v2_cfg: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    slots = {k: [] for k in (v2_cfg.get("slots", {}) or {}).keys()}
    slots.setdefault("overflow", [])
    for it in candidates:
        slot = it.get("v2_slot", "overflow")
        slots.setdefault(slot, []).append(it)

    for slot, arr in slots.items():
        arr.sort(key=lambda x: x.get("v2_prefilter_score", 0), reverse=True)
    return slots


def compute_llm_score(lb: dict[str, Any]) -> float:
    fit = float(lb.get("fit_agentic_platform", 3))
    act = float(lb.get("actionability", 3))
    nov = float(lb.get("novelty", 3))
    evq = float(lb.get("evidence_quality", 3))
    hype = float(lb.get("hype_risk", 2))
    return 0.40 * fit + 0.25 * act + 0.20 * nov + 0.15 * evq - 0.25 * max(0.0, hype - 3.0)


def _to_clean_oneline(text: str, max_chars: int = 220) -> str:
    s = html.unescape(str(text or ""))
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"<[^\s]*", " ", s)  # strip dangling/incomplete HTML tags
    s = s.replace("<", " ").replace(">", " ")
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) > max_chars:
        s = s[: max_chars - 3].rstrip() + "..."
    return s


def _summary_is_noisy(s: str) -> bool:
    t = (s or "").lower()
    return any(x in t for x in ["href=", "class=", "style=", "js-"])


def _summary_has_eval_tone(s: str) -> bool:
    t = (s or "").lower()
    markers = [
        "limited technical depth",
        "limited depth",
        "low signal",
        "high signal",
        "high relevance",
        "low relevance",
        "lacks",
        "not actionable",
        "weak evidence",
    ]
    return any(m in t for m in markers)


def _infer_item_type(item: dict[str, Any], slot: str) -> str:
    src = str(item.get("source", "")).lower()
    title = str(item.get("title", "")).lower()
    url = str(item.get("url", "")).lower()

    if slot in {"agent_tooling_releases", "infra_runtime_releases"}:
        return "release"
    if slot == "research_watch":
        return "paper" if (src.startswith("arxiv_") or "paperswithcode" in src or "arxiv.org" in url) else "research"

    if "release" in src or src.endswith("_releases"):
        return "release"
    if any(k in title for k in ["release", "changelog", "what's changed", "version", "sdk==", " v2.", " v1."]):
        return "release"
    if src.startswith("arxiv_") or "arxiv.org" in url or "paperswithcode" in src:
        return "paper"

    return "news"


def _select_slot_items(slot: str, items: list[dict[str, Any]], scfg: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    max_items = int(scfg.get("max_items", len(items)))
    max_per_source = int(scfg.get("max_per_source", max_items))
    src_counts = defaultdict(int)
    out: list[dict[str, Any]] = []
    reject = {"source_cap": 0, "slot_cap": 0}
    for it in items:
        if len(out) >= max_items:
            reject["slot_cap"] += 1
            continue
        src = it.get("source", "unknown")
        if src_counts[src] >= max_per_source:
            reject["source_cap"] += 1
            continue
        out.append(it)
        src_counts[src] += 1
    return out, reject


def stage_c_score_and_select(slotted: dict[str, list[dict[str, Any]]], v2_cfg: dict[str, Any], llm_budget: int) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    slots_cfg = v2_cfg.get("slots", {}) or {}
    source_bias_cfg = v2_cfg.get("source_bias", {}) or {}
    topical_cfg = v2_cfg.get("topical_bias", {}) or {}
    pos_kw = [str(x).lower() for x in (topical_cfg.get("positive_keywords", []) or [])]
    neg_kw = [str(x).lower() for x in (topical_cfg.get("negative_keywords", []) or [])]
    pos_w = float(topical_cfg.get("positive_weight", 0.0))
    neg_w = float(topical_cfg.get("negative_weight", 0.0))
    selected_by_slot: dict[str, list[dict[str, Any]]] = {}
    diag_slots: dict[str, Any] = {}
    budget_used = 0

    for slot, candidates in slotted.items():
        scfg = slots_cfg.get(slot, {})
        alpha = float((scfg.get("blend", {}) or {}).get("alpha", 0.8))
        beta = float((scfg.get("blend", {}) or {}).get("beta", 0.2))

        remaining = max(0, int(llm_budget) - budget_used)
        labels, meta = label_items_v2(candidates, budget=remaining, rubric_version="v2.1")
        budget_used += int(meta.get("llm_called", 0))

        scored = []
        for it in candidates:
            key = it.get("id") or f"{it.get('source')}::{it.get('url')}"
            lb = labels.get(key, {})
            llm_s = compute_llm_score(lb)
            src_bias = float(source_bias_cfg.get(it.get("source", ""), 0.0))
            text = f"{it.get('title','')} {it.get('summary','')}".lower()
            topical = 0.0
            if any(k in text for k in pos_kw):
                topical += pos_w
            if any(k in text for k in neg_kw):
                topical += neg_w
            fs = alpha * llm_s + beta * float(it.get("freshness", 0)) + src_bias + topical
            item = dict(it)
            item["type"] = _infer_item_type(item, slot)
            item["llm_label_source"] = lb.get("__label_source", "heuristic")
            item["llm_category"] = lb.get("category", "platform")
            item["llm_summary_1line"] = str(lb.get("summary_1line", "")).strip()
            item["llm_why_1line"] = lb.get("why_1line", "")
            item["v2_llm_score"] = round(llm_s, 3)
            item["v2_source_bias"] = round(src_bias, 3)
            item["v2_topical_bias"] = round(topical, 3)
            item["v2_final_score"] = round(fs, 3)
            if item["llm_summary_1line"]:
                summary = _to_clean_oneline(item["llm_summary_1line"], 220)
            else:
                summary = _to_clean_oneline(item.get("summary", "") or item.get("title", ""), 220)
            if _summary_is_noisy(summary) or _summary_has_eval_tone(summary):
                summary = _to_clean_oneline(item.get("summary", "") or item.get("title", ""), 220)
            item["summary_1line"] = summary
            if item["llm_why_1line"]:
                item["why_it_matters"] = item["llm_why_1line"]
            scored.append(item)

        scored.sort(key=lambda x: x.get("v2_final_score", 0), reverse=True)
        picked, reject = _select_slot_items(slot, scored, scfg)
        selected_by_slot[slot] = picked
        diag_slots[slot] = {
            "candidates": len(candidates),
            "llm_scored": len(candidates),
            "cache_hits": int(meta.get("cache_hits", 0)),
            "llm_called": int(meta.get("llm_called", 0)),
            "selected": len(picked),
            "reject_source_cap": int(reject.get("source_cap", 0)),
            "reject_slot_cap": int(reject.get("slot_cap", 0)),
        }

    return selected_by_slot, {"slots": diag_slots, "llm_budget_total": llm_budget, "llm_budget_used": budget_used}


def global_merge(slot_selections: dict[str, list[dict[str, Any]]], v2_cfg: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, float], dict[str, int]]:
    max_items = int(v2_cfg.get("max_items", 20))
    slots_cfg = v2_cfg.get("slots", {}) or {}

    dyn = (v2_cfg.get("dynamic_slot_rerank", {}) or {})
    dyn_enabled = bool(dyn.get("enabled", False))
    q_w = float(dyn.get("quality_weight", 0.0))
    f_w = float(dyn.get("freshness_weight", 0.0))
    base_bias = dyn.get("base_bias", {}) or {}

    slot_priority: dict[str, float] = {}
    for slot, arr in slot_selections.items():
        if not dyn_enabled:
            slot_priority[slot] = 0.0
            continue
        if not arr:
            slot_priority[slot] = float(base_bias.get(slot, 0.0))
            continue
        avg_llm = sum(float(x.get("v2_llm_score", 0.0)) for x in arr) / max(1, len(arr))
        avg_fresh = sum(float(x.get("freshness", 0.0)) for x in arr) / max(1, len(arr))
        slot_priority[slot] = float(base_bias.get(slot, 0.0)) + q_w * avg_llm + f_w * avg_fresh

    # Build scored candidates with slot priority applied.
    by_slot_scored: dict[str, list[dict[str, Any]]] = {}
    for slot, arr in slot_selections.items():
        scored: list[dict[str, Any]] = []
        for it in arr:
            item = dict(it)
            sp = float(slot_priority.get(slot, 0.0))
            item["v2_slot_priority"] = round(sp, 3)
            item["v2_global_score"] = round(float(item.get("v2_final_score", 0.0)) + sp, 3)
            scored.append(item)
        scored.sort(key=lambda x: x.get("v2_global_score", x.get("v2_final_score", 0)), reverse=True)
        by_slot_scored[slot] = scored

    # Strategy: fixed slot floors first, then dynamic headroom fill.
    out: list[dict[str, Any]] = []
    used = set()
    slot_counts = defaultdict(int)
    merge_diag = {"floor_selected": 0, "headroom_selected": 0, "skip_duplicate": 0, "skip_slot_max": 0}

    # Phase 1: reserve minimum floors.
    for slot, scored in by_slot_scored.items():
        min_items = int((slots_cfg.get(slot, {}) or {}).get("min_items", 0))
        for it in scored:
            if slot_counts[slot] >= min_items or len(out) >= max_items:
                break
            key = it.get("id") or f"{it.get('source')}::{it.get('url')}"
            if key in used:
                continue
            out.append(it)
            used.add(key)
            slot_counts[slot] += 1
            merge_diag["floor_selected"] += 1

    # Phase 2: fill remaining capacity dynamically by best global score,
    # while respecting each slot's max_items.
    remainder: list[dict[str, Any]] = []
    for slot, scored in by_slot_scored.items():
        remainder.extend(scored)
    remainder.sort(key=lambda x: x.get("v2_global_score", x.get("v2_final_score", 0)), reverse=True)

    for it in remainder:
        if len(out) >= max_items:
            break
        slot = it.get("v2_slot", "overflow")
        max_slot = int((slots_cfg.get(slot, {}) or {}).get("max_items", max_items))
        key = it.get("id") or f"{it.get('source')}::{it.get('url')}"
        if key in used:
            merge_diag["skip_duplicate"] += 1
            continue
        if slot_counts[slot] >= max_slot:
            merge_diag["skip_slot_max"] += 1
            continue
        out.append(it)
        used.add(key)
        slot_counts[slot] += 1
        merge_diag["headroom_selected"] += 1

    out.sort(key=lambda x: x.get("v2_global_score", x.get("v2_final_score", 0)), reverse=True)
    return out[:max_items], slot_priority, merge_diag


def enforce_top_band_constraints(items: list[dict[str, Any]], v2_cfg: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    cfg = (v2_cfg.get("top_band_constraints", {}) or {})

    band_diag = {"dedup_removed": 0, "promoted_frontier": 0, "promoted_anthropic_frontier": 0, "research_demoted": 0}

    # Always dedupe final list by canonical key to prevent visible duplicates.
    deduped: list[dict[str, Any]] = []
    seen = set()
    for it in items:
        key = (it.get("url") or "").split("#")[0].strip().lower() or f"{it.get('source')}::{it.get('title')}"
        if key in seen:
            band_diag["dedup_removed"] += 1
            continue
        seen.add(key)
        deduped.append(it)

    if not cfg.get("enabled", False):
        return deduped, band_diag
    top_n = max(1, int(cfg.get("top_n", 10)))
    min_frontier = int(cfg.get("min_frontier_official", 0))
    min_anthropic = int(cfg.get("min_anthropic_frontier", 0))
    max_research = int(cfg.get("max_research_in_top_n", 99))

    out = list(deduped)
    top = out[:top_n]

    def is_frontier(x: dict[str, Any]) -> bool:
        return x.get("v2_slot") == "frontier_official"

    def is_anth_frontier(x: dict[str, Any]) -> bool:
        s = (x.get("source") or "")
        return is_frontier(x) and s.startswith("anthropic")


    def promote(predicate, needed: int, counter_key: str):
        nonlocal out, top
        have = sum(1 for x in top if predicate(x))
        if have >= needed:
            return
        candidates = [x for x in out[top_n:] if predicate(x)]
        candidates.sort(key=lambda x: x.get("v2_global_score", 0), reverse=True)
        while have < needed and candidates:
            cand = candidates.pop(0)
            replace_idx = None
            for i in range(top_n - 1, -1, -1):
                if not predicate(top[i]):
                    replace_idx = i
                    break
            if replace_idx is None:
                break
            old = top[replace_idx]
            top[replace_idx] = cand
            out.remove(cand)
            out.append(old)
            have += 1
            band_diag[counter_key] += 1
        top.sort(key=lambda x: x.get("v2_global_score", 0), reverse=True)
        tail = [x for x in out if x not in top]
        tail.sort(key=lambda x: x.get("v2_global_score", 0), reverse=True)
        out = top + tail

    promote(is_frontier, min_frontier, "promoted_frontier")
    promote(is_anth_frontier, min_anthropic, "promoted_anthropic_frontier")

    # Cap research-heavy items in visible top band.
    def is_research(x: dict[str, Any]) -> bool:
        return (x.get("v2_slot") == "research_watch") or ((x.get("llm_category") or "") == "research")

    research_count = sum(1 for x in top if is_research(x))
    if research_count > max_research:
        tail_candidates = [x for x in out[top_n:] if not is_research(x)]
        tail_candidates.sort(key=lambda x: x.get("v2_global_score", 0), reverse=True)
        i = top_n - 1
        while research_count > max_research and i >= 0 and tail_candidates:
            if is_research(top[i]):
                repl = tail_candidates.pop(0)
                old = top[i]
                top[i] = repl
                out.remove(repl)
                out.append(old)
                research_count -= 1
                band_diag["research_demoted"] += 1
            i -= 1
        top.sort(key=lambda x: x.get("v2_global_score", 0), reverse=True)
        tail = [x for x in out if x not in top]
        tail.sort(key=lambda x: x.get("v2_global_score", 0), reverse=True)
        out = top + tail

    final: list[dict[str, Any]] = []
    seen3 = set()
    for it in out:
        key = (it.get("url") or "").split("#")[0].strip().lower() or f"{it.get('source')}::{it.get('title')}"
        if key in seen3:
            band_diag["dedup_removed"] += 1
            continue
        seen3.add(key)
        final.append(it)
    return final, band_diag


def run_v2(items: list[dict[str, Any]], profile: dict[str, Any], llm_cfg: dict[str, Any], source_health: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    v2_cfg = load_v2_config()
    candidates, diag_a = stage_a_prefilter(items, v2_cfg, profile, source_health)
    slotted = assign_slots(candidates, v2_cfg)
    llm_budget = int(v2_cfg.get("llm_budget", 40))
    selected_by_slot, diag_c = stage_c_score_and_select(slotted, v2_cfg, llm_budget)
    top, slot_priority, merge_diag = global_merge(selected_by_slot, v2_cfg)
    top, band_diag = enforce_top_band_constraints(top, v2_cfg)

    # Final summary enrichment for ALL presented items (~20):
    # run label pass again only on final top list so summary_1line is consistently LLM-generated.
    final_labels, final_meta = label_items_v2(top, budget=len(top), rubric_version="v2.1-final-summary")
    for it in top:
      key = it.get("id") or f"{it.get('source')}::{it.get('url')}"
      lb = final_labels.get(key, {})
      llm_sum = str(lb.get("summary_1line", "")).strip()
      if llm_sum:
          summary = _to_clean_oneline(llm_sum, 220)
      elif not it.get("summary_1line"):
          summary = _to_clean_oneline(it.get("summary", "") or it.get("title", ""), 220)
      else:
          summary = _to_clean_oneline(it.get("summary_1line", ""), 220)

      if _summary_is_noisy(summary) or _summary_has_eval_tone(summary):
          summary = _to_clean_oneline(it.get("summary", "") or it.get("title", ""), 220)
      it["summary_1line"] = summary

    diag = {
        **diag_a,
        **diag_c,
        "slot_priority": {k: round(v, 3) for k, v in slot_priority.items()},
        "merge": merge_diag,
        "top_band": band_diag,
        "final_summary_pass": {
            "llm_called": int(final_meta.get("llm_called", 0)),
            "cache_hits": int(final_meta.get("cache_hits", 0)),
            "items": len(top),
        },
    }
    slot_bits = []
    for k, v in (diag.get("slots", {}) or {}).items():
        slot_bits.append(f"{k}:{v.get('selected',0)}")
    sp_bits = []
    for k, v in (diag.get("slot_priority", {}) or {}).items():
        sp_bits.append(f"{k}:{v:.2f}")
    m = diag.get("merge", {}) or {}
    tb = diag.get("top_band", {}) or {}
    print(
        "v2_stats "
        f"prefilter={diag.get('prefilter_in',0)}->{diag.get('prefilter_out',0)} "
        f"llm_used={diag.get('llm_budget_used',0)}/{diag.get('llm_budget_total',0)} "
        f"slots={'/'.join(slot_bits)} "
        f"slot_priority={'/'.join(sp_bits)} "
        f"merge=floor{m.get('floor_selected',0)}/headroom{m.get('headroom_selected',0)}/dupSkip{m.get('skip_duplicate',0)}/slotMaxSkip{m.get('skip_slot_max',0)} "
        f"top_band=promoteF{tb.get('promoted_frontier',0)}/promoteA{tb.get('promoted_anthropic_frontier',0)}/researchDemote{tb.get('research_demoted',0)} total={len(top)}"
    )
    return top, diag
