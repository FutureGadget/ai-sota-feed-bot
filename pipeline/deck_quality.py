"""Judge-derived quality annotations for the editor-deck input bundles.

The five agent-curated decks (daily recap, weekly recap, Playbook, wiki,
Foundations) read ranked edition items, story-store records, or run snapshots.
The Jev gate already writes the selection signal those decks need:

- ``data/processed/classified.json``: compact judged pool from the latest build
- ``data/processed/judgments.json``: durable judged entries (14-day TTL)

This module joins those artifacts to a deck item, attaches the judge verdict,
category, score, and confidence, and applies the same drop exemptions as
ranking. It never invents a verdict for an unjudged item, so the decks fail
open exactly like the feed pipeline.

The deck builders keep the ranked edition composition. classified.json is a
routing/annotation layer here, not a replacement candidate pool: its latest
build covers one two-hour window, it drops article text, and its Stage A pool
is research-heavy before ranking balances the slots.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Must match config/judge.yaml -> ranking.drop_below / keep_at. Judgment-store
# entries written before 2026-10-24 do not carry a stored verdict, so their
# verdict is derived from the score with these thresholds.
DROP_BELOW = 0.10
KEEP_AT = 0.25

# Mirror ranking's judge_gate exemptions. A release note belongs in the
# release lane even when the Brief gate answers "drop".
EXEMPT_SOURCE_ROLES = {"release"}
EXEMPT_CATEGORIES = {"release_note"}

CATEGORY_LABELS = {
    "agent_engineering": "Agent engineering",
    "inference_serving": "Inference & serving",
    "evaluation_reliability": "Evals & reliability",
    "frontier_product": "Models & products",
    "research_method": "Research & methods",
    "release_note": "Releases",
    "business_policy": "Business & policy",
    "off_topic": "Off-topic",
}
CATEGORY_ORDER = list(CATEGORY_LABELS.values())
_ORDER_INDEX = {name: index for index, name in enumerate(CATEGORY_ORDER)}

QUALITY_FIELDS = (
    "judge_score",
    "judge_verdict",
    "judge_category",
    "judge_category_confidence",
    "judge_signals",
    "judge_model",
    "judge_rubric_version",
    "judge_judged_at",
    "source_role",
)

MISSING_VALUES = (None, "", {}, "unjudged")


def normalize_url(value: Any) -> str:
    """Normalize a URL for identity comparison (strip, drop a trailing slash)."""
    url = str(value or "").strip()
    return url[:-1] if url.endswith("/") and len(url) > 1 else url


def verdict_for_score(score: Any) -> str:
    """Derive the judge verdict band from a score."""
    try:
        value = float(score)
    except (TypeError, ValueError):
        return "unjudged"
    if value < DROP_BELOW:
        return "drop"
    if value < KEEP_AT:
        return "review"
    return "keep"


def squeeze(value: Any) -> str:
    return " ".join(str(value or "").replace("\n", " ").split())


def deck_summary(item: dict[str, Any], *, excerpt_limit: int = 600, teaser_limit: int = 400) -> tuple[str, str]:
    """Return (summary, source) preferring a fetched article excerpt.

    ``content_excerpt`` is real page text fetched by the judge, so it beats the
    publisher's scraped teaser. ``summary_1line`` stays the fallback for items
    whose teaser was already long enough to judge.
    """
    excerpt = squeeze(item.get("content_excerpt"))
    if excerpt:
        return excerpt[:excerpt_limit], "content_excerpt"
    line = squeeze(item.get("summary_1line"))
    if line:
        return line[:teaser_limit], "summary_1line"
    return squeeze(item.get("summary"))[:teaser_limit], "summary"


def category_label(article: dict[str, Any]) -> str:
    """Reader-facing label for an article's judge category, or an empty string."""
    category = str(article.get("judge_category") or "").strip()
    return CATEGORY_LABELS.get(category, "")


