---
name: wiki-curator
description: Maintain the agent-engineering knowledge wiki for ai-sota-feed-bot — the reader-facing obstacle→solution graph at /map and /topic/<slug>. Files new stories as dated, themed entries under each topic, keeps each topic's short overview current, then compiles + validates. Use this when running the wiki ingest/lint routine.
---

You are the curator of an LLM-maintained **knowledge wiki** for AI **platform
engineers** (see `AGENTS.md` → Product Positioning). The wiki maps the
**obstacles** to building and operating agents (memory, reliability, tool use,
cost, …) to the **solutions** the field uses for each, and grounds every claim
in real source articles. It powers `/map` and `/topic/<slug>`.

Read the schema first: **`config/wiki_schema.md`** is the contract (topic page
format, entry format, themes, word caps, invariants). If this file and the
schema disagree, the schema wins.

Quality bar: "would the owner read this `/topic` page and understand the state
of this problem in 60 seconds, then find exactly what changed and its source in
one click." Anti-hype, platform-engineer lens, no invented sources.

Prose bar: every overview section, theme summary, and entry follows
`.agents/skills/writing-style/SKILL.md` — BLUF, one idea per paragraph,
specifics over generalities.

## Files

- **Topic pages** `data/wiki/{obstacles,solutions}/<slug>.md` — the short
  overview (TL;DR, State of the art, Trade-offs, Why it matters) plus the
  topic's `themes:`. Word-capped.
- **Entries** `data/wiki/entries/<slug>/<YYYY-MM-DD>-<name>.md` — one dated,
  source-backed development per file, filed under one theme.
- **Generated, never hand-edit:** `data/wiki/index.json` and
  `data/wiki/index.md` (both written by `pipeline/build_wiki.py`).
- **Log** `data/wiki/log.md` — append-only, one short line per run.
- **Read-only evidence:** `data/raw/`, `data/stories/`, `data/storylines/`.

## The routine (run in order)

### 1. Build the ingest bundle
```bash
python .agents/skills/wiki-curator/scripts/build_wiki_input.py
#   --days N     only stories from the last N days (default 7)
#   --slug S     add a `focus` dossier: topic S's themes, entries, and every source it cites
```
Writes `data/wiki/input/latest.json`: recent stories grouped by the obstacle
`area` their keywords suggest, each with `filed_in` (topics already citing it),
plus every topic with its themes and entry counts.

### 2. Ingest — file new sources as entries
Work only from stories with an empty `filed_in` that are on-brand and carry
real content (skip title-only aggregator redirects, version-bump changelogs,
and business news). For each genuinely new development:

1. Pick the topic it belongs to. Create a new topic page only for a
   substantial cluster that fits no existing topic.
2. Pick the theme. Add a theme to the page's `themes:` only when no existing
   theme fits and the topic has at most 5 themes.
3. Write one entry file `data/wiki/entries/<slug>/<today>-<name>.md`:
   - `title`: the claim, not the source name (<= 110 chars).
   - `date`: today (the filing date); it must match the filename.
   - `theme`, `evidence` (1-6 real sids; a launch post and its cloud-provider
     write-up share one entry), optional `also:` for other topics it informs.
   - Body <= 130 words: what the source shows, with the specific mechanism or
     number, then what it changes for builders. Mark vendor-reported numbers
     as vendor-reported.
4. If the entry changes the big picture, rewrite **State of the art** (and the
   theme's `summary`) so it still reads as one synthesis within 350 words —
   replace or compress older sentences; never append a running list. Bump the
   page's `updated`. Most entries do not need an overview change.
5. Declare new obstacle↔solution edges from the obstacle's `solutions:`.

Never invent sources: every sid must exist in `data/stories/index.json`, every
`related_storylines` slug in the storylines index.

### 3. Lint (every run, whole graph)
- **Overview drift** — a topic's State of the art no longer reflects its newest
  entries: rewrite it.
- **Theme health** — a theme over ~15 entries, or two themes that overlap: split
  or merge (edit `themes:` and the affected entries' `theme:`).
- **Misfiled entries** — an entry that belongs under another topic: move the
  file to that topic's directory (keep its filename) and fix `theme:`.
- **Graph** — orphan topics (no edges), `stub` pages, contradictions between
  pages.
`build_wiki.py --check` catches the mechanical problems (caps, unknown themes,
unresolved sids, dangling edges); the judgment calls are yours.

### 4. Log
Append one line to `data/wiki/log.md`, at most 60 words:
```text
YYYY-MM-DD  ingest+lint  <slugs touched>  — <N> entries filed (<entry titles, shortened>); overview rewrites: <slugs or none>; lint: <fixes or clean>.
```

### 5. Compile + validate
```bash
python pipeline/build_wiki.py --check            # or --check --slug <slug> while editing one topic
python pipeline/build_wiki.py                    # writes data/wiki/index.json + index.md
```
Exits non-zero with `WIKI_BUILD_FAIL …` listing every problem. Fix them all and
re-run until it prints `WIKI_BUILD_OK`.

### 6. Render (optional local check) + publish
```bash
python pipeline/render_static_pages.py   # regenerates web/map.html + web/topic/*.html
git add data/wiki/ web/map.html web/topic/ web/sitemap.xml
# Pin the agent identity so the commit signature can't inherit the machine's
# ambient git config (sets both author and committer).
git -c user.name="Claude" -c user.email="noreply@anthropic.com" \
  commit -m "wiki: <slugs touched>"
git push
```
Committing `data/wiki/` publishes. Keep this a data-only commit (see
`docs/status/git-hygiene.md`).

## Scaling to many topics (optional Workflow)
When a run reorganizes many topics at once (theme splits, overview rewrites),
fan out with the `Workflow` tool — one agent per topic, each touching only its
own page and `entries/<slug>/` directory, validating with
`build_wiki.py --check --slug <slug>`.

## Where it shows up
- `/map`: obstacle→solution map with a cross-wiki "Recently filed" list.
- `/topic/<slug>`: TL;DR, Latest updates, overview, then entries grouped by
  theme (newest first, older ones collapsed), each linking to its sources.
- API: `/api/topics`, `/api/topics?slug=<slug>`.
