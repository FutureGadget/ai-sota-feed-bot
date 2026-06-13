"""Shared helpers for the storyline-scout recall routine.

Stdlib only, so it runs in CI and inside a Claude Code routine without installs.

Data model
----------
The scout adds *recall* on top of the precision-first clustering without letting
an LLM decide what becomes a storyline:

- ``data/storylines/scout/candidates.json``
    Machine-built bundle of near-miss anchors + co-mention buckets — what the
    agent reads. Built by ``pipeline/scout_candidates.py``.

- ``data/storylines/scout/links.json``
    Agent-confirmed thread links (the durable source of truth this routine
    writes). Schema in ``LINK_SCHEMA`` / ``skills/storyline-scout/SKILL.md``.

``pipeline/build_storylines.py`` applies each confirmed link as a *synthetic
candidate through the same MIN_ITEMS/MIN_DAYS/MIN_SOURCES floor* — the
deterministic gate. A link is inert unless its nodes clear the floor, so a wrong
or thin link simply doesn't surface; nothing reaches readers as raw LLM output.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def _find_repo_root(start: Path) -> Path:
    for parent in [start, *start.parents]:
        if (parent / ".git").exists() or (parent / "data" / "storylines").is_dir():
            return parent
    return start.parents[1]


ROOT = _find_repo_root(Path(__file__).resolve())
STORYLINES_DIR = ROOT / "data" / "storylines"
SCOUT_DIR = STORYLINES_DIR / "scout"
CANDIDATES_FILE = SCOUT_DIR / "candidates.json"
LINKS_FILE = SCOUT_DIR / "links.json"

SID_RE = re.compile(r"^[0-9a-f]{6,40}$")
MAX_LABEL = 80
MAX_REASON = 400


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


def load_links() -> list[dict]:
    data = load_json(LINKS_FILE, [])
    if isinstance(data, dict):
        data = data.get("links", [])
    return data if isinstance(data, list) else []


LINK_SCHEMA = {
    "id": "stable id for the link (kebab-case; reused across runs so slugs/follows are stable)",
    "label_hint": "thread label shown when the link forms a scout-only storyline",
    "members": "array of >=2 sids (from the candidate bundle) that belong to one story/thread",
    "reason": "one line: why these are the same story/thread (provenance for the audit trail)",
    "confidence": "optional: 'high' | 'medium'",
    "confirmed_at": "optional: ISO-8601 timestamp",
    "candidate_id": "optional: the candidates.json id this came from",
}


def validate_link(link: Any, *, valid_sids: set[str] | None = None) -> list[str]:
    """Return human-readable errors for one link (empty == valid)."""
    errors: list[str] = []
    if not isinstance(link, dict):
        return ["link must be a JSON object"]

    members = link.get("members")
    if not isinstance(members, list) or len(members) < 2:
        errors.append("'members' must be an array of >=2 sids")
    else:
        for sid in members:
            if not isinstance(sid, str) or not SID_RE.match(sid):
                errors.append(f"member sid {sid!r} is not a valid sid")
            elif valid_sids is not None and sid not in valid_sids:
                errors.append(f"member sid {sid!r} is not in the current window")
        if len(set(members)) < 2:
            errors.append("'members' has fewer than 2 distinct sids")

    hint = link.get("label_hint")
    if not hint or not isinstance(hint, str) or not hint.strip():
        errors.append("missing required field: label_hint (non-empty string)")
    elif len(hint) > MAX_LABEL:
        errors.append(f"'label_hint' too long ({len(hint)} > {MAX_LABEL})")

    reason = link.get("reason")
    if reason is not None and (not isinstance(reason, str) or len(reason) > MAX_REASON):
        errors.append(f"'reason' must be a string <= {MAX_REASON} chars")

    conf = link.get("confidence")
    if conf is not None and conf not in ("high", "medium", "low"):
        errors.append("'confidence' must be one of: high, medium, low")
    return errors


def validate_links(links: Any, *, valid_sids: set[str] | None = None) -> list[str]:
    """Validate a list of links; prefixes each error with its index."""
    if not isinstance(links, list):
        return ["links file must be a JSON array of link objects"]
    errors: list[str] = []
    seen_ids: set[str] = set()
    for i, link in enumerate(links):
        for e in validate_link(link, valid_sids=valid_sids):
            errors.append(f"links[{i}]: {e}")
        if isinstance(link, dict) and link.get("id"):
            if link["id"] in seen_ids:
                errors.append(f"links[{i}]: duplicate id {link['id']!r}")
            seen_ids.add(link["id"])
    return errors


def candidate_sids() -> set[str]:
    """Every sid in the current storyline window.

    The bundle includes a compact ``window_sids`` allowlist in addition to the
    candidate groups. Using the full window keeps accepted links valid after
    they surface and disappear from subsequent candidate groups, and permits a
    near-miss to include members of the existing storyline it extends.
    """
    bundle = load_json(CANDIDATES_FILE, {}) or {}
    sids = {
        sid for sid in (bundle.get("window_sids") or [])
        if isinstance(sid, str)
    }
    for group in (bundle.get("near_miss") or []) + (bundle.get("co_mention") or []):
        for n in group.get("nodes") or []:
            if n.get("sid"):
                sids.add(n["sid"])
    return sids
