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

The `/storyline/<slug>` page renders an **Arc view** when you provide it: a
live-status banner, a spine of named **beats** (LAUNCH → FRICTION → THE TURN →
NOW), a "what to watch" list of open questions, and a builder takeaway — with a
plain "Timeline" view as the fallback tab. Provide the arc fields below and the
page upgrades automatically; omit them and it falls back to the day-by-day
timeline. Every badge on the page must be **true** — we surface only real
provenance (mechanical threading, scout, the editor). Do not invent
verification/agent labels the system doesn't actually produce.

Audience: **AI platform engineers** (see `AGENTS.md` → Product Positioning).
Write for the person who skimmed the headline last Tuesday and wants the
through-line, not hype. The quality bar is "would the owner read this and feel
caught up in 20 seconds".

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
  "tldr": "2-3 sentences: the arc of the whole thread, in order. What it is, what happened next, where it stands now.",
  "whats_new": "1-2 sentences: what the most recent day added vs. before. Omit on a brand-new single-burst thread.",
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
  "take_for_builders": "One actionable line for platform engineers (falls back to why_it_matters).",
  "day_captions": {
    "<sid>": "one line on what THIS item added to the story (not a re-summary of the article)"
  }
}
```

**The arc fields (optional but recommended — they drive the Arc view)**
- `status` is the live-status banner. `state` is a short label ("Shipping",
  "Suspended · temporary", "Resolved"); `tone` ∈ `launch | rising | turn | now |
  resolved | alert | neutral` colors the banner; `changed` is the ISO date the
  state last moved; `reenable`/`detail` are optional clarifiers. Use it for a
  thread that has a *current state*; omit it for a thread that's just developing.
  `status.track` (optional) is the **"Access over time"** bar — an ordered list
  of `{label, detail, tone, weight}` phases (weights are relative widths); use
  it for threads where a state visibly flips over time (available → suspended).
- `provenance` (optional) keys agent badges by item `sid`:
  `surfaced_by: "scout"` (🔍 dashed pill, for an item the scout actually
  surfaced), `verified: <N sources>` (✓ pill + a per-beat "verified across N
  sources" line — only set it when N independent sources genuinely corroborate
  the beat), `status_update: true` (↻ pill, for the item that moved the status).
  These drive the "Agents on this story" strip and the "maintained by N agents"
  count — so set them **truthfully**; a badge with no real work behind it is
  exactly the kind of hype this product exists to avoid.
- `beats` are the spine — an **ordered** arc, each beat grouping the member
  `sids` that moved the story in that phase. `headline` is required; `kicker` is
  the short phase label (LAUNCH / FRICTION / THE TURN / NOW — your call); `tone`
  colors the node (use `turn` for the pivot, it gets the emphasized red node).
  The renderer derives each beat's date range from its items and sweeps any
  uncovered members into a trailing "More in this thread" beat — but aim to
  place every sid. Only use sids present in the bundle; the validator rejects
  unknown ones.
- `open_questions` is "what to watch" — up to 6 genuinely open questions an
  engineer would track, not rhetorical filler.
- `take_for_builders` renders as the **Take for builders** line; if omitted the
  page falls back to `why_it_matters`.

**Editorial guidance**
- `covers_last_updated` and `covers_member_sids` are the **staleness snapshot** —
  copy `last_updated` verbatim and include the `sid` of every item in the
  timeline. Getting these right is what keeps the overlay from re-flagging your
  work stale on the next run.
- `tldr` is the payoff. Lead with the substance, in chronological order. No
  "in this storyline we see…" throat-clearing.
- `whats_new` is what makes a **follow** worth it (threads have a Follow
  button). Answer "what happened next?" since the prior beat. Leave it out
  (or empty) when the thread is a single same-day burst with no prior state.
- `why_it_matters` is the platform-engineer lens — pricing, availability,
  agent/tooling impact, reliability — not generic "this is significant".
- `day_captions` are keyed by `sid` and describe what each item *added* to the
  arc ("first independent benchmark", "Anthropic's official response"), not a
  restatement of the headline. You don't need a caption for every item; caption
  the ones that move the story.
- **Never invent links or items.** Only use `sid`s present in the bundle's
  timeline — the validator rejects unknown sids.

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
  required: ['slug', 'tldr', 'covers_last_updated', 'covers_member_sids'],
  properties: {
    slug: { type: 'string' }, tldr: { type: 'string' },
    whats_new: { type: 'string' }, why_it_matters: { type: 'string' },
    take_for_builders: { type: 'string' },
    covers_last_updated: { type: 'string' },
    covers_member_sids: { type: 'array', items: { type: 'string' } },
    status: { type: 'object', properties: {
      state: { type: 'string' }, tone: TONE, changed: { type: 'string' },
      reenable: { type: 'string' }, detail: { type: 'string' },
      track: { type: 'array', items: { type: 'object', properties: {
        label: { type: 'string' }, detail: { type: 'string' },
        tone: TONE, weight: { type: 'number' } } } } } },
    provenance: { type: 'object', additionalProperties: { type: 'object', properties: {
      surfaced_by: { type: 'string' }, verified: { type: 'integer' },
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
`editor_note`) and `index.json` (adds a TL;DR teaser). The `/storyline/<slug>`
page renders these automatically — there is no separate static render step
(storyline pages are client-rendered from `/api/storylines`).

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
  overlay, in one go, for smoke-testing the UI.
- `scripts/seed_storyline_sample.py` — deterministic **placeholder** narratives
  from the bundle. NOT real summaries; only for testing the `/storyline` render.

## Where it shows up
- Page: `/storylines` (TL;DR teaser per card) and `/storyline/<slug>` (the Arc
  view — status banner, beat spine, what-to-watch, builder take — with a
  Timeline fallback tab and per-item editor notes)
- API: `/api/storylines`, `/api/storylines?slug=<slug>`
- The page is rendered by `pipeline/render_static_pages.py`
  (`render_storyline_body`) from the overlaid `data/storylines/<slug>.json`.
