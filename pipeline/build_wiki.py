#!/usr/bin/env python3
"""Compile the agent-engineering wiki (markdown pages) into a served index.json.

This is the deterministic half of the LLM-wiki loop (Karpathy's pattern): the
``wiki-curator`` Claude Code routine writes the markdown sources under
``data/wiki/`` (the source of truth); this script reads them, validates the
schema invariants in ``config/wiki_schema.md``, symmetrizes the
obstacle<->solution edges, resolves evidence to real story titles, and emits
``data/wiki/index.json`` — the single artifact the static renderer and the
``/api/topics`` function read — plus the human catalog ``data/wiki/index.md``.
No LLM in this path.

Two kinds of source file:

- **topic pages** ``data/wiki/{obstacles,solutions}/<slug>.md`` — a short,
  word-capped overview (TL;DR, State of the art, Why it matters, Trade-offs)
  plus the page's declared ``themes``;
- **entries** ``data/wiki/entries/<slug>/<YYYY-MM-DD>-<name>.md`` — one dated,
  source-backed development filed under one theme of that topic. New sources
  become new entries; the overview is rewritten, never appended to.

Validation failures (dangling edges, unresolved evidence, over-length sections,
unknown themes) are collected and reported together; any failure exits non-zero
so a broken page is caught before publish, mirroring ``validate_narratives.py``.

    python pipeline/build_wiki.py [--check] [--slug SLUG]

``--check`` validates without writing. ``--slug`` reports only errors for that
topic (its page and its entries) — useful while other pages are mid-edit.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime, timezone
from html import escape
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WIKI_DIR = ROOT / "data" / "wiki"
ENTRIES_DIR = WIKI_DIR / "entries"
STORIES_INDEX = ROOT / "data" / "stories" / "index.json"
STORYLINES_INDEX = ROOT / "data" / "storylines" / "index.json"

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,80}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ENTRY_FILE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-([a-z0-9][a-z0-9-]{0,80})$")
FRONT_MATTER_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)$", re.DOTALL)

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

# Overview sections allowed on a topic page, with their word caps. The caps keep
# a page readable in a minute; new material goes into entries, not here.
WHY_HEADING = "Why it matters for platform engineers"
SECTION_LIMITS: dict[str, int] = {
    "TL;DR": 80,
    "State of the art": 350,
    WHY_HEADING: 150,
    "Trade-offs": 200,
}
SECTIONS_BY_KIND = {
    "obstacle": ["TL;DR", "State of the art", WHY_HEADING],
    "solution": ["TL;DR", "State of the art", "Trade-offs", WHY_HEADING],
}
MAX_THEMES = 6
THEME_TITLE_MAX_CHARS = 80
THEME_SUMMARY_MAX_WORDS = 45
ENTRY_TITLE_MAX_CHARS = 110
ENTRY_BODY_MAX_WORDS = 130
ENTRY_MAX_EVIDENCE = 6
LATEST_ENTRIES = 20


class WikiError(Exception):
    """A schema/validation problem in the wiki source."""


class Errors:
    """Collects (slug, message) validation errors so a run reports them all."""

    def __init__(self) -> None:
        self.items: list[tuple[str, str]] = []

    def add(self, slug: str, message: str) -> None:
        self.items.append((slug, message))

    def for_slug(self, slug: str | None) -> list[str]:
        return [f"{s}: {m}" if s else m for s, m in self.items if slug is None or s in (slug, "")]


def split_front_matter(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    m = FRONT_MATTER_RE.match(text)
    if not m:
        raise WikiError(f"{path.name}: missing YAML front matter")
    try:
        meta = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as e:
        raise WikiError(f"{path.name}: bad front matter: {e}") from e
    if not isinstance(meta, dict):
        raise WikiError(f"{path.name}: front matter is not a mapping")
    return meta, m.group(2)


def parse_page(path: Path) -> dict:
    """Parse one topic page into {meta..., 'sections': [(heading, body)]}."""
    meta, body = split_front_matter(path)
    meta["sections"] = parse_sections(body)
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
    """Escape, then apply a tiny inline-markdown subset: links + bold + italic + code."""
    out = escape(text)
    out = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', out)
    out = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"(?<![*\w])\*([^*\s][^*]*)\*(?![*\w])", r"<em>\1</em>", out)
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
        elif items and line.startswith((" ", "\t")):
            items[-1] += " " + stripped  # wrapped continuation of a bullet
        else:
            flush_list()
            para.append(stripped)
    flush_para()
    flush_list()
    return "\n".join(blocks)


def word_count(text: str) -> int:
    plain = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text or "")
    return len(plain.split())


def as_list(value) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [value]
    return [str(v) for v in value]


def as_date(value) -> str:
    if isinstance(value, (date, datetime)):
        return value.isoformat()[:10]
    return str(value or "").strip()


def load_pages(errors: Errors) -> dict[str, dict]:
    pages: dict[str, dict] = {}
    for sub in ("obstacles", "solutions"):
        d = WIKI_DIR / sub
        if not d.is_dir():
            continue
        for path in sorted(d.glob("*.md")):
            try:
                page = parse_page(path)
            except WikiError as e:
                errors.add(path.stem, str(e))
                continue
            slug = str(page.get("slug") or "")
            if not SLUG_RE.match(slug):
                errors.add(path.stem, f"{path.name}: invalid slug {slug!r}")
                continue
            if slug != path.stem:
                errors.add(path.stem, f"{path.name}: slug {slug!r} != filename stem")
                continue
            if slug in pages:
                errors.add(slug, f"duplicate slug {slug!r}")
                continue
            kind = page.get("kind")
            expected = "obstacle" if sub == "obstacles" else "solution"
            if kind != expected:
                errors.add(slug, f"{path.name}: page under {sub}/ must be kind: {expected}")
                continue
            if kind == "obstacle" and page.get("area") not in AREA_LABELS:
                errors.add(slug, f"unknown area {page.get('area')!r}")
            validate_page_body(slug, page, errors)
            page["_themes"] = parse_themes(slug, page.get("themes"), errors)
            pages[slug] = page
    return pages


def validate_page_body(slug: str, page: dict, errors: Errors) -> None:
    allowed = SECTIONS_BY_KIND[page["kind"]]
    seen: set[str] = set()
    for heading, body in page["sections"]:
        if heading not in allowed:
            errors.add(
                slug,
                f"section '## {heading}' is not allowed on a {page['kind']} page "
                f"(allowed: {', '.join(allowed)}); new developments go in entries",
            )
            continue
        if heading in seen:
            errors.add(slug, f"duplicate section '## {heading}'")
        seen.add(heading)
        n = word_count(body)
        if n > SECTION_LIMITS[heading]:
            errors.add(
                slug,
                f"'## {heading}' is {n} words (max {SECTION_LIMITS[heading]}); "
                "rewrite it tighter and move specifics into entries",
            )
    if not any(h == "TL;DR" and b for h, b in page["sections"]):
        errors.add(slug, "missing required TL;DR section")


def parse_themes(slug: str, raw, errors: Errors) -> list[dict]:
    themes: list[dict] = []
    if not raw:
        errors.add(slug, "front matter needs at least one theme under `themes:`")
        return themes
    if not isinstance(raw, list):
        errors.add(slug, "`themes:` must be a list of {key, title, summary}")
        return themes
    if len(raw) > MAX_THEMES:
        errors.add(slug, f"{len(raw)} themes (max {MAX_THEMES}); merge related themes")
    keys: set[str] = set()
    for t in raw:
        if not isinstance(t, dict):
            errors.add(slug, f"theme {t!r} must be a mapping with key/title/summary")
            continue
        key = str(t.get("key") or "")
        title = " ".join(str(t.get("title") or "").split())
        summary = " ".join(str(t.get("summary") or "").split())
        if not SLUG_RE.match(key):
            errors.add(slug, f"theme key {key!r} must match {SLUG_RE.pattern}")
            continue
        if key in keys:
            errors.add(slug, f"duplicate theme key {key!r}")
            continue
        keys.add(key)
        if not title:
            errors.add(slug, f"theme {key!r} needs a title")
        elif len(title) > THEME_TITLE_MAX_CHARS:
            errors.add(slug, f"theme {key!r} title is {len(title)} chars (max {THEME_TITLE_MAX_CHARS})")
        if not summary:
            errors.add(slug, f"theme {key!r} needs a one-sentence summary")
        elif word_count(summary) > THEME_SUMMARY_MAX_WORDS:
            errors.add(
                slug,
                f"theme {key!r} summary is {word_count(summary)} words (max {THEME_SUMMARY_MAX_WORDS})",
            )
        themes.append({"key": key, "title": title, "summary": summary})
    return themes


def load_entries(pages: dict[str, dict], errors: Errors) -> dict[str, list[dict]]:
    """Read data/wiki/entries/<slug>/*.md into {slug: [entry, ...]}."""
    out: dict[str, list[dict]] = {slug: [] for slug in pages}
    if not ENTRIES_DIR.is_dir():
        return out
    for topic_dir in sorted(p for p in ENTRIES_DIR.iterdir() if p.is_dir()):
        slug = topic_dir.name
        if slug not in pages:
            errors.add(slug, f"entries/{slug}/ has no matching topic page")
            continue
        theme_keys = {t["key"] for t in pages[slug]["_themes"]}
        for path in sorted(topic_dir.iterdir()):
            rel = f"entries/{slug}/{path.name}"
            if path.suffix != ".md" or not path.is_file():
                errors.add(slug, f"{rel}: only <YYYY-MM-DD>-<name>.md entry files belong here")
                continue
            fm = ENTRY_FILE_RE.match(path.stem)
            if not fm:
                errors.add(slug, f"{rel}: filename must be <YYYY-MM-DD>-<name>.md")
                continue
            try:
                meta, body = split_front_matter(path)
            except WikiError as e:
                errors.add(slug, f"{rel}: {e}")
                continue
            entry_date = as_date(meta.get("date"))
            title = " ".join(str(meta.get("title") or "").split())
            theme = str(meta.get("theme") or "")
            body = body.strip()
            if not DATE_RE.match(entry_date):
                errors.add(slug, f"{rel}: `date:` must be YYYY-MM-DD")
            elif entry_date != fm.group(1):
                errors.add(slug, f"{rel}: filename date {fm.group(1)} != date {entry_date}")
            if not title:
                errors.add(slug, f"{rel}: missing title")
            elif len(title) > ENTRY_TITLE_MAX_CHARS:
                errors.add(slug, f"{rel}: title is {len(title)} chars (max {ENTRY_TITLE_MAX_CHARS})")
            if theme not in theme_keys:
                errors.add(slug, f"{rel}: theme {theme!r} is not declared on the {slug} page")
            if not body:
                errors.add(slug, f"{rel}: empty body")
            elif re.search(r"^#{1,6}\s", body, re.MULTILINE):
                errors.add(slug, f"{rel}: entry bodies are plain paragraphs/bullets, no headings")
            elif word_count(body) > ENTRY_BODY_MAX_WORDS:
                errors.add(
                    slug, f"{rel}: body is {word_count(body)} words (max {ENTRY_BODY_MAX_WORDS})"
                )
            evidence = as_list(meta.get("evidence"))
            if not evidence:
                errors.add(slug, f"{rel}: needs at least one evidence sid")
            elif len(evidence) > ENTRY_MAX_EVIDENCE:
                errors.add(slug, f"{rel}: {len(evidence)} evidence sids (max {ENTRY_MAX_EVIDENCE})")
            also = as_list(meta.get("also"))
            for other in also:
                if other == slug or other not in pages:
                    errors.add(slug, f"{rel}: `also` names unknown or own topic {other!r}")
            out[slug].append(
                {
                    "id": path.stem,
                    "topic": slug,
                    "date": entry_date,
                    "title": title,
                    "theme": theme,
                    "body": body,
                    "evidence": evidence,
                    "also": [o for o in also if o != slug and o in pages],
                }
            )
    for slug, entries in out.items():
        entries.sort(key=lambda e: (e["date"], e["id"]), reverse=True)
        used = {e["theme"] for e in entries}
        for t in pages[slug]["_themes"]:
            if t["key"] not in used:
                errors.add(slug, f"theme {t['key']!r} has no entries; remove it or file one")
    return out


def symmetrize(pages: dict[str, dict], errors: Errors) -> None:
    """Make obstacle.solutions <-> solution.obstacles consistent; reject dangling."""
    sol_of: dict[str, set[str]] = {s: set() for s in pages}
    obs_of: dict[str, set[str]] = {s: set() for s in pages}
    for slug, p in pages.items():
        for other in as_list(p.get("solutions")):
            if other not in pages or pages[other]["kind"] != "solution":
                errors.add(slug, f"links to unknown solution {other!r}")
                continue
            sol_of[slug].add(other)
            obs_of[other].add(slug)
        for other in as_list(p.get("obstacles")):
            if other not in pages or pages[other]["kind"] != "obstacle":
                errors.add(slug, f"links to unknown obstacle {other!r}")
                continue
            obs_of[slug].add(other)
            sol_of[other].add(slug)
    for slug, p in pages.items():
        p["_solutions"] = sorted(sol_of[slug])
        p["_obstacles"] = sorted(obs_of[slug])


def build_index(
    pages: dict[str, dict], entries: dict[str, list[dict]], errors: Errors
) -> dict:
    stories = json.loads(STORIES_INDEX.read_text()) if STORIES_INDEX.exists() else {}
    sl_index = json.loads(STORYLINES_INDEX.read_text()) if STORYLINES_INDEX.exists() else {}
    sl_labels = {
        str(s.get("slug")): s.get("label") or s.get("slug")
        for s in (sl_index.get("storylines") or [])
        if isinstance(s, dict) and s.get("slug")
    }

    def title_of(slug: str) -> str:
        return str(pages[slug].get("title") or slug)

    def resolve(slug: str, sids: list[str], where: str) -> list[dict]:
        out = []
        for sid in sids:
            rec = stories.get(sid)
            if rec is None:
                errors.add(slug, f"{where}: evidence sid {sid} not in stories index")
                continue
            out.append({"sid": sid, "title": rec.get("title") or sid})
        return out

    compiled: dict[str, list[dict]] = {}
    for slug, items in entries.items():
        compiled[slug] = [
            {
                "id": e["id"],
                "topic": slug,
                "date": e["date"],
                "title": e["title"],
                "theme": e["theme"],
                "html": md_to_html(e["body"]),
                "evidence": resolve(slug, e["evidence"], f"entries/{slug}/{e['id']}.md"),
                "also": [{"slug": o, "title": title_of(o)} for o in e["also"]],
            }
            for e in items
        ]

    cross: dict[str, list[dict]] = {slug: [] for slug in pages}
    for slug, items in compiled.items():
        for e in items:
            for o in e["also"]:
                cross[o["slug"]].append(
                    {
                        "id": e["id"],
                        "topic": slug,
                        "topic_title": title_of(slug),
                        "date": e["date"],
                        "title": e["title"],
                    }
                )

    nodes: dict[str, dict] = {}
    for slug, p in pages.items():
        own = compiled.get(slug, [])
        storylines = []
        for sl in as_list(p.get("related_storylines")):
            if sl not in sl_labels:
                errors.add(slug, f"related storyline {sl!r} not in index")
                continue
            storylines.append({"slug": sl, "label": sl_labels[sl]})

        # Node evidence = overview sources, then every entry's sources (newest
        # first), de-duplicated: the full ledger behind the page.
        evidence: list[dict] = []
        seen: set[str] = set()
        for ev in resolve(slug, as_list(p.get("evidence")), "page evidence") + [
            ev for e in own for ev in e["evidence"]
        ]:
            if ev["sid"] not in seen:
                seen.add(ev["sid"])
                evidence.append(ev)

        sections = [(h, b) for h, b in p.get("sections", []) if b]
        summary = next((b for h, b in sections if h == "TL;DR"), "")
        latest = own[0]["date"] if own else ""
        page_updated = as_date(p.get("updated"))
        themes = []
        for t in p["_themes"]:
            ids = [e["id"] for e in own if e["theme"] == t["key"]]
            themes.append(dict(t, count=len(ids)))
        cross_entries = sorted(
            cross.get(slug, []), key=lambda e: (e["date"], e["id"]), reverse=True
        )
        nodes[slug] = {
            "slug": slug,
            "kind": p["kind"],
            "title": title_of(slug),
            "area": p.get("area"),
            "status": p.get("status") or "active",
            "summary": summary,
            "sections": [{"heading": h, "html": md_to_html(b)} for h, b in sections],
            "themes": themes,
            "entries": own,
            "cross_entries": cross_entries,
            "entry_count": len(own),
            "latest_entry_date": latest or None,
            "solutions": [{"slug": s, "title": title_of(s)} for s in p["_solutions"]],
            "obstacles": [{"slug": s, "title": title_of(s)} for s in p["_obstacles"]],
            "related_storylines": storylines,
            "evidence": evidence,
            "updated": max(page_updated, latest),
        }

    areas = []
    for area, label in AREAS:
        slugs = sorted(
            s for s, n in nodes.items() if n["kind"] == "obstacle" and n["area"] == area
        )
        if slugs:
            areas.append({"area": area, "label": label, "obstacles": slugs})

    all_entries = [e for items in compiled.values() for e in items]
    all_entries.sort(key=lambda e: (e["date"], e["topic"], e["id"]), reverse=True)
    latest_entries = [
        {
            "id": e["id"],
            "topic": e["topic"],
            "topic_title": title_of(e["topic"]),
            "kind": pages[e["topic"]]["kind"],
            "date": e["date"],
            "title": e["title"],
        }
        for e in all_entries[:LATEST_ENTRIES]
    ]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "areas": areas,
        "latest_entries": latest_entries,
        "nodes": nodes,
    }


def render_catalog(index: dict) -> str:
    """The human catalog data/wiki/index.md (generated; do not hand-edit)."""
    nodes = index["nodes"]
    lines = [
        "# Agent Engineering Wiki — catalog",
        "",
        "Generated by `pipeline/build_wiki.py` — do not hand-edit. Topic pages live",
        "under `obstacles/` and `solutions/`; dated entries under `entries/<slug>/`.",
        "Schema: `config/wiki_schema.md`.",
        "",
        "## Obstacles by area",
    ]

    def topic_lines(n: dict, folder: str) -> list[str]:
        out = [
            f"- [{n['slug']}]({folder}/{n['slug']}.md) — {n['title']} "
            f"({n['entry_count']} entries, updated {n['updated'] or '—'})"
        ]
        if n["kind"] == "obstacle" and n["solutions"]:
            out.append("  → solutions: " + ", ".join(s["slug"] for s in n["solutions"]))
        for t in n["themes"]:
            out.append(f"  - theme `{t['key']}` — {t['title']} ({t['count']})")
        return out

    for area in index["areas"]:
        lines += ["", f"### {area['area']}"]
        for slug in area["obstacles"]:
            lines += topic_lines(nodes[slug], "obstacles")
    lines += ["", "## Solutions"]
    for slug in sorted(s for s, n in nodes.items() if n["kind"] == "solution"):
        lines += topic_lines(nodes[slug], "solutions")
    return "\n".join(lines) + "\n"


def compile_wiki() -> tuple[dict, Errors]:
    errors = Errors()
    pages = load_pages(errors)
    entries = load_entries(pages, errors)
    symmetrize(pages, errors)
    index = build_index(pages, entries, errors)
    return index, errors


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="validate without writing")
    ap.add_argument("--slug", default=None, help="report only errors for this topic")
    args = ap.parse_args()

    index, errors = compile_wiki()
    problems = errors.for_slug(args.slug)
    if problems:
        for msg in problems:
            print(f"WIKI_BUILD_FAIL {msg}", file=sys.stderr)
        sys.exit(1)
    if args.slug is not None:
        node = index["nodes"].get(args.slug)
        if node is None:
            print(f"WIKI_BUILD_FAIL unknown slug {args.slug!r}", file=sys.stderr)
            sys.exit(1)
        print(
            f"WIKI_BUILD_OK slug={args.slug} entries={node['entry_count']} "
            f"themes={len(node['themes'])} sources={len(node['evidence'])} (validated only)"
        )
        return
    if errors.items:  # pragma: no cover - for_slug(None) already covered these
        sys.exit(1)

    nodes = index["nodes"]
    n_obs = sum(1 for n in nodes.values() if n["kind"] == "obstacle")
    n_sol = sum(1 for n in nodes.values() if n["kind"] == "solution")
    n_entries = sum(n["entry_count"] for n in nodes.values())
    if not args.check:
        (WIKI_DIR / "index.json").write_text(
            json.dumps(index, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
        )
        (WIKI_DIR / "index.md").write_text(render_catalog(index), encoding="utf-8")
    print(
        f"WIKI_BUILD_OK nodes={len(nodes)} obstacles={n_obs} solutions={n_sol} "
        f"entries={n_entries} areas={len(index['areas'])}"
        + ("" if args.check else " -> data/wiki/index.json + index.md")
    )


if __name__ == "__main__":
    main()
