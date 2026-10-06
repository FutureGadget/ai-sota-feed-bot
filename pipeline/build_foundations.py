#!/usr/bin/env python3
"""Compile Agent Builder Foundations markdown into served index.json.

The ``foundations-curator`` routine writes markdown pages under
``data/foundations/concepts/``. This deterministic compiler validates the page
schema, resolves internal links, renders a small safe Markdown subset to HTML,
and writes ``data/foundations/index.json`` for the API and static renderer.

Each concept is a bounded explanation (word-capped sections) plus a dated
evidence list: new findings arrive as new evidence entries with an ``added``
date and a short note, and the explanation is rewritten rather than appended
to. Every violation is reported at once.

Run after editing Foundation pages:

    python pipeline/build_foundations.py [--check] [--slug SLUG]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime, timezone
from html import escape
from pathlib import Path
from urllib.parse import urlparse

import yaml

ROOT = Path(__file__).resolve().parents[1]
FOUNDATIONS_DIR = ROOT / "data" / "foundations"
CONCEPTS_DIRNAME = "concepts"
STORIES_INDEX = ROOT / "data" / "stories" / "index.json"
STORYLINES_INDEX = ROOT / "data" / "storylines" / "index.json"
WIKI_INDEX = ROOT / "data" / "wiki" / "index.json"

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,80}$")
FRONT_MATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)

CLUSTERS: list[tuple[str, str]] = [
    ("prompting", "Prompting and instruction following"),
    ("retrieval", "Retrieval and grounding"),
    ("tool-use", "Tool use and agents"),
    ("memory", "Memory and context"),
    ("evaluation", "Evals and reliability"),
    ("operations", "Cost, latency, and operations"),
    ("safety", "Safety and control"),
]
CLUSTER_LABELS = dict(CLUSTERS)

# Allowed sections in reading order, with word caps. The caps keep a concept
# readable in a few minutes; study-by-study detail belongs in evidence notes.
SECTION_LIMITS: dict[str, int] = {
    "builder consequence": 80,
    "short answer": 120,
    "builder model": 200,
    "mechanism": 350,
    "math intuition": 200,
    "how to apply": 250,
    "failure modes": 150,
    "related": 60,
}
REQUIRED_SECTIONS = {
    "builder consequence",
    "short answer",
    "mechanism",
    "how to apply",
    "failure modes",
}
MAX_EVIDENCE = 12
EVIDENCE_NOTE_MAX_WORDS = 80
SUMMARY_MAX_WORDS = 45
RECENT_EVIDENCE = 8
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

EVIDENCE_TIERS = {
    "theory-paper": "theory/paper-backed",
    "benchmark-result": "benchmark/result-backed",
    "production-field-report": "production field-report-backed",
    "primary-doc": "primary-doc-backed",
    "editorial-inference": "editorial inference",
    "story": "source story",
    "storyline": "storyline",
}
EXTERNAL_EVIDENCE = {
    "theory-paper",
    "benchmark-result",
    "production-field-report",
    "primary-doc",
}


class FoundationsError(Exception):
    """A schema or reference problem in Foundation source pages."""


def load_json(path: Path, fallback):
    try:
        if not path.exists():
            return fallback
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def as_list(value) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [value]
    return [str(v) for v in value]


def parse_sections(body: str) -> list[tuple[str, str]]:
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
    out = escape(text)
    out = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', out)
    out = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    return out


def md_to_html(text: str) -> str:
    """Paragraphs plus ``-``/``*`` bullet and ``1.`` numbered lists."""
    blocks: list[str] = []
    para: list[str] = []
    items: list[str] = []
    list_tag = "ul"

    def flush_para() -> None:
        if para:
            blocks.append("<p>" + md_inline(" ".join(para)) + "</p>")
            para.clear()

    def flush_list() -> None:
        if items:
            lis = "".join(f"<li>{md_inline(i)}</li>" for i in items)
            blocks.append(f"<{list_tag}>{lis}</{list_tag}>")
            items.clear()

    for line in text.splitlines():
        stripped = line.strip()
        bullet = re.match(r"^[-*]\s+(.*)$", stripped)
        numbered = re.match(r"^\d+[.)]\s+(.*)$", stripped)
        if bullet or numbered:
            tag = "ul" if bullet else "ol"
            if items and tag != list_tag:
                flush_list()
            flush_para()
            list_tag = tag
            items.append((bullet or numbered).group(1))
        elif not stripped:
            flush_para()
            flush_list()
        elif items and line.startswith((" ", "\t")):
            items[-1] += " " + stripped  # wrapped continuation of a list item
        else:
            flush_list()
            para.append(stripped)
    flush_para()
    flush_list()
    return "\n".join(blocks)


def parse_page(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    m = FRONT_MATTER_RE.match(text)
    if not m:
        raise FoundationsError(f"{path.name}: missing YAML front matter")
    try:
        meta = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as e:
        raise FoundationsError(f"{path.name}: bad front matter: {e}") from e
    if not isinstance(meta, dict):
        raise FoundationsError(f"{path.name}: front matter is not a mapping")
    meta["_file"] = path.name
    meta["_sections_raw"] = parse_sections(m.group(2))
    return meta


def valid_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def word_count(text: str) -> int:
    plain = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text or "")
    return len(plain.split())


def as_date(value) -> str:
    if isinstance(value, (date, datetime)):
        return value.isoformat()[:10]
    return str(value or "").strip()


def validate_page(page: dict, path: Path, errors: list[tuple[str, str]]) -> None:
    """Append (slug, message) for every schema problem on one page."""
    slug = str(page.get("slug") or path.stem)

    def err(msg: str) -> None:
        errors.append((slug, f"{slug}: {msg}"))

    if not SLUG_RE.match(str(page.get("slug") or "")):
        err(f"{path.name}: invalid slug {page.get('slug')!r}")
    elif page.get("slug") != path.stem:
        err(f"{path.name}: slug {page.get('slug')!r} != filename stem")
    for field in ("title", "question", "summary", "status", "cluster", "updated"):
        if not str(page.get(field) or "").strip():
            err(f"missing {field}")
    if word_count(str(page.get("summary") or "")) > SUMMARY_MAX_WORDS:
        err(f"summary is {word_count(str(page.get('summary')))} words (max {SUMMARY_MAX_WORDS})")
    if page.get("status") not in {"active", "draft"}:
        err(f"unknown status {page.get('status')!r}")
    if page.get("cluster") not in CLUSTER_LABELS:
        err(f"unknown cluster {page.get('cluster')!r}")

    seen: set[str] = set()
    for heading, body in page["_sections_raw"]:
        key = str(heading).strip().lower()
        if key not in SECTION_LIMITS:
            hint = " (study details go in evidence notes)" if key == "evidence" else ""
            err(f"section '## {heading}' is not allowed{hint}; allowed: {', '.join(h.capitalize() for h in SECTION_LIMITS)}")
            continue
        if key in seen:
            err(f"duplicate section '## {heading}'")
        seen.add(key)
        n = word_count(body)
        if n > SECTION_LIMITS[key]:
            err(f"'## {heading}' is {n} words (max {SECTION_LIMITS[key]}); rewrite it tighter")
    headings = {str(h).strip().lower() for h, body in page["_sections_raw"] if body.strip()}
    missing = sorted(REQUIRED_SECTIONS - headings)
    if missing:
        err(f"missing required sections {', '.join(missing)}")
    if page.get("math_depth") == "intuition" and "math intuition" not in headings:
        err("math_depth intuition requires Math intuition section")

    evidence = page.get("evidence") or []
    if not isinstance(evidence, list) or not evidence:
        err("evidence must be a non-empty list")
        return
    if len(evidence) > MAX_EVIDENCE:
        err(f"{len(evidence)} evidence entries (max {MAX_EVIDENCE}); retire the weakest or superseded ones")
    ids: set[str] = set()
    for ev in evidence:
        if not isinstance(ev, dict):
            err("evidence entries must be mappings")
            continue
        kind = str(ev.get("kind") or "")
        eid = str(ev.get("id") or "").strip()
        label = eid or "<no id>"
        if kind not in EVIDENCE_TIERS:
            err(f"evidence {label}: unknown kind {kind!r}")
            continue
        if not eid:
            err("evidence missing id")
        elif eid in ids:
            err(f"duplicate evidence id {eid!r}")
        ids.add(eid)
        added = as_date(ev.get("added"))
        if not DATE_RE.match(added):
            err(f"evidence {label}: `added:` must be YYYY-MM-DD (the date it was filed)")
        note = str(ev.get("note") or "")
        if word_count(note) > EVIDENCE_NOTE_MAX_WORDS:
            err(f"evidence {label}: note is {word_count(note)} words (max {EVIDENCE_NOTE_MAX_WORDS})")
        if kind in EXTERNAL_EVIDENCE:
            if not str(ev.get("title") or "").strip() or not valid_url(str(ev.get("url") or "")):
                err(f"evidence {label}: {kind} evidence requires title and http(s) url")
            if not note.strip():
                err(f"evidence {label}: needs a note saying what it shows")
        elif kind == "editorial-inference":
            if not str(ev.get("title") or "").strip() or not note.strip():
                err(f"evidence {label}: editorial inference requires title and note")
        elif kind == "story" and not str(ev.get("sid") or "").strip():
            err(f"evidence {label}: story evidence requires sid")
        elif kind == "storyline" and not str(ev.get("slug") or "").strip():
            err(f"evidence {label}: storyline evidence requires slug")


def load_pages(errors: list[tuple[str, str]]) -> dict[str, dict]:
    concepts_dir = FOUNDATIONS_DIR / CONCEPTS_DIRNAME
    pages: dict[str, dict] = {}
    if not concepts_dir.is_dir():
        return pages
    for path in sorted(concepts_dir.glob("*.md")):
        try:
            page = parse_page(path)
        except FoundationsError as e:
            errors.append((path.stem, str(e)))
            continue
        validate_page(page, path, errors)
        slug = str(page.get("slug") or path.stem)
        if slug in pages:
            errors.append((slug, f"duplicate concept slug {slug!r}"))
            continue
        pages[slug] = page
    return pages


def resolve_references(
    page: dict, stories: dict, storylines: dict, wiki: dict, errors: list[tuple[str, str]]
) -> tuple[list[dict], list[dict], list[dict]]:
    slug = str(page["slug"])
    sl_labels = {
        str(s.get("slug")): s.get("label") or s.get("slug")
        for s in (storylines.get("storylines") or [])
        if isinstance(s, dict) and s.get("slug")
    }
    wiki_nodes = wiki.get("nodes") or {}

    def err(msg: str) -> None:
        errors.append((slug, f"{slug}: {msg}"))

    evidence: list[dict] = []
    for ev in page.get("evidence") or []:
        if not isinstance(ev, dict) or str(ev.get("kind")) not in EVIDENCE_TIERS:
            continue
        kind = str(ev.get("kind"))
        item = {
            "id": str(ev.get("id")),
            "kind": kind,
            "tier": EVIDENCE_TIERS[kind],
            "title": str(ev.get("title") or ""),
            "note": " ".join(str(ev.get("note") or "").split()),
            "added": as_date(ev.get("added")),
        }
        if ev.get("url"):
            item["url"] = str(ev["url"])
        sid = str(ev.get("sid") or "")
        if sid:
            # External evidence may carry the feed story it arrived through, so
            # one entry links both the primary source and its /story permalink.
            rec = stories.get(sid)
            if rec is None:
                err(f"story sid {sid} not in stories index")
            else:
                item["sid"] = sid
                if kind == "story":
                    item["title"] = str(rec.get("title") or ev.get("title") or sid)
        if kind == "storyline":
            sl = str(ev.get("slug") or "")
            if sl not in sl_labels:
                err(f"storyline {sl!r} not in index")
            else:
                item["slug"] = sl
                item["title"] = str(sl_labels[sl])
        evidence.append(item)
    # Newest evidence first; ties keep the page's own order.
    evidence = [
        ev for _, ev in sorted(enumerate(evidence), key=lambda t: (t[1]["added"], -t[0]), reverse=True)
    ]

    topics = []
    for topic in as_list(page.get("related_topics")):
        if wiki_nodes and topic not in wiki_nodes:
            err(f"related topic {topic!r} not in wiki index")
            continue
        title = topic
        if isinstance(wiki_nodes.get(topic), dict):
            title = str(wiki_nodes[topic].get("title") or topic)
        topics.append({"slug": topic, "title": title})

    related_storylines = []
    for sl in as_list(page.get("related_storylines")):
        if sl not in sl_labels:
            err(f"related storyline {sl!r} not in index")
            continue
        related_storylines.append({"slug": sl, "label": str(sl_labels[sl])})

    return evidence, topics, related_storylines


def compile_foundations() -> tuple[dict, list[tuple[str, str]]]:
    """Return (index, errors); errors are (slug, message) pairs."""
    errors: list[tuple[str, str]] = []
    pages = load_pages(errors)
    stories = load_json(STORIES_INDEX, {})
    storylines = load_json(STORYLINES_INDEX, {"storylines": []})
    wiki = load_json(WIKI_INDEX, {"nodes": {}})

    concepts: dict[str, dict] = {}
    used_clusters: dict[str, list[str]] = {slug: [] for slug, _ in CLUSTERS}
    for slug, page in pages.items():
        evidence, topics, related_storylines = resolve_references(page, stories, storylines, wiki, errors)
        sections = [
            {"heading": heading, "html": md_to_html(body)}
            for heading, body in page["_sections_raw"]
            if body.strip()
        ]
        cluster = str(page.get("cluster"))
        if cluster not in CLUSTER_LABELS:
            continue
        used_clusters.setdefault(cluster, []).append(slug)
        latest = max((ev["added"] for ev in evidence if DATE_RE.match(ev["added"])), default="")
        concepts[slug] = {
            "slug": slug,
            "title": str(page.get("title")),
            "question": str(page.get("question")),
            "summary": str(page.get("summary")),
            "status": str(page.get("status")),
            "cluster": cluster,
            "cluster_label": CLUSTER_LABELS[cluster],
            "updated": max(as_date(page.get("updated")), latest),
            "latest_evidence_added": latest or None,
            "audience": str(page.get("audience") or ""),
            "math_depth": str(page.get("math_depth") or ""),
            "sections": sections,
            "evidence": evidence,
            "related_topics": topics,
            "related_playbook_cards": as_list(page.get("related_playbook_cards")),
            "related_storylines": related_storylines,
        }

    clusters = [
        {"slug": slug, "label": label, "concepts": sorted(used_clusters.get(slug) or [])}
        for slug, label in CLUSTERS
        if used_clusters.get(slug)
    ]
    recent = sorted(
        (
            {
                "concept": slug,
                "concept_title": c["title"],
                "id": ev["id"],
                "title": ev["title"],
                "tier": ev["tier"],
                "kind": ev["kind"],
                "added": ev["added"],
            }
            for slug, c in concepts.items()
            for ev in c["evidence"]
            if ev["kind"] not in ("story", "storyline", "editorial-inference") and ev["added"]
        ),
        key=lambda r: (r["added"], r["concept"], r["id"]),
        reverse=True,
    )[:RECENT_EVIDENCE]
    index = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "clusters": clusters,
        "recent_evidence": recent,
        "concepts": concepts,
    }
    return index, errors


def build_index() -> dict:
    index, errors = compile_foundations()
    if errors:
        raise FoundationsError("; ".join(msg for _, msg in errors))
    return index


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="validate without writing index.json")
    ap.add_argument("--slug", default=None, help="report only errors for this concept")
    args = ap.parse_args()
    index, errors = compile_foundations()
    problems = [msg for slug, msg in errors if args.slug is None or slug == args.slug]
    if problems:
        for msg in problems:
            print(f"FOUNDATIONS_BUILD_FAIL {msg}", file=sys.stderr)
        raise SystemExit(1)
    if args.slug is not None:
        concept = index["concepts"].get(args.slug)
        if concept is None:
            print(f"FOUNDATIONS_BUILD_FAIL unknown slug {args.slug!r}", file=sys.stderr)
            raise SystemExit(1)
        print(f"FOUNDATIONS_BUILD_OK slug={args.slug} evidence={len(concept['evidence'])} (validated only)")
        return
    if not args.check:
        FOUNDATIONS_DIR.mkdir(parents=True, exist_ok=True)
        (FOUNDATIONS_DIR / "index.json").write_text(
            json.dumps(index, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    suffix = "" if args.check else " -> data/foundations/index.json"
    print(f"FOUNDATIONS_BUILD_OK concepts={len(index['concepts'])} clusters={len(index['clusters'])}{suffix}")


if __name__ == "__main__":
    main()
