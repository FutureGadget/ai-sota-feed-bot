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
    "status": "optional: live-status banner { state, tone, changed, detail, reenable } "
    "for a thread with a current state (shipping / suspended / resolved …)",
    "beats": "optional: ordered arc of { kicker, tone, headline, summary, sids[] } — "
    "each beat groups the member sids that moved the story in that phase",
    "open_questions": "optional: array of 'what to watch' questions agents are tracking",
    "take_for_builders": "optional: one actionable line for AI platform engineers "
    "(falls back to why_it_matters when omitted)",
}

# Semantic tones for the arc/status (node + kicker colors). Mirrored in
# pipeline/render_static_pages.py STORYLINE_TONES.
STORYLINE_TONES = frozenset(
    {"launch", "rising", "turn", "now", "resolved", "alert", "neutral"}
)

# Guardrails so a runaway summary can't blow out the card layout.
MAX_TLDR = 700
MAX_LINE = 400
MAX_BEATS = 10
MAX_QUESTIONS = 6


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

    for field in ("generated_at", "covers_last_updated"):
        value = data.get(field)
        if not _is_str(value) or not value.strip():
            errors.append(f"missing required field: {field} (non-empty string)")

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
    if not isinstance(sids, list) or not sids or not all(_is_str(s) and s for s in sids):
        errors.append("missing required field: covers_member_sids (non-empty array of strings)")

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

    status = data.get("status")
    if status is not None:
        if not isinstance(status, dict):
            errors.append("'status' must be an object")
        else:
            for field in ("state", "detail", "changed", "reenable"):
                v = status.get(field)
                if v is not None and not _is_str(v):
                    errors.append(f"status.{field} must be a string")
                elif _is_str(v) and len(v) > MAX_LINE:
                    errors.append(f"status.{field} is too long ({len(v)} chars)")
            tone = status.get("tone")
            if not _is_str(status.get("state")) or not str(status.get("state")).strip():
                errors.append("status.state must be a non-empty string")
            if tone is None:
                errors.append("status.tone is required when status is present")
            if tone is not None and tone not in STORYLINE_TONES:
                errors.append(f"status.tone {tone!r} not in {sorted(STORYLINE_TONES)}")
            track = status.get("track")
            if track is not None:
                if not isinstance(track, list):
                    errors.append("status.track must be an array")
                else:
                    for i, seg in enumerate(track):
                        if not isinstance(seg, dict):
                            errors.append(f"status.track[{i}] must be an object")
                            continue
                        st = seg.get("tone")
                        if st is not None and st not in STORYLINE_TONES:
                            errors.append(f"status.track[{i}].tone {st!r} not in {sorted(STORYLINE_TONES)}")
                        w = seg.get("weight")
                        if w is not None and not isinstance(w, (int, float)):
                            errors.append(f"status.track[{i}].weight must be a number")

    beats = data.get("beats")
    if beats is not None:
        if not isinstance(beats, list):
            errors.append("'beats' must be an array")
        else:
            if len(beats) > MAX_BEATS:
                errors.append(f"too many beats ({len(beats)} > {MAX_BEATS})")
            for i, b in enumerate(beats):
                if not isinstance(b, dict):
                    errors.append(f"beats[{i}] must be an object")
                    continue
                if not _is_str(b.get("headline")) or not str(b.get("headline")).strip():
                    errors.append(f"beats[{i}] missing required 'headline' string")
                tone = b.get("tone")
                if tone is not None and tone not in STORYLINE_TONES:
                    errors.append(f"beats[{i}].tone {tone!r} not in {sorted(STORYLINE_TONES)}")
                for field in ("kicker", "headline", "summary"):
                    v = b.get(field)
                    if v is not None and not _is_str(v):
                        errors.append(f"beats[{i}].{field} must be a string")
                    elif _is_str(v) and len(v) > MAX_LINE:
                        errors.append(f"beats[{i}].{field} is too long ({len(v)} chars)")
                sids = b.get("sids")
                if sids is None:
                    continue
                if not (isinstance(sids, list) and all(_is_str(s) for s in sids)):
                    errors.append(f"beats[{i}].sids must be an array of strings")
                elif valid_sids is not None:
                    for s in sids:
                        if s not in valid_sids:
                            errors.append(f"beats[{i}] references unknown sid {s!r}")

    oq = data.get("open_questions")
    if oq is not None:
        if not (isinstance(oq, list) and all(_is_str(q) for q in oq)):
            errors.append("'open_questions' must be an array of strings")
        elif len(oq) > MAX_QUESTIONS:
            errors.append(f"too many open_questions ({len(oq)} > {MAX_QUESTIONS})")
        else:
            for q in oq:
                if len(q) > MAX_LINE:
                    errors.append(f"open_questions entry too long ({len(q)} chars)")

    take = data.get("take_for_builders")
    if take is not None:
        if not _is_str(take):
            errors.append("'take_for_builders' must be a string")
        elif len(take) > MAX_LINE:
            errors.append(f"'take_for_builders' is too long ({len(take)} chars)")

    prov = data.get("provenance")
    if prov is not None:
        if not isinstance(prov, dict):
            errors.append("'provenance' must be an object keyed by sid")
        else:
            for sid, entry in prov.items():
                if valid_sids is not None and sid not in valid_sids:
                    errors.append(f"provenance references unknown sid {sid!r}")
                if not isinstance(entry, dict):
                    errors.append(f"provenance[{sid!r}] must be an object")
                    continue
                sb = entry.get("surfaced_by")
                if sb is not None and sb != "scout":
                    errors.append(f"provenance[{sid!r}].surfaced_by must be 'scout'")
                v = entry.get("verified")
                if v is not None and (isinstance(v, bool) or not isinstance(v, int) or v < 2):
                    errors.append(f"provenance[{sid!r}].verified must be an integer >= 2")
                su = entry.get("status_update")
                if su is not None and not isinstance(su, bool):
                    errors.append(f"provenance[{sid!r}].status_update must be a bool")
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
