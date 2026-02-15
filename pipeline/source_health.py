from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RUNS_FILE = ROOT / "data" / "health" / "ingest_runs.jsonl"
HEALTH_FILE = ROOT / "data" / "health" / "source_health.json"


def parse_ts(ts: str) -> datetime:
    d = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d


def load_runs(limit: int = 1000) -> list[dict[str, Any]]:
    if not RUNS_FILE.exists():
        return []
    lines = RUNS_FILE.read_text(encoding="utf-8").splitlines()[-limit:]
    out = []
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        try:
            out.append(json.loads(ln))
        except Exception:
            continue
    return out


def staleness_penalty(last_success_ts: str | None) -> float:
    if not last_success_ts:
        return 0.5
    age_h = (datetime.now(timezone.utc) - parse_ts(last_success_ts)).total_seconds() / 3600.0
    if age_h <= 12:
        return 0.0
    if age_h <= 48:
        return 0.1
    if age_h <= 120:
        return 0.25
    return 0.4


def build_health(runs: list[dict[str, Any]]) -> dict[str, Any]:
    by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in runs:
        by_source[r.get("source", "unknown")].append(r)

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sources": {},
    }

    for src, rows in by_source.items():
        rows = sorted(rows, key=lambda x: x.get("ts", ""))
        total = len(rows)
        ok_rows = [r for r in rows if r.get("status") == "ok"]
        ok = len(ok_rows)
        success_rate = ok / total if total else 0.0

        # consecutive failure streak from latest backwards
        fail_streak = 0
        for r in reversed(rows):
            if r.get("status") == "ok":
                break
            fail_streak += 1

        last_success_ts = ok_rows[-1]["ts"] if ok_rows else None
        avg_items_ok = sum(r.get("items", 0) for r in ok_rows) / max(ok, 1)

        rel = 1.0
        rel -= (1.0 - success_rate) * 0.5
        rel -= min(0.3, fail_streak * 0.05)
        rel -= staleness_penalty(last_success_ts)
        if avg_items_ok < 1:
            rel -= 0.1
        rel = max(0.2, min(1.0, rel))

        out["sources"][src] = {
            "success_rate": round(success_rate, 3),
            "total_runs": total,
            "consecutive_failures": fail_streak,
            "last_success_ts": last_success_ts,
            "avg_items_ok": round(avg_items_ok, 2),
            "reliability": round(rel, 3),
        }

    return out


def cmd_update() -> None:
    runs = load_runs()
    health = build_health(runs)
    HEALTH_FILE.parent.mkdir(parents=True, exist_ok=True)
    HEALTH_FILE.write_text(json.dumps(health, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"source_health_updated=true sources={len(health.get('sources', {}))}")


def cmd_report() -> None:
    if not HEALTH_FILE.exists():
        print("no_source_health")
        return
    health = json.loads(HEALTH_FILE.read_text(encoding="utf-8"))
    print("source_health_report")
    for src, h in sorted(health.get("sources", {}).items(), key=lambda kv: kv[1].get("reliability", 0), reverse=True):
        print(
            f"- {src}: rel={h.get('reliability')} success={h.get('success_rate')} runs={h.get('total_runs')} fail_streak={h.get('consecutive_failures')}"
        )


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("update")
    sub.add_parser("report")
    args = ap.parse_args()

    if args.cmd == "update":
        cmd_update()
    elif args.cmd == "report":
        cmd_report()


if __name__ == "__main__":
    main()
