# Product spec: the Agent Engineering Wiki (`/map`, `/topic/<slug>`)

## What it is
A reader-facing **knowledge graph** for AI platform engineers that maps the
**obstacles** to building and operating agents to the **solutions** the field
uses for each — every claim grounded in real source articles already in the
feed. It is the site's **semantic memory**: where the feed answers "what's new
about agent memory today", the wiki answers "what is the current state of the
agent-memory problem, and how do people solve it".

It is built with the **LLM-wiki** pattern (Karpathy): instead of re-retrieving
raw sources on every query, a Claude Code routine **incrementally synthesizes** a
persistent, cross-linked artifact that compounds as new sources arrive.

## Why (positioning fit)
"Memory" is pillar 3 of the product positioning (storylines, recaps, durable
permalinks). The wiki extends that moat from *episodic* memory (storylines: what
happened next) to *semantic* memory (the state of a problem). It is a shareable,
SEO-friendly growth artifact — the kind of page linked into HN/Slack/Reddit —
and it is on-brand: anti-hype, one shared deterministic structure, sources
visible.

## The two surfaces
- **`/map`** — the index. Obstacle **areas** (memory, reliability, tool use,
  cost, …) → obstacles → their linked solutions. The reader's entry point into
  the graph.
- **`/topic/<slug>`** — a single node (obstacle or solution): a synthesized
  TL;DR, state-of-the-art, what's-new, why-it-matters, cross-links to the other
  side of the graph, related storylines, and the evidence articles.

## How it's produced (the loop)
```text
data/stories/ (+ storylines)         raw sources (immutable; never edited)
        │  wiki-curator routine (LLM, ingest/lint — OUTSIDE GitHub Actions)
        ▼
data/wiki/{obstacles,solutions}/*.md  the wiki (markdown pages = source of truth)
        │  pipeline/build_wiki.py (deterministic compile + validate)
        ▼
data/wiki/index.json                  served artifact (single source for serving)
        │  render_static_pages.py            │ api/topics.js
        ▼                                    ▼
web/map.html + web/topic/*.html        /api/topics, /api/topics?slug=
```
- **Synthesis is offline + agent-driven** (LLM is disabled in the pipeline,
  `config/llm.yaml`), mirroring `storyline-editor`/`daily-summary`. Committing
  `data/wiki/` *is* publishing.
- **Serving is deterministic.** `build_wiki.py` validates the schema invariants
  (`config/wiki_schema.md`) — valid/unique slugs, known obstacle areas, no
  dangling edges, edges symmetrized, and **every evidence sid + storyline slug
  must resolve** — so a broken page fails the build before it can ship.

## Schema & taxonomy
The obstacle areas, page format, the three operations (ingest / lint / query),
and the validation invariants live in **`config/wiki_schema.md`** (the contract).
The maintenance routine is **`.agents/skills/wiki-curator/`**.

## Relationship to storylines
Separate graphs, cross-linked. Storylines cluster stories over *time*; the wiki
organizes knowledge over *topic*. Wiki pages **reference** storylines/stories as
evidence; they never re-cluster them. This keeps the shipping `/storylines`
subsystem untouched and gives a clean episodic/semantic split.

## Status
Seeded end-to-end with the **memory** cluster (`agent-memory` →
`vector-kb`, `context-compaction`) to prove build → render → serve. The next step
is scaling ingestion across the obstacle areas via the `wiki-curator` routine.
See ADR `docs/design-docs/decision-log.md` (2026-06-18).
