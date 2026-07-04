---
name: playbook
description: Produce and post the "Agent Builder's Playbook" — actionable cards an agent engineer can apply to their own agents. Reads recent feed articles, distills each into a problem → apply → result card, writes an edition JSON the /playbook page renders, validates it, and commits. Use this when running the playbook curation routine.
---

You are the editor of the **Agent Builder's Playbook** for llm-digest.com. Your
job: turn recent AI feed articles into a small set of *actionable cards* an
agent engineer can apply to their own systems. The page at `/playbook` renders
straight from a JSON file you write and commit — committing to the repo *is*
posting.

Every card must answer three things, plainly:
1. **Problem** — what problem this solves for someone building/operating agents.
2. **Apply** — the concrete change to make to your agent.
3. **Result** — the expected result / payoff once you apply it.

This is the engineering-of-agents lens (orchestration, tool use, evals, memory,
retrieval, cost/latency, reliability, safety) — never framework churn, prompt
listicles, or generic AI news. If an article has no applicable takeaway for an
agent builder, **skip it**. Curate hard; 4–8 strong cards beat 20 weak ones.

Prose bar: `problem`, `apply`, and `result` on every card follow
`.agents/skills/writing-style/SKILL.md` — BLUF, one idea per paragraph,
scannability, specifics over generalities. This matters most here: these
fields are capped to 1–2 tight sentences, so every word has to earn its place.

This routine is the **only editorial author** of Playbook takeaways. Daily and
weekly recap agents never rewrite `problem`, `apply`, or `result`; deterministic
code joins validated cards into recaps by the source article's durable SID.
When these routines cover the same period, run Playbook first, validate it, then
generate the recap.

All scripts live next to this file in `scripts/` and run from anywhere (they
locate the repo root automatically). This routine mirrors the `daily-summary`
skill, but the unit is an *actionable card*, not a news summary.

## The routine (run in order)

### 1. Build the input bundle
```bash
python .agents/skills/playbook/scripts/build_playbook_input.py
# Window ending today (UTC), 3-day lookback, all applicable types. Override:
#   --date 2026-06-21      (end date)
#   --days 5               (lookback window ending on --date; default 3)
#   --types all            (default: news,release,research,paper)
#   --keep-carryover       (include items published before the window)
#   --no-prior-dedup       (include items already cited in an earlier edition)
```
This writes `data/playbook/input/latest.json` (and `input/<date>.json`) — the
window's unique, deduped articles. **This is your reading material.** Items
already cited in an earlier edition are dropped by default so editions don't
repeat learnings.

### 2. Check the edition isn't already published (dedup)
The **unique key for an edition is its date id** (`YYYY-MM-DD`) — the `date`
field, the filename `data/playbook/<date>.json`, and the index key. Read the
`date` from `data/playbook/input/latest.json`, then check whether
`data/playbook/<date>.json` already exists:

- **If it exists**, stop — do not overwrite or duplicate. Report it's done.
- **Only continue if it does not exist.** (To regenerate, delete that one file.)

### 3. Write the edition (your editorial work — only an agent can do this)
Read `data/playbook/input/latest.json`. Each entry in `articles[]` has `title`,
`url` (original source link), `source`, `type`, `summary`, `published`. The
bundle also carries `date`, `range_label`, `article_count`, and `area_hints`.

Write `data/playbook/<date>.json` (e.g. `data/playbook/2026-06-21.json`):
```json
{
  "date": "2026-06-21",
  "title": "Agent Builder's Playbook — Jun 21, 2026",
  "generated_at": "<ISO-8601 now>",
  "intro": [
    "Optional 1–2 sentence opener: the through-line of this edition."
  ],
  "card_count": 5,
  "cards": [
    {
      "id": "pb-cache-tool-schemas",
      "kind": "source-backed",
      "title": "Verb-first headline, e.g. 'Cache tool schemas to cut first-token latency'",
      "area": "Tool use",
      "problem": "What hurts today for an agent builder (1–2 sentences).",
      "apply": "The concrete change to make — specific enough to act on.",
      "result": "The expected result / payoff (quantify when the source does).",
      "effort": "low",
      "source": "anthropic_blog",
      "source_url": "https://…  (copy verbatim from the bundle)",
      "source_sid": "sha256(normalized source_url)[:16]",
      "topic_url": "/topic/tool-use",
      "evidence": {
        "kind": "source-measured",
        "note": "The source measured the result in its published benchmark."
      },
      "published": "2026-06-21T17:44:18Z"
    }
  ]
}
```

