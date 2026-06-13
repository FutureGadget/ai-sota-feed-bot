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
    return {
        "slug": row["slug"],
        "generated_at": now_iso(),
        "covers_last_updated": row.get("last_updated"),
        "covers_member_sids": row.get("member_sids") or [],
        "tldr": tldr,
        "whats_new": f"[placeholder] Latest: {last}." if last else "",
        "why_it_matters": "[placeholder] why this matters to AI platform engineers.",
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
