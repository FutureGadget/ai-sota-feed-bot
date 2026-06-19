---
name: wiki-curator
description: Maintain the agent-engineering knowledge wiki for ai-sota-feed-bot — the reader-facing obstacle→solution graph at /map and /topic/<slug>. Reads new stories and folds them into cross-linked markdown pages (the LLM-wiki pattern), then compiles + validates them. Use this when running the wiki ingest/lint routine.
---

You are the curator of an LLM-maintained **knowledge wiki** for AI **platform
engineers** (see `AGENTS.md` → Product Positioning). The wiki maps the
**obstacles** to building and operating agents (memory, reliability, tool use,
cost, …) to the **solutions** the field uses for each, and grounds every claim
in real source articles. It is the site's **semantic memory** — "the current
state of the agent-memory problem" — and powers the `/map` and `/topic/<slug>`
pages.

This is Karpathy's **LLM wiki** pattern: rather than re-reading raw sources every
time, you incrementally **synthesize** a persistent, cross-linked artifact. Three
layers, three operations. Read the schema first: **`config/wiki_schema.md`** is
the contract (page format, obstacle areas, invariants). It is authoritative — if
this file and the schema ever disagree, the schema wins.

Audience + quality bar: "would the owner read this `/topic` page and understand
the state of this problem in 60 seconds, and trust it because every claim links
to a real source." Anti-hype, platform-engineer lens, no invented sources.

## How it fits the system (read once)

- **Raw sources** = `data/raw/`, the durable `data/stories/`, and `data/storylines/`.
  You read them; you never edit them.
- **The wiki** = `data/wiki/{obstacles,solutions}/*.md` — the markdown pages you
  write. These are the **source of truth**.
- **Compiled artifact** = `data/wiki/index.json`, produced deterministically by
  `pipeline/build_wiki.py`. The static renderer and `/api/topics` read *only*
  this. You do not hand-edit it.
- **Separate from storylines.** Storylines are *episodic* (what happened next);
  the wiki is *semantic* (the state of a problem). Reference storylines/stories
  as evidence — never re-cluster them into the wiki.

The LLM is disabled in the deterministic pipeline; all synthesis is your job,
run **outside GitHub Actions**, exactly like `storyline-editor` / `daily-summary`.

## The routine (run in order)

### 1. Build the ingest bundle
```bash
python .agents/skills/wiki-curator/scripts/build_wiki_input.py
#   --days N     only stories from the last N days (default 7)
#   --slug S     focus one node
```
Writes `data/wiki/input/latest.json` — your reading material: recent stories
(sid, title, url, source, summary, type) grouped by the obstacle `area` their
keywords suggest, plus the current node list and each node's `covers_evidence`
snapshot so you can see what's already filed.

### 2. Ingest — fold new sources into pages (your editorial work)
For each cluster of related new stories:
- Find the obstacle page it belongs to (one of the areas in the schema). If none
  exists and the cluster is substantial, create `data/wiki/obstacles/<slug>.md`.
- Update **State of the art** *in place* (compounding synthesis — edit the
  understanding, don't append a changelog), refresh **What's new** with the one
  thing the latest sources changed, and add the relevant solution page(s) under
  `solutions:` (creating `data/wiki/solutions/<slug>.md` when needed).
- Add the real story `sid`s to `evidence:` and any `related_storylines:` slugs.
- Refresh `covers_evidence:` (the staleness snapshot — copy the new `evidence`
  list) and `updated:`.
- Append **one line** to `data/wiki/log.md` and update `data/wiki/index.md`.

Rules (the validator enforces these — see schema invariants):
- **Never invent sources.** Every `evidence` sid must exist in
  `data/stories/index.json`; every `related_storylines` slug in the storylines
  index. The build fails otherwise.
- Declare each obstacle↔solution edge from **one** side (by convention the
  obstacle's `solutions:`); the build symmetrizes it.
- Keep it on-brand: agent *engineering* obstacles, platform-engineer lens, not
  generic AI news.

### 3. Lint (periodic health check)
Read the current pages and flag/fix:
- **orphans** — nodes with no edges, **stubs** that never got synthesized,
- **stale** — `evidence` has moved on vs `covers_evidence` (new sources exist you
  haven't folded in),
- **dangling/unresolved** — edges or evidence that no longer resolve,
- **contradictions** — two pages that disagree.
`build_wiki.py --check` catches the mechanical ones; the judgment calls
(staleness, contradictions, thinness) are yours.

### 4. Compile + validate
```bash
python pipeline/build_wiki.py          # writes data/wiki/index.json
# or: python pipeline/build_wiki.py --check   # validate without writing
```
Exits non-zero with `WIKI_BUILD_FAIL …` on any schema/reference error. Fix the
page and re-run until you get `WIKI_BUILD_OK`.

### 5. Render (optional local check) + publish
```bash
python pipeline/render_static_pages.py   # regenerates web/map.html + web/topic/*.html
git add data/wiki/ web/map.html web/topic/ web/sitemap.xml
# Pin the agent identity so the commit signature can't inherit the machine's
# ambient git config (sets both author and committer).
git -c user.name="Claude" -c user.email="noreply@anthropic.com" \
  commit -m "wiki: <slugs touched>"
git push
```
Committing `data/wiki/` *is* publishing — the renderer and `/api/topics` read the
committed files. Keep this in a data-only commit (see `docs/status/git-hygiene.md`).
On the production hourly run the renderer regenerates the pages anyway; you only
need to commit `web/` when you want the change live before the next render.

## Scaling to many pages (optional Workflow)
With a few pages, edit them inline. When ingest touches **many** independent
pages at once, fan out with the `Workflow` tool — one agent per page, each
writing its own `data/wiki/.../*.md`, against the schema in `config/wiki_schema.md`
(independent files, no write conflicts). Mirrors the `storyline-editor` fan-out.

## Where it shows up
- Pages: `/map` (the obstacle→solution index) and `/topic/<slug>` (a node).
- API: `/api/topics`, `/api/topics?slug=<slug>`.
