"""Hacker News votes for the stories the collector took from HN.

The collector reads ``hnrss.org/newest``, so every HN item arrives with the
point count it had minutes after submission (almost always 1). This module
re-reads each story's points and comment count from the HN API while the
story is young, so the recap bundles can show how HN actually voted.

    python pipeline/hn_signal.py refresh     # run by run_full.sh, fail-open

Store: ``data/processed/hn_signal.json``

    {"version": 1, "items": {"<hn id>": {"url", "points", "comments",
                                         "posted_at", "checked_at"}}}

A story is re-read when it is under ``WINDOW_HOURS`` old and its last read is
``REFRESH_HOURS`` old or more, at most ``MAX_REQUESTS`` reads per run, oldest
read first. Entries older than ``KEEP_DAYS`` are dropped.
"""

from __future__ import annotations

import argparse
import json
import re
import urllib.request
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Callable, Iterable

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
STORE_PATH = ROOT / "data" / "processed" / "hn_signal.json"
SOURCE = "hackernews_ai"
API = "https://hacker-news.firebaseio.com/v0/item/{id}.json"

WINDOW_HOURS = 72
REFRESH_HOURS = 4
MAX_REQUESTS = 150
KEEP_DAYS = 10
RAW_DAYS = 3

_ID_RE = re.compile(r"news\.ycombinator\.com/item\?id=(\d+)")

Fetch = Callable[[str], "dict[str, Any] | None"]


def hn_id(item: dict[str, Any]) -> str | None:
    for field in ("url", "summary", "comments_url"):
        match = _ID_RE.search(str(item.get(field) or ""))
        if match:
            return match.group(1)
    return None


def _ts(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(text)
        except (TypeError, ValueError):
            return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def load_store(path: Path = STORE_PATH) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    items = data.get("items") if isinstance(data, dict) else None
    return {"version": 1, "items": items if isinstance(items, dict) else {}}


def save_store(store: dict[str, Any], path: Path = STORE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(store, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def recent_raw_items(now: datetime, raw_dir: Path = RAW_DIR, days: int = RAW_DAYS) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for offset in range(days):
        path = raw_dir / (now - timedelta(days=offset)).strftime("%Y-%m-%d") / "items.json"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        rows = data.get("items") if isinstance(data, dict) else data
        out.extend(r for r in rows or [] if isinstance(r, dict) and r.get("source") == SOURCE)
    return out


def fetch_item(item_id: str, timeout: float = 10.0) -> dict[str, Any] | None:
    req = urllib.request.Request(API.format(id=item_id), headers={"User-Agent": "ai-sota-feed-bot/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - fixed https host
        data = json.loads(resp.read().decode("utf-8"))
    return data if isinstance(data, dict) else None


def refresh(
    store: dict[str, Any],
    raw_items: Iterable[dict[str, Any]],
    now: datetime,
    fetch: Fetch = fetch_item,
    max_requests: int = MAX_REQUESTS,
) -> dict[str, int]:
    """Update ``store`` in place; return counts for the log line."""
    items = store["items"]
    for raw in raw_items:
        key = hn_id(raw)
        if not key:
            continue
        entry = items.setdefault(key, {})
        entry.setdefault("url", str(raw.get("url") or ""))
        entry.setdefault("posted_at", (_ts(raw.get("published")) or now).isoformat())

    def due(entry: dict[str, Any]) -> bool:
        posted = _ts(entry.get("posted_at"))
        if posted is None or now - posted > timedelta(hours=WINDOW_HOURS):
            return False
        checked = _ts(entry.get("checked_at"))
        return checked is None or now - checked >= timedelta(hours=REFRESH_HOURS)

    queue = sorted((k for k, e in items.items() if due(e)), key=lambda k: items[k].get("checked_at") or "")
    stats = {"due": len(queue), "read": 0, "failed": 0}
    for key in queue[:max_requests]:
        try:
            data = fetch(key)
        except Exception:  # one unreachable item must not stop the rest
            data = None
        if not data or data.get("deleted") or data.get("dead"):
            stats["failed"] += 1
            continue
        entry = items[key]
        entry["points"] = int(data.get("score") or 0)
        entry["comments"] = int(data.get("descendants") or 0)
        if data.get("time"):
            entry["posted_at"] = datetime.fromtimestamp(int(data["time"]), tz=timezone.utc).isoformat()
        entry["checked_at"] = now.isoformat()
        stats["read"] += 1

    cutoff = now - timedelta(days=KEEP_DAYS)
    for key in [k for k, e in items.items() if (_ts(e.get("posted_at")) or now) < cutoff]:
        del items[key]
    stats["stored"] = len(items)
    return stats


def annotate(articles: list[dict[str, Any]], store: dict[str, Any] | None = None) -> int:
    """Add ``hn_points``/``hn_comments`` to HN articles with a stored read."""
    store = store if store is not None else load_store()
    by_url = {e.get("url"): e for e in store["items"].values() if e.get("url") and "points" in e}
    by_id = {k: e for k, e in store["items"].items() if "points" in e}
    count = 0
    for article in articles:
        if article.get("source") != SOURCE:
            continue
        key = hn_id(article)
        entry = by_id.get(key) if key else None
        entry = entry or by_url.get(article.get("url"))
        if not entry:
            continue
        article["hn_points"] = entry["points"]
        article["hn_comments"] = entry.get("comments", 0)
        count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=["refresh"])
    parser.add_argument("--max-requests", type=int, default=MAX_REQUESTS)
    args = parser.parse_args()
    now = datetime.now(timezone.utc)
    store = load_store()
    stats = refresh(store, recent_raw_items(now), now, max_requests=args.max_requests)
    save_store(store)
    print("hn_signal " + " ".join(f"{k}={v}" for k, v in stats.items()))


if __name__ == "__main__":
    main()
