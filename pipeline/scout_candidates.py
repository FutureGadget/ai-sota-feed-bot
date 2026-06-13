"""Deterministic candidate generator for the storyline-scout routine.

The storyline clustering in ``build_storylines.py`` is precision-first: it joins
stories only on a shared *rare anchor token*, so it structurally misses two
kinds of real thread —

1. **near-miss anchors** — a pair that shares an anchor and is *almost* a thread
   but sits under the MIN_ITEMS/MIN_DAYS/MIN_SOURCES floor (an emerging story, or
   a real thread that's still single-source);
2. **co-mention buckets** — unclustered stories about the same broad subject
   (e.g. several "openai" items) that the agent can scan for a genuine
   same-story/same-thread link the anchor rule can't see because the headlines
   share no *rare* word ("OpenAI's new flagship" vs "GPT-5 is here").

This script does the cheap, exact, reproducible prep: it reuses the real
clustering internals, subtracts what's already a storyline, and emits a tight
bundle of candidates for Haiku judges to rule on. It writes NO links itself —
the agent (storyline-scout) reads this and writes confirmed links to
``data/storylines/scout/links.json``, which ``build_storylines.py`` applies
through the same deterministic floor.

Stdlib only. Run after ``build_storylines.py`` so the current index exists:

    python pipeline/scout_candidates.py
"""

from __future__ import annotations

import itertools
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone

from build_storylines import (
    MIN_DAYS,
    MIN_ITEMS,
    MIN_SOURCES,
    OUT_DIR,
    WEAK,
    dedup_nodes,
    load_json,
    load_window,
    title_tokens,
)

SCOUT_DIR = OUT_DIR / "scout"
CANDIDATES_FILE = SCOUT_DIR / "candidates.json"

# Keep the bundle the agent reads small (token budget) — cap both candidate
# kinds and log when we drop, never silently truncate.
MAX_NEAR_MISS = 15
MAX_BUCKETS = 10
MAX_BUCKET_NODES = 8


def _node_view(node: dict) -> dict:
    """Project a node to the fields a judge needs, with one representative sid."""
    return {
        "sid": (node["sids"] or [None])[0],
        "title": node["title"],
        "sources": node["sources"],
        "type": node["rep"].get("type") or "news",
        "date": node["_dt"].date().isoformat(),
        "url": node["rep"].get("url") or "",
    }


def _signal(nodes: list[dict], idx) -> dict:
    days = {nodes[i]["_dt"].date() for i in idx}
    sources = {s for i in idx for s in nodes[i]["sources"]}
    return {"items": len(idx), "days": len(days), "sources": len(sources)}


