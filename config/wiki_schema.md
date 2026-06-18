# Agent Engineering Wiki — Schema

This is the **schema layer** of the LLM-maintained knowledge wiki (Karpathy's
"LLM wiki" pattern: raw sources → wiki → schema). It is the contract the
`wiki-curator` agent routine writes against and that `pipeline/build_wiki.py`
compiles deterministically into the served `data/wiki/index.json`.

The wiki is a **reader-facing knowledge graph** for AI **platform engineers**
(see `AGENTS.md` → Product Positioning), organized as *obstacles* (problems you
hit building and operating agents) cross-linked to *solutions* (the approaches
the field uses to address them). It is **semantic** memory — "the state of the
agent-memory problem" — and is deliberately **separate from storylines**, which
are *episodic* memory ("what happened next with X"). Wiki pages **reference**
storylines and stories as evidence; they never re-cluster them.

> The LLM is disabled in the deterministic pipeline (`config/llm.yaml`). All
> synthesis is done by the `wiki-curator` Claude Code routine **outside** GitHub
> Actions, exactly like `storyline-editor` / `daily-summary`. The pipeline only
> compiles and serves what the routine committed.

## The graph

- **Node** = one markdown page under `data/wiki/`, of `kind: obstacle | solution`.
- **Edge** = a cross-reference. An obstacle lists the `solutions:` that address
  it; a solution lists the `obstacles:` it addresses. Edges are **bidirectional
  by construction** — `build_wiki.py` reconciles both sides, so you only need to
  declare a link from one end (declare from the obstacle by convention).
- **Evidence** = real story `sid`s (and optionally `related_storylines` slugs)
  that ground the node. Never invent these — they must resolve in
  `data/stories/index.json` / `data/storylines/`.

## Obstacle areas (the spine)

Every obstacle belongs to exactly one `area`. Seed taxonomy:

**Build-time** (getting an agent to work)
| area | the problem |
|---|---|
| `reliability` | agent makes mistakes / unreliable or unfaithful output |
| `memory` | forgetting, limited context, memory that doesn't scale |
| `planning` | weak multi-step decomposition; loops; getting stuck |
| `tool-use` | fragile tool calling, selection, schemas, interop |
| `grounding` | weak/stale knowledge, retrieval quality, attribution |
| `evaluation` | hard to measure quality; non-determinism; regressions |
| `multi-agent` | coordination, handoffs, communication overhead |

**Run-time** (keeping it working in production)
| area | the problem |
|---|---|
| `cost` | token-cost blowups, runaway loops |
| `latency` | latency / throughput / serving |
| `observability` | "why did it do that"; tracing; debugging |
| `security` | prompt injection, exfiltration, sandboxing, permissions |
| `prod-reliability` | error recovery, retries, idempotency, determinism |
| `scalability` | concurrency, durable state, horizontal scaling |
| `human-control` | approvals, interruption, steering, escalation |
| `drift` | model-upgrade regressions, behavior monitoring, maintenance |

Adding an area is a schema change: add the row here, then use it.

## Page format

Each page is YAML front matter + a markdown body with **known section
headings**. `build_wiki.py` parses both; unknown sections are ignored, missing
optional sections are fine.

```markdown
---
slug: agent-memory            # matches filename; [a-z0-9-], unique across the wiki
kind: obstacle                # obstacle | solution
title: "Agents forget across steps and sessions"
area: memory                  # obstacle pages only; must be a known area above
status: active                # active | stub  (stub = seeded, not yet synthesized)
solutions: [vector-kb, context-compaction]   # obstacle pages: edges to solutions
obstacles: []                 # solution pages: edges to obstacles
related_storylines: [deep-research]           # storyline slugs (optional)
evidence: [9022c498f1c24442, b3b803dc3d3ab1b8]  # real story sids
updated: 2026-06-18
# covers snapshot — lets the curator detect when a node has gone stale,
# mirroring the storyline narrative sidecar's covers_* fields.
covers_evidence: [9022c498f1c24442, b3b803dc3d3ab1b8]
---

## TL;DR
One or two sentences: what this problem/solution is, in plain terms.

## State of the art
The synthesized current understanding. Compounds over time — edit in place as
new sources arrive; do not append a changelog here (that is what `log.md` is).

## What's new
1-2 sentences on what the most recent ingested sources changed vs. before.
Omit on a brand-new stub.

## Why it matters for platform engineers
The platform-engineer lens — cost, reliability, ops, build-vs-buy — not generic
significance.

## Trade-offs            (solution pages)
When this approach helps and where it breaks down.
```

### Body sections by kind
- **Obstacle**: `TL;DR`, `State of the art`, `What's new`, `Why it matters for platform engineers`.
- **Solution**: `TL;DR`, `State of the art`, `What's new`, `Trade-offs`, `Why it matters for platform engineers`.

Only `TL;DR` is required to render; the rest render when present.

## Operations (run by `wiki-curator`)

- **ingest** — fold new `data/stories/` deltas into the right obstacle/solution
  pages: update `State of the art` in place, refresh `What's new`, add real
  `evidence` sids and `related_storylines`, refresh the `covers_*` snapshot and
  `updated`. Append one line to `log.md`.
- **lint** — periodic health check: orphan nodes (no edges), stale nodes
  (evidence moved on vs `covers_*`), thin/`stub` pages, dangling edges, evidence
  sids that no longer resolve, contradictions across pages.
- **query** *(later phase)* — answers worth keeping get filed back as a new page.

## Invariants `build_wiki.py` enforces

1. `slug` matches `^[a-z0-9][a-z0-9-]{0,80}$` and equals the filename stem; unique.
2. `kind ∈ {obstacle, solution}`; obstacle `area` is one of the known areas.
3. Every edge resolves to an existing node of the opposite kind (no dangling links).
4. Edges are symmetrized (obstacle↔solution) regardless of which side declared them.
5. Every `evidence` sid resolves in `data/stories/index.json`; every
   `related_storylines` slug resolves in `data/storylines/index.json`.
   Unresolved references fail the build (caught before publish, like
   `validate_narratives.py`).
