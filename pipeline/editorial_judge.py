"""Run the Jev quality gate over the candidate pool.

This is a stage in the single edition builder, not a separate tier. It runs
after the deterministic editorial pre-ranking (dedupe, story clusters, search
and first-party quarantine, seen-memory) and before ranking.

The gate is fail-open: a missing key, timeout, or malformed response leaves the
item unjudged and the deterministic policy continues. Judgments are cached by
the provider by payload hash.
"""

from __future__ import annotations

import argparse
import json
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from content_fetch import build_paragraph_map
    from judge import (
        judge_verdict,
        load_judge_config,
        provider_from_config,
    )
    from judgment_store import (
        attach_entry,
        evidence_chars,
        get_entry,
        judgment_key,
        load_store,
        prune_store,
        put_entry,
        save_store,
    )
except Exception:
    from pipeline.content_fetch import build_paragraph_map
    from pipeline.judge import (
        judge_verdict,
        load_judge_config,
        provider_from_config,
    )
    from pipeline.judgment_store import (
        attach_entry,
        evidence_chars,
        get_entry,
        judgment_key,
        load_store,
        prune_store,
        put_entry,
        save_store,
    )

ROOT = Path(__file__).resolve().parents[1]
CLASSIFIED_DIR = ROOT / "data" / "quality" / "classified"
COMPACT_CLASSIFIED = ROOT / "data" / "processed" / "classified.json"


def _priority(item: dict[str, Any]) -> float:
    for field in ("final_score", "freshness", "score"):
        try:
            value = float(item.get(field, 0) or 0)
        except (TypeError, ValueError):
            continue
        if value:
            return value
    return 0.0


def _evidence_exempt_roles(cfg: dict[str, Any]) -> set[str]:
    content_cfg = cfg.get("content_fetch", {}) or {}
    raw = content_cfg.get("min_evidence_exempt_roles")
    if raw is None:
        raw = ["release"]
    return {str(role) for role in raw}


def has_sufficient_evidence(item: dict[str, Any], cfg: dict[str, Any]) -> bool:
    """Whether the judge has enough text to make a defensible decision.

    A model asked to score a title and a 76-character search snippet will
    answer low, because its own rubric says a teaser is not evidence. Scoring
    that answer as a quality verdict starves the lane. Leave the item unjudged
    instead and let the deterministic policy decide.
    """
    min_chars = int((cfg.get("content_fetch", {}) or {}).get("min_evidence_chars", 0) or 0)
    if min_chars <= 0:
        return True
    if str(item.get("source_role") or "") in _evidence_exempt_roles(cfg):
        return True
    return evidence_chars(item) >= min_chars


def _entry_is_thin(entry: dict[str, Any], cfg: dict[str, Any]) -> bool:
    """A stored judgment made on a thin excerpt must be refreshed."""
    min_chars = int((cfg.get("content_fetch", {}) or {}).get("min_evidence_chars", 0) or 0)
    if min_chars <= 0:
        return False
    if str(entry.get("source_role") or "") in _evidence_exempt_roles(cfg):
        return False
    return int(entry.get("judge_evidence_chars") or 0) < min_chars


