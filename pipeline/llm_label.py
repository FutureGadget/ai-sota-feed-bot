from __future__ import annotations

import json
import os
import re
import urllib.request
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
CFG_FILE = ROOT / "config" / "llm.yaml"
CACHE_FILE = ROOT / "data" / "llm" / "labels.json"


def load_cfg() -> dict[str, Any]:
    if not CFG_FILE.exists():
        return {"enabled": False}
    return yaml.safe_load(CFG_FILE.read_text(encoding="utf-8"))


def load_cache() -> dict[str, Any]:
    if not CACHE_FILE.exists():
        return {}
    try:
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_cache(cache: dict[str, Any]) -> None:
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def heuristic_label(item: dict[str, Any]) -> dict[str, Any]:
    t = (item.get("title", "") + " " + item.get("summary", "")).lower()
    platform_tokens = [
        "inference",
        "latency",
        "throughput",
        "quantization",
        "rag",
        "eval",
        "agent",
        "benchmark",
        "serving",
    ]
    hype_tokens = ["game changing", "revolutionary", "unbelievable", "customer story"]

    p = sum(1 for k in platform_tokens if re.search(rf"\b{re.escape(k)}\b", t))
    h = sum(1 for k in hype_tokens if k in t)

    relevance = p > 0
    novelty = 3 if "new" in t or "introducing" in t else 2
    practicality = min(5, 1 + p)
    hype = min(5, 1 + h)

    why = "Relevant to AI platform engineering workflows." if relevance else "Potentially relevant; low direct platform signal."
    return {
        "platform_relevant": relevance,
        "novelty": novelty,
        "practicality": practicality,
        "hype": hype,
        "why_1line": why,
    }


def call_openai_compatible(item: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    api_key = os.getenv(cfg.get("api_key_env", "OPENAI_API_KEY"), "")
    if not api_key:
        raise RuntimeError("missing_api_key")

    prompt = {
        "title": item.get("title", ""),
        "summary": item.get("summary", ""),
        "source": item.get("source", ""),
        "url": item.get("url", ""),
    }

    sys = (
        "You are labeling AI content for an AI platform engineer digest. "
        "Return strict JSON only with keys: platform_relevant(bool), novelty(1-5), practicality(1-5), hype(1-5), why_1line(string <=120 chars)."
    )

    body = {
        "model": cfg.get("model", "gpt-4o-mini"),
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": sys},
            {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
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
    return json.loads(content)


def label_items(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    cfg = load_cfg()
    cache = load_cache()
    out = {}

    enabled = bool(cfg.get("enabled", False))
    for it in items:
        key = it.get("id") or f"{it.get('source')}::{it.get('url')}"
        if key in cache:
            out[key] = cache[key]
            continue

        label = None
        if enabled and cfg.get("provider") == "openai_compatible":
            try:
                label = call_openai_compatible(it, cfg)
            except Exception:
                label = None

        if label is None:
            label = heuristic_label(it)

        cache[key] = label
        out[key] = label

    save_cache(cache)
    return out
