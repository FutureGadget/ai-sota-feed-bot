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
from datetime import date, datetime, timedelta, timezone
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
    if not v:
        return None
    try:
        d = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return d
    except Exception:
        return None


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


def collect_week_articles(start: datetime, end: datetime) -> list[dict[str, Any]]:
    """Deduped list of unique articles that appeared in the feed in [start, end].

    Walks the processed run snapshots, dedupes by URL (falling back to id), and
    keeps the richest copy seen. Sorted newest-first by published date.
    """
    index = load_json(PROCESSED_RUNS_INDEX, [])
    if not isinstance(index, list):
        return []

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
    "intro": "1-3 paragraph narrative overview of the week",
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
