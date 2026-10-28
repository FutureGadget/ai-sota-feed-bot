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
        # The cap is a context-size guard, not a ranking: newest first.
        missing.sort(key=lambda r: (str(r.get("published") or ""), r["key"]), reverse=True)
        capped = 0
        if spec["max_additions"] and len(missing) > spec["max_additions"]:
            capped = len(missing) - spec["max_additions"]
            missing = missing[: spec["max_additions"]]
        diag.update(
            {
                "added": len(missing),
                "capped": capped,
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
    """Set ``event_group`` on articles that share a model+version event.

    Returns the number of groups with more than one article. Articles not in
    such a group are left untouched.
    """
    groups: dict[str, list[dict[str, Any]]] = {}
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    tokens_by_index: list[set[str]] = []
    for index, article in enumerate(articles):
        node = f"a{index}"
        find(node)
        tokens = deck_select.event_tokens(article)
        tokens_by_index.append(tokens)
        for token in tokens:
            a, b = find(node), find(f"event:{token}")
            if a != b:
                parent[max(a, b)] = min(a, b)
    for index, article in enumerate(articles):
        groups.setdefault(find(f"a{index}"), []).append(index)

    count = 0
    for members in groups.values():
        if len(members) < 2:
            continue
        # Label with the anchor most members share, so a comparison headline
        # ("Kimi K3.1 Pro vs. Claude ...") does not name the group.
        counts: dict[str, int] = {}
        for i in members:
            for token in tokens_by_index[i]:
                counts[token] = counts.get(token, 0) + 1
        label = min(counts, key=lambda t: (-counts[t], t))
        for i in members:
            articles[i]["event_group"] = label
        count += 1
    return count
