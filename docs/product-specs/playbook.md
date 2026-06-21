# Agent Builder's Playbook (`/playbook`)

## What it is
A reader-facing tab of **actionable cards** for agent engineers. Where the live
feed tells you *what happened* and the recaps tell you *what you missed*, the
Playbook answers **"what should I change in my agent because of it?"**

Each card states three things plainly:

1. **Problem** — the problem it solves for someone building/operating agents.
2. **Apply** — the concrete change to make to your agent.
3. **Result** — the expected result / payoff once you apply it.

A card may also carry an **area** (Memory, Tool use, Orchestration, Evals,
Reliability, Cost & latency, Safety, Retrieval — aligned with the
agent-engineering wiki at `/map`), an **effort** estimate (low/medium/high),
and a **source** link back to the primary article.

## Why it exists
The product positioning targets **engineers who build and operate AI systems**.
The feed, recaps, and storylines are all *informational* surfaces. The Playbook
is the *applicational* one — it closes the loop from "I read about this
technique" to "I shipped it." It is explicitly the engineering-of-agents lens
(orchestration, tool use, evals, memory, retrieval, cost/latency, reliability,
safety) — never framework churn, prompt listicles, or generic AI news. If an
item has no change a reader could make on Monday, it doesn't belong here.

It is distinct from the wiki (`/map`): the wiki is an evergreen
obstacle→solution *graph* (semantic memory of a problem space); the Playbook is
a dated stream of *do-this-now* cards distilled from recent articles.

## How it's produced (agent routine, not a workflow)
The Playbook follows the same agent-routine + deterministic-builder split as the
daily/weekly recaps and the wiki — the LLM stays out of the hourly pipeline.

```text
build_playbook_input.py   -> data/playbook/input/latest.json  (reading material)
   (an agent reads it and writes the edition)
data/playbook/<date>.json -> the published edition (problem→apply→result cards)
build_playbook_index.py   -> data/playbook/{index,latest}.json (validated; served)
```

- **Input bundle:** `build_playbook_input.py` aggregates the unique, deduped
  articles from the feed over a lookback window (default 3 days; includes
  papers/releases where most applicable learnings live). Items already cited in
  an earlier edition are dropped so editions don't repeat.
- **Editorial work (agent only):** the `playbook` skill
  (`.agents/skills/playbook/SKILL.md`) reads the bundle and writes
  `data/playbook/<date>.json`. Curate hard — 4–8 strong cards beat 20 weak ones.
  The `apply` field is the heart of each card; if you can't name a concrete
  change, cut the item.
- **Validate + serve:** `build_playbook_index.py` validates every edition
  against the schema (`playbook_common.validate_edition`) and rebuilds
  `index.json` + `latest.json`. It exits non-zero on a malformed edition.

An edition's **unique key is its date id** (`YYYY-MM-DD`) — the `date` field,
the filename, and the index key. There is exactly one edition per date; the
routine refuses to overwrite an existing one.

## How it's served
- **Page:** `/playbook` (latest) and `/playbook?date=<date>` (archive dropdown).
  Client-rendered shell `web/playbook.html` (no static archive pages in the
  first slice — a fast-follow if SEO demand appears).
- **API:** `api/playbook.js` — `/api/playbook` (latest), `/api/playbook?date=`
  (one edition), `/api/playbook?list=1` (index). `vercel.json` routes
  `/playbook` and bundles `data/playbook/{index,latest}.json` +
  `data/playbook/<date>.json` (the `input/` bundle is excluded from deploys).
- **Discovery:** linked from the home-page quicknav + `<noscript>` list, and
  carries a "New" nav-update dot driven by `/api/updates` (the `playbook`
  signal: newest edition `date` + `generated_at`, with a 10-day freshness gate
  so a stale edition stops reading as fresh).

## Schema (published edition)
```json
{
  "date": "2026-06-21",
  "title": "Agent Builder's Playbook — Jun 21, 2026",
  "generated_at": "<ISO-8601>",
  "intro": ["optional short opener"],
  "card_count": 6,
  "cards": [
    {
      "title": "Verb-first actionable headline",
      "area": "Memory",
      "problem": "What hurts today for an agent builder.",
      "apply": "The concrete change to make.",
      "result": "The expected result / payoff.",
      "effort": "low",
      "source": "anthropic_blog",
      "url": "https://…",
      "published": "<ISO-8601, optional>",
      "tags": ["optional"]
    }
  ]
}
```
Required per card: `title`, `problem`, `apply`, `result`, `url`. `effort`, when
present, must be `low` | `medium` | `high`.

## Status / follow-ups
- Shipped with a hand-authored **starter edition** (`2026-06-21`) whose cards are
  distilled from the agent-engineering wiki and link to the relevant `/topic`
  pages. Live editions are written by the `playbook` agent routine and cite the
  primary sources from the input bundle.
- Not yet wired: a cadence (the routine is run on demand, like the recaps);
  static per-edition SEO pages; and an "add to Playbook" affordance from a feed
  item. These are deliberate fast-follows, not part of the first slice.
