from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def parse_ts(v: str | None) -> datetime | None:
    if not v:
        return None
    try:
        d = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return d
    except Exception:
        return None


def load_json(path: Path, fallback: Any):
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            row = json.loads(ln)
            if isinstance(row, dict):
                out.append(row)
        except Exception:
            continue
    return out


def recent_count(index_rows: list[dict[str, Any]], hours: int = 24) -> int:
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=hours)
    c = 0
    for r in index_rows:
        d = parse_ts(r.get("run_at"))
        if d and d >= cutoff:
            c += 1
    return c


def latest_row(index_rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not index_rows:
        return None
    rows = sorted(index_rows, key=lambda x: str(x.get("run_at") or ""), reverse=True)
    return rows[0]


def ingest_statuses_last_24h(rows: list[dict[str, Any]]) -> dict[str, int]:
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=24)
    out: dict[str, int] = {}
    for r in rows:
        d = parse_ts(r.get("ts"))
        if not d or d < cutoff:
            continue
        st = str(r.get("status") or "unknown")
        out[st] = out.get(st, 0) + 1
    return dict(sorted(out.items(), key=lambda kv: kv[0]))


def main() -> None:
    processed_idx = load_json(ROOT / "data" / "processed" / "runs_index.json", [])
    tier1_idx = load_json(ROOT / "data" / "tier1" / "runs_index.json", [])
    ingest_rows = load_jsonl(ROOT / "data" / "health" / "ingest_runs.jsonl")

    latest_processed = latest_row(processed_idx if isinstance(processed_idx, list) else [])
    latest_tier1 = latest_row(tier1_idx if isinstance(tier1_idx, list) else [])

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "processed_runs_24h": recent_count(processed_idx if isinstance(processed_idx, list) else [], 24),
        "tier1_runs_24h": recent_count(tier1_idx if isinstance(tier1_idx, list) else [], 24),
        "latest_processed_run_at": latest_processed.get("run_at") if latest_processed else None,
        "latest_processed_item_count": latest_processed.get("item_count") if latest_processed else None,
        "latest_tier1_run_at": latest_tier1.get("run_at") if latest_tier1 else None,
        "latest_tier1_item_count": latest_tier1.get("item_count") if latest_tier1 else None,
        "ingest_status_counts_24h": ingest_statuses_last_24h(ingest_rows),
    }

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(
        "ops_summary "
        f"processed_24h={summary['processed_runs_24h']} "
        f"tier1_24h={summary['tier1_runs_24h']} "
        f"latest_processed_items={summary['latest_processed_item_count']} "
        f"latest_tier1_items={summary['latest_tier1_item_count']}"
    )


if __name__ == "__main__":
    main()
