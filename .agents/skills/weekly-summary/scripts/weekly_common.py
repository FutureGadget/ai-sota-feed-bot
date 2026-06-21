"""Shared helpers for the weekly AI recap feature.

This module is intentionally dependency-free (stdlib only) so it can run in the
hourly/daily CI jobs and inside a Claude Code routine without extra installs.

Data model
----------
The weekly recap pipeline has three artifacts under ``data/weekly/``:

- ``input/<week>.json`` / ``input/latest.json``
    Machine-built bundle of the week's unique articles. This is the *reading
    material* an agent (Claude Code routine) consumes. Built by
    ``pipeline/build_weekly_input.py``.

- ``<week>.json``
    The published recap the agent writes (intro narrative + categorized
    article summaries). Schema documented in ``WEEKLY_SCHEMA`` below and in
    ``skills/weekly-summary/SKILL.md``.

- ``index.json`` / ``latest.json``
    Index of available recaps + a copy of the most recent one, rebuilt from the
    ``<week>.json`` files by ``pipeline/build_weekly_index.py``.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

def _find_repo_root(start: Path) -> Path:
    """Walk up from this file to the repo root (works wherever the script lives)."""
    for parent in [start, *start.parents]:
        if (parent / ".git").exists() or (parent / "data" / "processed").is_dir():
            return parent
    # Fallback: assume two levels up (legacy pipeline/ location).
    return start.parents[1]


ROOT = _find_repo_root(Path(__file__).resolve())
WEEKLY_DIR = ROOT / "data" / "weekly"
WEEKLY_INPUT_DIR = WEEKLY_DIR / "input"
PROCESSED_RUNS_DIR = ROOT / "data" / "processed" / "runs"
PROCESSED_RUNS_INDEX = ROOT / "data" / "processed" / "runs_index.json"

# Matches a published-recap filename, e.g. ``2026-W23.json`` (excludes
# index.json / latest.json so they are never treated as recaps).
WEEK_FILE_RE = re.compile(r"^\d{4}-W\d{2}\.json$")

# Friendly category names keyed by the item ``type`` field, in display order.
# The agent is free to introduce richer thematic categories; these are the
# deterministic fallback used by the input bundle and the seed sample.
CATEGORY_ORDER: list[tuple[str, str]] = [
    ("release", "Model & Product Releases"),
    ("research", "Research & Techniques"),
    ("news", "Industry News"),
]
CATEGORY_LABELS: dict[str, str] = {
    "release": "Model & Product Releases",
    "paper": "Research & Techniques",
    "research": "Research & Techniques",
    "news": "Industry News",
}
DEFAULT_CATEGORY = "Industry News"


def parse_ts(v: Any) -> datetime | None:
    """Parse a timestamp into an aware UTC datetime.

    Feed ``published`` values arrive in two shapes: ISO-8601
    (``2026-06-02T11:00:00+00:00``) and RFC-822 (``Mon, 01 Jun 2026 10:00:00
    GMT``). Try ISO first, then fall back to the email/RFC-822 parser so that
    neither sort order nor the published-date window silently drops articles.
    """
    if not v:
        return None
    s = str(v).strip()
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        try:
            d = parsedate_to_datetime(s)
        except Exception:
            return None
    if d is None:
        return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d


def load_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def iso_week_id(d: date) -> str:
    """ISO-8601 week id, e.g. ``2026-W23``."""
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def week_bounds(week_id: str) -> tuple[date, date]:
    """Return (Monday, Sunday) dates for an ISO ``YYYY-Www`` id."""
    year_s, week_s = week_id.split("-W")
    monday = date.fromisocalendar(int(year_s), int(week_s), 1)
    return monday, monday + timedelta(days=6)


def category_for_type(item_type: str | None) -> str:
    return CATEGORY_LABELS.get(str(item_type or "").lower(), DEFAULT_CATEGORY)


def clean_article(item: dict[str, Any]) -> dict[str, Any]:
    """Project a processed feed item down to the fields the recap needs."""
    summary = item.get("summary_1line") or item.get("summary") or ""
    summary = " ".join(str(summary).replace("\n", " ").split())[:400]
    return {
        "id": item.get("id") or item.get("url") or item.get("title"),
        "title": str(item.get("title") or "Untitled").strip(),
        "url": item.get("url") or "",
        "source": item.get("source") or "unknown",
        "type": str(item.get("type") or "news").lower(),
        "category": category_for_type(item.get("type")),
        "summary": summary,
        "published": item.get("published") or item.get("collected_at"),
    }


def norm_url(value: Any) -> str:
    """Normalize a URL for dedup comparison (strip + drop a trailing slash)."""
    s = str(value or "").strip()
    return s[:-1] if s.endswith("/") and len(s) > 1 else s


def recap_article_urls(exclude_week: str | None = None) -> set[str]:
    """Collect every article URL from already-published recaps.

    Scans ``data/weekly/<week>.json`` recap files (skipping ``exclude_week``)
    and returns the set of normalized article URLs they contain. Used to keep
    an article that lingers in the feed across a week boundary from being
    re-published in a later week's recap.
    """
    urls: set[str] = set()
    if not WEEKLY_DIR.is_dir():
        return urls
    for path in WEEKLY_DIR.glob("*.json"):
        if not WEEK_FILE_RE.match(path.name):
            continue
        data = load_json(path, None)
        if not isinstance(data, dict):
            continue
        if exclude_week and data.get("week") == exclude_week:
            continue
        for cat in data.get("categories", []) or []:
            if not isinstance(cat, dict):
                continue
            for art in cat.get("articles", []) or []:
                if isinstance(art, dict) and art.get("url"):
                    urls.add(norm_url(art["url"]))
    return urls


def collect_week_articles(
    start: datetime,
    end: datetime,
    *,
    require_published_in_window: bool = True,
    exclude_urls: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Deduped list of unique articles that *happened* in [start, end].

    Walks the processed run snapshots, dedupes by URL (falling back to id), and
    keeps the richest copy seen. Sorted newest-first by published date.

    Two filters guard against re-publishing stale articles that linger in the
    feed across a week boundary (an article can persist in the live feed for
    several days, so its run timestamps straddle two ISO weeks):

    - ``require_published_in_window``: keep an article only if its own
      ``published`` date falls within [start, end] — i.e. it was actually
      published this week, not merely still being collected this week.
    - ``exclude_urls``: drop any article whose URL already appeared in a
      previously published recap (see :func:`recap_article_urls`).
    """
    index = load_json(PROCESSED_RUNS_INDEX, [])
    if not isinstance(index, list):
        return []

    exclude_urls = exclude_urls or set()
    by_key: dict[str, dict[str, Any]] = {}
    for row in index:
        run_at = parse_ts(row.get("run_at"))
        if not run_at or run_at < start or run_at > end:
            continue
        rel = row.get("path") or row.get("file")
        if not rel:
            continue
        run = load_json(PROCESSED_RUNS_DIR / rel, None)
        items = run.get("items") if isinstance(run, dict) else run
        if not isinstance(items, list):
            continue
        for it in items:
            if not isinstance(it, dict):
                continue
            cleaned = clean_article(it)
            key = cleaned["url"] or cleaned["id"] or cleaned["title"]
            if not key:
                continue
            # #1: only articles actually published within the week window.
            if require_published_in_window:
                pub = parse_ts(cleaned.get("published"))
                if pub is None or pub < start or pub > end:
                    continue
            # #2: skip anything already covered by an earlier week's recap.
            if exclude_urls and norm_url(cleaned["url"]) in exclude_urls:
                continue
            # Prefer the copy with the longer summary (more informative).
            prev = by_key.get(key)
            if prev is None or len(cleaned["summary"]) > len(prev["summary"]):
                by_key[key] = cleaned

    articles = list(by_key.values())
    articles.sort(key=lambda a: parse_ts(a.get("published")) or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return articles


def fmt_range(start: date, end: date) -> str:
    """Human range like ``Jun 1–7, 2026`` or ``Dec 29, 2025 – Jan 4, 2026``."""
    if start.year == end.year and start.month == end.month:
        return f"{start.strftime('%b')} {start.day}–{end.day}, {end.year}"
    if start.year == end.year:
        return f"{start.strftime('%b %-d')} – {end.strftime('%b %-d')}, {end.year}"
    return f"{start.strftime('%b %-d, %Y')} – {end.strftime('%b %-d, %Y')}"


# Minimal description of the published recap schema, surfaced in errors and docs.
WEEKLY_SCHEMA = {
    "week": "ISO week id, e.g. 2026-W23",
    "start": "YYYY-MM-DD (Monday)",
    "end": "YYYY-MM-DD (Sunday)",
    "title": "string headline, e.g. 'What happened in AI — Jun 1–7, 2026'",
    "generated_at": "ISO-8601 timestamp",
    "intro": "narrative overview: array of paragraph strings (a plain string also works)",
    "highlights": "optional: array of 3-6 scannable one-line takeaways (rendered as an 'In 30 seconds' list)",
    "article_count": "int, number of source articles considered",
    "categories": [
        {
            "name": "category display name",
            "slug": "url-safe slug",
            "summary": "1-2 sentence what-happened for this category",
            "articles": [
                {
                    "title": "string",
                    "summary": "one-line takeaway",
                    "source": "source name",
                    "url": "original source link",
                    "published": "ISO-8601 timestamp (optional)",
                }
            ],
        }
    ],
}


def validate_recap(data: Any) -> list[str]:
    """Return a list of human-readable validation errors (empty == valid)."""
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["recap must be a JSON object"]
    for field in ("week", "start", "end", "title", "categories"):
        if field not in data:
            errors.append(f"missing required field: {field}")
    cats = data.get("categories")
    if not isinstance(cats, list) or not cats:
        errors.append("'categories' must be a non-empty array")
        return errors
    for ci, cat in enumerate(cats):
        if not isinstance(cat, dict):
            errors.append(f"categories[{ci}] must be an object")
            continue
        if not cat.get("name"):
            errors.append(f"categories[{ci}] missing 'name'")
        arts = cat.get("articles")
        if not isinstance(arts, list) or not arts:
            errors.append(f"categories[{ci}] '{cat.get('name')}' has no articles")
            continue
        for ai, art in enumerate(arts):
            if not isinstance(art, dict):
                errors.append(f"categories[{ci}].articles[{ai}] must be an object")
                continue
            if not art.get("title"):
                errors.append(f"categories[{ci}].articles[{ai}] missing 'title'")
            if not art.get("url"):
                errors.append(f"categories[{ci}].articles[{ai}] missing 'url' (source link)")
    return errors


def slugify(value: str) -> str:
    out = "".join(c.lower() if c.isalnum() else "-" for c in value)
    while "--" in out:
        out = out.replace("--", "-")
    return out.strip("-") or "category"
