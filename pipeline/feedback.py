#!/usr/bin/env python3
"""Reader feedback loop utilities (spec: docs/product-specs/feedback-loop.md).

Feedback events are stored append-only in data/feedback/events.jsonl, one JSON
object per line:
  ts           ISO timestamp
  url          item URL the feedback refers to
  signal       useful | irrelevant | hype
  source       event channel: manual (CLI) | web (synced from PostHog)
  note         optional free text (manual only)
  item_id      feed item key (web only)
  item_source  feed source, e.g. openai_blog (web only)
  user         anonymous reader id (web only)
  action       set | unset — readers can retract a signal (web only)
  uuid         PostHog event uuid, used for sync de-duplication (web only)

Commands:
  add           append a manual feedback event
  summary       aggregate net feedback by signal and item source
  sync-posthog  pull `item_feedback` web events from PostHog into events.jsonl

sync-posthog reads POSTHOG_PERSONAL_API_KEY, POSTHOG_PROJECT_ID and optional
POSTHOG_API_HOST (default https://us.posthog.com) from the environment and
exits cleanly (no-op) when they are missing.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
EVENTS_PATH = ROOT / "data" / "feedback" / "events.jsonl"

SIGNALS = ("useful", "irrelevant", "hype")
ACTIONS = ("set", "unset")
SYNC_OVERLAP_MINUTES = 30
SYNC_LIMIT = 10000


def load_events(path: Path = EVENTS_PATH) -> list[dict]:
    if not path.exists():
        return []
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(ev, dict):
            events.append(ev)
    return events


def append_events(rows: list[dict], path: Path = EVENTS_PATH) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_ts(value) -> datetime | None:
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def item_source_of(ev: dict) -> str:
    src = str(ev.get("item_source") or "").strip()
    if src:
        return src
    host = urlparse(str(ev.get("url") or "")).netloc
    return host or "unknown"


def net_events(events: list[dict]) -> list[dict]:
    """Reduce raw events to net state: latest set/unset per (user, item).

    Events without a user (manual CLI entries, legacy rows) count
    individually and cannot be retracted.
    """
    state: dict[tuple[str, str], dict] = {}
    ordered = sorted(events, key=lambda e: str(e.get("ts") or ""))
    for i, ev in enumerate(ordered):
        user = str(ev.get("user") or f"_row:{i}")
        item = str(ev.get("item_id") or ev.get("url") or f"_row:{i}")
        if str(ev.get("action") or "set") == "unset":
            state.pop((user, item), None)
        else:
            state[(user, item)] = ev
    return list(state.values())


def cmd_add(args: argparse.Namespace) -> int:
    event = {
        "ts": utc_now().isoformat(),
        "url": args.url,
        "signal": args.signal,
        "source": "manual",
        "note": args.note,
    }
    append_events([event])
    print(f"feedback_added signal={args.signal} url={args.url}")
    return 0


def cmd_summary(args: argparse.Namespace) -> int:
    events = load_events()
    if args.days:
        cutoff = utc_now() - timedelta(days=args.days)
        events = [e for e in events if (parse_ts(e.get("ts")) or utc_now()) >= cutoff]
    net = net_events(events)
    print(f"Net feedback: {len(net)} (from {len(events)} raw events)")
    if not net:
        return 0

    by_signal: dict[str, int] = {}
    by_source: dict[str, dict[str, int]] = {}
    for ev in net:
        signal = str(ev.get("signal") or "unknown")
        by_signal[signal] = by_signal.get(signal, 0) + 1
        per = by_source.setdefault(item_source_of(ev), {})
        per[signal] = per.get(signal, 0) + 1

    print("By signal: " + " | ".join(f"{s}={by_signal.get(s, 0)}" for s in SIGNALS))
    print("By item source:")
    for src in sorted(by_source, key=lambda s: -sum(by_source[s].values())):
        counts = " ".join(f"{s}={by_source[src].get(s, 0)}" for s in SIGNALS)
        print(f"  {src:<28} {counts}")
    return 0


def cmd_sync_posthog(args: argparse.Namespace) -> int:
    api_key = os.environ.get("POSTHOG_PERSONAL_API_KEY", "").strip()
    project_id = os.environ.get("POSTHOG_PROJECT_ID", "").strip()
    host = (os.environ.get("POSTHOG_API_HOST", "").strip() or "https://us.posthog.com").rstrip("/")
    if not api_key or not project_id:
        print("posthog_sync_skipped reason=missing_credentials")
        return 0

    import requests

    existing = load_events()
    known_uuids = {str(e["uuid"]) for e in existing if e.get("uuid")}
    last_web_ts = max(
        (parse_ts(e.get("ts")) for e in existing if e.get("source") == "web"),
        key=lambda d: d or datetime.min.replace(tzinfo=timezone.utc),
        default=None,
    )
    since = last_web_ts - timedelta(minutes=SYNC_OVERLAP_MINUTES) if last_web_ts else (
        utc_now() - timedelta(days=args.days)
    )

    hogql = (
        "SELECT uuid, timestamp, distinct_id, properties.item_id, properties.url, "
        "properties.source, properties.signal, properties.action "
        "FROM events WHERE event = 'item_feedback' "
        f"AND timestamp >= toDateTime('{since.strftime('%Y-%m-%d %H:%M:%S')}') "
        f"ORDER BY timestamp ASC LIMIT {SYNC_LIMIT}"
    )
    resp = requests.post(
        f"{host}/api/projects/{project_id}/query",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"query": {"kind": "HogQLQuery", "query": hogql}},
        timeout=60,
    )
    resp.raise_for_status()
    results = resp.json().get("results") or []

    rows = []
    for uuid, ts, distinct_id, item_id, url, item_source, signal, action in results:
        uuid = str(uuid or "")
        if not uuid or uuid in known_uuids:
            continue
        signal = str(signal or "").strip()
        action = str(action or "set").strip()
        if signal not in SIGNALS or action not in ACTIONS:
            continue
        known_uuids.add(uuid)
        ts_dt = parse_ts(ts)
        rows.append({
            "ts": (ts_dt or utc_now()).isoformat(),
            "url": str(url or "") or None,
            "signal": signal,
            "source": "web",
            "note": None,
            "item_id": str(item_id or "") or None,
            "item_source": str(item_source or "") or None,
            "user": str(distinct_id or "") or None,
            "action": action,
            "uuid": uuid,
        })

    append_events(rows)
    print(f"posthog_sync_done fetched={len(results)} appended={len(rows)} since={since.isoformat()}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="append a manual feedback event")
    p_add.add_argument("--url", required=True)
    p_add.add_argument("--signal", required=True, choices=SIGNALS)
    p_add.add_argument("--note", default=None)
    p_add.set_defaults(func=cmd_add)

    p_summary = sub.add_parser("summary", help="aggregate net feedback by signal/source")
    p_summary.add_argument("--days", type=int, default=None, help="only include events from the last N days")
    p_summary.set_defaults(func=cmd_summary)

    p_sync = sub.add_parser("sync-posthog", help="pull item_feedback events from PostHog")
    p_sync.add_argument("--days", type=int, default=7, help="initial lookback window when events.jsonl has no web events yet")
    p_sync.set_defaults(func=cmd_sync_posthog)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
