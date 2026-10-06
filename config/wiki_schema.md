# Agent Engineering Wiki — Schema

This is the **schema layer** of the LLM-maintained knowledge wiki (Karpathy's
"LLM wiki" pattern: raw sources → wiki → schema). It is the contract the
`wiki-curator` agent routine writes against and that `pipeline/build_wiki.py`
compiles deterministically into the served `data/wiki/index.json` (and the
generated catalog `data/wiki/index.md`).

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

- **Topic** = one markdown page under `data/wiki/{obstacles,solutions}/`, of
  `kind: obstacle | solution`. It holds a short, bounded **overview** and the
  topic's declared **themes**.
- **Entry** = one markdown file under `data/wiki/entries/<topic-slug>/`: a
  single dated, source-backed development (a launch, a paper, a field report),
  filed under exactly one theme of its topic.
- **Edge** = a cross-reference. An obstacle lists the `solutions:` that address
  it; a solution lists the `obstacles:` it addresses. Edges are **bidirectional
  by construction** — `build_wiki.py` reconciles both sides, so you only need to
  declare a link from one end (declare from the obstacle by convention).
- **Evidence** = real story `sid`s that ground an entry (and optionally the
  overview), plus optional `related_storylines` slugs on the topic. Never invent
  these — they must resolve in `data/stories/index.json` / `data/storylines/`.

Why two file kinds: a topic page answers "what is the state of this problem" in
about a minute; entries answer "what exactly happened, when, and where is the
source". New sources become **new entry files**. The overview is **rewritten**
when the synthesis changes — never appended to.

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

## Topic page format

`data/wiki/obstacles/<slug>.md` or `data/wiki/solutions/<slug>.md`:

```markdown
---
slug: agent-memory            # matches filename; [a-z0-9-], unique across the wiki
kind: obstacle                # obstacle | solution
title: "Agents forget across steps and sessions"
area: memory                  # obstacle pages only; must be a known area above
status: active                # active | stub  (stub = seeded, not yet synthesized)
solutions: [vector-kb, context-compaction]   # obstacle pages: edges to solutions
obstacles: []                 # solution pages: edges to obstacles
related_storylines: [deep-research]          # storyline slugs (optional)
evidence: []                  # optional: sids backing the overview itself
updated: 2026-10-06           # last edit to this page's overview/themes
themes:                       # 1-6 themes; every theme needs >= 1 entry
  - key: tiered-memory        # [a-z0-9-], unique within the page
    title: Tiered memory stores           # <= 80 chars
    summary: One sentence on the state of this sub-thread.   # <= 45 words
---

## TL;DR
One or two sentences: what this problem/solution is, in plain terms.

## State of the art
The current synthesis across all entries: the main approaches, the consensus,
and the open problem. Names patterns, not a list of every source — the entries
carry the specifics. Rewrite in place when the picture changes.

## Trade-offs            (solution pages only)
When this approach helps and where it breaks down.

## Why it matters for platform engineers
The platform-engineer lens — cost, reliability, ops, build-vs-buy — not generic
significance.
```

### Section rules (enforced)

| section | pages | max words |
|---|---|---|
| `TL;DR` (required) | all | 80 |
| `State of the art` | all | 350 |
| `Trade-offs` | solution | 200 |
| `Why it matters for platform engineers` | all | 150 |

No other `##` sections are allowed. In particular there is **no `What's new`
section**: "what's new" is derived from entry dates and rendered as the page's
*Latest updates* list.

## Entry format

`data/wiki/entries/<topic-slug>/<YYYY-MM-DD>-<name>.md`:

```markdown
---
title: "LangSmith Align Evals calibrates judges against human labels"   # <= 110 chars
date: 2026-07-30              # date filed; must equal the filename date
theme: trusting-the-judge     # a theme key declared on the topic page
evidence: [1923a6eccdfa6038]  # 1-6 real story sids
also: [agent-evaluation]      # optional: other topics this entry is listed on
---
What the source shows, with the specific mechanism or number, then what it
changes for builders. One or two short paragraphs or a few bullets, no
headings, <= 130 words. Inline markdown: **bold**, *italic*, `code`,
[links](/topic/<slug>).
```

- **One entry per development.** A launch post and its cloud-provider
  write-up of the same launch share one entry; two unrelated papers are two
  entries.
- **Title = the claim, not the source name.** "Encoder classifiers can match
  generative judges for guardrail verdicts", not "Do Encoders Suffice?".
- `<name>` is a short kebab-case handle; the file stem is the entry's anchor on
  the topic page (`/topic/<slug>#<stem>`), so never rename a published entry.
- `also:` lists the entry on other topics' pages under *From related topics*,
  linking back to this one. Prefer it over writing a duplicate entry.
- Entries are not edited after filing except to fix an error. A newer
  development gets its own entry; it may say what it supersedes.

## Themes

A theme is a sub-thread of the topic ("Cheaper judges", "Trusting the judge").
The topic page renders entries grouped by theme, newest first, with older
entries collapsed. Keep 2-5 themes on a mature page (max 6). When a theme grows
past ~15 entries or two themes blur together, re-split or merge them: change
the `themes:` list and update each affected entry's `theme:`.

## Operations (run by `wiki-curator`)

- **ingest** — for each genuinely new on-brand story: write a new entry under
  the right topic and theme (create a theme or topic only when the cluster is
  substantial). If the entry changes the synthesis, rewrite `State of the art`
  and the theme summary within their caps, and bump `updated`. Append one short
  line to `log.md`.
- **lint** — periodic health check: orphan topics (no edges), thin/`stub`
  pages, dangling edges, evidence that no longer resolves, overviews that no
  longer match their newest entries, overgrown or blurred themes, and
  contradictions across pages.
- **query** *(later phase)* — answers worth keeping get filed back as a new page.

## Invariants `build_wiki.py` enforces

1. `slug` matches `^[a-z0-9][a-z0-9-]{0,80}$` and equals the filename stem; unique.
2. `kind ∈ {obstacle, solution}` and matches its directory; obstacle `area` is
   one of the known areas.
3. Every edge resolves to an existing node of the opposite kind (no dangling
   links); edges are symmetrized regardless of which side declared them.
4. Every `evidence` sid (page and entry) resolves in `data/stories/index.json`;
   every `related_storylines` slug resolves in `data/storylines/index.json`.
5. Only the allowed sections appear, each within its word cap; `TL;DR` exists.
6. 1-6 themes per page, each with a unique key, a title, and a summary within
   caps, and each used by at least one entry.
7. Every entry lives under an existing topic's `entries/<slug>/` directory, is
   named `<YYYY-MM-DD>-<name>.md` with a matching `date`, has a title within
   caps, a declared `theme`, 1-6 resolving evidence sids, a body of at most 130
   words without headings, and `also` slugs that name other existing topics.

`build_wiki.py` reports every violation at once and exits non-zero with
`WIKI_BUILD_FAIL …`; `--slug <slug>` limits the report to one topic.

## Compiled shape (`data/wiki/index.json`)

`{generated_at, areas[], latest_entries[], nodes{slug: node}}`. Each node has
the overview `sections`, `themes` (with counts), `entries` (newest first, each
with resolved evidence), `cross_entries` (entries from other topics listing this
one in `also`), the symmetrized edges, the de-duplicated `evidence` ledger, and
`updated` = the later of the page's `updated` and its newest entry date.