def category_hint(articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group counts for the bundle's starting categories.

    Uses the judge label when an item carries one, otherwise the builder's
    type-based ``category`` field. The agent still does its own grouping pass;
    this only replaces the single "Industry News" bucket with judged lanes.
    """
    grouped: dict[str, int] = {}
    for article in articles:
        name = str(article.get("deck_category") or article.get("category") or "Other")
        grouped[name] = grouped.get(name, 0) + 1
    names = sorted(grouped, key=lambda name: (_ORDER_INDEX.get(name, 999), name))
    return [{"name": name, "count": grouped[name]} for name in names]


def judge_category_hint(articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Raw judge-category counts (stable keys plus display labels)."""
    grouped: dict[str, int] = {}
    for article in articles:
        key = str(article.get("judge_category") or "").strip()
        if key:
            grouped[key] = grouped.get(key, 0) + 1
    return [
        {"key": key, "name": CATEGORY_LABELS.get(key, key), "count": count}
        for key, count in sorted(grouped.items(), key=lambda pair: (-pair[1], pair[0]))
    ]


def quality_summary(articles: list[dict[str, Any]]) -> dict[str, Any]:
    """Audit counts for a deck bundle: judged coverage and verdict mix."""
    verdicts: dict[str, int] = {}
    categories: dict[str, int] = {}
    judged = 0
    for article in articles:
        verdict = str(article.get("judge_verdict") or "unjudged").strip() or "unjudged"
        if verdict != "unjudged":
            judged += 1
        verdicts[verdict] = verdicts.get(verdict, 0) + 1
        category = str(article.get("judge_category") or "").strip()
        if category:
            categories[category] = categories.get(category, 0) + 1
    return {
        "judged": judged,
        "unjudged": max(0, len(articles) - judged),
        "verdicts": dict(sorted(verdicts.items())),
        "categories": dict(sorted(categories.items(), key=lambda pair: (-pair[1], pair[0]))),
    }


def _read_json(path: Path, fallback: Any) -> Any:
    try:
        if not path.exists():
            return fallback
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def _clean_entry(raw: dict[str, Any]) -> dict[str, Any]:
    entry = {field: raw.get(field) for field in QUALITY_FIELDS}
    if entry.get("judge_verdict") in MISSING_VALUES and entry.get("judge_score") is not None:
        entry["judge_verdict"] = verdict_for_score(entry["judge_score"])
    return {key: value for key, value in entry.items() if value not in MISSING_VALUES}


class QualityIndex:
    """URL/id/story-key index over the committed judge artifacts."""

    def __init__(self) -> None:
        self.by_url: dict[str, dict[str, Any]] = {}
        self.by_id: dict[str, dict[str, Any]] = {}
        self.by_story_key: dict[str, dict[str, Any]] = {}
        self.sources = {"classified": 0, "judgments": 0}

    def _add(
        self,
        entry: dict[str, Any],
        *,
        url: Any = "",
        item_id: Any = "",
        story_key: Any = "",
        source: str = "",
    ) -> None:
        if not entry:
            return
        url = normalize_url(url)
        item_id = str(item_id or "").strip()
        story_key = str(story_key or "").strip()

        existing = None
        for mapping, key in (
            (self.by_url, url),
            (self.by_id, item_id),
            (self.by_story_key, story_key),
        ):
            if key and key in mapping:
                existing = mapping[key]
                break

        merged = dict(existing or {})
        for key, value in entry.items():
            if value not in MISSING_VALUES:
                merged[key] = value

        self.sources[source] = self.sources.get(source, 0) + 1
        for mapping, key in (
            (self.by_url, url),
            (self.by_id, item_id),
            (self.by_story_key, story_key),
        ):
            if key:
                mapping[key] = merged

    def lookup(self, article: dict[str, Any]) -> dict[str, Any] | None:
        url = normalize_url(article.get("url"))
        if url and url in self.by_url:
            return self.by_url[url]
        story_key = str(article.get("story_key") or "").strip()
        if story_key and story_key in self.by_story_key:
            return self.by_story_key[story_key]
        item_id = str(article.get("id") or "").strip()
        if item_id and item_id in self.by_id:
            return self.by_id[item_id]
        return None

    def annotate(self, article: dict[str, Any]) -> dict[str, Any]:
        """Fill missing judge fields, then add the reader-facing deck category."""
        entry = self.lookup(article)
        if entry:
            for field in QUALITY_FIELDS:
                if article.get(field) in MISSING_VALUES and entry.get(field) not in MISSING_VALUES:
                    article[field] = entry[field]
            if article.get("judge_verdict") in MISSING_VALUES and article.get("judge_score") is not None:
                article["judge_verdict"] = verdict_for_score(article["judge_score"])
        label = category_label(article)
        if label:
            article["deck_category"] = label
        return article

    def is_dropped(self, article: dict[str, Any], *, exempt_releases: bool = True) -> bool:
        """Whether the judge says this item does not belong in a deck.

        Release-lane items are exempt by default, matching the feed's judge
        gate. Decks that do not have a release lane (wiki, Foundations) pass
        ``exempt_releases=False`` so routine version bumps stay out of the
        knowledge base. Unjudged items pass through (fail-open). A non-keep
        ``off_topic`` item is dropped; a ``keep`` off_topic item is rare and
        left to the editor.
        """
        verdict = str(article.get("judge_verdict") or "").strip().lower()
        category = str(article.get("judge_category") or "").strip().lower()
        role = str(article.get("source_role") or "").strip().lower()
        if exempt_releases and (role in EXEMPT_SOURCE_ROLES or category in EXEMPT_CATEGORIES):
            return False
        if not exempt_releases and category in EXEMPT_CATEGORIES and verdict != "keep":
            return True
        if verdict == "drop":
            return True
        if category == "off_topic" and verdict != "keep":
            return True
        return False


def load_quality_index(processed_dir: Path) -> QualityIndex:
    """Load the durable store first, then overlay the latest classified pool."""
    index = QualityIndex()

    store = _read_json(Path(processed_dir) / "judgments.json", {})
    for row in (store.get("entries") or {}).values() if isinstance(store, dict) else []:
        if not isinstance(row, dict):
            continue
        index._add(
            _clean_entry(row),
            url=row.get("url"),
            item_id=row.get("id"),
            story_key=row.get("story_key"),
            source="judgments",
        )

    classified = _read_json(Path(processed_dir) / "classified.json", {})
    for row in (classified.get("items") or []) if isinstance(classified, dict) else []:
        if not isinstance(row, dict):
            continue
        index._add(
            _clean_entry(row),
            url=row.get("url"),
            item_id=row.get("id"),
            story_key=row.get("story_key"),
            source="classified",
        )

    return index
