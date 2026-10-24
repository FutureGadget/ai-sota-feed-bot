"""Durable judgment store for the Jev quality gate.

The provider cache under ``data/quality/cache`` is a local response cache. It
is intentionally gitignored, so a fresh CI runner starts cold. This module is
the durable layer: a compact, committed store keyed by item identity + model +
rubric + prompt fingerprint. The judge reads it before calling Jev, merges the
prior score/signals/category onto the item, and only calls the API for missing
or expired entries.

The store deliberately keeps only compact fields. Raw API responses, prompts,
usage, and cost stay in the local provider cache.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STORE_FILE = ROOT / "data" / "processed" / "judgments.json"
STORE_VERSION = 1


def _canonical_url(value: Any) -> str:
    return str(value or "").split("#")[0].split("?")[0].strip().lower()


def _normalize_title(value: Any) -> str:
    import re

    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def prompt_fingerprint(cfg: dict[str, Any]) -> str:
    """Hash the parts of the judge config that change the decision itself.

    Verdict thresholds (`ranking.*`) and ranking weights are excluded because
    the stored score/signals/category are independent of them; the verdict is
    recomputed at attach time. Model, rubric version, questions, criteria, and
    the content budget are included.
    """
    or_cfg = cfg.get("openrouter", {}) or {}
    blob = json.dumps(
        {
            "version": cfg.get("version"),
            "model": or_cfg.get("model") or cfg.get("model"),
            "score_mode": or_cfg.get("score_mode"),
            "use_holistic_keep": or_cfg.get("use_holistic_keep"),
            "questions": or_cfg.get("questions"),
            "hybrid": or_cfg.get("hybrid"),
            "composite": or_cfg.get("composite"),
            "instructions": cfg.get("instructions"),
            "criteria": cfg.get("criteria"),
            "content_fetch": {
                "max_chars": (cfg.get("content_fetch", {}) or {}).get("max_chars"),
            },
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def item_identity(item: dict[str, Any]) -> str:
    url = _canonical_url(item.get("url"))
    title = _normalize_title(item.get("title"))
    source = str(item.get("source") or "").strip().lower()
    return f"{url}|{title}|{source}"


def judgment_key(item: dict[str, Any], cfg: dict[str, Any]) -> str:
    or_cfg = cfg.get("openrouter", {}) or {}
    model = str(or_cfg.get("model") or cfg.get("model") or "jev-1.14")
    rubric = str(cfg.get("version") or "feed-quality-v1")
    identity = item_identity(item)
    blob = f"{identity}|{model}|{rubric}|{prompt_fingerprint(cfg)}"
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:32]


def load_store(path: Path | None = None) -> dict[str, Any]:
    path = path or STORE_FILE
    if not path.exists():
        return {"version": STORE_VERSION, "generated_at": None, "entries": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"version": STORE_VERSION, "generated_at": None, "entries": {}}
    if not isinstance(payload, dict):
        return {"version": STORE_VERSION, "generated_at": None, "entries": {}}
    entries = payload.get("entries")
    if not isinstance(entries, dict):
        payload["entries"] = {}
    payload.setdefault("version", STORE_VERSION)
    return payload


def save_store(store: dict[str, Any], path: Path | None = None) -> Path:
    path = path or STORE_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": STORE_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "entries": store.get("entries") or {},
    }
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass
    return path


def _parse_ts(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def get_entry(store: dict[str, Any], key: str, ttl_days: float) -> dict[str, Any] | None:
    entry = (store.get("entries") or {}).get(key)
    if not isinstance(entry, dict):
        return None
    judged_at = _parse_ts(entry.get("judge_judged_at"))
    if judged_at is None:
        return None
    if (datetime.now(timezone.utc) - judged_at) > timedelta(days=max(0.0, float(ttl_days))):
        return None
    return entry


def put_entry(store: dict[str, Any], key: str, item: dict[str, Any], cfg: dict[str, Any]) -> None:
    entries = store.setdefault("entries", {})
    entries[key] = {
        "identity": item_identity(item),
        "story_key": item.get("story_key"),
        "url": item.get("url"),
        "title": item.get("title"),
        "source": item.get("source"),
        "source_role": item.get("source_role"),
        "judge_score": item.get("judge_score"),
        "judge_signals": item.get("judge_signals") or {},
        "judge_category": item.get("judge_category"),
        "judge_category_confidence": item.get("judge_category_confidence"),
        "judge_category_probabilities": item.get("judge_category_probabilities") or {},
        "judge_model": item.get("judge_model"),
        "judge_rubric_version": item.get("judge_rubric_version"),
        "judge_judged_at": item.get("judge_judged_at") or datetime.now(timezone.utc).isoformat(),
    }


def prune_store(store: dict[str, Any], ttl_days: float, max_entries: int) -> tuple[dict[str, Any], int]:
    entries = store.get("entries") or {}
    cutoff = datetime.now(timezone.utc) - timedelta(days=max(0.0, float(ttl_days)))
    kept = []
    for key, entry in entries.items():
        if not isinstance(entry, dict):
            continue
        judged_at = _parse_ts(entry.get("judge_judged_at"))
        if judged_at is None or judged_at < cutoff:
            continue
        kept.append((judged_at, key, entry))
    kept.sort(key=lambda row: row[0], reverse=True)
    dropped = len(entries) - len(kept)
    if max_entries > 0 and len(kept) > max_entries:
        dropped += len(kept) - max_entries
        kept = kept[:max_entries]
    store["entries"] = {key: entry for _ts, key, entry in kept}
    return store, dropped


def attach_entry(item: dict[str, Any], entry: dict[str, Any]) -> dict[str, Any]:
    """Return a judge-result-shaped payload from a stored entry."""
    category = None
    if entry.get("judge_category"):
        category = {
            "choice": entry.get("judge_category"),
            "confidence": entry.get("judge_category_confidence") or 0.0,
            "probabilities": entry.get("judge_category_probabilities") or {},
        }
    return {
        "score": entry.get("judge_score"),
        "signals": entry.get("judge_signals") or {},
        "choices": {"category": category} if category else {},
        "judged_at": entry.get("judge_judged_at"),
        "judge_model": entry.get("judge_model"),
        "judge_rubric_version": entry.get("judge_rubric_version"),
        "cached": True,
        "store": True,
        "store_key": entry.get("identity"),
    }
