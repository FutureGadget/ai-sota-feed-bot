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

try:
    from llm_label import label_items_v2
except Exception:
    from pipeline.llm_label import label_items_v2

ROOT = Path(__file__).resolve().parents[1]
V2_CFG_FILE = ROOT / "config" / "ranking_v2.yaml"


def load_v2_config() -> dict[str, Any]:
    if not V2_CFG_FILE.exists():
        return {"enabled": False}
    return yaml.safe_load(V2_CFG_FILE.read_text(encoding="utf-8")) or {"enabled": False}


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


def _select_slot_items(slot: str, items: list[dict[str, Any]], scfg: dict[str, Any]) -> list[dict[str, Any]]:
    max_items = int(scfg.get("max_items", len(items)))
    max_per_source = int(scfg.get("max_per_source", max_items))
    src_counts = defaultdict(int)
    out: list[dict[str, Any]] = []
    for it in items:
        if len(out) >= max_items:
            break
        src = it.get("source", "unknown")
        if src_counts[src] >= max_per_source:
            continue
        out.append(it)
        src_counts[src] += 1
    return out


def stage_c_score_and_select(slotted: dict[str, list[dict[str, Any]]], v2_cfg: dict[str, Any], llm_budget: int) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    slots_cfg = v2_cfg.get("slots", {}) or {}
    selected_by_slot: dict[str, list[dict[str, Any]]] = {}
    diag_slots: dict[str, Any] = {}
    budget_used = 0

    for slot, candidates in slotted.items():
        scfg = slots_cfg.get(slot, {})
        alpha = float((scfg.get("blend", {}) or {}).get("alpha", 0.8))
        beta = float((scfg.get("blend", {}) or {}).get("beta", 0.2))

        remaining = max(0, int(llm_budget) - budget_used)
        labels, meta = label_items_v2(candidates, budget=remaining)
        budget_used += int(meta.get("llm_called", 0))

        scored = []
        for it in candidates:
            key = it.get("id") or f"{it.get('source')}::{it.get('url')}"
            lb = labels.get(key, {})
            llm_s = compute_llm_score(lb)
            fs = alpha * llm_s + beta * float(it.get("freshness", 0))
            item = dict(it)
            item["llm_label_source"] = lb.get("__label_source", "heuristic")
            item["llm_category"] = lb.get("category", "platform")
            item["llm_why_1line"] = lb.get("why_1line", "")
            item["v2_llm_score"] = round(llm_s, 3)
            item["v2_final_score"] = round(fs, 3)
            if item["llm_why_1line"]:
                item["why_it_matters"] = item["llm_why_1line"]
            scored.append(item)

        scored.sort(key=lambda x: x.get("v2_final_score", 0), reverse=True)
        picked = _select_slot_items(slot, scored, scfg)
        selected_by_slot[slot] = picked
        diag_slots[slot] = {
            "candidates": len(candidates),
            "llm_scored": len(candidates),
            "cache_hits": int(meta.get("cache_hits", 0)),
            "llm_called": int(meta.get("llm_called", 0)),
            "selected": len(picked),
        }

    return selected_by_slot, {"slots": diag_slots, "llm_budget_total": llm_budget, "llm_budget_used": budget_used}


def global_merge(slot_selections: dict[str, list[dict[str, Any]]], v2_cfg: dict[str, Any]) -> list[dict[str, Any]]:
    max_items = int(v2_cfg.get("max_items", 20))
    slots_cfg = v2_cfg.get("slots", {}) or {}

    all_items: list[dict[str, Any]] = []
    for _, arr in slot_selections.items():
        all_items.extend(arr)

    all_items.sort(key=lambda x: x.get("v2_final_score", 0), reverse=True)
    if len(all_items) <= max_items:
        return all_items

    min_by_slot = {k: int((slots_cfg.get(k, {}) or {}).get("min_items", 0)) for k in slot_selections.keys()}
    counts = defaultdict(int)
    for it in all_items:
        counts[it.get("v2_slot", "overflow")] += 1

    out = list(all_items)
    i = len(out) - 1
    while len(out) > max_items and i >= 0:
        slot = out[i].get("v2_slot", "overflow")
        if counts[slot] > min_by_slot.get(slot, 0):
            counts[slot] -= 1
            out.pop(i)
        i -= 1
    return out[:max_items]


def run_v2(items: list[dict[str, Any]], profile: dict[str, Any], llm_cfg: dict[str, Any], source_health: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    v2_cfg = load_v2_config()
    candidates, diag_a = stage_a_prefilter(items, v2_cfg, profile, source_health)
    slotted = assign_slots(candidates, v2_cfg)
    llm_budget = int(v2_cfg.get("llm_budget", 40))
    selected_by_slot, diag_c = stage_c_score_and_select(slotted, v2_cfg, llm_budget)
    top = global_merge(selected_by_slot, v2_cfg)

    diag = {**diag_a, **diag_c}
    slot_bits = []
    for k, v in (diag.get("slots", {}) or {}).items():
        slot_bits.append(f"{k}:{v.get('selected',0)}")
    print(
        "v2_stats "
        f"prefilter={diag.get('prefilter_in',0)}->{diag.get('prefilter_out',0)} "
        f"llm_used={diag.get('llm_budget_used',0)}/{diag.get('llm_budget_total',0)} "
        f"slots={'/'.join(slot_bits)} total={len(top)}"
    )
    return top, diag
