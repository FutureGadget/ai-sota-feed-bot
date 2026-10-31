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

import hashlib
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
PROCESSED_DIR = ROOT / "data" / "processed"
PROCESSED_RUNS_DIR = PROCESSED_DIR / "runs"
PROCESSED_RUNS_INDEX = PROCESSED_DIR / "runs_index.json"

_DECK_QUALITY = None


def _deck_quality():
    """Load the shared judge-join helper lazily (index/seed scripts skip it)."""
    global _DECK_QUALITY
    if _DECK_QUALITY is None:
        import sys

        pipeline_dir = str(ROOT / "pipeline")
        if pipeline_dir not in sys.path:
            sys.path.insert(0, pipeline_dir)
        import deck_quality

        _DECK_QUALITY = deck_quality
    return _DECK_QUALITY

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


def source_sid(url: Any) -> str:
    normalized = norm_url(url)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16] if normalized else ""


def clean_article(item: dict[str, Any], quality=None) -> dict[str, Any]:
    """Project a processed feed item down to the fields the recap needs."""
    summary, summary_source = _deck_quality().deck_summary(item)
    article = {
        "id": item.get("id") or item.get("url") or item.get("title"),
        "title": str(item.get("title") or "Untitled").strip(),
        "url": item.get("url") or "",
        "source_sid": source_sid(item.get("url")),
        "source": item.get("source") or "unknown",
        "type": str(item.get("type") or "news").lower(),
        "category": category_for_type(item.get("type")),
        "summary": summary,
        "published": item.get("published") or item.get("collected_at"),
    }
    if summary:
        article["summary_source"] = summary_source
    for field in ("in_brief", "brief_admitted_at"):
        value = item.get(field)
        if value not in (None, "", False):
            article[field] = value
    for field in ("publisher_name", "publisher_domain"):
        value = " ".join(str(item.get(field) or "").split())
        if value:
            article[field] = value[:200]
    if quality is not None:
        quality.annotate(article)
    article.setdefault("deck_category", article.get("category") or DEFAULT_CATEGORY)
    return article


def deck_category_hint(articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return _deck_quality().category_hint(articles)


def judge_category_hint(articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return _deck_quality().judge_category_hint(articles)


def deck_quality_summary(articles: list[dict[str, Any]]) -> dict[str, Any]:
    return _deck_quality().quality_summary(articles)


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
    include_dropped: bool = False,
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

    Known judge drops are removed unless ``include_dropped`` is set. Release
    items and release notes are exempt, and unjudged items pass through.
    """
    index = load_json(PROCESSED_RUNS_INDEX, [])
    if not isinstance(index, list):
        return []

    quality = _deck_quality().load_quality_index(PROCESSED_DIR)
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
            cleaned = clean_article(it, quality)
            key = cleaned["url"] or cleaned["id"] or cleaned["title"]
            if not key:
                continue
            # #1: only articles actually published within the week window.
            if require_published_in_window:
                pub = parse_ts(cleaned.get("published"))
                if pub is None or pub < start or pub > end:
                    continue
            if not include_dropped and quality.is_dropped(cleaned):
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
    video = data.get("video")
    if video is not None:
        vid = video.get("youtube_id") if isinstance(video, dict) else None
        if not isinstance(vid, str) or not re.fullmatch(r"[A-Za-z0-9_-]{11}", vid):
            errors.append("'video.youtube_id' must be an 11-character YouTube video id")
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


def deck_selection(deck: str, start, end, include_types, exclude_urls) -> dict[str, Any]:
    """Selector shortlist/bench for the bundle window (``--selector``)."""
    _deck_quality()  # puts pipeline/ on sys.path
    import deck_select

    return deck_select.build_selection(deck, start, end, types=include_types, exclude_urls=exclude_urls)


def add_pool_articles(articles, start, end, include_types, exclude_urls, enabled=None):
    """Append judged keeps the bundle's feed editions did not include and tag
    same-release articles with ``event_group``.

    Returns (articles, diagnostics). With ``enabled=False`` (``--no-pool``)
    the articles come back unchanged and diagnostics is None. Any failure
    returns the articles unchanged with the error, so the bundle still builds.
    """
    if enabled is False:
        return articles, None
    try:
        _deck_quality()  # puts pipeline/ on sys.path
        import deck_bundle

        if enabled is None and not deck_bundle.bundle_config("weekly")["pool_additions"]:
            return articles, None
        quality = _deck_quality().load_quality_index(PROCESSED_DIR)
        existing = {a.get("url") for a in articles if a.get("url")}
        items, diag = deck_bundle.pool_additions(
            "weekly", start, end, types=include_types, exclude_urls=exclude_urls,
            existing_urls=existing, enabled=True,
        )
        added = []
        for item in items:
            article = clean_article(item, quality)
            article["from_pool"] = True
            added.append(article)
        merged = [dict(a) for a in articles] + added
        merged.sort(key=lambda a: parse_ts(a.get("published")) or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        diag["event_groups"] = deck_bundle.annotate_event_groups(merged)
        return merged, diag
    except Exception as exc:  # the recap must still get its bundle
        return articles, {"enabled": True, "added": 0, "error": f"{type(exc).__name__}: {exc}"}
