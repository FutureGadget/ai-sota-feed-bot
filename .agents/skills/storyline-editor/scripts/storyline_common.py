"""Shared helpers for the storyline-editor recap feature.

Stdlib only (like the rest of the recap tooling) so it runs in CI and inside a
Claude Code routine without extra installs.

Data model
----------
Storylines are built *mechanically* every hour by ``pipeline/build_storylines.py``
into ``data/storylines/<slug>.json`` (day-by-day timeline) + ``index.json``.
Those files are regenerated on every run, so an agent must **never** write into
them directly — its work would be clobbered on the next pipeline pass.

Instead the editorial layer lives in a durable **narrative sidecar**:

- ``data/storylines/narratives/<slug>.json``
    The agent-written narrative for one storyline (TL;DR arc, "what's new",
    why-it-matters, per-item editor notes). Schema in ``NARRATIVE_SCHEMA`` /
    ``skills/storyline-editor/SKILL.md``. This is the source of truth.

- ``data/storylines/input/latest.json``
    Machine-built bundle of the storylines that currently *need* a narrative
    (new or stale), each with its full timeline as reading material. Built by
    ``build_storyline_input.py``. This is what the agent reads.

``build_storylines.py`` deterministically **overlays** a fresh sidecar onto the
served ``<slug>.json`` (and a teaser onto the index entry) on every run, so the
narrative survives reclustering and there is still exactly one file the API
serves. The overlay is a plain JSON read + dict merge — no LLM in the hourly
loop. The sidecar carries a membership/timestamp snapshot so the overlay can
flag a narrative as stale when the thread moved on since it was written.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _find_repo_root(start: Path) -> Path:
    """Walk up from this file to the repo root (works wherever the script lives)."""
    for parent in [start, *start.parents]:
        if (parent / ".git").exists() or (parent / "data" / "storylines").is_dir():
            return parent
    return start.parents[1]


ROOT = _find_repo_root(Path(__file__).resolve())
STORYLINES_DIR = ROOT / "data" / "storylines"
STORYLINES_INDEX = STORYLINES_DIR / "index.json"
NARRATIVE_DIR = STORYLINES_DIR / "narratives"
INPUT_DIR = STORYLINES_DIR / "input"

# A storyline slug, e.g. ``claude-fable``. Mirrors api/storylines.js SLUG_RE.
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,80}$")

# The timeline fields the agent reads per item; ``sid`` is the stable join key
# used to attach a per-item editor note back onto the timeline.
ITEM_FIELDS = ("sid", "title", "url", "source", "type", "summary_1line", "published")


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


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def member_sids(storyline: dict[str, Any]) -> list[str]:
    """All member sids of a storyline, from either an index entry (flat
    ``member_sids``) or a detail file (``days[].items[].sid``)."""
    if isinstance(storyline.get("member_sids"), list):
        return [str(s) for s in storyline["member_sids"] if s]
    out: list[str] = []
    for day in storyline.get("days") or []:
        for it in (day or {}).get("items") or []:
            if isinstance(it, dict) and it.get("sid"):
                out.append(str(it["sid"]))
    return out


def narrative_path(slug: str) -> Path:
    return NARRATIVE_DIR / f"{slug}.json"


# ----------------------------------------------------------------------------
# Narrative schema + validation
# ----------------------------------------------------------------------------

NARRATIVE_SCHEMA = {
    "slug": "storyline slug this narrative belongs to (must match the file name)",
    "generated_at": "ISO-8601 timestamp the narrative was written",
    "covers_last_updated": "the storyline's last_updated this narrative was written "
    "against (used to flag the narrative stale when the thread moves on)",
    "covers_member_sids": "array of member sids the narrative covered (staleness snapshot)",
    "tldr": "2-3 sentence arc of the whole thread: what happened, in order",
    "whats_new": "optional: 1-2 sentences on what the most recent update added "
    "(omit on a brand-new thread with nothing to compare against)",
    "why_it_matters": "optional: one line through the AI-platform-engineer lens",
    "day_captions": "optional: { <sid>: 'one line on what this item added to the "
    "story' } — keyed by the timeline item's sid",
}

# Guardrails so a runaway summary can't blow out the card layout.
MAX_TLDR = 700
MAX_LINE = 400


def _is_str(v: Any) -> bool:
    return isinstance(v, str)


def validate_narrative(data: Any, *, valid_sids: set[str] | None = None) -> list[str]:
    """Return human-readable validation errors (empty == valid).

    ``valid_sids`` (the current member set, when known) turns unknown caption
    keys into errors so a narrative can't reference items that aren't in the
    thread; pass ``None`` to skip that cross-check.
    """
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["narrative must be a JSON object"]

    slug = data.get("slug")
    if not slug:
        errors.append("missing required field: slug")
    elif not SLUG_RE.match(str(slug)):
        errors.append(f"'slug' is not a valid slug: {slug!r}")

    tldr = data.get("tldr")
    if not tldr or not _is_str(tldr) or not tldr.strip():
        errors.append("missing required field: tldr (non-empty string)")
    elif len(tldr) > MAX_TLDR:
        errors.append(f"'tldr' is too long ({len(tldr)} > {MAX_TLDR} chars)")

    for field in ("whats_new", "why_it_matters"):
        v = data.get(field)
        if v is None:
            continue
        if not _is_str(v):
            errors.append(f"'{field}' must be a string")
        elif len(v) > MAX_LINE:
            errors.append(f"'{field}' is too long ({len(v)} > {MAX_LINE} chars)")

    sids = data.get("covers_member_sids")
    if sids is not None and not (isinstance(sids, list) and all(_is_str(s) for s in sids)):
        errors.append("'covers_member_sids' must be an array of strings")

    caps = data.get("day_captions")
    if caps is not None:
        if not isinstance(caps, dict):
            errors.append("'day_captions' must be an object keyed by sid")
        else:
            for sid, text in caps.items():
                if not _is_str(text):
                    errors.append(f"day_captions[{sid!r}] must be a string")
                elif len(text) > MAX_LINE:
                    errors.append(f"day_captions[{sid!r}] is too long ({len(text)} chars)")
                elif valid_sids is not None and sid not in valid_sids:
                    errors.append(f"day_captions references unknown sid {sid!r}")
    return errors


def narrative_is_fresh(narrative: dict[str, Any], index_entry: dict[str, Any]) -> bool:
    """True when ``narrative`` still matches the storyline's current state.

    A narrative is fresh only if it was written against the same
    ``last_updated`` *and* the same member set — i.e. nothing was appended or
    reclustered since. Anything else means the thread moved on and the
    narrative should be refreshed (the overlay still shows it, flagged stale).
    """
    if not isinstance(narrative, dict):
        return False
    if narrative.get("covers_last_updated") != index_entry.get("last_updated"):
        return False
    return set(narrative.get("covers_member_sids") or []) == set(member_sids(index_entry))
