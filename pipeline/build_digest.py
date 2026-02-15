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
        return "Potential relevance to AI platform stack; review for downstream impact."
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


def run():
    profile = load_profile()
    raw_file = latest_raw_file()

    with open(raw_file, "r", encoding="utf-8") as f:
        items = json.load(f)

    items = dedupe(items)

    pkw = profile.get("platform_keywords", [])
    hkw = profile.get("hype_keywords", [])
    w = profile.get("weights", {})
    decay = float(w.get("freshness_hours_decay", 72))
    source_health = load_source_health()

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
        score = (
            float(it.get("source_weight", 1.0)) * float(w.get("source_weight", 1.0))
            + fresh
            + platform_hits * float(w.get("platform_relevance", 1.8))
            - hype_hits * float(w.get("hype_penalty", 0.8))
            + src_rel * float(w.get("source_reliability", 1.0))
            + float(type_bonus_cfg.get(item_type, 0.0))
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

    labels = label_items(pre_sorted[:label_top_n])

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
        if it["llm_why_1line"] and src == "llm":
            it["why_it_matters"] = it["llm_why_1line"]

    scored.sort(key=lambda x: x["score"], reverse=True)
    print(f"label_stats llm={llm_used} heuristic={heuristic_used} label_top_n={label_top_n}")

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

    max_per_source = int(profile.get("selection", {}).get("max_per_source", 0))
    top = apply_source_cap(top, eligible, max_items, max_per_source, diversity_cfg.get("max_per_type", {}))

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

    print(f"digest_items={len(top)} file={out}")


if __name__ == "__main__":
    run()
