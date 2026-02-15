from __future__ import annotations

import json
import os
import urllib.request
from typing import Any


def heuristic_rerank(candidates: list[dict[str, Any]], max_items: int) -> list[dict[str, Any]]:
    return sorted(candidates, key=lambda x: x.get("score", 0), reverse=True)[:max_items]


def enforce_quotas(items: list[dict[str, Any]], max_items: int, quotas: dict[str, dict[str, int]]) -> list[dict[str, Any]]:
    min_q = quotas.get("min", {})
    max_q = quotas.get("max", {})

    by_type = {"paper": [], "news": [], "release": []}
    for it in items:
        by_type.setdefault(it.get("type", "news"), []).append(it)

    selected: list[dict[str, Any]] = []
    counts = {"paper": 0, "news": 0, "release": 0}

    # enforce mins
    for t in ["paper", "news", "release"]:
        need = int(min_q.get(t, 0))
        for it in by_type.get(t, []):
            if counts[t] >= need or len(selected) >= max_items:
                break
            selected.append(it)
            counts[t] += 1

    # fill by score under max caps
    all_sorted = sorted(items, key=lambda x: x.get("score", 0), reverse=True)
    for it in all_sorted:
        if len(selected) >= max_items:
            break
        if it in selected:
            continue
        t = it.get("type", "news")
        cap = int(max_q.get(t, max_items))
        if counts.get(t, 0) >= cap:
            continue
        selected.append(it)
        counts[t] = counts.get(t, 0) + 1

    return selected[:max_items]


def call_openai_compatible(candidates: list[dict[str, Any]], cfg: dict[str, Any], max_items: int) -> list[str]:
    api_key = os.getenv(cfg.get("api_key_env", "OPENAI_API_KEY"), "")
    if not api_key:
        raise RuntimeError("missing_api_key")

    prompt_rows = []
    for c in candidates:
        prompt_rows.append(
            {
                "id": c.get("id"),
                "title": c.get("title"),
                "type": c.get("type"),
                "source": c.get("source"),
                "score": c.get("score"),
                "why": c.get("why_it_matters", ""),
            }
        )

    sys = (
        "Rank candidates for an AI platform engineer daily digest. "
        "Return strict JSON: {\"ordered_ids\": [..]} using only provided ids, max length requested. "
        "Prefer practical, high-signal, low-hype, and diverse type mix."
    )
    user_payload = {"max_items": max_items, "candidates": prompt_rows}

    body = {
        "model": cfg.get("model", "gpt-4o-mini"),
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": sys},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ],
    }

    req = urllib.request.Request(
        cfg.get("endpoint", "https://api.openai.com/v1/chat/completions"),
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    timeout = int(cfg.get("timeout_seconds", 20))
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode("utf-8"))
    content = data["choices"][0]["message"]["content"]
    parsed = json.loads(content)
    return parsed.get("ordered_ids", [])


def rerank_candidates(candidates: list[dict[str, Any]], cfg: dict[str, Any], max_items: int, quotas: dict[str, dict[str, int]]) -> list[dict[str, Any]]:
    base = sorted(candidates, key=lambda x: x.get("score", 0), reverse=True)
    enabled = bool(cfg.get("enabled", False))

    if not enabled:
        return enforce_quotas(base, max_items, quotas)

    ordered = []
    try:
        ordered_ids = call_openai_compatible(base[: int(cfg.get("rerank_top_n", 40))], cfg, max_items)
        by_id = {c.get("id"): c for c in base}
        for oid in ordered_ids:
            if oid in by_id and by_id[oid] not in ordered:
                ordered.append(by_id[oid])
        for c in base:
            if c not in ordered:
                ordered.append(c)
    except Exception:
        ordered = base

    return enforce_quotas(ordered, max_items, quotas)
