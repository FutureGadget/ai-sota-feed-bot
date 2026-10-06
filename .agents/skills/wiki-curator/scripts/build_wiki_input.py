#!/usr/bin/env python3
"""Build the wiki-curator ingest bundle: recent stories grouped by obstacle area.

Reads the durable story store, keeps the last N days, and buckets each story
under the obstacle `area`s whose keywords it matches (a story can land in
several). Each story carries `filed_in` — the topics whose page or entries
already cite it — so the curator files only what is genuinely new. Also emits
the current topic list with each topic's themes and entry counts.

`--slug S` adds a `focus` dossier for one topic: its themes, its entries, and
every source it cites (title, url, source, dates, summary), for rewriting the
overview or reorganizing entries.

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
ENTRIES_DIR = WIKI_DIR / "entries"
INPUT_DIR = WIKI_DIR / "input"
FRONT_MATTER_RE = re.compile(r"^---\n(.*?)\n---\n?", re.DOTALL)

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


def front_matter(path: Path) -> dict:
    m = FRONT_MATTER_RE.match(path.read_text(encoding="utf-8"))
    meta = yaml.safe_load(m.group(1)) if m else {}
    return meta if isinstance(meta, dict) else {}


def as_list(value) -> list[str]:
    if not value:
        return []
    return [str(value)] if isinstance(value, str) else [str(v) for v in value]


def collect_topics() -> list[dict]:
    topics = []
    for sub in ("obstacles", "solutions"):
        d = WIKI_DIR / sub
        for path in sorted(d.glob("*.md")) if d.is_dir() else []:
            meta = front_matter(path)
            slug = str(meta.get("slug") or path.stem)
            entries = []
            edir = ENTRIES_DIR / slug
            for epath in sorted(edir.glob("*.md")) if edir.is_dir() else []:
                em = front_matter(epath)
                entries.append(
                    {
                        "id": epath.stem,
                        "date": str(em.get("date") or ""),
                        "title": em.get("title"),
                        "theme": em.get("theme"),
                        "evidence": as_list(em.get("evidence")),
                        "also": as_list(em.get("also")),
                    }
                )
            entries.sort(key=lambda e: (e["date"], e["id"]), reverse=True)
            themes = []
            for t in meta.get("themes") or []:
                if isinstance(t, dict):
                    key = t.get("key")
                    themes.append(
                        {
                            "key": key,
                            "title": t.get("title"),
                            "count": sum(1 for e in entries if e["theme"] == key),
                        }
                    )
            topics.append(
                {
                    "slug": slug,
                    "kind": meta.get("kind"),
                    "area": meta.get("area"),
                    "title": meta.get("title"),
                    "themes": themes,
                    "entry_count": len(entries),
                    "latest_entry_date": entries[0]["date"] if entries else None,
                    "_page_evidence": as_list(meta.get("evidence")),
                    "_entries": entries,
                }
            )
    return topics


def filed_index(topics: list[dict]) -> dict[str, list[str]]:
    """sid -> topics whose page evidence or entries already cite it."""
    filed: dict[str, list[str]] = {}
    for t in topics:
        sids = set(t["_page_evidence"])
        for e in t["_entries"]:
            sids.update(e["evidence"])
        for sid in sids:
            filed.setdefault(sid, []).append(t["slug"])
    return filed


def story_row(sid: str, rec: dict) -> dict:
    return {
        "sid": sid,
        "title": rec.get("title"),
        "url": rec.get("url"),
        "source": rec.get("source"),
        "type": rec.get("type"),
        "summary": (rec.get("summary_1line") or rec.get("summary") or "")[:280],
        "published": rec.get("published"),
        "first_seen": rec.get("first_seen"),
    }


def areas_for(text: str) -> list[str]:
    t = text.lower()
    return [area for area, cues in AREA_CUES.items() if any(c in t for c in cues)]


def focus_dossier(topic: dict, store: dict) -> dict:
    cited: list[str] = list(topic["_page_evidence"])
    filed_as: dict[str, list[str]] = {}
    for e in topic["_entries"]:
        for sid in e["evidence"]:
            filed_as.setdefault(sid, []).append(e["id"])
            if sid not in cited:
                cited.append(sid)
    sources = []
    for sid in cited:
        rec = store.get(sid)
        if rec is None:
            sources.append({"sid": sid, "missing": True})
            continue
        row = story_row(sid, rec)
        row["summary"] = (rec.get("summary") or rec.get("summary_1line") or "")[:600]
        row["filed_as"] = filed_as.get(sid, [])
        sources.append(row)
    return {
        "slug": topic["slug"],
        "themes": topic["themes"],
        "entries": topic["_entries"],
        "sources": sources,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--slug", default="")
    ap.add_argument("--out", default=str(INPUT_DIR / "latest.json"))
    args = ap.parse_args()

    topics = collect_topics()
    filed = filed_index(topics)
    cutoff = datetime.now(timezone.utc) - timedelta(days=args.days)
    store = load_store()
    by_area: dict[str, list[dict]] = {}
    for sid, rec in store.items():
        dt = parse_dt(rec.get("published") or rec.get("first_seen"))
        if dt and dt < cutoff:
            continue
        blob = f"{rec.get('title', '')} {rec.get('summary_1line') or rec.get('summary', '')}"
        for area in areas_for(blob):
            row = story_row(sid, rec)
            row["filed_in"] = filed.get(sid, [])
            by_area.setdefault(area, []).append(row)

    for area in by_area:
        by_area[area].sort(key=lambda r: r.get("published") or "", reverse=True)

    focus = None
    if args.slug:
        match = next((t for t in topics if t["slug"] == args.slug), None)
        if match is None:
            sys.exit(f"unknown slug {args.slug!r}")
        focus = focus_dossier(match, store)

    bundle = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "window_days": args.days,
        "topics": [{k: v for k, v in t.items() if not k.startswith("_")} for t in topics],
        "stories_by_area": by_area,
        "focus": focus,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(bundle, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    n_stories = sum(len(v) for v in by_area.values())
    n_new = sum(1 for v in by_area.values() for r in v if not r["filed_in"])
    print(
        f"wiki input: {len(topics)} topics, {n_stories} story-matches ({n_new} unfiled) across "
        f"{len(by_area)} areas (last {args.days}d)"
        + (f", focus={args.slug} ({len(focus['sources'])} sources)" if focus else "")
        + f" -> {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out}"
    )


if __name__ == "__main__":
    main()
