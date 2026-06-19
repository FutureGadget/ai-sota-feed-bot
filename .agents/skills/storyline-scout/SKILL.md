---
name: storyline-scout
description: Improve storyline recall for ai-sota-feed-bot. Reads machine-built candidate threads the precision-first clustering missed (near-miss anchors, same-subject co-mention buckets), judges which are genuinely one story/thread, and writes confirmed links that the pipeline applies through its deterministic floor. Use this when running the storyline recall/scout routine.
---

You are a scout for an AI news intelligence product. The storyline clustering is
deliberately precision-first — it links stories only on a shared *rare anchor
word* — so it structurally misses real threads: the same launch covered as
"OpenAI's new flagship" and "GPT-5 is here" (no shared rare word), or a genuine
thread sitting one item/day/source under the floor. Your job is to catch those.

You do **not** decide what becomes a storyline. You propose **links** (these
sids are one story/thread); `pipeline/build_storylines.py` applies each link as a
synthetic candidate **through the same MIN_ITEMS=3 / MIN_DAYS=2 / MIN_SOURCES=2
floor**. A link is inert unless its nodes clear that floor — so a wrong or thin
link simply never surfaces. Precision is the whole job: **a bogus storyline
costs reader trust; a missed one costs nothing. When unsure, do not link.**

All scripts live next to this file in `scripts/` and locate the repo root
automatically. This routine mirrors `storyline-editor`, but you write *links*
(`data/storylines/scout/links.json`), not narratives.

## The routine (run in order)

### 1. Build the candidate bundle
```bash
python pipeline/build_storylines.py        # refresh the current threads first
python pipeline/scout_candidates.py        # -> data/storylines/scout/candidates.json
```
`candidates.json` is **your reading material**. Two kinds of group:
- **`near_miss`** — shares an anchor but is under the floor (`signal` shows
  items/days/sources). `related_storyline` is set if its nodes touch an existing
  thread. Question: *is this a real developing thread worth surfacing — and which
  sids belong?*
- **`co_mention`** — unclustered stories sharing a broad subject word
  (`subject`), with no shared rare anchor. Question: *are any of these the same
  story/thread despite different wording?*

Each node carries `sid`, `title`, `sources`, `date`, `url`. The bundle also
contains `window_sids`, a validation allowlist for preserving accepted links
and extending an existing storyline. (Candidate groups are capped; `dropped`
reports anything trimmed.)

### 2. Judge each group (precision-first)
Decide which sids genuinely belong to one story/thread. Rules:
- **Default to NOT linking.** Only link when you're confident the items are the
  same event or a clear development of it (launch → hands-on → reaction).
- Same broad topic is **not** a thread ("two OpenAI items this week" ≠ one
  story). Same *specific event or its follow-ups* is.
- To actually surface, a link needs **≥3 sids across ≥2 days and ≥2 sources**.
  Fewer is allowed but inert (kept for when it grows) — prefer to skip it.
- When extending an existing thread (`related_storyline` set), **include that
  storyline's member sids** in `members` so the link merges into it instead of
  spawning a duplicate.

### 3. Write the links file
Write `data/storylines/scout/links.json` — a JSON array of:
```json
[
  {
    "id": "mimo-code-vs-claude",
    "label_hint": "MiMo Code vs Claude Code",
    "members": ["73bd33cfe3d02d07", "41ecbecdcff07506", "72c805579f21b6e8"],
    "reason": "Same story — Xiaomi's MiMo Code beating Claude Code — across 3 sources.",
    "confidence": "high",
    "candidate_id": "comention-claude"
  }
]
```
- **`id` is stable** — reuse the same id across runs for the same thread so its
  slug and followers survive (slugs carry over by member overlap; a steady id
  keeps that anchored). Updating a thread = same id, expanded `members`.
- `members` sids **must come from candidate nodes, the related existing
  storyline, or another existing confirmed link**. Every sid must appear in the
  bundle's `window_sids` allowlist (the validator enforces this). Never invent
  sids.
- `label_hint` is the thread title used if the link forms a scout-only
  storyline. Keep it specific.

