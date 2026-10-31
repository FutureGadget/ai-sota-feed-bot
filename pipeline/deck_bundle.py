"""Recall additions for the recap input bundles.

The daily and weekly bundles are built from the ranked feed editions, so a
story the Jev gate kept but the feed layout never placed cannot reach a recap.
This module finds those stories in the judged candidate pool
(``pipeline/deck_candidates.py``) and returns them as feed-item-shaped dicts
for the bundle builders to clean and append. The agent still chooses what to
publish; nothing here ranks or selects.

It also tags articles that name the same model at the same version
(``kimi|3.1``) with a shared ``event_group``, so one launch reported under
several headlines reads as one event.

Owner grades on 2026-10-24..27 showed the Jev score has no ranking signal past
the gate, which is why this adds candidates instead of choosing them. See
``docs/exec-plans/active/2026-10-29-deck-candidate-selector.md``.
"""

from __future__ import annotations

from datetime import date
from typing import Any

try:
    import deck_candidates
    import deck_select
except Exception:  # pragma: no cover - package-style import
    from pipeline import deck_candidates, deck_select


def bundle_config(deck: str, cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = cfg or deck_select.load_config()
    spec = ((cfg.get("decks") or {}).get(deck) or {}).get("bundle") or {}
    return {
        "pool_additions": bool(spec.get("pool_additions", False)),
        "verdicts": set(spec.get("verdicts") or ["keep"]),
        "max_additions": int(spec.get("max_additions", 0) or 0),
        "max_by_type": {str(k): int(v) for k, v in (spec.get("max_by_type") or {}).items()},
    }


def _as_item(row: dict[str, Any]) -> dict[str, Any]:
    """Pool row -> the feed-item fields the bundle builders' clean_article reads."""
    item = {
        "id": row.get("id") or row.get("url") or row.get("key"),
        "title": row.get("title"),
        "url": row.get("url") or row.get("key"),
        "source": row.get("source"),
        "type": row.get("type") or "news",
        "published": row.get("published"),
        "summary": row.get("summary") or "",
        "content_excerpt": row.get("excerpt") or "",
        "story_key": row.get("story_key"),
        "source_role": row.get("source_role"),
        "in_brief": bool(row.get("in_brief")),
        "brief_admitted_at": row.get("brief_admitted_at"),
    }
    for field in deck_candidates.JUDGE_FIELDS:
        if row.get(field) is not None:
            item[field] = row[field]
    return item


def pool_additions(
    deck: str,
    start: date,
    end: date,
    *,
    types: set[str] | None,
    exclude_urls: set[str] | None,
    existing_urls: set[str],
    cfg: dict[str, Any] | None = None,
    enabled: bool | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Judged keeps for the window that the bundle does not already hold.

    Returns (feed-item dicts, diagnostics). Never raises: a failure returns no
    additions and the reason, so the bundle builds exactly as before.
    """
    spec = bundle_config(deck, cfg)
    on = spec["pool_additions"] if enabled is None else enabled
    diag: dict[str, Any] = {"enabled": bool(on), "added": 0}
    if not on:
        return [], diag
    try:
        candidates, cand_diag = deck_candidates.load_candidates(
            start, end, types=types, exclude_urls=exclude_urls
        )
        existing = {deck_candidates.normalize_url(u) for u in existing_urls}
        missing = [
            row
            for row in candidates
            if row.get("judge_verdict") in spec["verdicts"] and row["key"] not in existing
        ]
        # The caps bound the agent's reading material. When they bind, the
        # higher Jev score wins, then the newer item. Past the gate the score
        # is a weak signal (owner grades, 2026-10-24..27), so keep caps loose
        # enough that they rarely bind on news.
        def order(row: dict[str, Any]) -> tuple:
            published = deck_candidates.parse_ts(row.get("published"))
            return (
                float(row.get("judge_score") or 0.0),
                published.timestamp() if published else 0.0,
                row["key"],
            )

        missing.sort(key=order, reverse=True)
        kept: list[dict[str, Any]] = []
        per_type: dict[str, int] = {}
        capped_by_type: dict[str, int] = {}
        for row in missing:
            kind = str(row.get("type") or "news")
            limit = spec["max_by_type"].get(kind)
            if limit is not None and per_type.get(kind, 0) >= limit:
                capped_by_type[kind] = capped_by_type.get(kind, 0) + 1
                continue
            per_type[kind] = per_type.get(kind, 0) + 1
            kept.append(row)
        capped = 0
        if spec["max_additions"] and len(kept) > spec["max_additions"]:
            capped = len(kept) - spec["max_additions"]
            kept = kept[: spec["max_additions"]]
        missing = kept
        diag.update(
            {
                "added": len(missing),
                "capped": capped,
                "capped_by_type": capped_by_type,
                "verdicts": sorted(spec["verdicts"]),
                "pool_candidates": cand_diag.get("candidates", 0),
                "from_pool_files": cand_diag.get("from_pool", 0),
                "by_type": _count(missing, "type"),
                "by_role": _count(missing, "source_role"),
            }
        )
        return [_as_item(row) for row in missing], diag
    except Exception as exc:
        diag.update({"added": 0, "error": str(exc)})
        return [], diag


def _count(rows: list[dict[str, Any]], field: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for row in rows:
        key = str(row.get(field) or "unknown")
        out[key] = out.get(key, 0) + 1
    return dict(sorted(out.items(), key=lambda kv: (-kv[1], kv[0])))


def annotate_event_groups(articles: list[dict[str, Any]]) -> int:
    """Set ``event_group`` on articles whose titles carry the same single
    ``model|version`` anchor (``deck_select.event_tokens``).

    Each article has at most one anchor, so groups never chain across
    models. A group can hold a launch and a later follow-up; the recap skill
    asks the agent not to repeat one announcement, not to merge distinct
    news. Returns the number of groups with more than one article.
    """
    by_token: dict[str, list[dict[str, Any]]] = {}
    for article in articles:
        tokens = deck_select.event_tokens(article)
        if len(tokens) == 1:
            by_token.setdefault(next(iter(tokens)), []).append(article)
    count = 0
    for token, members in by_token.items():
        if len(members) < 2:
            continue
        for article in members:
            article["event_group"] = token
        count += 1
    return count
