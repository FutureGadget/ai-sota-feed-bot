from __future__ import annotations

import json
import math
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dateutil import parser as dt_parser

ROOT = Path(__file__).resolve().parents[1]


def latest_raw_file() -> Path:
    raw_root = ROOT / "data" / "raw"
    if not raw_root.exists():
        raise FileNotFoundError("No raw data found")
    days = sorted([p for p in raw_root.iterdir() if p.is_dir()])
    if not days:
        raise FileNotFoundError("No dated raw directories found")
    fp = days[-1] / "items.json"
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
    return set(re.findall(r"[a-z0-9]+", (t or "").lower()))


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def dedupe(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_url: dict[str, dict[str, Any]] = {}
    for it in items:
        key = canonical_url(it.get("url", ""))
        if not key:
            continue
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
    return math.exp(-age_hours / max(1.0, decay_hours))


def signal_type(item: dict[str, Any]) -> str:
    s = (item.get("source") or "").lower()
    t = (item.get("title") or "").lower()
    if "arxiv" in s or "paper" in s or "paperswithcode" in s:
        return "paper"
    if "release" in s or "release" in t:
        return "release"
    return "news"


def write_tier1_snapshot(items: list[dict[str, Any]], run_at: datetime | None = None) -> tuple[str, str]:
    ts = run_at or datetime.now(timezone.utc)
    run_at_iso = ts.isoformat()
    run_key = ts.strftime("%Y/%m/%Y%m%d-%H%M%S")
    rel_path = f"{run_key}.json"

    run_file = ROOT / "data" / "tier1" / "runs" / rel_path
    run_file.parent.mkdir(parents=True, exist_ok=True)
    run_file.write_text(json.dumps({"run_at": run_at_iso, "item_count": len(items), "items": items}, ensure_ascii=False, indent=2), encoding="utf-8")

    index_file = ROOT / "data" / "tier1" / "runs_index.json"
    idx = []
    if index_file.exists():
        try:
            idx = json.loads(index_file.read_text(encoding="utf-8"))
        except Exception:
            idx = []
    idx = [{"run_at": run_at_iso, "path": rel_path, "item_count": len(items)}] + [x for x in idx if x.get("path") != rel_path]
    idx = idx[:2000]
    index_file.parent.mkdir(parents=True, exist_ok=True)
    index_file.write_text(json.dumps(idx, ensure_ascii=False, indent=2), encoding="utf-8")
    return run_at_iso, rel_path


def run() -> None:
    raw_file = latest_raw_file()
    items = json.loads(raw_file.read_text(encoding="utf-8"))
    src_health = load_source_health()

    deduped = dedupe(items)

    out = []
    for it in deduped:
        rel = float(src_health.get(it.get("source", ""), 1.0))
        fresh = freshness_score(it.get("published", ""), decay_hours=72.0)
        quick = float(it.get("source_weight", 1.0)) + fresh + rel
        out.append(
            {
                **it,
                "tier": "tier1",
                "type": signal_type(it),
                "source_reliability": round(rel, 3),
                "freshness": round(fresh, 3),
                "tier1_quick_score": round(quick, 3),
            }
        )

    out.sort(key=lambda x: x.get("tier1_quick_score", 0), reverse=True)

    tier1_dir = ROOT / "data" / "tier1"
    tier1_dir.mkdir(parents=True, exist_ok=True)
    latest_file = tier1_dir / "latest.json"
    latest_file.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    run_at_iso, run_rel_path = write_tier1_snapshot(out)
    print(f"tier1_items={len(out)} file={latest_file} run_at={run_at_iso} run_file={run_rel_path}")


if __name__ == "__main__":
    run()
