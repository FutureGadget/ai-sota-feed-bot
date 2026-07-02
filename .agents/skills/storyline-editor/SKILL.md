---
name: storyline-editor
description: Write editorial narratives for ai-sota-feed-bot storylines — the cross-day AI threads on /storylines. Reads the mechanically-built timeline for each developing story, writes a TL;DR arc, a "what's new" update, a platform-engineer "why it matters", and per-item editor notes to a durable sidecar the pipeline overlays. Use this when running the storyline narration routine.
---

You are the storylines editor of an AI news intelligence product. The site
threads stories *mechanically* — it knows that six articles across five days
are all about "Claude Fable", but it can't tell the reader **what actually
happened**: launched → hands-on impressions → controversial terms → access
changes → suspension. That narrative arc is your job. You turn a clustered
timeline into a story a reader can follow.

The `/storyline/<slug>` page renders an **Evidence trace** when you provide it. Its
reader hierarchy is: current state → latest change → builder action → optional
earlier context → evidence trace/source timeline → open questions. A spine of named **beats** commonly
looks like LAUNCH → FRICTION → THE TURN → NOW, but use labels that accurately
describe the thread. Every provenance claim must be true. Do not invent
verification/agent labels the system doesn't actually produce.

Audience: **AI platform engineers** (see `AGENTS.md` → Product Positioning).
Write for the person who skimmed the headline last Tuesday and wants the
through-line, not hype. The quality bar is "would the owner read this and feel
caught up in 20 seconds".

Prose bar: every field you write below (`tldr`, `whats_new`, `why_it_matters`,
`beats[].headline`/`summary`, `open_questions`, `take_for_builders`,
`day_captions`) follows `.agents/skills/writing-style/SKILL.md` — BLUF, one
idea per paragraph, scannability, specifics over generalities.

All scripts live next to this file in `scripts/` and locate the repo root
automatically, so they run from anywhere. This routine mirrors `daily-summary`
and `weekly-summary`, but the unit is a **storyline** (a slug like
`claude-fable`), not a date.

## Why a sidecar (read this once)

`pipeline/build_storylines.py` rebuilds `data/storylines/<slug>.json` and
`index.json` **every hour** from the durable story store. If you wrote your
narrative into those files it would be **clobbered** on the next pipeline run.

So you write to a separate, durable file — the **narrative sidecar**
`data/storylines/narratives/<slug>.json`. The pipeline deterministically
**overlays** a fresh sidecar back onto the served `<slug>.json` (and a TL;DR
teaser onto the index entry) on every run. The sidecar is the source of truth;
the overlay is a plain JSON merge with no LLM in the loop. Each sidecar carries
a membership/timestamp snapshot (`covers_*`) so the overlay can flag it stale
when the thread moves on — that's also how this routine knows what to refresh.

## The routine (run in order)

### 1. Build the input bundle
```bash
python .agents/skills/storyline-editor/scripts/build_storyline_input.py
# By default: only storylines that NEED a narrative (none yet, or gone stale).
#   --all            include every active storyline (still flags which need work)
#   --slug <slug>    target a single storyline
#   --refresh-all    treat every storyline as needing a (re)write
```
This writes `data/storylines/input/latest.json` — **your reading material**.
Each entry in `storylines[]` has: `slug`, `label`, the counts
(`item_count`/`source_count`/`day_count`), `first_seen`/`last_updated`,
`needs_narrative` + `reason`, and a `timeline[]` of `{date, items[]}` where each
item carries `sid`, `title`, `url`, `source`, `summary_1line`, `published`.

If `needs_narrative_count` is 0, **stop** — every storyline is current. Report
that and exit.

### 2. Write a narrative sidecar per storyline (your editorial work)
For each storyline with `needs_narrative: true`, read its `timeline[]` in order
and write `data/storylines/narratives/<slug>.json`:
```json
{
  "slug": "claude-fable",
  "generated_at": "<ISO-8601 now>",
  "covers_last_updated": "<copy last_updated from the bundle entry, verbatim>",
  "covers_member_sids": ["<every sid in this storyline's timeline>"],
  "tldr": "2 concise sentences of background: establish the starting point, the major turn, and where the prior context ended. Do not repeat the latest change or builder takeaway.",
  "whats_new": "1 compact sentence led by the newest consequential fact. This is the primary index-card and detail-page update.",
  "why_it_matters": "One line through the AI-platform-engineer lens: what an engineer should take from this.",
  "status": {
    "state": "Suspended · temporary",
    "tone": "alert",
    "changed": "2026-06-13",
    "reenable": "re-enable date unknown",
    "detail": "One sentence on the current framing of the whole thread.",
    "track": [
      { "label": "available", "detail": "Jun 10–13", "tone": "launch", "weight": 62 },
      { "label": "suspended", "detail": "Jun 13 → now", "tone": "now", "weight": 38 }
    ]
  },
  "provenance": {
    "<sid>": { "surfaced_by": "scout", "verified": 3, "status_update": true }
  },
  "beats": [
    {
      "kicker": "LAUNCH",
      "tone": "launch",
      "headline": "Fable 5 + Mythos 5 ship — \"made safe for general use\"",
      "summary": "Optional one line on what this phase was.",
      "sids": ["<sid>", "<sid>"]
    },
    { "kicker": "THE TURN", "tone": "turn", "headline": "Export-control directive suspends access", "sids": ["<sid>"] }
  ],
  "open_questions": [
    "Is \"temporary\" confirmed — does any re-enable date appear?",
    "Does the directive extend to other frontier labs?"
  ],
  "take_for_builders": "One actionable line: what a platform or agent engineer should check, change, defer, or monitor now.",
  "day_captions": {
    "<sid>": "one line on what THIS item added to the story (not a re-summary of the article)"
  }
}
```

