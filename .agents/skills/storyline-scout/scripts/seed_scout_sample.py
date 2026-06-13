"""Write a deterministic PLACEHOLDER scout link from the candidate bundle.

NOT a real judgment — it mechanically picks the first candidate group whose
nodes can clear the floor (>=3 items, >=2 days, >=2 sources) and links them, so
the scout -> link -> build -> render path can be smoke-tested without an agent.
The real links (the editorial judgment) are written by the storyline-scout
routine after Haiku judges rule on each candidate.

Usage:
    python seed_scout_sample.py
"""

from __future__ import annotations

from scout_common import CANDIDATES_FILE, LINKS_FILE, load_json, write_json


def _floor_subset(nodes: list[dict]) -> list[dict] | None:
    """Smallest prefix of nodes (newest-first bundle order) that clears the floor."""
    picked: list[dict] = []
    for n in nodes:
        picked.append(n)
        days = {p.get("date") for p in picked}
        sources = {s for p in picked for s in (p.get("sources") or [])}
        if len(picked) >= 3 and len(days) >= 2 and len(sources) >= 2:
            return picked
    return None


def main() -> None:
    bundle = load_json(CANDIDATES_FILE, {}) or {}
    groups = (bundle.get("co_mention") or []) + (bundle.get("near_miss") or [])
    for g in groups:
        subset = _floor_subset(g.get("nodes") or [])
        if subset:
            link = {
                "id": f"placeholder-{g.get('id')}",
                "label_hint": f"[placeholder] {g.get('subject') or g.get('id')}",
                "members": [n["sid"] for n in subset if n.get("sid")],
                "reason": "[placeholder] seeded for UI smoke-test, not a real judgment",
                "confidence": "low",
                "candidate_id": g.get("id"),
            }
            write_json(LINKS_FILE, [link])
            print(f"seeded placeholder link from candidate {g.get('id')} "
                  f"({len(link['members'])} members)")
            return
    print("no candidate group could clear the floor — nothing seeded")


if __name__ == "__main__":
    main()
