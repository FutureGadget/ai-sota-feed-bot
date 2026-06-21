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

## Surface design (redesigned 2026-06-21)
The page belongs to the site's **AI operations instrument** family (shared cool
instrument-paper palette, blue `#2457d6` accent, condensed display titles,
monospace utility labels, hairline rules — no large rounded cards, no pill
navigation). It spends its one page-specific expressive idea on the **change
record**:

- Each entry is an engineer's change record with a vertical
  **`SIGNAL → APPLY → EXPECTED`** spine. `problem` is the *Signal* (what should
  make you act), `apply` is the change, `result` is the *Expected* outcome.
- **`Apply` is the single dominant block** — accent left-rule, faint accent
  wash, the largest body type on the card — so it reads like a patch hunk. The
  earlier layout gave problem/apply/result three equal field labels; the
  redesign deliberately breaks that false equality, because the reader's job is
  to decide *what to change*. `problem`/`result` are demoted to compact,
  muted, monospace-labeled annotations.
- A left **area rail** indexes each record by engineering area (Memory, Tool
  use, Evals, …), aligned with `/map`. Area — not a decorative `01 / 02`
  sequence — is the honest classifier, since the cards are independent changes,
  not steps in a process. The hero carries a "Covers …" strip summarizing the
  edition's span.
- **`effort` renders as a 3-segment meter** (low/medium/high = 1/2/3 filled),
  not a red/amber/green pill — honest magnitude, no hype color.
- The hero states the **finishable** count ("N changes worth making") and the
  list closes with a "That's the edition — N changes" finish line, matching the
  finishable promise of the daily brief without reusing its reading-route
  signature.

Behavior preserved by the redesign: the `/api/playbook` latest/date/list
contract, the archive dropdown, the JSON link, source links
(`target="_blank" rel="noopener"`, `data-track="playbook-link"`), the
`/api/updates` nav "New" dot (`ai_feed_seen_playbook_v1`), light/dark themes,
visible keyboard focus, reduced motion, and empty/error states. A localhost-only
fallback reads committed `data/playbook/{latest,index}.json` / `<date>.json`
when `/api/*` is unavailable (local visual QA only; production API behavior is
unchanged), mirroring the recap shells.

Editorial implication (no schema change): because `problem`/`result` are small
annotations and `apply` is the hero, the `playbook` skill keeps `problem` and
`result` to 1–2 tight sentences and puts the substance in `apply`; `area` is now
load-bearing for the rail/coverage index and should be set when clear. See
`.agents/skills/playbook/SKILL.md`.

Regression coverage: `tests/test_playbook_surface.py`.

## Status / follow-ups
- Shipped with a hand-authored **starter edition** (`2026-06-21`) whose cards are
  distilled from the agent-engineering wiki and link to the relevant `/topic`
  pages. Live editions are written by the `playbook` agent routine and cite the
  primary sources from the input bundle.
- Not yet wired: a cadence (the routine is run on demand, like the recaps);
  static per-edition SEO pages; and an "add to Playbook" affordance from a feed
  item. These are deliberate fast-follows, not part of the first slice.
