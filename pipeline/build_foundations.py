#!/usr/bin/env python3
"""Compile Agent Builder Foundations markdown into served index.json.

The ``foundations-curator`` routine writes markdown pages under
``data/foundations/concepts/``. This deterministic compiler validates the page
schema, resolves internal links, renders a small safe Markdown subset to HTML,
and writes ``data/foundations/index.json`` for the API and static renderer.

Run after editing Foundation pages:

    python pipeline/build_foundations.py [--check]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
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

REQUIRED_SECTIONS = {
    "builder consequence",
    "short answer",
    "mechanism",
    "evidence",
    "how to apply",
    "failure modes",
}

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
    blocks: list[str] = []
    para: list[str] = []
    items: list[str] = []

    def flush_para() -> None:
        if para:
            blocks.append("<p>" + md_inline(" ".join(para)) + "</p>")
            para.clear()

    def flush_list() -> None:
        if items:
            blocks.append("<ul>" + "".join(f"<li>{md_inline(i)}</li>" for i in items) + "</ul>")
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


def validate_page(page: dict, path: Path) -> None:
    slug = str(page.get("slug") or "")
    if not SLUG_RE.match(slug):
        raise FoundationsError(f"{path.name}: invalid slug {slug!r}")
    if slug != path.stem:
        raise FoundationsError(f"{path.name}: slug {slug!r} != filename stem")
    for field in ("title", "question", "summary", "status", "cluster", "updated"):
        if not str(page.get(field) or "").strip():
            raise FoundationsError(f"{slug}: missing {field}")
    if page.get("status") not in {"active", "draft"}:
        raise FoundationsError(f"{slug}: unknown status {page.get('status')!r}")
    if page.get("cluster") not in CLUSTER_LABELS:
        raise FoundationsError(f"{slug}: unknown cluster {page.get('cluster')!r}")
    headings = {str(h).strip().lower() for h, body in page["_sections_raw"] if body.strip()}
    missing = sorted(REQUIRED_SECTIONS - headings)
    if missing:
        raise FoundationsError(f"{slug}: missing required sections {', '.join(missing)}")
    if page.get("math_depth") == "intuition" and "math intuition" not in headings:
        raise FoundationsError(f"{slug}: math_depth intuition requires Math intuition section")
    evidence = page.get("evidence") or []
    if not isinstance(evidence, list) or not evidence:
        raise FoundationsError(f"{slug}: evidence must be a non-empty list")
    for ev in evidence:
        if not isinstance(ev, dict):
            raise FoundationsError(f"{slug}: evidence entries must be mappings")
        kind = str(ev.get("kind") or "")
        if kind not in EVIDENCE_TIERS:
            raise FoundationsError(f"{slug}: unknown evidence kind {kind!r}")
        if not str(ev.get("id") or "").strip():
            raise FoundationsError(f"{slug}: evidence missing id")
        if kind in EXTERNAL_EVIDENCE:
            if not str(ev.get("title") or "").strip() or not valid_url(str(ev.get("url") or "")):
                raise FoundationsError(f"{slug}: {kind} evidence requires title and http(s) url")
        elif kind == "editorial-inference":
            if not str(ev.get("title") or "").strip() or not str(ev.get("note") or "").strip():
                raise FoundationsError(f"{slug}: editorial inference requires title and note")
        elif kind == "story" and not str(ev.get("sid") or "").strip():
            raise FoundationsError(f"{slug}: story evidence requires sid")
        elif kind == "storyline" and not str(ev.get("slug") or "").strip():
            raise FoundationsError(f"{slug}: storyline evidence requires slug")


def load_pages() -> dict[str, dict]:
    concepts_dir = FOUNDATIONS_DIR / CONCEPTS_DIRNAME
    pages: dict[str, dict] = {}
    if not concepts_dir.is_dir():
        return pages
    for path in sorted(concepts_dir.glob("*.md")):
        page = parse_page(path)
        validate_page(page, path)
        slug = str(page["slug"])
        if slug in pages:
            raise FoundationsError(f"duplicate concept slug {slug!r}")
        pages[slug] = page
    return pages


def resolve_references(page: dict, stories: dict, storylines: dict, wiki: dict) -> tuple[list[dict], list[dict], list[dict]]:
    slug = str(page["slug"])
    sl_labels = {
        str(s.get("slug")): s.get("label") or s.get("slug")
        for s in (storylines.get("storylines") or [])
        if isinstance(s, dict) and s.get("slug")
    }
    wiki_nodes = wiki.get("nodes") or {}

    evidence: list[dict] = []
    for ev in page.get("evidence") or []:
        kind = str(ev.get("kind"))
        item = {
            "id": str(ev.get("id")),
            "kind": kind,
            "tier": EVIDENCE_TIERS[kind],
            "title": str(ev.get("title") or ""),
            "note": str(ev.get("note") or ""),
        }
        if ev.get("url"):
            item["url"] = str(ev["url"])
        if kind == "story":
            sid = str(ev.get("sid") or "")
            rec = stories.get(sid)
            if rec is None:
                raise FoundationsError(f"{slug}: story sid {sid} not in stories index")
            item["sid"] = sid
            item["title"] = str(rec.get("title") or ev.get("title") or sid)
        if kind == "storyline":
            sl = str(ev.get("slug") or "")
            if sl not in sl_labels:
                raise FoundationsError(f"{slug}: storyline {sl!r} not in index")
            item["slug"] = sl
            item["title"] = str(sl_labels[sl])
        evidence.append(item)

    topics = []
    for topic in as_list(page.get("related_topics")):
        if wiki_nodes and topic not in wiki_nodes:
            raise FoundationsError(f"{slug}: related topic {topic!r} not in wiki index")
        title = topic
        if isinstance(wiki_nodes.get(topic), dict):
            title = str(wiki_nodes[topic].get("title") or topic)
        topics.append({"slug": topic, "title": title})

    related_storylines = []
    for sl in as_list(page.get("related_storylines")):
        if sl not in sl_labels:
            raise FoundationsError(f"{slug}: related storyline {sl!r} not in index")
        related_storylines.append({"slug": sl, "label": str(sl_labels[sl])})

    return evidence, topics, related_storylines


def build_index() -> dict:
    pages = load_pages()
    stories = load_json(STORIES_INDEX, {})
    storylines = load_json(STORYLINES_INDEX, {"storylines": []})
    wiki = load_json(WIKI_INDEX, {"nodes": {}})

    concepts: dict[str, dict] = {}
    used_clusters: dict[str, list[str]] = {slug: [] for slug, _ in CLUSTERS}
    for slug, page in pages.items():
        evidence, topics, related_storylines = resolve_references(page, stories, storylines, wiki)
        sections = [
            {"heading": heading, "html": md_to_html(body)}
            for heading, body in page["_sections_raw"]
            if body.strip()
        ]
        cluster = str(page["cluster"])
        used_clusters.setdefault(cluster, []).append(slug)
        concepts[slug] = {
            "slug": slug,
            "title": str(page.get("title")),
            "question": str(page.get("question")),
            "summary": str(page.get("summary")),
            "status": str(page.get("status")),
            "cluster": cluster,
            "cluster_label": CLUSTER_LABELS[cluster],
            "updated": str(page.get("updated")),
            "audience": str(page.get("audience") or ""),
            "math_depth": str(page.get("math_depth") or ""),
            "sections": sections,
            "evidence": evidence,
            "related_topics": topics,
            "related_playbook_cards": as_list(page.get("related_playbook_cards")),
            "related_storylines": related_storylines,
            "covers_evidence": as_list(page.get("covers_evidence")),
        }

    clusters = [
        {"slug": slug, "label": label, "concepts": sorted(used_clusters.get(slug) or [])}
        for slug, label in CLUSTERS
        if used_clusters.get(slug)
    ]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "clusters": clusters,
        "concepts": concepts,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="validate without writing index.json")
    args = ap.parse_args()
    try:
        index = build_index()
        if not args.check:
            FOUNDATIONS_DIR.mkdir(parents=True, exist_ok=True)
            (FOUNDATIONS_DIR / "index.json").write_text(
                json.dumps(index, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        suffix = "" if args.check else " -> data/foundations/index.json"
        print(f"FOUNDATIONS_BUILD_OK concepts={len(index['concepts'])} clusters={len(index['clusters'])}{suffix}")
    except FoundationsError as e:
        print(f"FOUNDATIONS_BUILD_FAIL {e}", file=sys.stderr)
        raise SystemExit(1) from e


if __name__ == "__main__":
    main()
