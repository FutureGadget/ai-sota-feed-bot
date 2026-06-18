#!/usr/bin/env python3
"""Build the wiki-curator ingest bundle: recent stories grouped by obstacle area.

Reads the durable story store, keeps the last N days, and buckets each story
under the obstacle `area`s whose keywords it matches (a story can land in
several). Also emits the current wiki nodes + their `covers_evidence` snapshot
so the curator can see what is already filed and what looks stale.

    python .agents/skills/wiki-curator/scripts/build_wiki_input.py [--days 7] [--slug S]

Writes data/wiki/input/latest.json. Stdlib + the repo's story_store helper only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "pipeline"))
from story_store import load_store, parse_dt  # noqa: E402

import yaml  # noqa: E402

WIKI_DIR = ROOT / "data" / "wiki"
INPUT_DIR = WIKI_DIR / "input"
FRONT_MATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)

# Keyword cues per obstacle area (cheap routing for the curator; not a classifier).
# Keep loosely aligned with config/wiki_schema.md areas + config/profile.yaml.
AREA_CUES: dict[str, list[str]] = {
    "reliability": ["hallucinat", "mistake", "self-correct", "verifier", "guardrail", "reliab", "faithful"],
    "memory": ["memory", "context window", "long-term", "forget", "recall", "compaction", "summariz"],
    "planning": ["planning", "reasoning", "decompos", "react", "plan-and-execute", "loop"],
    "tool-use": ["tool use", "tool call", "function call", "mcp", "tool selection", "interop"],
    "grounding": ["rag", "retrieval", "grounding", "embedding", "knowledge base", "citation", "vector"],
    "evaluation": ["eval", "benchmark", "regression", "judge", "trajectory"],
    "multi-agent": ["multi-agent", "multi agent", "orchestrat", "handoff", "swarm"],
    "cost": ["token cost", "cost", "cheaper", "budget", "caching", "kv cache"],
    "latency": ["latency", "throughput", "serving", "vllm", "tgi", "triton", "speculative"],
    "observability": ["observability", "tracing", "debug", "logging", "telemetry"],
    "security": ["prompt injection", "exfiltrat", "sandbox", "permission", "jailbreak", "security"],
    "prod-reliability": ["retries", "idempoten", "checkpoint", "recovery", "determinism"],
    "scalability": ["scalab", "concurren", "horizontal", "durable", "queue", "state"],
    "human-control": ["human-in-the-loop", "approval", "interrupt", "escalation", "steering"],
    "drift": ["drift", "regression", "upgrade", "deprecat", "version"],
}


def page_meta(path: Path) -> dict:
    m = FRONT_MATTER_RE.match(path.read_text(encoding="utf-8"))
    return yaml.safe_load(m.group(1)) if m else {}


def collect_nodes() -> list[dict]:
    nodes = []
    for sub in ("obstacles", "solutions"):
        for path in sorted((WIKI_DIR / sub).glob("*.md")) if (WIKI_DIR / sub).is_dir() else []:
            meta = page_meta(path) or {}
            nodes.append(
                {
                    "slug": meta.get("slug"),
                    "kind": meta.get("kind"),
                    "area": meta.get("area"),
                    "status": meta.get("status"),
                    "evidence": meta.get("evidence") or [],
                    "covers_evidence": meta.get("covers_evidence") or [],
                }
            )
    return nodes


def areas_for(text: str) -> list[str]:
    t = text.lower()
    return [area for area, cues in AREA_CUES.items() if any(c in t for c in cues)]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--slug", default="")
    args = ap.parse_args()

    cutoff = datetime.now(timezone.utc) - timedelta(days=args.days)
    store = load_store()
    by_area: dict[str, list[dict]] = {}
    for sid, rec in store.items():
        dt = parse_dt(rec.get("published") or rec.get("first_seen"))
        if dt and dt < cutoff:
            continue
        blob = f"{rec.get('title', '')} {rec.get('summary_1line') or rec.get('summary', '')}"
        for area in areas_for(blob):
            by_area.setdefault(area, []).append(
                {
                    "sid": sid,
                    "title": rec.get("title"),
                    "url": rec.get("url"),
                    "source": rec.get("source"),
                    "type": rec.get("type"),
                    "summary": (rec.get("summary_1line") or rec.get("summary") or "")[:280],
                    "published": rec.get("published"),
                }
            )

    for area in by_area:
        by_area[area].sort(key=lambda r: r.get("published") or "", reverse=True)

    bundle = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "window_days": args.days,
        "nodes": collect_nodes(),
        "stories_by_area": by_area if not args.slug else {},
        "focus_slug": args.slug or None,
    }
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    (INPUT_DIR / "latest.json").write_text(
        json.dumps(bundle, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    n_stories = sum(len(v) for v in by_area.values())
    print(
        f"wiki input: {len(bundle['nodes'])} nodes, {n_stories} story-matches across "
        f"{len(by_area)} areas (last {args.days}d) -> data/wiki/input/latest.json"
    )


if __name__ == "__main__":
    main()
