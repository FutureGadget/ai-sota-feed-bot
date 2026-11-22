"""Per-card translation store: ``data/i18n/<locale>/feed/cards.json``.

One entry per English feed card, keyed by the builder's ``_translation_key``.
The feed API overlays an entry onto a live card only while the entry's
``source_hash`` still equals the card's current English hash, so a stale entry
is harmless. ``last_seen`` is the last build that saw the card in a translation
target set; entries unseen for ``PRUNE_AFTER`` are dropped.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, TypedDict

PRUNE_AFTER = timedelta(days=14)


class AlsoCoveredText(TypedDict):
    url: str | None
    title: str | None


class CardEntry(TypedDict):
    source_hash: str
    model: str
    translated_at: str
    last_seen: str
    title: str
    summary_1line: str
    why_it_matters: str
    also_covered: list[AlsoCoveredText]


class CardStore(TypedDict):
    locale: str
    updated_at: str
    cards: dict[str, CardEntry]


def store_path(root: Path, locale: str) -> Path:
    return root / "data" / "i18n" / locale / "feed" / "cards.json"


def load(path: Path, locale: str) -> CardStore:
    """The stored cards, or an empty store when the file is missing or unreadable."""
    empty: CardStore = {"locale": locale, "updated_at": "", "cards": {}}
    try:
        raw: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return empty
    cards = raw.get("cards") if isinstance(raw, dict) else None
    if not isinstance(cards, dict):
        return empty
    return {"locale": locale, "updated_at": str(raw.get("updated_at") or ""), "cards": cards}


def is_fresh(entry: CardEntry | None, source_hash: str, model: str) -> bool:
    """Reusable: the English source is unchanged and the current model translated it."""
    return bool(entry) and entry["source_hash"] == source_hash and entry["model"] == model


def prune(store: CardStore, now: datetime) -> int:
    """Drop entries not seen for ``PRUNE_AFTER``. Returns how many were removed."""
    cutoff = (now - PRUNE_AFTER).isoformat()
    stale = [k for k, e in store["cards"].items() if str(e.get("last_seen") or "") < cutoff]
    for key in stale:
        del store["cards"][key]
    return len(stale)


def save(path: Path, store: CardStore, now: datetime) -> None:
    out = {
        "locale": store["locale"],
        "updated_at": now.isoformat(),
        "cards": dict(sorted(store["cards"].items())),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
