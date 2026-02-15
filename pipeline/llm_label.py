from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import urllib.request
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
CFG_FILE = ROOT / "config" / "llm.yaml"
PREF_FILE = ROOT / "config" / "user_preferences.yaml"
PROMPT_FILE = ROOT / "config" / "prompts" / "label_system.txt"
CACHE_FILE = ROOT / "data" / "llm" / "labels.json"


def load_cfg() -> dict[str, Any]:
    if not CFG_FILE.exists():
        return {"enabled": False}
    return yaml.safe_load(CFG_FILE.read_text(encoding="utf-8"))


def load_preferences() -> dict[str, Any]:
    if not PREF_FILE.exists():
        return {}
    return yaml.safe_load(PREF_FILE.read_text(encoding="utf-8")) or {}


def load_prompt_text() -> str:
    if not PROMPT_FILE.exists():
        return (
            "You label AI content for an AI platform engineer digest. "
            "Return strict JSON with keys: platform_relevant(bool), novelty(1-5), practicality(1-5), hype(1-5), why_1line(string<=120)."
        )
    return PROMPT_FILE.read_text(encoding="utf-8").strip()


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
    platform_tokens = ["inference", "latency", "throughput", "quantization", "rag", "eval", "agent", "benchmark", "serving"]
    hype_tokens = ["game changing", "revolutionary", "unbelievable", "customer story"]

    p = sum(1 for k in platform_tokens if re.search(rf"\b{re.escape(k)}\b", t))
    h = sum(1 for k in hype_tokens if k in t)

    relevance = p > 0
    novelty = 3 if "new" in t or "introducing" in t else 2
    practicality = min(5, 1 + p)
    hype = min(5, 1 + h)
    why = "Relevant to AI platform engineering workflows." if relevance else "Potentially relevant; low direct platform signal."
    return {"platform_relevant": relevance, "novelty": novelty, "practicality": practicality, "hype": hype, "why_1line": why}


def call_bridge(payload: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    cmd = cfg.get("bridge_command", "node scripts/llm_bridge.mjs")
    p = subprocess.run(
        shlex.split(cmd),
        input=json.dumps(payload, ensure_ascii=False),
        text=True,
        capture_output=True,
        timeout=int(cfg.get("timeout_seconds", 30)),
        cwd=str(ROOT),
    )
    if p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout or "bridge_failed").strip())
    return json.loads((p.stdout or "{}").strip())


def call_openai_compatible(item: dict[str, Any], cfg: dict[str, Any], preferences: dict[str, Any], prompt_text: str) -> dict[str, Any]:
    api_key = os.getenv(cfg.get("api_key_env", "OPENAI_API_KEY"), "")
    if not api_key:
        raise RuntimeError("missing_api_key")

    prompt = {
        "preferences": preferences,
        "item": {
            "title": item.get("title", ""),
            "summary": item.get("summary", ""),
            "source": item.get("source", ""),
            "url": item.get("url", ""),
        },
    }

    body = {
        "model": cfg.get("model", "gpt-4o-mini"),
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": prompt_text},
            {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
        ],
    }

    req = urllib.request.Request(
        cfg.get("endpoint", "https://api.openai.com/v1/chat/completions"),
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    timeout = int(cfg.get("timeout_seconds", 20))
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode("utf-8"))
    return json.loads(data["choices"][0]["message"]["content"])


def label_items(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    cfg = load_cfg()
    prefs = load_preferences()
    prompt_text = load_prompt_text()
    cache = load_cache()
    out = {}

    enabled = bool(cfg.get("enabled", False))
    for it in items:
        key = it.get("id") or f"{it.get('source')}::{it.get('url')}"
        if key in cache:
            out[key] = cache[key]
            continue

        label = None
        if enabled:
            try:
                if cfg.get("provider") == "openai_compatible":
                    label = call_openai_compatible(it, cfg, prefs, prompt_text)
                elif cfg.get("provider") == "pi_oauth":
                    label = call_bridge(
                        {
                            "cfg": cfg,
                            "system": prompt_text,
                            "payload": {
                                "preferences": prefs,
                                "item": {
                                    "title": it.get("title", ""),
                                    "summary": it.get("summary", ""),
                                    "source": it.get("source", ""),
                                    "url": it.get("url", ""),
                                },
                            },
                        },
                        cfg,
                    )
            except Exception:
                label = None

        if label is None:
            label = heuristic_label(it)

        cache[key] = label
        out[key] = label

    save_cache(cache)
    return out
