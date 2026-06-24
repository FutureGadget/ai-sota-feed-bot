#!/usr/bin/env python3
"""Build the Foundations curator input bundle.

The bundle is reading material for the agent routine. It proposes candidate
source stories and shows current Foundation/wiki/Playbook context, but it never
creates or edits published concept pages.

Usage:
    python .agents/skills/foundations-curator/scripts/build_foundations_input.py
    python .agents/skills/foundations-curator/scripts/build_foundations_input.py --days 30
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "pipeline"))
from story_store import load_store, parse_dt  # noqa: E402

FOUNDATIONS_DIR = ROOT / "data" / "foundations"
INPUT_DIR = FOUNDATIONS_DIR / "input"

CLUSTER_CUES: dict[str, list[str]] = {
    "prompting": ["prompt", "instruction", "few-shot", "chain-of-thought", "cot", "schema"],
    "retrieval": ["rag", "retrieval", "ground", "citation", "embedding", "vector"],
    "tool-use": ["tool", "function call", "mcp", "interop", "schema"],
    "memory": ["memory", "context", "compaction", "long-context", "recall"],
    "evaluation": ["eval", "benchmark", "judge", "regression", "test"],
    "operations": ["cost", "latency", "throughput", "serving", "cache"],
    "safety": ["injection", "sandbox", "permission", "safety", "guardrail"],
}


def load_json(path: Path, fallback: Any) -> Any:
    try:
        if not path.exists():
            return fallback
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def squeeze(value: Any, limit: int = 420) -> str:
    text = " ".join(str(value or "").replace("\n", " ").split())
    return text[:limit]


def clusters_for(text: str) -> list[str]:
    t = text.lower()
    return [cluster for cluster, cues in CLUSTER_CUES.items() if any(c in t for c in cues)]


def recent_stories(days: int) -> list[dict[str, Any]]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    stories = []
    for sid, rec in load_store().items():
        dt = parse_dt(rec.get("published") or rec.get("first_seen"))
        if dt and dt < cutoff:
            continue
        blob = f"{rec.get('title', '')} {rec.get('summary_1line') or rec.get('summary', '')}"
        clusters = clusters_for(blob)
        if not clusters:
            continue
        stories.append(
            {
                "sid": sid,
                "title": rec.get("title"),
                "url": rec.get("url"),
                "source": rec.get("source"),
                "type": rec.get("type"),
                "published": rec.get("published") or rec.get("first_seen"),
                "summary": squeeze(rec.get("summary_1line") or rec.get("summary")),
                "cluster_hints": clusters,
            }
        )
    stories.sort(key=lambda r: str(r.get("published") or ""), reverse=True)
    return stories


def current_foundations() -> list[dict[str, Any]]:
    index = load_json(FOUNDATIONS_DIR / "index.json", {})
    concepts = index.get("concepts") if isinstance(index, dict) else {}
    out = []
    for slug, concept in sorted((concepts or {}).items()):
        evidence = concept.get("evidence") or []
        covers = concept.get("covers_evidence") or []
        out.append(
            {
                "slug": slug,
                "title": concept.get("title"),
                "cluster": concept.get("cluster"),
                "updated": concept.get("updated"),
                "evidence_ids": [e.get("id") for e in evidence if isinstance(e, dict)],
                "covers_evidence": covers,
                "stale_hint": bool(covers) and set(covers) != {e.get("id") for e in evidence if isinstance(e, dict)},
            }
        )
    return out


def wiki_topics() -> list[dict[str, Any]]:
    index = load_json(ROOT / "data" / "wiki" / "index.json", {})
    nodes = index.get("nodes") if isinstance(index, dict) else {}
    return [
        {
            "slug": slug,
            "kind": node.get("kind"),
            "title": node.get("title"),
            "summary": node.get("summary"),
            "updated": node.get("updated"),
        }
        for slug, node in sorted((nodes or {}).items())
        if isinstance(node, dict)
    ]


def playbook_cards() -> list[dict[str, Any]]:
    latest = load_json(ROOT / "data" / "playbook" / "latest.json", {})
    cards = latest.get("cards") if isinstance(latest, dict) else []
    return [
        {
            "id": card.get("id"),
            "title": card.get("title"),
            "area": card.get("area"),
            "problem": card.get("problem"),
            "apply": card.get("apply"),
            "source_sid": card.get("source_sid"),
            "topic_url": card.get("topic_url"),
        }
        for card in cards or []
        if isinstance(card, dict)
    ]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--days", type=int, default=14)
    args = ap.parse_args()

    stories = recent_stories(args.days)
    bundle = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "window_days": args.days,
        "candidate_story_count": len(stories),
        "candidate_stories": stories,
        "current_foundations": current_foundations(),
        "wiki_topics": wiki_topics(),
        "latest_playbook_cards": playbook_cards(),
        "cluster_cues": CLUSTER_CUES,
    }
    write_json(INPUT_DIR / "latest.json", bundle)
    date_id = datetime.now(timezone.utc).date().isoformat()
    write_json(INPUT_DIR / f"{date_id}.json", bundle)
    print(
        f"foundations input: {len(stories)} candidate stories, "
        f"{len(bundle['current_foundations'])} existing concepts "
        f"-> data/foundations/input/latest.json"
    )


if __name__ == "__main__":
    main()
