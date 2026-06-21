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

## Surface design (redesigned 2026-06-21)
Both surfaces belong to the site's **AI operations instrument** family (shared
cool instrument-paper palette, blue `#2457d6` accent, condensed display titles,
monospace utility labels, hairline rules — no large rounded cards, no pill
navigation). They are rendered by `pipeline/render_static_pages.py` and share
`WIKI_PAGE_CSS`; **`web/map.html` and `web/topic/*.html` are generated — never
hand-edit them.** Each surface spends its one expressive idea differently:

- **`/map` — obstacle → solution adjacency map.** Areas group obstacles (the
  failure modes); each obstacle row places the **obstacle** on the left and the
  **solutions that address it** on the right, joined by a `→` edge. It reads as a
  scannable bipartite graph, not a grid of topic cards, and is *not* a canvas
  visualization (it stacks cleanly on mobile and is fully keyboard/screen-reader
  navigable). A monospace **area legend** at the top doubles as a jump nav and
  conveys the breadth of the problem space; a trailing **"Solutions in this map"**
  index keeps every solution node one click away (and crawlable). Entry points:
  `wiki_map_body` (pure, testable) + `render_map_page`.
- **`/topic/<slug>` — problem readout.** A monospace **status line** (kind ·
  area · status · N sources · updated), the **TL;DR pulled out as the lead**, then
  a high **graph-neighborhood cross-link panel** (`→ Solved by` for an obstacle /
  `→ Addresses` for a solution, plus *Tracked in storylines*) so the reader's next
  hop across the graph is immediate. The synthesized sections (State of the art,
  What's new, Trade-offs, Why it matters) render as a **left-rail dossier**
  (mono section label left, prose right) — semantic state foregrounded, **not a
  chronology**. Evidence sids close the page as a source ledger linking to durable
  `/story/<sid>` permalinks. Entry points: `wiki_topic_hero` + `render_topic_body`.

The cross-link `→` language is the shared device tying the two surfaces together:
`/map` is the whole graph; `/topic` is one node's neighborhood. Preserved by the
redesign: all cross-links, evidence sids → `/story`, related storylines →
`/storyline`, canonical URLs, sitemap entries, JSON-LD/breadcrumbs, deterministic
rendering, and the `/api/topics` contract (rendering-only change). Quality floor:
light/dark themes, visible keyboard focus, reduced motion, an empty-graph guard,
and a fix for the Oat `<article>` card box leaking into the adjacency rows.

No `wiki-curator` skill or `config/wiki_schema.md` change was needed: the renderer
adapts to whatever sections exist (TL;DR special-cased as the lead, the rest as
dossier entries), so the agent contract is unchanged. Regression coverage:
`tests/test_wiki_surface.py`.

## Status
Seeded end-to-end with the **memory** cluster (`agent-memory` →
`vector-kb`, `context-compaction`) to prove build → render → serve. The next step
is scaling ingestion across the obstacle areas via the `wiki-curator` routine.
See ADR `docs/design-docs/decision-log.md` (2026-06-18).
