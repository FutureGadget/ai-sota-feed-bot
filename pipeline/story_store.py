"""Durable per-story record store backing the /story/<sid> permalink pages.

Ranked feed snapshots (``data/processed/latest.json`` + ``data/processed/
runs/**``) are pruned after ~45 days, which is why share links and recap
references eventually go dead. This module captures every story that made a
published snapshot into an append-only store the static renderer and the
share endpoint can rely on forever:

- ``data/stories/<YYYY-MM>.json``  one shard per publication month,
  ``{sid: record}``
- ``data/stories/index.json``      compact ``{sid: {"month", "title"}}`` map
  (small enough to bundle into the /s share function)

``sid`` is ``sha256(normalized_url)[:16]`` — derivable from a URL alone, so
``api/share.js`` can map an incoming share URL to its story page without a
full-store lookup. Keep the normalization in sync with ``storySid`` there.

Usage:
    python pipeline/story_store.py sync   # upsert stories from processed runs
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"
STORE_DIR = ROOT / "data" / "stories"

MONTH_FILE_RE = re.compile(r"^\d{4}-\d{2}\.json$")
SUMMARY_MAX_CHARS = 1500
TAG_RE = re.compile(r"<[^>]+>")

# Legacy boilerplate that predates "why_it_matters only from real signal";
# storing it would stamp identical filler on hundreds of story pages.
GENERIC_WHY = {"Potential relevance to AI platform engineering; verify practical impact."}

# Content fields carried onto the story record. Upserts only overwrite with
# truthy values so a later run with a blank field can't erase earlier signal.
CONTENT_FIELDS = (
    "title",
    "source",
    "type",
    "summary",
    "summary_1line",
    "why_it_matters",
    "release_highlights",
    "matched_topics",
    "also_covered",
    "image_url",
)


def strip_html(value) -> str:
    """Release feeds ship HTML changelog summaries; store readable text."""
    text = TAG_RE.sub(" ", html.unescape(str(value or "")))
    return " ".join(text.split())


def norm_url(value) -> str:
    s = str(value or "").strip()
    return s[:-1] if s.endswith("/") and len(s) > 1 else s


def story_sid(url: str) -> str:
    return hashlib.sha256(norm_url(url).encode("utf-8")).hexdigest()[:16]


def parse_dt(value) -> datetime | None:
    s = str(value or "").strip()
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        try:
            dt = parsedate_to_datetime(s)
        except Exception:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def load_json(path: Path, fallback):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def iter_run_items():
    """Yield (run_at, item) for every item in every available snapshot, oldest
    run first so newer runs win field upserts."""
    rows = []
    for row in load_json(PROCESSED_DIR / "runs_index.json", []):
        rel = row.get("path") or row.get("file") if isinstance(row, dict) else None
        if rel:
            rows.append((str(row.get("run_at") or ""), PROCESSED_DIR / "runs" / rel))
    rows.sort(key=lambda r: r[0])
    now = datetime.now(timezone.utc).isoformat()
    rows.append((now, PROCESSED_DIR / "latest.json"))
    for run_at, path in rows:
        run = load_json(path, None)
        items = run.get("items") if isinstance(run, dict) else run
        for it in items or []:
            if isinstance(it, dict):
                yield run_at, it


def story_record(sid: str, item: dict, run_at: str) -> dict:
    published = parse_dt(item.get("published")) or parse_dt(item.get("collected_at"))
    rec = {
        "sid": sid,
        "id": str(item.get("id") or ""),
        "url": norm_url(item.get("url")),
        "published": published.isoformat() if published else None,
        "first_seen": str(item.get("collected_at") or run_at or ""),
    }
    for field in CONTENT_FIELDS:
        value = item.get(field)
        if field in ("summary", "summary_1line") and value:
            value = strip_html(value)
        if field == "summary" and value:
            value = value[:SUMMARY_MAX_CHARS]
        if field == "why_it_matters" and str(value or "").strip() in GENERIC_WHY:
            value = ""
        if value:
            rec[field] = value
    return rec


def record_month(rec: dict) -> str:
    dt = parse_dt(rec.get("published")) or parse_dt(rec.get("first_seen"))
    return (dt or datetime.now(timezone.utc)).strftime("%Y-%m")


def load_store() -> dict[str, dict]:
    """All story records across shards, keyed by sid."""
    stories: dict[str, dict] = {}
    if not STORE_DIR.is_dir():
        return stories
    for path in sorted(STORE_DIR.glob("*.json")):
        if not MONTH_FILE_RE.match(path.name):
            continue
        shard = load_json(path, {})
        if isinstance(shard, dict):
            stories.update({k: v for k, v in shard.items() if isinstance(v, dict)})
    return stories


def load_index() -> dict[str, dict]:
    index = load_json(STORE_DIR / "index.json", {})
    return index if isinstance(index, dict) else {}


def write_store(stories: dict[str, dict]) -> None:
    STORE_DIR.mkdir(parents=True, exist_ok=True)
    shards: dict[str, dict] = {}
    for sid, rec in stories.items():
        shards.setdefault(record_month(rec), {})[sid] = rec
    for month, shard in shards.items():
        (STORE_DIR / f"{month}.json").write_text(
            json.dumps(shard, ensure_ascii=False, sort_keys=True, indent=1) + "\n",
            encoding="utf-8",
        )
    index = {
        sid: {"month": record_month(rec), "title": str(rec.get("title") or "")}
        for sid, rec in stories.items()
    }
    (STORE_DIR / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, sort_keys=True, indent=0) + "\n",
        encoding="utf-8",
    )


def sync() -> tuple[int, int]:
    """Upsert stories from available processed snapshots. Returns
    (new_stories, total_stories)."""
    stories = load_store()
    before = len(stories)
    for run_at, item in iter_run_items():
        url = norm_url(item.get("url"))
        if not url.startswith(("http://", "https://")) or not item.get("title"):
            continue
        sid = story_sid(url)
        fresh = story_record(sid, item, run_at)
        prev = stories.get(sid)
        if prev is None:
            stories[sid] = fresh
            continue
        # Append-only upsert: keep earliest first_seen, refresh content fields
        # only when the newer run actually has a value.
        if str(fresh.get("first_seen") or "") < str(prev.get("first_seen") or ""):
            prev["first_seen"] = fresh["first_seen"]
        if fresh.get("published"):
            prev["published"] = fresh["published"]
        for field in ("id", *CONTENT_FIELDS):
            if fresh.get(field):
                prev[field] = fresh[field]
    write_store(stories)
    return len(stories) - before, len(stories)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("sync", help="upsert stories from processed snapshots")
    args = ap.parse_args()
    if args.cmd == "sync":
        new, total = sync()
        print(f"story store synced: +{new} new, {total} total -> data/stories/")


if __name__ == "__main__":
    main()