**Editorial guidance**
- Use `kind: "source-backed"` for a card distilled from one article. Preserve
  `source_url` exactly from the bundle and copy its supplied `source_sid`. Never
  invent, shorten, normalize, or guess the source URL.
- Use `kind: "evergreen"` only for durable wiki guidance that cannot honestly
  be attributed to one input article. It requires `topic_url` and appears on
  `/playbook`, but is deliberately ineligible for recap embedding.
- Every card needs a stable `id` beginning with `pb-`. When correcting an
  existing edition, preserve a card's `id` if it still represents the same
  takeaway.
- Required per card: `id`, `kind`, `title`, `problem`, `apply`, `result`.
  Optional:
  `area` (use the `area_hints` — Memory, Tool use, Orchestration, Evals,
  Reliability, Cost & latency, Safety, Retrieval), `effort` (`low`/`medium`/
  `high`), `published`, `tags`.
- Keep `card_count` equal to the number of entries in `cards` — update it
  whenever cards are added or removed.
- **`apply` is the heart of the card** — it must be something the reader can do,
  not a restatement of the headline. If you can't name a concrete change, the
  item doesn't belong in the Playbook.
- **`result` is the promise** — what changes once they apply it. Quantify when
  the source gives numbers; otherwise describe the qualitative win honestly.
- Source-backed cards require `evidence.kind`:
  - `source-measured`: the primary source reports a measured result.
  - `source-claimed`: a vendor/project claims the result; word it as a claim.
  - `editorial-inference`: a qualitative expected outcome inferred by the
    editor. Never put percentages, multipliers, latency figures, benchmark
    scores, or guarantees in an inferred result.
- Keep the audience bar: "would an AI platform/agent engineer change something
  on Monday because of this card?" If not, cut it.
- Favor cards that document a measured cost or time delta (e.g., token reduction, latency improvement, or developer productivity hours saved) to support cost-efficiency coverage.
- `intro` is optional and short — one or two sentences. The cards carry the value.

**How the page renders your fields (write to this hierarchy)**
The `/playbook` page renders each card as a change record with a
`SIGNAL → APPLY → EXPECTED` spine, and `apply` is the one dominant, visually
weighted block — `problem` and `result` are quiet annotations bracketing it:

- Keep `problem` (the **Signal**) and `result` (the **Expected** outcome) to
  **1–2 tight sentences each**. They are set in small, muted type; a paragraph
  there fights the Apply block and breaks the scan. Put the substance in `apply`.
- `apply` can run a little longer (it's the largest text on the card) but stays a
  concrete instruction, not a summary.
- Set `area` whenever the area is clear: it's the page's structural index — it
  labels the left rail of each record and feeds the edition's "Covers …" strip,
  so readers scan by engineering area (Memory, Tool use, Evals, …). A card with
  no `area` still renders, but loses that index.

### 4. Validate + rebuild the index (what the site serves)
```bash
python .agents/skills/playbook/scripts/build_playbook_index.py
```
Validates every edition against the schema and rebuilds
`data/playbook/index.json` + `data/playbook/latest.json` and the recap lookup
`data/playbook/source-index.json`. Exits non-zero on a
malformed edition — fix and re-run until clean. (`--check` validates without
writing.) These three files are generated — never hand-edit them; edit the
dated edition file under `data/playbook/<date>.json` and rerun this script
instead.

### 5. Post it (commit + push)
```bash
git add data/playbook/
git -c user.name="Claude" -c user.email="noreply@anthropic.com" \
  commit -m "playbook: edition <date>"
git push
```

## Helpers
- `scripts/seed_playbook_sample.py` — deterministic **placeholder** edition from
  the input bundle. NOT a real edition (problem/apply/result are stubs); use it
  only to test the `/playbook` page rendering.

## Where it shows up
- Page: `/playbook` (latest) and `/playbook?date=<date>` (archive dropdown)
- API: `/api/playbook`, `/api/playbook?date=<date>`, `/api/playbook?list=1`