### Recommended: Haiku judge fan-out (ultracode Workflow)
Candidate groups are many, independent, and each is a small, narrow judgment —
ideal for a **Haiku** fan-out with an adversarial check. Run the `Workflow` tool
(requires the `ultracode` opt-in; the cloud routine has it) with the bundle as
`args`:

```js
export const meta = {
  name: 'storyline-scout-judge',
  description: 'Judge storyline candidate groups into confirmed links',
  phases: [{ title: 'Judge' }, { title: 'Verify' }],
}
const LINK = {
  type: 'object',
  required: ['link', 'members', 'label_hint'],
  properties: {
    link: { type: 'boolean' },                 // false = not one story; skip
    members: { type: 'array', items: { type: 'string' } },
    label_hint: { type: 'string' },
    reason: { type: 'string' },
    confidence: { enum: ['high', 'medium', 'low'] },
  },
}
const groups = [...(args.near_miss || []), ...(args.co_mention || [])]
const judged = await pipeline(
  groups,
  g => agent(
    `Audience: AI platform engineers. Are these the SAME story or a clear ` +
    `development of one (launch -> hands-on -> reaction)? Default link=false ` +
    `unless confident. Return the member sids that belong together.\n` +
    JSON.stringify(g),
    { label: `judge:${g.id}`, phase: 'Judge', schema: LINK, model: 'haiku' }),
  (v, g) => (v && v.link && (v.members || []).length >= 2)
    ? agent(`Try to REFUTE that these sids are one story. Default refuted=true ` +
        `if the connection is only "same topic". Group: ${JSON.stringify(g)}\n` +
        `Claimed members: ${JSON.stringify(v.members)}`,
        { label: `verify:${g.id}`, phase: 'Verify',
          schema: { type: 'object', required: ['refuted'], properties: { refuted: { type: 'boolean' } } },
          model: 'haiku' })
        .then(r => (r && !r.refuted)
          ? { id: g.id, label_hint: v.label_hint, members: v.members, reason: v.reason,
              confidence: v.confidence || 'high', candidate_id: g.id }
          : null)
    : null,
)
return judged.filter(Boolean)
```
Read `data/storylines/scout/candidates.json`, call `Workflow` with `{ args: <that JSON> }`,
then write the returned array to `data/storylines/scout/links.json` (merge with
any existing links by `id`). For a handful of candidates, judging inline is fine.

### 4. Validate
```bash
python .agents/skills/storyline-scout/scripts/validate_links.py --check
```
Structural check + every member sid must be a real candidate sid. Fix until clean.

### 5. Apply through the floor gate
```bash
python pipeline/build_storylines.py
```
Confirmed links are applied; a thread that used a link gets `via_scout: true`
(the page badges it "🔍 surfaced by scout"). Links that don't clear the floor
silently no-op — that's intended.

### 6. (Optional) hand new threads to the editor
A freshly surfaced scout thread has no narrative yet. Running the
`storyline-editor` routine afterward will pick it up (it appears in that
routine's `needs_narrative` set).

### 7. Post it (commit + push)
```bash
git add data/storylines/
# Pin the agent identity so the commit signature can't inherit the machine's
# ambient git config (sets both author and committer).
git -c user.name="Claude" -c user.email="noreply@anthropic.com" \
  commit -m "storyline scout links: <ids>"
git push
```
Committing the `data/` change *is* publishing. Keep it a data-only commit.

## Helpers
- `scripts/run_scout.sh` — candidates → (optionally `--seed`) → validate → apply,
  for smoke-testing.
- `scripts/seed_scout_sample.py` — deterministic **placeholder** link from the
  bundle. NOT a real judgment; only for testing the path end to end.

## Maintenance
Stale links (members aged out of the 21-day window) are **harmless** — the floor
gate makes them inert — but prune them occasionally so the file stays readable.
Keep `confidence: high` links only unless you have a reason to keep weaker ones.

## Where it shows up
- `/storylines` + `/storyline/<slug>` — scout-surfaced threads render like any
  other, badged "🔍 surfaced by scout".