def _attach(item: dict[str, Any], result: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    item = dict(item)
    score = result.get("score")
    try:
        score = float(score) if score is not None else None
    except (TypeError, ValueError):
        score = None
    item["judge_score"] = round(score, 4) if score is not None else None
    item["judge_signals"] = result.get("signals") or {}
    choices = result.get("choices") or {}
    category = choices.get("category") if isinstance(choices.get("category"), dict) else None
    item["judge_choices"] = choices
    item["judge_category"] = category.get("choice") if category else None
    item["judge_category_confidence"] = round(float(category.get("confidence", 0.0)), 4) if category else None
    item["judge_category_probabilities"] = category.get("probabilities") if category else {}
    item["judge_verdict"] = judge_verdict(
        score,
        drop_below=float((cfg.get("ranking", {}) or {}).get("drop_below", 0.15)),
        keep_at=float((cfg.get("ranking", {}) or {}).get("keep_at", 0.5)),
    )
    item["judge_model"] = str(
        result.get("judge_model")
        or (cfg.get("openrouter", {}) or {}).get("model")
        or cfg.get("model")
        or "jev-1.14"
    )
    item["judge_rubric_version"] = str(result.get("judge_rubric_version") or cfg.get("version") or "feed-quality-v1")
    item["judge_evidence_chars"] = evidence_chars(item)
    item["judge_judged_at"] = str(result.get("judged_at") or datetime.now(timezone.utc).isoformat())
    item["judge_store_cached"] = bool(result.get("store", False))
    return item


def _cap_drops(items: list[dict[str, Any]], max_drop_share: float) -> tuple[list[dict[str, Any]], int]:
    """Do not let a bad judge batch empty the feed.

    Keep the worst drops and downgrade the highest-scoring excess drops to
    `review`, which still lets the deterministic ranking decide.
    """
    judged = [item for item in items if item.get("judge_verdict") in {"drop", "review", "keep"}]
    if not judged:
        return items, 0
    max_drops = max(0, int(len(judged) * max_drop_share))
    drops = [item for item in judged if item.get("judge_verdict") == "drop"]
    if len(drops) <= max_drops:
        return items, 0
    excess = len(drops) - max_drops
    ranked = sorted(drops, key=lambda item: float(item.get("judge_score") or 0.0), reverse=True)
    downgraded = set(id(item) for item in ranked[:excess])
    out = []
    for item in items:
        if id(item) in downgraded:
            item = dict(item)
            item["judge_verdict"] = "review"
            item["judge_drop_downgraded"] = True
        out.append(item)
    return out, excess


def write_classified(items: list[dict[str, Any]], cfg: dict[str, Any], diag: dict[str, Any]) -> Path:
    CLASSIFIED_DIR.mkdir(parents=True, exist_ok=True)
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = CLASSIFIED_DIR / f"{date}.json"
    rows = []
    for item in items:
        if item.get("judge_score") is None:
            continue
        rows.append(
            {
                "id": item.get("id"),
                "story_key": item.get("story_key"),
                "title": item.get("title"),
                "url": item.get("url"),
                "source": item.get("source"),
                "source_role": item.get("source_role"),
                "published": item.get("published"),
                "judge_score": item.get("judge_score"),
                "judge_verdict": item.get("judge_verdict"),
                "judge_evidence_chars": item.get("judge_evidence_chars"),
                "judge_category": item.get("judge_category"),
                "judge_category_confidence": item.get("judge_category_confidence"),
                "judge_category_probabilities": item.get("judge_category_probabilities"),
                "judge_signals": item.get("judge_signals"),
                "judge_model": item.get("judge_model"),
                "judge_rubric_version": item.get("judge_rubric_version"),
                "judge_judged_at": item.get("judge_judged_at"),
            }
        )
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": str((cfg.get("openrouter", {}) or {}).get("model") or cfg.get("model") or "jev-1.14"),
        "rubric_version": str(cfg.get("version") or "feed-quality-v1"),
        "item_count": len(rows),
        "diagnostics": diag,
        "items": rows,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # Compact, committed artifact for the editor-deck routines. Keep the top
    # judged items plus category/verdict counts so a routine can route without
    # reading the full local classified file.
    compact_items = sorted(rows, key=lambda row: float(row.get("judge_score") or 0.0), reverse=True)[:120]
    compact = {
        "generated_at": payload["generated_at"],
        "model": payload["model"],
        "rubric_version": payload["rubric_version"],
        "item_count": len(rows),
        "category_counts": dict(sorted(diag.get("categories", {}).items(), key=lambda kv: -kv[1])),
        "verdict_counts": dict(sorted(diag.get("verdicts", {}).items())),
        "items": [
            {
                "id": row.get("id"),
                "story_key": row.get("story_key"),
                "title": row.get("title"),
                "url": row.get("url"),
                "source": row.get("source"),
                "source_role": row.get("source_role"),
                "published": row.get("published"),
                "judge_score": row.get("judge_score"),
                "judge_verdict": row.get("judge_verdict"),
                "judge_evidence_chars": row.get("judge_evidence_chars"),
                "judge_category": row.get("judge_category"),
                "judge_category_confidence": row.get("judge_category_confidence"),
            }
            for row in compact_items
        ],
    }
    COMPACT_CLASSIFIED.parent.mkdir(parents=True, exist_ok=True)
    COMPACT_CLASSIFIED.write_text(json.dumps(compact, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def apply_judge(items: list[dict[str, Any]], cfg: dict[str, Any] | None = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    cfg = cfg or load_judge_config()
    diag: dict[str, Any] = {
        "enabled": False,
        "input": len(items),
        "judged": 0,
        "errors": 0,
        "cached": 0,
        "store_hits": 0,
        "store_misses": 0,
        "store_entries": 0,
        "store_pruned": 0,
        "insufficient_evidence": 0,
        "verdicts": {},
        "categories": {},
        "downgraded": 0,
    }
    if not cfg.get("enabled", False):
        diag["reason"] = "disabled"
        return items, diag

    provider = provider_from_config(cfg)
    if not provider.configured():
        diag["reason"] = "not_configured"
        print("judge_skipped reason=not_configured")
        return items, diag

    or_cfg = cfg.get("openrouter", {}) or {}
    max_items = int(or_cfg.get("max_items", cfg.get("max_items", 0)) or 0)
    max_workers = max(1, int(or_cfg.get("max_workers", 12) or 12))
    time_budget = float(or_cfg.get("time_budget_seconds", 300) or 300)

    indexed = list(enumerate(items))
    ranked = sorted(indexed, key=lambda pair: _priority(pair[1]), reverse=True)
    if max_items > 0:
        ranked = ranked[:max_items]
    diag["enabled"] = True
    diag["selected"] = len(ranked)

    store_cfg = cfg.get("judgment_store", {}) or {}
    store_path = store_cfg.get("path")
    store = load_store(Path(store_path) if store_path else None)
    ttl_days = float(store_cfg.get("ttl_days", 14) or 14)
    max_entries = int(store_cfg.get("max_entries", 6000) or 0)

    cached_by_index: dict[int, dict[str, Any]] = {}
    pending: list[tuple[int, dict[str, Any]]] = []
    for index, item in ranked:
        key = judgment_key(item, cfg)
        entry = get_entry(store, key, ttl_days)
        if entry is not None and not _entry_is_thin(entry, cfg):
            cached_by_index[index] = entry
        else:
            pending.append((index, item))

    content_cfg = cfg.get("content_fetch", {}) or {}
    if content_cfg.get("enabled", True) and pending:
        paragraph_map = build_paragraph_map(
            [item for _index, item in pending],
            top_n=len(pending),
            max_chars=int(content_cfg.get("max_chars", 2500) or 2500),
            timeout=int(content_cfg.get("timeout_seconds", 8) or 8),
            workers=int(content_cfg.get("workers", 8) or 8),
            time_budget_seconds=int(content_cfg.get("time_budget_seconds", 120) or 120),
        )
        fetched = 0
        transcript_fetched = 0
        transcript_missing = 0
        video_items = 0
        for _index, item in pending:
            is_video = str(item.get("type") or "").lower() == "video" or bool(item.get("video_id"))
            if is_video:
                video_items += 1
            text = paragraph_map.get(str(item.get("url") or "").split("#")[0].strip())
            if text:
                item["content_excerpt"] = text
                item["judge_excerpt_source"] = "transcript" if is_video else "fetched"
                fetched += 1
                if is_video:
                    transcript_fetched += 1
            elif is_video and item.get("transcript_url"):
                transcript_missing += 1
        diag["content_fetched"] = fetched
        diag["video_items"] = video_items
        diag["transcript_fetched"] = transcript_fetched
        diag["transcript_missing"] = transcript_missing

    # Re-key after enrichment. A judgment made on a thin excerpt must not be
    # reused once the article body is available, and an item that still has no
    # usable text is left unjudged rather than scored on a teaser.
    to_judge: list[tuple[int, dict[str, Any], str]] = []
    insufficient: dict[int, dict[str, Any]] = {}
    for index, item in pending:
        key = judgment_key(item, cfg)
        entry = get_entry(store, key, ttl_days)
        if entry is not None and not _entry_is_thin(entry, cfg):
            cached_by_index[index] = entry
            continue
        if not has_sufficient_evidence(item, cfg):
            insufficient[index] = item
            continue
        to_judge.append((index, item, key))
    diag["store_hits"] = len(cached_by_index)
    diag["store_misses"] = len(to_judge)
    diag["insufficient_evidence"] = len(insufficient)

    started = time.monotonic()
    results: dict[int, tuple[dict[str, Any] | None, str | None]] = {}

    def score_one(index: int, item: dict[str, Any]) -> tuple[int, dict[str, Any] | None, str | None]:
        try:
            return index, provider.score(item, cfg), None
        except Exception as exc:
            return index, None, str(exc)

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {}
        for index, item, _key in to_judge:
            if time.monotonic() - started > time_budget:
                diag["time_budget_hit"] = True
                break
            futures[pool.submit(score_one, index, item)] = (index, item)
        for future in as_completed(futures):
            index, result, error = future.result()
            results[index] = (result, error)

    judged_items: list[dict[str, Any]] = []
    key_by_index = {index: key for index, _item, key in to_judge}
    for index, item in enumerate(items):
        if index in cached_by_index:
            judged = _attach(item, attach_entry(item, cached_by_index[index]), cfg)
            judged["judge_evidence_chars"] = int(cached_by_index[index].get("judge_evidence_chars") or 0)
            diag["verdicts"][judged["judge_verdict"]] = diag["verdicts"].get(judged["judge_verdict"], 0) + 1
            category = judged.get("judge_category")
            if category:
                diag["categories"][category] = diag["categories"].get(category, 0) + 1
            judged_items.append(judged)
            continue
        if index in insufficient:
            item = dict(insufficient[index])
            item["judge_score"] = None
            item["judge_verdict"] = "unjudged"
            item["judge_error"] = "insufficient_evidence"
            item["judge_evidence_chars"] = evidence_chars(item)
            judged_items.append(item)
            continue
        result, error = results.get(index, (None, None))
        if result is None and error is None:
            judged_items.append(item)
            continue
        if error or result is None:
            item = dict(item)
            item["judge_score"] = None
            item["judge_error"] = error or "judge_failed"
            item["judge_verdict"] = "unjudged"
            diag["errors"] += 1
            judged_items.append(item)
            continue
        judged = _attach(item, result, cfg)
        put_entry(store, key_by_index.get(index, judgment_key(judged, cfg)), judged, cfg)
        diag["judged"] += 1
        if result.get("cached"):
            diag["cached"] += 1
        diag["verdicts"][judged["judge_verdict"]] = diag["verdicts"].get(judged["judge_verdict"], 0) + 1
        category = judged.get("judge_category")
        if category:
            diag["categories"][category] = diag["categories"].get(category, 0) + 1
        judged_items.append(judged)

    store, pruned = prune_store(store, ttl_days, max_entries)
    diag["store_pruned"] = pruned
    diag["store_entries"] = len(store.get("entries") or {})
    saved_path = save_store(store, Path(store_path) if store_path else None)
    diag["store_path"] = str(saved_path)

    judged_items, downgraded = _cap_drops(
        judged_items,
        float((cfg.get("ranking", {}) or {}).get("max_drop_share", 0.6)),
    )
    diag["downgraded"] = downgraded
    diag["elapsed_seconds"] = round(time.monotonic() - started, 2)
    diag["verdicts"] = dict(diag["verdicts"])
    diag["categories"] = dict(diag["categories"])
    path = write_classified(judged_items, cfg, diag)
    diag["classified_path"] = str(path)
    return judged_items, diag


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Jev quality gate over a JSON item list")
    parser.add_argument("--input", required=True, help="JSON list of items (or {items:[...]})")
    parser.add_argument("--out", help="write the judged items to this path")
    args = parser.parse_args()
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    items = payload if isinstance(payload, list) else payload.get("items", [])
    judged, diag = apply_judge(items)
    print(json.dumps(diag, ensure_ascii=False, indent=2))
    if args.out:
        Path(args.out).write_text(json.dumps(judged, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
