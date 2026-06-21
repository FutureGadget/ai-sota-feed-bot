"""Deterministic PLACEHOLDER Playbook edition, for smoke-testing the UI.

This is NOT real editorial work — it mechanically turns the top articles in the
input bundle into template cards so the /playbook page can be eyeballed before a
real agent run exists. The problem/apply/result lines are generic stubs, clearly
marked, and must never be published as a real edition.

Usage:
    python build_playbook_input.py            # build the bundle first
    python seed_playbook_sample.py            # writes data/playbook/<date>.json
    python seed_playbook_sample.py --limit 6
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone

from playbook_common import (
    PLAYBOOK_DIR,
    PLAYBOOK_INPUT_DIR,
    fmt_day,
    load_json,
    source_sid,
    write_json,
)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=6, help="max cards (default 6)")
    args = ap.parse_args()

    bundle = load_json(PLAYBOOK_INPUT_DIR / "latest.json", None)
    if not isinstance(bundle, dict) or not bundle.get("articles"):
        raise SystemExit("no input bundle — run build_playbook_input.py first")

    day = bundle["date"]
    articles = bundle["articles"][: args.limit]

    cards = []
    for a in articles:
        cards.append(
            {
                "id": f"pb-{source_sid(a['url'])}",
                "kind": "source-backed",
                "title": f"[placeholder] Apply the learning from: {a['title']}",
                "area": "Tool use",
                "problem": "PLACEHOLDER — replace with the problem this solves for an agent builder.",
                "apply": f"PLACEHOLDER — read the source ({a['source']}) and state the concrete change to make.",
                "result": "PLACEHOLDER — state the expected result / payoff.",
                "effort": "medium",
                "source": a["source"],
                "source_url": a["url"],
                "source_sid": source_sid(a["url"]),
                "evidence": {
                    "kind": "editorial-inference",
                    "note": "PLACEHOLDER — replace with the source's actual evidence basis.",
                },
                "published": a.get("published"),
            }
        )

    edition = {
        "date": day,
        "title": f"Agent Builder's Playbook — {bundle.get('range_label', fmt_day(datetime.now(timezone.utc).date()))}",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "intro": [
            "PLACEHOLDER edition seeded from the input bundle for UI testing only. "
            "Replace every card with real editorial cards before publishing."
        ],
        "card_count": len(cards),
        "cards": cards,
    }

    out = PLAYBOOK_DIR / f"{day}.json"
    write_json(out, edition)
    print(f"wrote placeholder edition: {out} ({len(cards)} cards)")


if __name__ == "__main__":
    main()
