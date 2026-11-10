#!/usr/bin/env python3
"""Watchlist entity layer: which stories are news about a thing a reader watches.

``config/watch.yaml`` lists the watchable entities (tools, model families,
engineering topics). This module matches stored stories against them by title
and source, then writes two artifacts:

- ``data/watch/index.json``  per-entity recent stories with URLs; read by
  ``publish/publish_follows.py`` to email readers when something they watch
  changes.
- ``web/watch-data.json``    the same entities with their matching rules and a
  shorter story list; read by ``web/watchlist.js`` for Watch chips and the
  feed's watchlist module.

Both are deterministic for a given story store (no build timestamp), so an
hourly run with no new matching story leaves them byte-identical.

The matching rules are duplicated in ``web/watchlist.js``;
``tests/fixtures/watch_match_cases.json`` pins both implementations.

Usage:
    python pipeline/watch.py build
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "watch.yaml"
STORE_DIR = ROOT / "data" / "stories"
INDEX_PATH = ROOT / "data" / "watch" / "index.json"
WEB_PATH = ROOT / "web" / "watch-data.json"

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,99}$")
MONTH_FILE_RE = re.compile(r"^\d{4}-\d{2}\.json$")
KINDS = ("tool", "model", "topic")
INDEX_ITEMS = 12  # per entity, for the email job
WEB_ITEMS = 5     # per entity, for the browser
DEFAULT_WINDOW_DAYS = 30

# Pre-release tags on release-type stories (v0.34.0rc0, 0.169.0-alpha.8,
# 1.2.0.dev3). They stay in the feed's Releases tab; a watcher is told about
# the release, not each build on the way to it.
_PRERELEASE = re.compile(r"(?i)(alpha|beta|nightly|preview|canary|\d[-.]?(rc|a|b)\.?\d+\b|\.dev\d*\b)")

_NON_WORD = re.compile(r"[^a-z0-9.+]+")
_TRAILING_DOT = re.compile(r"\.+(?= |$)")


def normalize(text: object) -> str:
    """Lowercase, punctuation to spaces, padded with one space on each side.

    Dots and plus signs survive inside a word (``z.ai``, ``gpt-5.5``, ``c++``);
    a sentence-ending dot does not.
    """
    s = _NON_WORD.sub(" ", str(text or "").lower())
    s = _TRAILING_DOT.sub("", s)
    return " " + " ".join(s.split()) + " "


def _compile_term(term: object) -> tuple[str, bool] | None:
    raw = str(term or "").strip()
    prefix = raw.endswith("*")
    body = normalize(raw.rstrip("*")).strip()
    return (body, prefix) if body else None


def _term_matches(norm_title: str, term: tuple[str, bool]) -> bool:
    body, prefix = term
    return (" " + body) in norm_title if prefix else (" " + body + " ") in norm_title


def load_entities(path: Path = CONFIG_PATH) -> tuple[list[dict], int]:
    """Validated entities in config order, plus the story window in days."""
    # Imported here so render_static_pages.py can import this module in a build
    # environment without PyYAML; it then renders story pages without chips.
    import yaml

    cfg = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    window = int(cfg.get("window_days") or DEFAULT_WINDOW_DAYS)
    entities: list[dict] = []
    seen: set[str] = set()
    for raw in cfg.get("entities") or []:
        slug = str(raw.get("slug") or "")
        label = str(raw.get("label") or "").strip()
        kind = str(raw.get("kind") or "")
        if not SLUG_RE.match(slug) or slug in seen:
            raise ValueError(f"watch.yaml: bad or duplicate slug {slug!r}")
        if not label or kind not in KINDS:
            raise ValueError(f"watch.yaml: {slug} needs a label and a kind in {KINDS}")
        terms = [str(t).strip() for t in raw.get("terms") or [] if _compile_term(t)]
        sources = [str(s).strip() for s in raw.get("sources") or [] if str(s).strip()]
        if not terms and not sources:
            raise ValueError(f"watch.yaml: {slug} has no terms or sources")
        seen.add(slug)
        entities.append({
            "slug": slug,
            "label": label,
            "kind": kind,
            "terms": terms,
            "not": [str(t).strip() for t in raw.get("not") or [] if _compile_term(t)],
            "sources": sources,
        })
    return entities, window


def match_entities(title: object, source: object, entities: list[dict]) -> list[str]:
    """Slugs of the entities a story is news about, in config order."""
    norm = normalize(title)
    src = str(source or "").strip()
    out: list[str] = []
    for ent in entities:
        if src and src in ent["sources"]:
            out.append(ent["slug"])
            continue
        text = norm
        for phrase in ent["not"]:
            body = normalize(phrase)
            text = text.replace(body, " ")
        if any(_term_matches(text, t) for t in map(_compile_term, ent["terms"]) if t):
            out.append(ent["slug"])
    return out


def is_prerelease(rec: dict) -> bool:
    return str(rec.get("type") or "") == "release" and bool(_PRERELEASE.search(str(rec.get("title") or "")))


def _parse_dt(value: object) -> datetime | None:
    try:
        dt = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def load_recent_stories(window_days: int, now: datetime | None = None, store_dir: Path = STORE_DIR) -> list[dict]:
    """Stories that entered the store within the window, newest first.

    "Entered the store" (``first_seen``) is when a reader could first have seen
    the story here, which is what "changed since your last visit" means. A
    story published long ago but collected today still counts as today's.
    """
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=window_days)
    rows: list[tuple[datetime, dict]] = []
    if not store_dir.is_dir():
        return []
    for shard in sorted(store_dir.iterdir()):
        if not MONTH_FILE_RE.match(shard.name):
            continue
        # A month shard can only hold stories from that month or later runs of
        # it; skip shards that end before the window opens.
        year, month = int(shard.name[:4]), int(shard.name[5:7])
        shard_end = datetime(year + month // 12, month % 12 + 1, 1, tzinfo=timezone.utc)
        if shard_end + timedelta(days=window_days) < cutoff:
            continue
        try:
            records = json.loads(shard.read_text(encoding="utf-8"))
        except Exception:
            continue
        for rec in records.values() if isinstance(records, dict) else []:
            if not isinstance(rec, dict):
                continue
            seen = _parse_dt(rec.get("first_seen")) or _parse_dt(rec.get("published"))
            if not seen or seen < cutoff or seen > now + timedelta(days=1):
                continue
            if not rec.get("sid") or not str(rec.get("title") or "").strip() or not rec.get("url"):
                continue
            rows.append((seen, rec))
    rows.sort(key=lambda r: (r[0], str(r[1].get("sid"))), reverse=True)
    # UTC everywhere, so the email job can compare timestamps as strings.
    return [dict(rec, _seen=seen.astimezone(timezone.utc).isoformat()) for seen, rec in rows]


def build_index(entities: list[dict], stories: list[dict], window_days: int) -> dict:
    by_slug: dict[str, list[dict]] = {e["slug"]: [] for e in entities}
    for rec in stories:
        if is_prerelease(rec):
            continue
        for slug in match_entities(rec.get("title"), rec.get("source"), entities):
            by_slug[slug].append(rec)
    out = []
    for ent in entities:
        matched = by_slug[ent["slug"]]
        out.append({
            **ent,
            "count": len(matched),
            "last_updated": matched[0]["_seen"] if matched else "",
            "items": [
                {
                    "sid": str(r["sid"]),
                    "title": " ".join(str(r.get("title") or "").split()),
                    "source": str(r.get("source") or ""),
                    "url": str(r.get("url") or ""),
                    "first_seen": r["_seen"],
                }
                for r in matched[:INDEX_ITEMS]
            ],
        })
    return {
        "version": 1,
        "window_days": window_days,
        "updated_at": max((e["last_updated"] for e in out), default=""),
        "entities": out,
    }


def web_payload(index: dict) -> dict:
    """The browser's copy: matching rules plus a short story list, no URLs."""
    return {
        "version": index["version"],
        "window_days": index["window_days"],
        "updated_at": index["updated_at"],
        "entities": [
            {
                "slug": e["slug"],
                "label": e["label"],
                "kind": e["kind"],
                "terms": e["terms"],
                "not": e["not"],
                "sources": e["sources"],
                "count": e["count"],
                "last_updated": e["last_updated"],
                "items": [
                    {"sid": i["sid"], "title": i["title"], "first_seen": i["first_seen"]}
                    for i in e["items"][:WEB_ITEMS]
                ],
            }
            for e in index["entities"]
        ],
    }


def _write_if_changed(path: Path, payload: dict) -> bool:
    text = json.dumps(payload, ensure_ascii=False, indent=1) + "\n"
    if path.is_file() and path.read_text(encoding="utf-8") == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


def cmd_build() -> int:
    entities, window = load_entities()
    index = build_index(entities, load_recent_stories(window), window)
    changed = _write_if_changed(INDEX_PATH, index)
    _write_if_changed(WEB_PATH, web_payload(index))
    active = sum(1 for e in index["entities"] if e["count"])
    print(f"watch_index_built=true entities={len(entities)} active={active} changed={str(changed).lower()}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("command", choices=["build"])
    ap.parse_args()
    return cmd_build()


if __name__ == "__main__":
    raise SystemExit(main())
