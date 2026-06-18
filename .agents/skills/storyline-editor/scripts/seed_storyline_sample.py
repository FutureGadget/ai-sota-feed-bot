"""Write deterministic PLACEHOLDER narrative sidecars from the input bundle.

NOT a real summary — it stitches together titles mechanically so the
``/storyline`` page can be smoke-tested end to end (input -> sidecar -> overlay
-> render) without invoking an agent. The real narrative (the editorial work)
is written by the storyline-editor routine.

Usage:
    python seed_storyline_sample.py            # seed every storyline needing one
    python seed_storyline_sample.py --slug claude-fable
"""

from __future__ import annotations

import argparse

from storyline_common import (
    INPUT_DIR,
    load_json,
    narrative_path,
    now_iso,
    write_json,
)


# Deterministic beat shape so the seeded arc exercises every tone/node style.
_BEAT_PLAN = [
    ("LAUNCH", "launch", "It begins"),
    ("DEVELOPS", "rising", "The story develops"),
    ("THE TURN", "turn", "The pivot"),
    ("NOW", "now", "Where it stands"),
]


def _chunk(items: list, n: int) -> list[list]:
    """Split items into up to n contiguous, roughly equal chunks (no empties)."""
    n = min(n, len(items)) or 1
    size = -(-len(items) // n)  # ceil
    return [items[i : i + size] for i in range(0, len(items), size)]


def _seed_for(row: dict) -> dict:
    days = row.get("timeline") or []
    items = [it for d in days for it in d.get("items") or []]
    first = items[0]["title"] if items else row.get("label")
    last = items[-1]["title"] if items else ""
    tldr = (
        f"[placeholder] {row.get('label')} has developed across "
        f"{row.get('day_count')} days and {row.get('source_count')} sources, "
        f"from “{first}” to “{last}”."
    )
    chunks = _chunk(items, len(_BEAT_PLAN)) if items else []
    beats = []
    provenance: dict = {}
    for i, ((kicker, tone, headline), group) in enumerate(zip(_BEAT_PLAN, chunks)):
        sids = [it["sid"] for it in group if it.get("sid")]
        beats.append(
            {
                "kicker": kicker,
                "tone": tone,
                "headline": f"[placeholder] {headline}",
                "summary": f"[placeholder] {group[0].get('title')}",
                "sids": sids,
            }
        )
        # Exercise each provenance badge across the seeded beats.
        if sids and i == 0:
            provenance[sids[0]] = {"surfaced_by": "scout"}
        if sids and tone == "turn":
            for s in sids:
                provenance[s] = {"verified": max(2, len(group))}
        if sids and i == len(_BEAT_PLAN) - 1:
            provenance[sids[-1]] = {"status_update": True}
    return {
        "slug": row["slug"],
        "generated_at": now_iso(),
        "covers_last_updated": row.get("last_updated"),
        "covers_member_sids": row.get("member_sids") or [],
        "tldr": tldr,
        "whats_new": f"[placeholder] Latest: {last}." if last else "",
        "why_it_matters": "[placeholder] why this matters to AI platform engineers.",
        "status": {
            "state": "Developing",
            "tone": "now",
            "changed": row.get("last_updated"),
            "detail": f"[placeholder] current framing of {row.get('label')}.",
            "track": [
                {"label": "early", "detail": "", "tone": "launch", "weight": 60},
                {"label": "now", "detail": "", "tone": "now", "weight": 40},
            ],
        },
        "beats": beats,
        "provenance": provenance,
        "open_questions": [
            "[placeholder] what should an engineer watch next?",
            "[placeholder] does this extend beyond this vendor?",
        ],
        "take_for_builders": "[placeholder] one actionable takeaway for platform engineers.",
        "day_captions": {
            it["sid"]: f"[placeholder] {it.get('title')}"
            for it in items
            if it.get("sid")
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--slug", help="seed only this storyline")
    args = ap.parse_args()

    bundle = load_json(INPUT_DIR / "latest.json", {}) or {}
    rows = bundle.get("storylines") or []
    if args.slug:
        rows = [r for r in rows if r.get("slug") == args.slug]

    seeded = 0
    for row in rows:
        if not row.get("slug"):
            continue
        if not args.slug and not row.get("needs_narrative"):
            continue
        write_json(narrative_path(row["slug"]), _seed_for(row))
        seeded += 1
        print(f"seeded placeholder: {row['slug']}")

    print(f"seeded {seeded} placeholder narrative(s)")


if __name__ == "__main__":
    main()
