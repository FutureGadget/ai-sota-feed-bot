from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FEEDBACK_FILE = ROOT / "data" / "feedback" / "events.jsonl"
VALID_SIGNALS = {"useful", "irrelevant", "hype"}


def ensure_dir() -> None:
    FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)


def add_event(url: str, signal: str, source: str | None = None, note: str | None = None) -> None:
    if signal not in VALID_SIGNALS:
        raise ValueError(f"signal must be one of {sorted(VALID_SIGNALS)}")
    ensure_dir()
    event = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "url": url,
        "signal": signal,
        "source": source,
        "note": note,
    }
    with open(FEEDBACK_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
    print("feedback_added=true")


def load_events() -> list[dict]:
    if not FEEDBACK_FILE.exists():
        return []
    out = []
    with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out


def summary() -> None:
    events = load_events()
    if not events:
        print("no_feedback_events")
        return

    by_signal = Counter(e["signal"] for e in events)
    by_source = Counter((e.get("source") or "unknown") for e in events)

    print("feedback_summary")
    print("signals:")
    for k, v in by_signal.most_common():
        print(f"  - {k}: {v}")
    print("sources:")
    for k, v in by_source.most_common(10):
        print(f"  - {k}: {v}")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("add")
    a.add_argument("--url", required=True)
    a.add_argument("--signal", required=True, choices=sorted(VALID_SIGNALS))
    a.add_argument("--source")
    a.add_argument("--note")

    sub.add_parser("summary")

    args = ap.parse_args()
    if args.cmd == "add":
        add_event(args.url, args.signal, args.source, args.note)
    elif args.cmd == "summary":
        summary()


if __name__ == "__main__":
    main()
