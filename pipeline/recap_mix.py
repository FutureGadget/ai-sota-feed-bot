"""Source-role caps on a published recap's cards.

The recap agent reads the full input bundle and chooses the cards; this check
runs on what it chose. ``config/decks.yaml`` ``decks.<deck>.recap`` holds the
caps:

    recap:
      max_cards_by_role: {community: 6}
      since: "2026-11-25"   # recaps dated before this are not checked

Roles come from ``pipeline/editorial.py`` ``source_role`` (the same map the
feed's caps use). A recap whose date id sorts before ``since`` is left alone,
so the index builders keep validating the archive.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import yaml

try:
    import editorial
except ModuleNotFoundError as exc:  # package-style import (pytest from repo root)
    if exc.name != "editorial":
        raise
    from pipeline import editorial

ROOT = Path(__file__).resolve().parents[1]
DECKS_PATH = ROOT / "config" / "decks.yaml"


def recap_caps(deck: str, cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    if cfg is None:
        cfg = yaml.safe_load(DECKS_PATH.read_text(encoding="utf-8")) or {}
    spec = (((cfg.get("decks") or {}).get(deck) or {}).get("recap")) or {}
    return {
        "max_cards_by_role": {str(k): int(v) for k, v in (spec.get("max_cards_by_role") or {}).items()},
        "since": str(spec.get("since") or ""),
    }


def role_counts(recap: dict[str, Any], editorial_cfg: dict[str, Any] | None = None) -> Counter:
    counts: Counter = Counter()
    for cat in recap.get("categories") or []:
        for art in (cat or {}).get("articles") or []:
            counts[editorial.source_role(str((art or {}).get("source") or ""), editorial_cfg)] += 1
    return counts


def role_cap_errors(
    deck: str,
    recap: dict[str, Any],
    recap_id: str,
    cfg: dict[str, Any] | None = None,
    editorial_cfg: dict[str, Any] | None = None,
) -> list[str]:
    """Errors for each source role over its cap; empty when within caps."""
    caps = recap_caps(deck, cfg)
    if not caps["max_cards_by_role"]:
        return []
    if caps["since"] and str(recap_id) < caps["since"]:
        return []
    counts = role_counts(recap, editorial_cfg)
    return [
        f"{counts[role]} cards from {role} sources; the {deck} recap allows at most {limit}"
        " (config/decks.yaml recap.max_cards_by_role). Keep the strongest and replace the rest"
        " with cards from other sources."
        for role, limit in sorted(caps["max_cards_by_role"].items())
        if counts[role] > limit
    ]