def main() -> None:
    now = datetime.now(timezone.utc)
    nodes = dedup_nodes(load_window(now))

    # sids already living in a published storyline — don't re-propose those.
    index = load_json(OUT_DIR / "index.json", {}) or {}
    clustered: set[str] = set()
    storyline_of: dict[str, str] = {}
    for s in index.get("storylines") or []:
        for sid in s.get("member_sids") or []:
            clustered.add(sid)
            storyline_of[sid] = s.get("slug")

    def node_storyline(i: int) -> str | None:
        for sid in nodes[i]["sids"]:
            if sid in storyline_of:
                return storyline_of[sid]
        return None

    def fully_clustered(idx) -> bool:
        return all(any(sid in clustered for sid in nodes[i]["sids"]) for i in idx)

    tokmap = [n["tokens"] for n in nodes]
    df = Counter(tok for toks in tokmap for tok in toks)
    rare_cap = max(5, round(len(nodes) * 0.02))

    def strong(tok: str) -> bool:  # mirrors build_storylines.cluster()
        return tok not in WEAK and df[tok] <= rare_cap

    # --- near-miss anchors -------------------------------------------------
    pair_items: dict[tuple[str, str], set[int]] = defaultdict(set)
    for i, toks in enumerate(tokmap):
        for a, b in itertools.combinations(sorted(toks), 2):
            if strong(a) or strong(b):
                pair_items[(a, b)].add(i)

    near_miss = []
    for key, idx in pair_items.items():
        if len(idx) < 2 or fully_clustered(idx):
            continue
        sig = _signal(nodes, idx)
        qualifies = sig["items"] >= MIN_ITEMS and sig["days"] >= MIN_DAYS and sig["sources"] >= MIN_SOURCES
        # "close to the floor": shares an anchor, ≥2 items, and is at most one
        # short on any single dimension — i.e. a plausible promote/extend.
        close = (
            not qualifies
            and sig["items"] >= MIN_ITEMS - 1
            and sig["days"] >= MIN_DAYS - 1
            and sig["sources"] >= MIN_SOURCES - 1
        )
        if not close:
            continue
        related = next((node_storyline(i) for i in idx if node_storyline(i)), None)
        near_miss.append(
            {
                "id": f"nearmiss-{key[0]}-{key[1]}",
                "type": "near_miss",
                "anchor": list(key),
                "reason": f"shares anchor '{key[0]}/{key[1]}' but is under the floor "
                f"({sig['items']} items / {sig['days']} days / {sig['sources']} sources)",
                "signal": sig,
                "related_storyline": related,
                "nodes": [_node_view(nodes[i]) for i in sorted(idx, key=lambda i: nodes[i]["_dt"])],
            }
        )
    near_miss.sort(key=lambda c: (c["signal"]["items"], c["signal"]["sources"], c["signal"]["days"]), reverse=True)
    near_miss_dropped = max(0, len(near_miss) - MAX_NEAR_MISS)
    near_miss = near_miss[:MAX_NEAR_MISS]

    # --- co-mention buckets (different-vocabulary candidates) ---------------
    # Group still-unclustered nodes by a shared broad subject word (WEAK token):
    # same company/topic, no shared *rare* anchor → exactly what the anchor rule
    # can't join but a human (or judge) can read as one story.
    by_weak: dict[str, list[int]] = defaultdict(list)
    for i, toks in enumerate(tokmap):
        if any(sid in clustered for sid in nodes[i]["sids"]):
            continue
        for tok in toks:
            if tok in WEAK:
                by_weak[tok].append(i)

    buckets = []
    for tok, idxs in by_weak.items():
        uniq = sorted(set(idxs), key=lambda i: nodes[i]["_dt"], reverse=True)
        if len(uniq) < 2:
            continue
        dropped = max(0, len(uniq) - MAX_BUCKET_NODES)
        uniq = uniq[:MAX_BUCKET_NODES]
        buckets.append(
            {
                "id": f"comention-{tok}",
                "type": "co_mention",
                "subject": tok,
                "reason": f"{len(uniq)} unclustered stories mention '{tok}'; check for a "
                f"same-story/same-thread link the anchor rule can't see",
                "node_dropped": dropped,
                "nodes": [_node_view(nodes[i]) for i in uniq],
            }
        )
    buckets.sort(key=lambda b: len(b["nodes"]), reverse=True)
    buckets_dropped = max(0, len(buckets) - MAX_BUCKETS)
    buckets = buckets[:MAX_BUCKETS]

    bundle = {
        "generated_at": now.isoformat(),
        "node_count": len(nodes),
        # Validation allowlist. This includes every sid in the current window,
        # not only nodes proposed below, so an accepted link remains valid on
        # later runs after it has surfaced and is no longer a candidate.
        "window_sids": sorted({sid for node in nodes for sid in node["sids"]}),
        "near_miss_count": len(near_miss),
        "bucket_count": len(buckets),
        "dropped": {"near_miss": near_miss_dropped, "buckets": buckets_dropped},
        "near_miss": near_miss,
        "co_mention": buckets,
    }
    SCOUT_DIR.mkdir(parents=True, exist_ok=True)
    CANDIDATES_FILE.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "node_count": len(nodes),
                "near_miss_count": len(near_miss),
                "bucket_count": len(buckets),
                "dropped": bundle["dropped"],
                "candidates_path": "data/storylines/scout/candidates.json",
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
