#!/usr/bin/env python3
"""Compile the agent-engineering wiki (markdown pages) into a served index.json.

This is the deterministic half of the LLM-wiki loop (Karpathy's pattern): the
``wiki-curator`` Claude Code routine writes/updates the markdown **pages** under
``data/wiki/{obstacles,solutions}/`` (the source of truth); this script reads
them, validates the schema invariants in ``config/wiki_schema.md``, symmetrizes
the obstacle<->solution edges, resolves evidence to real story titles, and emits
``data/wiki/index.json`` — the single artifact the static renderer and the
``/api/topics`` function read. No LLM in this path.

Validation failures (dangling edges, unresolved evidence, bad slugs) raise and
exit non-zero so a broken page is caught before publish, mirroring
``validate_narratives.py``. Run after the curator edits pages:

    python pipeline/build_wiki.py [--check]

``--check`` validates without writing index.json.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from html import escape
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WIKI_DIR = ROOT / "data" / "wiki"
STORIES_INDEX = ROOT / "data" / "stories" / "index.json"
STORYLINES_INDEX = ROOT / "data" / "storylines" / "index.json"

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,80}$")
FRONT_MATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)

# Obstacle areas (the spine). Keep in sync with config/wiki_schema.md.
AREAS: list[tuple[str, str]] = [
    ("reliability", "Reliability & correctness"),
    ("memory", "Memory & context"),
    ("planning", "Planning & reasoning"),
    ("tool-use", "Tool use & interop"),
    ("grounding", "Grounding & knowledge"),
    ("evaluation", "Evaluation"),
    ("multi-agent", "Multi-agent coordination"),
    ("cost", "Cost"),
    ("latency", "Latency & throughput"),
    ("observability", "Observability & debugging"),
    ("security", "Security & safety"),
    ("prod-reliability", "Production reliability"),
    ("scalability", "Scalability & state"),
    ("human-control", "Human-in-the-loop & control"),
    ("drift", "Drift & maintenance"),
]
AREA_LABELS = dict(AREAS)


class WikiError(Exception):
    """A schema/validation problem in the wiki source."""


def parse_page(path: Path) -> dict:
    """Parse one markdown page into {meta..., 'sections': [(heading, body)]}."""
    text = path.read_text(encoding="utf-8")
    m = FRONT_MATTER_RE.match(text)
    if not m:
        raise WikiError(f"{path.name}: missing YAML front matter")
    try:
        meta = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as e:  # pragma: no cover - defensive
        raise WikiError(f"{path.name}: bad front matter: {e}") from e
    if not isinstance(meta, dict):
        raise WikiError(f"{path.name}: front matter is not a mapping")
    meta["sections"] = parse_sections(m.group(2))
    meta["_file"] = path.name
    return meta


def parse_sections(body: str) -> list[tuple[str, str]]:
    """Split a markdown body on ``## Heading`` into ordered (heading, text)."""
    sections: list[tuple[str, str]] = []
    heading = None
    buf: list[str] = []
    for line in body.splitlines():
        h = re.match(r"^##\s+(.*)$", line)
        if h:
            if heading is not None:
                sections.append((heading, "\n".join(buf).strip()))
            heading = h.group(1).strip()
            buf = []
        elif heading is not None:
            buf.append(line)
    if heading is not None:
        sections.append((heading, "\n".join(buf).strip()))
    return sections


def md_inline(text: str) -> str:
    """Escape, then apply a tiny inline-markdown subset: links + bold + code."""
    out = escape(text)
    out = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', out)
    out = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    return out


def md_to_html(text: str) -> str:
    """Render a section body: blank-line paragraphs + ``- ``/``* `` bullet lists."""
    blocks: list[str] = []
    para: list[str] = []
    items: list[str] = []

    def flush_para() -> None:
        if para:
            blocks.append("<p>" + md_inline(" ".join(para)) + "</p>")
            para.clear()

    def flush_list() -> None:
        if items:
            lis = "".join(f"<li>{md_inline(i)}</li>" for i in items)
            blocks.append(f"<ul>{lis}</ul>")
            items.clear()

    for line in text.splitlines():
        stripped = line.strip()
        bullet = re.match(r"^[-*]\s+(.*)$", stripped)
        if bullet:
            flush_para()
            items.append(bullet.group(1))
        elif not stripped:
            flush_para()
            flush_list()
        else:
            flush_list()
            para.append(stripped)
    flush_para()
    flush_list()
    return "\n".join(blocks)


def as_list(value) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [value]
    return [str(v) for v in value]


