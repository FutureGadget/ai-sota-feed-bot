"""Shared helpers for the daily AI recap feature.

This module is intentionally dependency-free (stdlib only) so it can run in the
hourly/daily CI jobs and inside a Claude Code routine without extra installs.

Data model
----------
The daily recap pipeline has three artifacts under ``data/daily/``:

- ``input/<date>.json`` / ``input/latest.json``
    Machine-built bundle of the day's unique articles. This is the *reading
    material* an agent (Claude Code routine) consumes. Built by
    ``build_daily_input.py``.

- ``<date>.json``
    The published recap the agent writes (intro narrative + categorized
    article summaries). Schema documented in ``DAILY_SCHEMA`` below and in
    ``skills/daily-summary/SKILL.md``.

- ``index.json`` / ``latest.json``
    Index of available recaps + a copy of the most recent one, rebuilt from the
    ``<date>.json`` files by ``build_daily_index.py``.

This mirrors the weekly recap feature, but the unit is a single calendar day
(``YYYY-MM-DD``) instead of an ISO week.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime, time, timedelta, timezone
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
DAILY_DIR = ROOT / "data" / "daily"
DAILY_INPUT_DIR = DAILY_DIR / "input"
PROCESSED_RUNS_DIR = ROOT / "data" / "processed" / "runs"
PROCESSED_RUNS_INDEX = ROOT / "data" / "processed" / "runs_index.json"

# Matches a published-recap filename, e.g. ``2026-06-07.json`` (excludes
# index.json / latest.json so they are never treated as recaps).
DATE_FILE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}\.json$")
# Matches a bare date id, e.g. ``2026-06-07``.
DATE_ID_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Friendly category names keyed by the item ``type`` field, in display order.
# The agent is free to introduce richer thematic categories; these are the
# deterministic fallback used by the input bundle and the seed sample.
CATEGORY_ORDER: list[tuple[str, str]] = [
    ("release", "Model & Product Releases"),
    ("paper", "Research Papers"),
    ("research", "Research & Techniques"),
    ("news", "Industry News"),
]
CATEGORY_LABELS: dict[str, str] = dict(CATEGORY_ORDER)
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


def date_id(d: date) -> str:
    """Calendar date id, e.g. ``2026-06-07``."""
    return d.isoformat()


def day_bounds(day_id: str) -> tuple[date, date]:
    """Return (day, day) for a ``YYYY-MM-DD`` id.

    The daily window is a single calendar day; this returns the same date for
    both bounds so callers can share the (start, end) shape used by weekly.
    """
    d = date.fromisoformat(day_id)
    return d, d


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


def recap_article_urls(exclude_date: str | None = None) -> set[str]:
    """Collect every article URL from already-published daily recaps.

    Scans ``data/daily/<date>.json`` recap files (skipping ``exclude_date``)
    and returns the set of normalized article URLs they contain. Used to keep
    an article that lingers in the feed across a day boundary from being
    re-published in a later day's recap.
    """
    urls: set[str] = set()
    if not DAILY_DIR.is_dir():
        return urls
    for path in DAILY_DIR.glob("*.json"):
        if not DATE_FILE_RE.match(path.name):
            continue
        data = load_json(path, None)
        if not isinstance(data, dict):
            continue
        if exclude_date and data.get("date") == exclude_date:
            continue
        for cat in data.get("categories", []) or []:
            if not isinstance(cat, dict):
                continue
            for art in cat.get("articles", []) or []:
                if isinstance(art, dict) and art.get("url"):
                    urls.add(norm_url(art["url"]))
    return urls


def collect_day_articles(
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
    feed across a day boundary (an article can persist in the live feed for
    several days, so its run timestamps straddle two calendar days):

    - ``require_published_in_window``: keep an article only if its own
      ``published`` date falls within [start, end] — i.e. it was actually
      published today, not merely still being collected today.
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
            # #1: only articles actually published within the day window.
            if require_published_in_window:
                pub = parse_ts(cleaned.get("published"))
                if pub is None or pub < start or pub > end:
                    continue
            # #2: skip anything already covered by an earlier day's recap.
            if exclude_urls and norm_url(cleaned["url"]) in exclude_urls:
                continue
            # Prefer the copy with the longer summary (more informative).
            prev = by_key.get(key)
            if prev is None or len(cleaned["summary"]) > len(prev["summary"]):
                by_key[key] = cleaned

    articles = list(by_key.values())
    articles.sort(key=lambda a: parse_ts(a.get("published")) or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return articles


def fmt_day(d: date) -> str:
    """Human date like ``Jun 7, 2026``."""
    return f"{d.strftime('%b')} {d.day}, {d.year}"


def day_window(day_id: str) -> tuple[datetime, datetime]:
    """Return the [00:00:00, 23:59:59.999999] UTC datetimes for a day id."""
    d = date.fromisoformat(day_id)
    start_dt = datetime.combine(d, time.min, tzinfo=timezone.utc)
    end_dt = datetime.combine(d, time.max, tzinfo=timezone.utc)
    return start_dt, end_dt


# Minimal description of the published recap schema, surfaced in errors and docs.
DAILY_SCHEMA = {
    "date": "calendar date id, e.g. 2026-06-07",
    "title": "string headline, e.g. 'What happened in AI — Jun 7, 2026'",
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
    for field in ("date", "title", "categories"):
        if field not in data:
            errors.append(f"missing required field: {field}")
    if data.get("date") and not DATE_ID_RE.match(str(data["date"])):
        errors.append("'date' must be formatted YYYY-MM-DD")
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