**The arc fields (optional but recommended — they drive the Evidence trace)**
- `status` is the live-status banner. `state` is a short label ("Shipping",
  "Suspended · temporary", "Resolved"); `tone` ∈ `launch | rising | turn | now |
  resolved | alert | neutral` colors the banner; `changed` is the ISO date the
  state last moved; `reenable`/`detail` are optional clarifiers. Use it for a
  thread that has a *current state*; omit it for a thread that's just developing.
  When the tracked event has genuinely ended, set `state: "Resolved"` and
  `tone: "resolved"` so the index can stop presenting it as active.
  `status.track` (optional) is the **"State over time"** trace — an ordered list
  of `{label, detail, tone, weight}` phases (weights are relative widths); use
  it for threads where a state visibly flips over time (available → suspended).
- `provenance` (optional) keys evidence signals by item `sid`:
  `surfaced_by: "scout"` (🔍 dashed pill, for an item the scout actually
  surfaced), `verified: <N sources>` (✓ pill + a per-beat "verified across N
  sources" line — only set it when N independent sources genuinely corroborate
  the beat), `status_update: true` (↻ pill, for the item that moved the status).
  These drive the collapsed reader-facing "How this thread was built" evidence
  block. Set them **truthfully**. `verified` means N genuinely independent
  sources corroborate the claim, not N syndicated copies or N items in the
  cluster.
- `beats` are the spine — an **ordered** arc, each beat grouping the member
  `sids` that moved the story in that phase. `headline` is required; `kicker` is
  the short phase label (LAUNCH / FRICTION / THE TURN / NOW — your call); `tone`
  colors the node (use `turn` for the pivot, it gets the emphasized red node).
  The renderer derives each beat's date range from its items and sweeps any
  uncovered member into a neutral chronological fallback so no source vanishes,
  but that fallback means the narrative is incomplete. Place every displayed
  timeline `sid` in exactly one beat; the validator rejects missing, duplicated,
  or unknown beat sids.
- `open_questions` is "what to watch" — up to 6 genuinely open questions an
  engineer would track, not rhetorical filler. Phrase each so a future source
  can clearly answer it; do not add internal assignees or workflow statuses to
  this reader-facing field.
- `take_for_builders` renders as the **Take for builders** line; if omitted the
  page falls back to `why_it_matters`.

**Editorial guidance**
- `covers_last_updated` and `covers_member_sids` are the **staleness snapshot** —
  copy `last_updated` verbatim and include the `sid` of every item in the
  timeline. Getting these right is what keeps the overlay from re-flagging your
  work stale on the next run.
- `whats_new` is the first editorial text readers see on both the index and
  detail page. Write one compact sentence, ideally under 240 characters. Lead
  with the newest consequential fact and answer "what happened next?" Do not
  start by recapping the launch or add scene-setting.
- `tldr` is subdued, collapsible background — not a second lead story. Use two
  concise chronological sentences, ideally under 420 characters total:
  establish the starting point and major turn, then stop before the fact already
  covered by `whats_new`. Avoid repeating `take_for_builders`.
- `why_it_matters` is the platform-engineer lens — pricing, availability,
  agent/tooling impact, reliability — not generic "this is significant".
- `take_for_builders` should be operational: check a deployment term, keep a
  fallback, rerun an eval, pin a version, change a guardrail, or explicitly
  wait for missing evidence. Avoid generic "teams should monitor this."
- Reward failure and degradation evidence. If the story includes an outage,
  rollback, suspension, cost regression, broken compatibility, or failed eval,
  give it a beat and state the concrete failure mode plus recovery status.
- `day_captions` are keyed by `sid` and describe what each item *added* to the
  arc ("first independent benchmark", "Anthropic's official response"), not a
  restatement of the headline. Use quantitative impact language only when the
  cited item actually supports the number or complexity claim.
- **Never invent links or items.** Only use `sid`s present in the bundle's
  timeline — the validator rejects unknown sids.
- Before saving, compare the union of every `beats[].sids` with every displayed
  `timeline[].items[].sid`. They must match exactly. When an early article is
  added during reclustering, extend the relevant early beat instead of allowing
  it to appear after the current-state beat as generic context.

