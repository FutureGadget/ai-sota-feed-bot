"""Build the storyline-editor *input bundle* for an agent to narrate.

Reads the mechanically-built storyline index + per-slug timelines and emits the
subset of storylines that currently need a narrative (no sidecar yet, or a
sidecar that's gone stale because the thread moved on), each with its full
day-by-day timeline as reading material.

A Claude Code routine reads ``data/storylines/input/latest.json``, writes one
narrative sidecar per storyline to ``data/storylines/narratives/<slug>.json``,
then runs the validator + ``pipeline/build_storylines.py`` to overlay them.

Usage:
    python build_storyline_input.py                 # storylines needing a narrative
    python build_storyline_input.py --all           # every active storyline (mark all)
    python build_storyline_input.py --slug claude-fable
    python build_storyline_input.py --refresh-all   # treat every storyline as needing one
"""

from __future__ import annotations

import argparse
import json

from storyline_common import (
    INPUT_DIR,
    ITEM_FIELDS,
    STORYLINES_INDEX,
    load_json,
    member_sids,
    narrative_is_fresh,
    narrative_path,
    now_iso,
    write_json,
)


def _timeline(detail: dict) -> list[dict]:
    """Project a detail file's days down to the fields the agent reads."""
    out = []
    for day in detail.get("days") or []:
        items = []
        for it in (day or {}).get("items") or []:
            if not isinstance(it, dict):
                continue
            proj = {k: it[k] for k in ITEM_FIELDS if it.get(k)}
            if it.get("sources"):
                proj["sources"] = it["sources"]
            items.append(proj)
        if items:
            out.append({"date": day.get("date"), "items": items})
    return out


def _needs_narrative(entry: dict, narrative: dict | None, *, force: bool) -> tuple[bool, str]:
    if force:
        return True, "refresh_requested"
    if not narrative:
        return True, "no_narrative"
    if not narrative_is_fresh(narrative, entry):
        return True, "stale"
    return False, "current"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--all", action="store_true", help="include every active storyline in the bundle (still flags which need work)")
    ap.add_argument("--slug", help="restrict the bundle to a single storyline slug")
    ap.add_argument("--refresh-all", action="store_true", help="treat every storyline as needing a (re)write")
    args = ap.parse_args()

    index = load_json(STORYLINES_INDEX, {}) or {}
    storylines = index.get("storylines") or []
    if args.slug:
        storylines = [s for s in storylines if s.get("slug") == args.slug]

    rows = []
    for entry in storylines:
        slug = entry.get("slug")
        if not slug:
            continue
        detail = load_json(narrative_path(slug).parent.parent / f"{slug}.json", {}) or {}
        narrative = load_json(narrative_path(slug), None)
        needs, reason = _needs_narrative(entry, narrative if isinstance(narrative, dict) else None, force=args.refresh_all)
        if not needs and not args.all and not args.slug:
            continue
        rows.append(
            {
                "slug": slug,
                "label": entry.get("label") or slug,
                "item_count": entry.get("item_count"),
                "source_count": entry.get("source_count"),
                "day_count": entry.get("day_count"),
                "first_seen": entry.get("first_seen"),
                "last_updated": entry.get("last_updated"),
                "latest_title": entry.get("latest_title"),
                "member_sids": member_sids(entry),
                "via_scout": bool(entry.get("via_scout")),
                "has_narrative": isinstance(narrative, dict),
                "needs_narrative": needs,
                "reason": reason,
                "narrative_path": f"data/storylines/narratives/{slug}.json",
                # On a refresh, hand the agent its prior narrative so it can
                # carry the arc forward (extend beats / update status) instead
                # of re-deriving the whole story from scratch.
                "prior_narrative": narrative if isinstance(narrative, dict) else None,
                "timeline": _timeline(detail),
            }
        )

    needs_count = sum(1 for r in rows if r["needs_narrative"])
    bundle = {
        "generated_at": now_iso(),
        "window_days": index.get("window_days"),
        "storyline_count": len(rows),
        "needs_narrative_count": needs_count,
        "storylines": rows,
    }
    write_json(INPUT_DIR / "latest.json", bundle)

    print(
        json.dumps(
            {
                "storyline_count": len(rows),
                "needs_narrative_count": needs_count,
                "needs_narrative": [
                    {"slug": r["slug"], "label": r["label"], "reason": r["reason"]}
                    for r in rows
                    if r["needs_narrative"]
                ],
                "input_path": "data/storylines/input/latest.json",
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
