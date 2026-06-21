"""Shared helpers for the Agent Builder's Playbook feature.

Stdlib-only (like the daily/weekly recap commons) so it runs in CI jobs and
inside a Claude Code routine without extra installs.

Data model
----------
The playbook pipeline has three artifacts under ``data/playbook/``:

- ``input/<date>.json`` / ``input/latest.json``
    Machine-built bundle of recent feed articles. This is the *reading material*
    an agent (Claude Code routine) consumes. Built by ``build_playbook_input.py``.

- ``<date>.json``
    The published *edition* the agent writes: a batch of actionable cards, each
    stating the problem it solves, what to apply to your agent, and the expected
    result. Schema documented in ``PLAYBOOK_SCHEMA`` below and in
    ``.agents/skills/playbook/SKILL.md``.

- ``index.json`` / ``latest.json``
    Index of available editions + a copy of the most recent one, rebuilt from
    the ``<date>.json`` files by ``build_playbook_index.py``.

This mirrors the daily-recap feature, but the unit is an *actionable card*
(problem -> apply -> result), not a news summary, and an edition is curated from
a multi-day lookback window rather than a single calendar day.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, time, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any


def _find_repo_root(start: Path) -> Path:
    """Walk up from this file to the repo root (works wherever the script lives)."""
    for parent in [start, *start.parents]:
        if (parent / ".git").exists() or (parent / "data" / "processed").is_dir():
            return parent
    return start.parents[1]


ROOT = _find_repo_root(Path(__file__).resolve())
PLAYBOOK_DIR = ROOT / "data" / "playbook"
PLAYBOOK_INPUT_DIR = PLAYBOOK_DIR / "input"
PROCESSED_RUNS_DIR = ROOT / "data" / "processed" / "runs"
PROCESSED_RUNS_INDEX = ROOT / "data" / "processed" / "runs_index.json"

# Matches a published-edition filename, e.g. ``2026-06-21.json`` (excludes
# index.json / latest.json so they are never treated as editions).
DATE_FILE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}\.json$")
# Matches a bare date id, e.g. ``2026-06-21``.
DATE_ID_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Suggested obstacle areas (aligned with the agent-engineering wiki at /map).
# The agent may introduce others; these are hints surfaced in the input bundle.
AREAS: list[str] = [
    "Memory",
    "Tool use",
    "Orchestration",
    "Evals",
    "Reliability",
    "Cost & latency",
    "Safety",
    "Retrieval",
]


def parse_ts(v: Any) -> datetime | None:
    """Parse an ISO-8601 or RFC-822 timestamp into an aware UTC datetime."""
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
    return d.isoformat()


def fmt_day(d: date) -> str:
    """Human date like ``Jun 21, 2026``."""
    return f"{d.strftime('%b')} {d.day}, {d.year}"


def norm_url(value: Any) -> str:
    """Normalize a URL for dedup comparison (strip + drop a trailing slash)."""
    s = str(value or "").strip()
    return s[:-1] if s.endswith("/") and len(s) > 1 else s


def source_sid(url: Any) -> str:
    """Return the durable story id used throughout the repository."""
    normalized = norm_url(url)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16] if normalized else ""


def clean_article(item: dict[str, Any]) -> dict[str, Any]:
    """Project a processed feed item down to the fields the routine needs."""
    summary = item.get("summary_1line") or item.get("summary") or ""
    summary = " ".join(str(summary).replace("\n", " ").split())[:400]
    return {
        "id": item.get("id") or item.get("url") or item.get("title"),
        "title": str(item.get("title") or "Untitled").strip(),
        "url": item.get("url") or "",
        "source_sid": source_sid(item.get("url")),
        "source": item.get("source") or "unknown",
        "type": str(item.get("type") or "news").lower(),
        "summary": summary,
        "published": item.get("published") or item.get("collected_at"),
    }


def edition_card_urls(exclude_date: str | None = None) -> set[str]:
    """Collect every card source URL from already-published editions.

    Used to keep a learning that lingers in the feed from being re-published in
    a later edition. Scans ``data/playbook/<date>.json`` (skipping
    ``exclude_date``) and returns the set of normalized card URLs.
    """
    urls: set[str] = set()
    if not PLAYBOOK_DIR.is_dir():
        return urls
    for path in PLAYBOOK_DIR.glob("*.json"):
        if not DATE_FILE_RE.match(path.name):
            continue
        data = load_json(path, None)
        if not isinstance(data, dict):
            continue
        if exclude_date and data.get("date") == exclude_date:
            continue
        for card in data.get("cards", []) or []:
            if not isinstance(card, dict):
                continue
            source_url = card.get("source_url")
            if source_url:
                urls.add(norm_url(source_url))
            elif str(card.get("url") or "").startswith(("http://", "https://")):
                urls.add(norm_url(card["url"]))
    return urls


def collect_articles(
    start: datetime,
    end: datetime,
    *,
    require_published_in_window: bool = True,
    exclude_urls: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Deduped list of unique articles seen in [start, end], newest-first.

    Walks the processed run snapshots, dedupes by URL (falling back to id), and
    keeps the richest copy. Mirrors the daily recap collector.
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
            if require_published_in_window:
                pub = parse_ts(cleaned.get("published"))
                if pub is None or pub < start or pub > end:
                    continue
            if exclude_urls and norm_url(cleaned["url"]) in exclude_urls:
                continue
            prev = by_key.get(key)
            if prev is None or len(cleaned["summary"]) > len(prev["summary"]):
                by_key[key] = cleaned

    articles = list(by_key.values())
    articles.sort(
        key=lambda a: parse_ts(a.get("published")) or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    return articles


def day_window(day_id: str) -> tuple[datetime, datetime]:
    """Return the [00:00:00, 23:59:59.999999] UTC datetimes for a day id."""
    d = date.fromisoformat(day_id)
    return (
        datetime.combine(d, time.min, tzinfo=timezone.utc),
        datetime.combine(d, time.max, tzinfo=timezone.utc),
    )


def slugify(value: str) -> str:
    out = "".join(c.lower() if c.isalnum() else "-" for c in value)
    while "--" in out:
        out = out.replace("--", "-")
    return out.strip("-") or "card"


# Minimal description of the published edition schema, surfaced in errors + docs.
PLAYBOOK_SCHEMA = {
    "date": "calendar date id, e.g. 2026-06-21 (the edition's id + filename)",
    "title": "string headline, e.g. \"Agent Builder's Playbook — Jun 21, 2026\"",
    "generated_at": "ISO-8601 timestamp",
    "intro": "optional: array of paragraph strings (a plain string also works)",
    "card_count": "int, number of cards in this edition",
    "cards": [
        {
            "id": "stable card id, e.g. 'pb-cache-tool-schemas'",
            "kind": "'source-backed' or 'evergreen'",
            "title": "verb-first actionable headline, e.g. 'Cache tool schemas to cut latency'",
            "area": "optional: obstacle area, e.g. 'Memory', 'Tool use', 'Evals'",
            "problem": "the problem this solves for an agent builder",
            "apply": "the concrete change to make to your agent",
            "result": "the expected result / payoff",
            "effort": "optional: 'low' | 'medium' | 'high'",
            "source": "source name",
            "source_url": "required for source-backed cards; copied verbatim from the bundle",
            "source_sid": "required for source-backed cards; sha256(normalized source_url)[:16]",
            "topic_url": "required for evergreen cards; optional for source-backed cards",
            "evidence": {
                "kind": "'source-measured' | 'source-claimed' | 'editorial-inference'",
                "note": "short explanation of the evidence basis",
            },
            "published": "optional: ISO-8601 timestamp",
            "tags": "optional: array of short tag strings",
        }
    ],
}

REQUIRED_CARD_FIELDS = ("id", "kind", "title", "problem", "apply", "result")
VALID_EFFORT = {"low", "medium", "high"}
VALID_CARD_KINDS = {"source-backed", "evergreen"}
CARD_ID_RE = re.compile(r"^pb-[a-z0-9][a-z0-9-]*$")
VALID_EVIDENCE_KINDS = {
    "source-measured",
    "source-claimed",
    "editorial-inference",
}
NUMERIC_RESULT_RE = re.compile(
    r"(?:\d+(?:\.\d+)?\s*%|\b\d+(?:\.\d+)?\s*[x×]\b|"
    r"\b\d+(?:\.\d+)?\s*(?:ms|milliseconds?|seconds?|minutes?|hours?|"
    r"tokens?|points?|requests?/s|req/s)\b)",
    re.IGNORECASE,
)
CLAIM_WORDING_RE = re.compile(
    r"\b(?:source|author|vendor|project|company|paper|release)\b.*"
    r"\b(?:claim|claims|claimed|report|reports|reported|say|says|said)\b|"
    r"\b(?:claim|claims|claimed|report|reports|reported)\b",
    re.IGNORECASE,
)


def _valid_topic_url(value: Any) -> bool:
    return bool(re.match(r"^/topic/[a-z0-9][a-z0-9-]*$", str(value or "").strip()))


def _source_index_row(card: dict[str, Any], edition: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": card["id"],
        "kind": "source-backed",
        "title": card["title"],
        "area": card.get("area"),
        "problem": card["problem"],
        "apply": card["apply"],
        "result": card["result"],
        "effort": card.get("effort"),
        "source": card.get("source"),
        "source_url": card["source_url"],
        "source_sid": card["source_sid"],
        "topic_url": card.get("topic_url"),
        "evidence": card["evidence"],
        "edition_date": edition["date"],
    }


def build_source_index(
    editions: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """Build the exact-source lookup used by recap renderers."""
    index: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    for edition in sorted(editions, key=lambda row: str(row.get("date") or "")):
        for card in edition.get("cards", []) or []:
            if not isinstance(card, dict) or card.get("kind") != "source-backed":
                continue
            sid = str(card.get("source_sid") or "")
            if sid in index:
                errors.append(
                    f"duplicate source-backed card for source_sid {sid}: "
                    f"{index[sid].get('id')} and {card.get('id')}"
                )
                continue
            index[sid] = _source_index_row(card, edition)
    if errors:
        return {}, errors
    return dict(sorted(index.items())), []


def validate_edition(data: Any) -> list[str]:
    """Return a list of human-readable validation errors (empty == valid)."""
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["edition must be a JSON object"]
    for field in ("date", "title", "cards"):
        if field not in data:
            errors.append(f"missing required field: {field}")
    if data.get("date") and not DATE_ID_RE.match(str(data["date"])):
        errors.append("'date' must be formatted YYYY-MM-DD")
    cards = data.get("cards")
    if not isinstance(cards, list) or not cards:
        errors.append("'cards' must be a non-empty array")
        return errors
    seen_ids: set[str] = set()
    for i, card in enumerate(cards):
        if not isinstance(card, dict):
            errors.append(f"cards[{i}] must be an object")
            continue
        for field in REQUIRED_CARD_FIELDS:
            if not str(card.get(field) or "").strip():
                errors.append(f"cards[{i}] missing '{field}'")
        card_id = str(card.get("id") or "")
        if card_id and not CARD_ID_RE.match(card_id):
            errors.append(f"cards[{i}] 'id' must start with 'pb-' and be URL-safe")
        if card_id in seen_ids:
            errors.append(f"cards[{i}] duplicates card id '{card_id}'")
        seen_ids.add(card_id)
        kind = str(card.get("kind") or "")
        if kind and kind not in VALID_CARD_KINDS:
            errors.append(f"cards[{i}] 'kind' must be one of {sorted(VALID_CARD_KINDS)}")
        eff = card.get("effort")
        if eff is not None and str(eff).lower() not in VALID_EFFORT:
            errors.append(f"cards[{i}] 'effort' must be one of {sorted(VALID_EFFORT)}")
        if kind == "evergreen":
            if not _valid_topic_url(card.get("topic_url")):
                errors.append(f"cards[{i}] evergreen card needs a valid 'topic_url'")
            continue
        if kind != "source-backed":
            continue
        source_url = str(card.get("source_url") or "").strip()
        if not source_url.startswith(("http://", "https://")):
            errors.append(f"cards[{i}] source-backed card needs an HTTP(S) 'source_url'")
        expected_sid = source_sid(source_url) if source_url else ""
        if str(card.get("source_sid") or "") != expected_sid:
            errors.append(f"cards[{i}] 'source_sid' does not match 'source_url'")
        topic_url = card.get("topic_url")
        if topic_url and not _valid_topic_url(topic_url):
            errors.append(f"cards[{i}] has invalid 'topic_url'")
        evidence = card.get("evidence")
        if not isinstance(evidence, dict):
            errors.append(f"cards[{i}] source-backed card needs an 'evidence' object")
            continue
        evidence_kind = str(evidence.get("kind") or "")
        if evidence_kind not in VALID_EVIDENCE_KINDS:
            errors.append(
                f"cards[{i}] evidence.kind must be one of {sorted(VALID_EVIDENCE_KINDS)}"
            )
        if not str(evidence.get("note") or "").strip():
            errors.append(f"cards[{i}] evidence needs a non-empty 'note'")
        if evidence_kind == "editorial-inference" and NUMERIC_RESULT_RE.search(
            str(card.get("result") or "")
        ):
            errors.append(
                f"cards[{i}] numeric result requires source-measured or source-claimed evidence"
            )
        if evidence_kind == "source-claimed" and not CLAIM_WORDING_RE.search(
            str(card.get("result") or "")
        ):
            errors.append(f"cards[{i}] source-claimed result must be worded as a claim")
    return errors