### Scaling to many storylines (optional Workflow)
With a handful of storylines, just write each sidecar inline (above). When the
bundle has **many** storylines to (re)write, fan out with the **Workflow** tool
so each storyline is narrated by its own agent against a strict schema —
schema-validated structured output is more deterministic than free-form
subagents, and the items are independent (each writes its own sidecar file, so
no write conflicts). Pattern:

```js
export const meta = {
  name: 'storyline-narratives',
  description: 'Write a narrative sidecar for each storyline needing one',
  phases: [{ title: 'Narrate' }],
}
const TONE = { type: 'string', enum: ['launch','rising','turn','now','resolved','alert','neutral'] }
const NARR = {
  type: 'object',
  required: ['slug', 'generated_at', 'tldr', 'covers_last_updated', 'covers_member_sids'],
  properties: {
    slug: { type: 'string' }, tldr: { type: 'string' },
    generated_at: { type: 'string' },
    whats_new: { type: 'string' }, why_it_matters: { type: 'string' },
    take_for_builders: { type: 'string' },
    covers_last_updated: { type: 'string' },
    covers_member_sids: { type: 'array', minItems: 1, items: { type: 'string' } },
    status: { type: 'object', required: ['state', 'tone'], properties: {
      state: { type: 'string' }, tone: TONE, changed: { type: 'string' },
      reenable: { type: 'string' }, detail: { type: 'string' },
      track: { type: 'array', items: { type: 'object', properties: {
        label: { type: 'string' }, detail: { type: 'string' },
        tone: TONE, weight: { type: 'number' } } } } } },
    provenance: { type: 'object', additionalProperties: { type: 'object', properties: {
      surfaced_by: { type: 'string', enum: ['scout'] },
      verified: { type: 'integer', minimum: 2 },
      status_update: { type: 'boolean' } } } },
    beats: { type: 'array', items: { type: 'object', required: ['headline'],
      properties: { kicker: { type: 'string' }, tone: TONE,
        headline: { type: 'string' }, summary: { type: 'string' },
        sids: { type: 'array', items: { type: 'string' } } } } },
    open_questions: { type: 'array', items: { type: 'string' } },
    day_captions: { type: 'object', additionalProperties: { type: 'string' } },
  },
}
const rows = args.storylines.filter(s => s.needs_narrative)
await parallel(rows.map(s => () =>
  agent(
    `You are the storylines editor (audience: AI platform engineers). Write the ` +
    `narrative for this storyline and SAVE it with the Write tool to ` +
    `data/storylines/narratives/${s.slug}.json (set generated_at to an ISO ` +
    `timestamp). Copy covers_last_updated and covers_member_sids verbatim from ` +
    `the input. Timeline + fields:\n` + JSON.stringify(s),
    { label: `narrate:${s.slug}`, phase: 'Narrate', schema: NARR },
  )))
return { wrote: rows.length }
```
Pass the bundle as `args`: read `data/storylines/input/latest.json` and call
`Workflow` with `{ args: <that JSON> }`. Running a Workflow requires the
`ultracode` opt-in — the cloud routine has it; locally, prefer the inline path.

### 3. Validate
```bash
python .agents/skills/storyline-editor/scripts/validate_narratives.py --check
```
Validates every sidecar against the schema and reports staleness. Exits
non-zero on a schema error — fix and re-run until clean.

### 4. Overlay onto the served files (what the site reads)
```bash
python pipeline/build_storylines.py
```
Rebuilds the storylines and **overlays** your fresh sidecars onto
`data/storylines/<slug>.json` (adds an `editorial` block + per-item
`editor_note`) and `index.json` (adds compact latest-change/status/builder
fields for the list). Production renders static `/storyline/<slug>` pages during
the Vercel build. For local visual QA, run:
```bash
python pipeline/render_static_pages.py
```

### 5. Post it (commit + push)
```bash
git add data/storylines/
# Pin the agent identity so the commit signature can't inherit the machine's
# ambient git config (sets both author and committer).
git -c user.name="Claude" -c user.email="noreply@anthropic.com" \
  commit -m "storyline narratives: <slugs>"
git push
```
Committing the `data/` change *is* publishing — the serverless API reads the
committed files. Keep this in a data-only commit (see
`docs/status/git-hygiene.md`).

## Helpers
- `scripts/run_storyline.sh` — build input → (optionally `--seed`) → validate →
  overlay → static render, in one go, for smoke-testing the UI.
- `scripts/seed_storyline_sample.py` — deterministic **placeholder** narratives
  from the bundle. NOT real summaries; only for testing the `/storyline` render.

## Where it shows up
- Page: `/storylines` (TL;DR teaser per card) and `/storyline/<slug>` (the Arc
  view — status banner, beat spine, what-to-watch, builder take — with a
  Timeline fallback tab and per-item editor notes)
- API: `/api/storylines`, `/api/storylines?slug=<slug>`
- The page is rendered by `pipeline/render_static_pages.py`
  (`render_storyline_body`) from the overlaid `data/storylines/<slug>.json`.
