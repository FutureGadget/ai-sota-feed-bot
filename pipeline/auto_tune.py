from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
SOURCES_FILE = ROOT / "config" / "sources.yaml"
FEEDBACK_FILE = ROOT / "data" / "feedback" / "events.jsonl"
PROCESSED_FILE = ROOT / "data" / "processed" / "latest.json"


def load_sources() -> dict[str, Any]:
    with open(SOURCES_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_sources(data: dict[str, Any]) -> None:
    with open(SOURCES_FILE, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)


def load_feedback() -> list[dict[str, Any]]:
    if not FEEDBACK_FILE.exists():
        return []
    out = []
    with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def load_url_to_source() -> dict[str, str]:
    if not PROCESSED_FILE.exists():
        return {}
    items = json.loads(PROCESSED_FILE.read_text(encoding="utf-8"))
    return {it.get("url", ""): it.get("source", "") for it in items}


def signal_value(signal: str) -> float:
    return {
        "useful": 1.0,
        "irrelevant": -1.2,
        "hype": -1.5,
    }.get(signal, 0.0)


def compute_adjustments(feedback: list[dict[str, Any]], url_to_source: dict[str, str]) -> dict[str, float]:
    agg = defaultdict(lambda: {"score": 0.0, "n": 0})
    for e in feedback:
        src = e.get("source") or url_to_source.get(e.get("url", ""))
        if not src:
            continue
        agg[src]["score"] += signal_value(e.get("signal", ""))
        agg[src]["n"] += 1

    lr = 0.06
    max_step = 0.08
    adjustments = {}
    for src, v in agg.items():
        avg = v["score"] / max(v["n"], 1)
        delta = max(-max_step, min(max_step, avg * lr))
        adjustments[src] = round(delta, 4)
    return adjustments


def apply_tuning() -> None:
    data = load_sources()
    feedback = load_feedback()
    if not feedback:
        print("auto_tune: no feedback events; no changes")
        return

    url_to_source = load_url_to_source()
    adjustments = compute_adjustments(feedback, url_to_source)
    if not adjustments:
        print("auto_tune: no mappable feedback sources; no changes")
        return

    min_w, max_w = 0.5, 1.6
    changed = 0
    for s in data.get("sources", []):
        name = s.get("name")
        if name not in adjustments:
            continue
        old = float(s.get("weight", 1.0))
        new = max(min_w, min(max_w, old + adjustments[name]))
        if abs(new - old) >= 1e-6:
            s["weight"] = round(new, 4)
            changed += 1
            print(f"tuned {name}: {old:.4f} -> {new:.4f} ({adjustments[name]:+0.4f})")

    if changed:
        save_sources(data)
    print(f"auto_tune: changed_sources={changed}")


def report() -> None:
    feedback = load_feedback()
    url_to_source = load_url_to_source()
    adjustments = compute_adjustments(feedback, url_to_source)
    if not adjustments:
        print("auto_tune_report: no adjustments")
        return
    print("auto_tune_report")
    for k, v in sorted(adjustments.items(), key=lambda kv: abs(kv[1]), reverse=True):
        print(f"- {k}: {v:+0.4f}")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("report")
    sub.add_parser("apply")
    args = ap.parse_args()

    if args.cmd == "report":
        report()
    elif args.cmd == "apply":
        apply_tuning()


if __name__ == "__main__":
    main()
