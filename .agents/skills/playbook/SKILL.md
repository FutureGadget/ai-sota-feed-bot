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
      "title": "Verb-first headline, e.g. 'Cache tool schemas to cut first-token latency'",
      "area": "Tool use",
      "problem": "What hurts today for an agent builder (1–2 sentences).",
      "apply": "The concrete change to make — specific enough to act on.",
      "result": "The expected result / payoff (quantify when the source does).",
      "effort": "low",
      "source": "anthropic_blog",
      "url": "https://…  (copy verbatim from the bundle)",
      "published": "2026-06-21T17:44:18Z"
    }
  ]
}
```

**Editorial guidance**
- **Preserve `url` exactly** from the bundle — it's the reader's link to the
  primary source. Never invent, shorten, or guess links. Every card needs one.
- Required per card: `title`, `problem`, `apply`, `result`, `url`. Optional:
  `area` (use the `area_hints` — Memory, Tool use, Orchestration, Evals,
  Reliability, Cost & latency, Safety, Retrieval), `effort` (`low`/`medium`/
  `high`), `published`, `tags`.
- **`apply` is the heart of the card** — it must be something the reader can do,
  not a restatement of the headline. If you can't name a concrete change, the
  item doesn't belong in the Playbook.
- **`result` is the promise** — what changes once they apply it. Quantify when
  the source gives numbers; otherwise describe the qualitative win honestly.
- Keep the audience bar: "would an AI platform/agent engineer change something
  on Monday because of this card?" If not, cut it.
- `intro` is optional and short — one or two sentences. The cards carry the value.

### 4. Validate + rebuild the index (what the site serves)
```bash
python .agents/skills/playbook/scripts/build_playbook_index.py
```
Validates every edition against the schema and rebuilds
`data/playbook/index.json` + `data/playbook/latest.json`. Exits non-zero on a
malformed edition — fix and re-run until clean. (`--check` validates without
writing.)

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
