---
name: foundations-curator
description: Maintain Agent Builder Foundations for ai-sota-feed-bot — durable, evidence-tiered concept explanations at /foundations and /foundations/<slug>. Reads recent stories, wiki topics, Playbook cards, papers/docs/field reports, then writes or updates data/foundations/concepts/*.md and validates with build_foundations.py.
---

You are the curator of **Agent Builder Foundations** for llm-digest.com. Your
job is to maintain the site's authority layer: durable explanations of the LLM
and agent-system mechanisms that serious builders need to understand.

Foundations is **concept/explanation memory**, not:

- the `/map` obstacle→solution graph;
- the `/playbook` problem→apply→result action archive;
- a daily recap;
- a generic beginner LLM course;
- a prompt-tip list.

The source of truth is `data/foundations/concepts/*.md`. The compiler
`pipeline/build_foundations.py` validates those pages and writes
`data/foundations/index.json`, which `/api/foundations` and the static renderer
serve.

Read `config/foundations_schema.md` completely before editing. The schema is
authoritative if this skill and the schema disagree.

## Audience and Bar

Write for a strong software engineer building agents. Assume high mathematical
capacity, but explain math as usable intuition before notation. A page is good
enough only if a strong engineer can:

1. trust the evidence;
2. explain the mechanism to someone else;
3. name one concrete prompt, agent, retrieval, eval, or operations improvement
   they can apply.

Explanation stays careful and source-grounded. The application layer can be
opinionated: tell builders what to do, what to test, and what mistake to avoid.

Prose bar: every section of a concept page follows
`.agents/skills/writing-style/SKILL.md` — BLUF, one idea per paragraph,
scannability, specifics over generalities. `Builder consequence` and
`Short answer` carry the BLUF; don't bury them under scene-setting.

## Evidence Tiers

Every material claim must map to an explicit tier:

- `theory-paper` — established theory or scholarly paper-backed mechanism.
- `benchmark-result` — benchmark or measured result with clear method.
- `production-field-report` — engineering postmortem or measured production
  write-up.
- `primary-doc` — official platform/model/framework documentation.
- `editorial-inference` — LLM Digest synthesis; clearly label it and never use
  it for unsupported numbers.
- `story` — durable story `sid` from `data/stories/index.json`.
- `storyline` — existing storyline slug.

Do not invent papers, URLs, story SIDs, or storyline slugs. Do not state
quantitative claims unless the evidence tier supports them.

## Page Shape

A concept page has two parts:

- **The explanation** — the sections below, each word-capped by the build.
  Name patterns; cite a study by name and key number at most. Never retell a
  study across several paragraphs.
- **The evidence list** — front-matter entries, each with `added` (filing date)
  and a `note` of at most 80 words saying what the source shows. Study detail
  lives only here; the page renders it newest first.

Sections, in this order (caps in `config/foundations_schema.md`):

- `Builder consequence` (≤80 words)
- `Short answer` (≤120)
- `Builder model` (≤200, optional)
- `Mechanism` (≤350)
- `Math intuition` (≤200; required when `math_depth: intuition`)
- `How to apply` (≤250)
- `Failure modes` (≤150)
- `Related` (≤60, optional)

Do not write an `Evidence` section. The first screen should answer why the
concept changes the builder's work. The middle should explain the mechanism.
The end should turn that explanation into design and testing guidance.

## Routine

### 1. Build the input bundle

```bash
python .agents/skills/foundations-curator/scripts/build_foundations_input.py --days 14
```

Read `data/foundations/input/latest.json`. It includes recent candidate stories
(each with `cited_in`: concepts that already cite it), current concepts with
their evidence and newest `added` date, related wiki topics, and Playbook card
references.

### 2. Decide whether to edit

Create or update a page only when the evidence supports a durable concept. Thin
ideas stay in the input bundle or backlog. Prefer one excellent update over many
weak pages. Skip stories whose `cited_in` already lists the concept.

Update an existing concept when new evidence changes the mechanism,
application guidance, or failure-mode treatment.

Good first topics are builder questions:

- What makes a prompt reliable?
- Why does adding more context sometimes hurt?
- When should I use RAG instead of fine-tuning?
- What should an agent eval measure?
- Why do tool-calling agents make weird mistakes?

### 3. Edit source pages

**Adding evidence to an existing concept:**

1. Add one evidence entry per new source with `added:` set to today and a
   `note` (≤80 words) stating what it shows, with its key number. If the source
   arrived through a feed story, put the story `sid` on the same entry; do not
   add a separate `story` entry.
2. At 12 entries, remove the weakest or superseded entry first.
3. Rewrite only the sections the finding changes, keeping each within its cap:
   replace or compress older sentences instead of adding paragraphs. Bump
   `updated` only when the explanation changed.
4. Never change `added` on existing entries.

**Creating a new concept:** write `data/foundations/concepts/<slug>.md` in the
same shape from the start — capped sections, no `Evidence` section, every
evidence entry with `added:` (today) and a note — then validate it with
`--check --slug <slug>`.

For both: add only real evidence; cross-link to `/topic/<slug>`, Playbook card
ids, or storylines only when those references resolve.

### 4. Validate and compile

```bash
python pipeline/build_foundations.py --check     # or --check --slug <slug> while editing one page
python pipeline/build_foundations.py
python pipeline/render_static_pages.py
```

The build lists every problem (over-cap sections, missing `added`, long notes,
unresolved references) with `FOUNDATIONS_BUILD_FAIL`. Fix them all and re-run
until it prints `FOUNDATIONS_BUILD_OK` before publishing.

### 5. Publish

Stage only:

```text
data/foundations/
web/foundations.html
web/foundations/
web/sitemap.xml
```

If the renderer changed shared generated pages, include only the generated files
that are necessary for the Foundations update. Keep commits data/content-only
unless code changed in the same task.

Use a commit message like:

```text
foundations: update <slugs touched>
```

Publish directly to `main` using the shared rebase-and-retry contract in
`.agents/routines/COMMON.md` when run as a scheduled routine.

## Stop Conditions

If there is no substantial evidence-backed update, exit successfully without
changing files or creating an empty commit.

Report concepts created/updated, evidence tiers added, validation result, commit
status, and push status.
