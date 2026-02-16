from __future__ import annotations

import hashlib
import html
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
# v2 ranking rubric will use a separate cache namespace to avoid schema collisions.
CACHE_FILE_V2 = ROOT / "data" / "llm" / "labels_v2.json"
SOURCES_FILE = ROOT / "config" / "sources.yaml"


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
            "Return strict JSON with keys: platform_relevant(bool), novelty(1-5), practicality(1-5), hype(1-5), summary_1line(string<=220), why_1line(string<=120)."
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


def sources_fingerprint() -> str:
    if not SOURCES_FILE.exists():
        return "none"
    raw = SOURCES_FILE.read_text(encoding="utf-8")
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:10]


def _clean_text_oneline(text: str, max_chars: int = 220) -> str:
    s = html.unescape(str(text or ""))
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) > max_chars:
        s = s[: max_chars - 3].rstrip() + "..."
    return s


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
    typ = (item.get("type") or "news").lower()
    category = "release" if typ == "release" else ("research" if typ == "paper" else "platform")
    summary = _clean_text_oneline(item.get("summary", "") or item.get("title", ""), 220)
    return {
        "platform_relevant": relevance,
        "novelty": novelty,
        "practicality": practicality,
        "hype": hype,
        "category": category,
        "summary_1line": summary,
        "why_1line": why,
    }


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

    version_blob = json.dumps(
        {
            "provider": cfg.get("provider"),
            "model": cfg.get("model"),
            "model_provider": cfg.get("model_provider"),
            "prompt": prompt_text,
            "prefs": prefs,
            "cache_version": cfg.get("cache_version", 1),
            "sources_fingerprint": sources_fingerprint(),
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    version = hashlib.sha256(version_blob.encode("utf-8")).hexdigest()[:10]

    enabled = bool(cfg.get("enabled", False))
    debug = bool(cfg.get("debug", False))
    debug_errors = 0
    for it in items:
        base_key = it.get("id") or f"{it.get('source')}::{it.get('url')}"
        key = f"{base_key}::v:{version}"
        if key in cache:
            out[base_key] = cache[key]
            continue

        label = None
        label_source = "heuristic"
        if enabled:
            try:
                if cfg.get("provider") == "openai_compatible":
                    label = call_openai_compatible(it, cfg, prefs, prompt_text)
                    label_source = "llm"
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
                                    "content_excerpt": it.get("content_excerpt", ""),
                                    "source": it.get("source", ""),
                                    "url": it.get("url", ""),
                                },
                            },
                        },
                        cfg,
                    )
                    label_source = "llm"
            except Exception as e:
                if debug and debug_errors < 5:
                    print(f"llm_label_error source={it.get('source','')} err={e}")
                    debug_errors += 1
                label = None

        if label is None:
            label = heuristic_label(it)
            label_source = "heuristic"

        label["__label_source"] = label_source
        cache[key] = label
        out[base_key] = label

    save_cache(cache)
    return out

PROMPT_FILE_V2 = ROOT / "config" / "prompts" / "label_v2_system.txt"


def load_prompt_text_v2() -> str:
    if not PROMPT_FILE_V2.exists():
        return (
            "You score AI content for an AI platform engineer daily digest. "
            "Return strict JSON with keys: fit_agentic_platform, actionability, novelty, evidence_quality, hype_risk, category, why_1line."
        )
    return PROMPT_FILE_V2.read_text(encoding="utf-8").strip()


def load_cache_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_cache_file(path: Path, cache: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def heuristic_label_v2(item: dict[str, Any]) -> dict[str, Any]:
    t = (item.get("title", "") + " " + item.get("summary", "")).lower()
    platform_tokens = ["agent", "eval", "benchmark", "inference", "latency", "serving", "orchestration", "automation"]
    evidence_tokens = ["benchmark", "code", "github", "dataset", "ablation", "reproduc"]
    hype_tokens = ["revolutionary", "game changing", "breakthrough", "unprecedented"]

    p = sum(1 for k in platform_tokens if k in t)
    e = sum(1 for k in evidence_tokens if k in t)
    h = sum(1 for k in hype_tokens if k in t)

    typ = (item.get("type") or "news").lower()
    category = "release" if typ == "release" else ("research" if typ == "paper" else "platform")

    return {
        "fit_agentic_platform": max(1, min(5, 2 + p // 2)),
        "actionability": max(1, min(5, 2 + (1 if typ == "release" else 0) + p // 3)),
        "novelty": 3 if ("new" in t or "introducing" in t) else 2,
        "evidence_quality": max(1, min(5, 2 + e // 2)),
        "hype_risk": max(1, min(5, 1 + h)),
        "category": category,
        "summary_1line": _clean_text_oneline(item.get("summary", "") or item.get("title", ""), 220),
        "why_1line": "Potential relevance to AI platform engineering; verify practical impact.",
    }


def label_items_v2(items: list[dict[str, Any]], budget: int = 40, rubric_version: str = "v2") -> tuple[dict[str, dict[str, Any]], dict[str, int]]:
    cfg = load_cfg()
    prefs = load_preferences()
    prompt_text = load_prompt_text_v2()
    cache = load_cache_file(CACHE_FILE_V2)
    out: dict[str, dict[str, Any]] = {}

    version_blob = json.dumps(
        {
            "provider": cfg.get("provider"),
            "model": cfg.get("model"),
            "model_provider": cfg.get("model_provider"),
            "prompt": prompt_text,
            "prefs": prefs,
            "cache_version": cfg.get("cache_version", 1),
            "sources_fingerprint": sources_fingerprint(),
            "rubric_version": rubric_version,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    version = hashlib.sha256(version_blob.encode("utf-8")).hexdigest()[:10]

    enabled = bool(cfg.get("enabled", False))
    debug = bool(cfg.get("debug", False))
    debug_errors = 0
    llm_called = 0
    cache_hits = 0

    for it in items:
        base_key = it.get("id") or f"{it.get('source')}::{it.get('url')}"
        key = f"{base_key}::v:{version}"
        if key in cache:
            out[base_key] = cache[key]
            cache_hits += 1
            continue

        label = None
        label_source = "heuristic"

        if enabled and llm_called < max(0, int(budget)):
            try:
                if cfg.get("provider") == "openai_compatible":
                    label = call_openai_compatible(it, cfg, prefs, prompt_text)
                    label_source = "llm"
                    llm_called += 1
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
                                    "content_excerpt": it.get("content_excerpt", ""),
                                    "source": it.get("source", ""),
                                    "url": it.get("url", ""),
                                },
                            },
                        },
                        cfg,
                    )
                    label_source = "llm"
                    llm_called += 1
            except Exception as e:
                if debug and debug_errors < 5:
                    print(f"llm_label_v2_error source={it.get('source','')} err={e}")
                    debug_errors += 1
                label = None

        if label is None:
            label = heuristic_label_v2(it)
            label_source = "heuristic"

        label["__label_source"] = label_source
        cache[key] = label
        out[base_key] = label

    save_cache_file(CACHE_FILE_V2, cache)
    return out, {"llm_called": llm_called, "cache_hits": cache_hits}