def load_pages() -> dict[str, dict]:
    pages: dict[str, dict] = {}
    for sub in ("obstacles", "solutions"):
        d = WIKI_DIR / sub
        if not d.is_dir():
            continue
        for path in sorted(d.glob("*.md")):
            page = parse_page(path)
            slug = str(page.get("slug") or "")
            if not SLUG_RE.match(slug):
                raise WikiError(f"{path.name}: invalid slug {slug!r}")
            if slug != path.stem:
                raise WikiError(f"{path.name}: slug {slug!r} != filename stem")
            if slug in pages:
                raise WikiError(f"duplicate slug {slug!r}")
            kind = page.get("kind")
            if kind not in ("obstacle", "solution"):
                raise WikiError(f"{path.name}: bad kind {kind!r}")
            if kind == "obstacle" and page.get("area") not in AREA_LABELS:
                raise WikiError(f"{path.name}: unknown area {page.get('area')!r}")
            if sub == "obstacles" and kind != "obstacle":
                raise WikiError(f"{path.name}: obstacle page must be kind: obstacle")
            if sub == "solutions" and kind != "solution":
                raise WikiError(f"{path.name}: solution page must be kind: solution")
            pages[slug] = page
    return pages


def symmetrize(pages: dict[str, dict]) -> None:
    """Make obstacle.solutions <-> solution.obstacles consistent; reject dangling."""
    sol_of: dict[str, set[str]] = {s: set() for s in pages}
    obs_of: dict[str, set[str]] = {s: set() for s in pages}
    for slug, p in pages.items():
        for other in as_list(p.get("solutions")):
            if other not in pages or pages[other]["kind"] != "solution":
                raise WikiError(f"{slug}: links to unknown solution {other!r}")
            sol_of[slug].add(other)
            obs_of[other].add(slug)
        for other in as_list(p.get("obstacles")):
            if other not in pages or pages[other]["kind"] != "obstacle":
                raise WikiError(f"{slug}: links to unknown obstacle {other!r}")
            obs_of[slug].add(other)
            sol_of[other].add(slug)
    for slug, p in pages.items():
        p["_solutions"] = sorted(sol_of[slug])
        p["_obstacles"] = sorted(obs_of[slug])


def build_index(pages: dict[str, dict]) -> dict:
    stories = json.loads(STORIES_INDEX.read_text()) if STORIES_INDEX.exists() else {}
    sl_index = json.loads(STORYLINES_INDEX.read_text()) if STORYLINES_INDEX.exists() else {}
    sl_labels = {
        str(s.get("slug")): s.get("label") or s.get("slug")
        for s in (sl_index.get("storylines") or [])
        if isinstance(s, dict) and s.get("slug")
    }

    def title_of(slug: str) -> str:
        return str(pages[slug].get("title") or slug)

    nodes: dict[str, dict] = {}
    for slug, p in pages.items():
        evidence = []
        for sid in as_list(p.get("evidence")):
            rec = stories.get(sid)
            if rec is None:
                raise WikiError(f"{slug}: evidence sid {sid} not in stories index")
            evidence.append({"sid": sid, "title": rec.get("title") or sid})
        storylines = []
        for sl in as_list(p.get("related_storylines")):
            if sl not in sl_labels:
                raise WikiError(f"{slug}: related storyline {sl!r} not in index")
            storylines.append({"slug": sl, "label": sl_labels[sl]})

        sections = [(h, b) for h, b in p.get("sections", []) if b]
        summary = next((b for h, b in sections if h.lower() == "tl;dr"), "")
        if not summary:
            raise WikiError(f"{slug}: missing required TL;DR section")
        nodes[slug] = {
            "slug": slug,
            "kind": p["kind"],
            "title": title_of(slug),
            "area": p.get("area"),
            "status": p.get("status") or "active",
            "summary": summary,
            "sections": [{"heading": h, "html": md_to_html(b)} for h, b in sections],
            "solutions": [{"slug": s, "title": title_of(s)} for s in p["_solutions"]],
            "obstacles": [{"slug": s, "title": title_of(s)} for s in p["_obstacles"]],
            "related_storylines": storylines,
            "evidence": evidence,
            "updated": str(p.get("updated") or ""),
        }

    areas = []
    for area, label in AREAS:
        slugs = sorted(
            s for s, n in nodes.items() if n["kind"] == "obstacle" and n["area"] == area
        )
        if slugs:
            areas.append({"area": area, "label": label, "obstacles": slugs})

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "areas": areas,
        "nodes": nodes,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="validate without writing index.json")
    args = ap.parse_args()

    try:
        pages = load_pages()
        symmetrize(pages)
        index = build_index(pages)
    except WikiError as e:
        print(f"WIKI_BUILD_FAIL {e}", file=sys.stderr)
        sys.exit(1)

    n_obs = sum(1 for n in index["nodes"].values() if n["kind"] == "obstacle")
    n_sol = sum(1 for n in index["nodes"].values() if n["kind"] == "solution")
    if not args.check:
        (WIKI_DIR / "index.json").write_text(
            json.dumps(index, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
        )
    print(
        f"WIKI_BUILD_OK nodes={len(index['nodes'])} obstacles={n_obs} "
        f"solutions={n_sol} areas={len(index['areas'])}"
        + ("" if args.check else " -> data/wiki/index.json")
    )


if __name__ == "__main__":
    main()
