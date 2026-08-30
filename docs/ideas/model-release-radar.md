# Model Release Radar (`/models`)

## Problem Statement

Readers who build and operate AI systems make a recurring decision the feed
does not directly serve: "a new model just dropped - is it real, what does it
cost, and should I route to it?" Today they assemble that answer from
Artificial Analysis, LMArena, benchmark repos, and r/LocalLLaMA threads by
hand. A single finishable `/models` page - latest releases, frontier coding
benchmarks, price/capability Pareto frontier, community pulse, official
links - does that catch-up job in one screen, consistent with the finishable /
transparent / memory positioning.

## Decided Parameters (2026-08-05)

- Refresh cadence: **every 6h**, in its **own GitHub Actions workflow**
  (not the 2h feed workflow).
- **Free data sources only** - no paid API tiers, no X.com API.
- The editorial "community pulse" agent routine gets **its own scheduled
  slot**, not a ride-along on the existing 5h storyline routine.

## Data Sources (all free tiers)

| Source | Access | Gives us |
|---|---|---|
| Artificial Analysis Data API | free key, 100 req/day, `api/v2` | release_date, context window, params (open models), open-weights flag, intelligence + coding index, pricing, tokens/sec |
| LMArena (arena.ai) | HF dataset `lmarena-ai/leaderboard-dataset`, `latest` split, no key | Arena Elo (crowd preference = quantitative sentiment), rank history |
| DeepSWE (Datacurve) | HF dataset `datacurve/deep-swe` + published leaderboard | long-horizon SWE-agent scores |
| FrontierCode 1.1 (Cognition) | published leaderboard (cognition.com/frontiercode) | mergeable-change coding scores |
| Hacker News | Algolia search API, no key | mention volume, points, top threads per model |
| Reddit (r/LocalLLaMA, r/MachineLearning) | official OAuth API free tier (~100 QPM) | mention volume, upvote-weighted engagement, top threads |
| In-house `data/stories/` | already collected | official announcement link per model (join on lab + model name) |

Constraints that shape the design:

- **Artificial Analysis attribution is mandatory** on every surface showing
  its data; free-tier redistribution terms must be re-read once before ship,
  and the attribution line lives in the page template, not client JS.
- llm-stats.com has an aggregator API but keys are request-access with
  unclear terms - treat as optional convenience, never a dependency; the two
  frontier benchmarks are ingested from their primary sources above.
- Parameter counts are undisclosed for closed frontier models: show real
  numbers for open weights, literal "undisclosed" otherwise. No rumored
  estimates - that would break the anti-hype contract.
- Reddit's free tier is nominally non-commercial; confirm comfort or launch
  HN-only and add Reddit later.

## Sentiment Design (two layers, matching repo invariants)

1. **Deterministic layer** (pipeline, LLM stays disabled): mention counts,
   upvote/point-weighted engagement, links to top threads, plus Arena Elo as
   the crowd-preference number. Observable numbers only - no lexicon-based
   sentiment scoring (keyword sentiment on sarcastic forum comments is noise
   dressed as data).
2. **Editorial layer** (agent routine, same pattern as `storyline-editor`):
   reads the collected top threads, writes a 2-3 sentence "community pulse"
   sidecar per model with thread links, with a `covers_*` snapshot so the
   pipeline can detect staleness and the routine refreshes only what moved.

## Presentation

Pareto frontier scatter as the centerpiece (the model-picking job, not a
vanity leaderboard):

- X: blended $/1M tokens, log scale. Y: coding capability - AA coding index
  by default, toggle to DeepSWE / FrontierCode 1.1 / Arena Elo.
- Frontier step-line; distinct mark for open-weight models; recency
  emphasis (released last 30/90 days).
- Sortable table below: model, lab, release date, params, context,
  benchmark scores, price, pulse blurb + mention stats, official link.
- Vanilla JS + SVG in a `web/models.html` shell reading `/api/models`,
  consistent with the rest of the site (no chart library).

## Architecture

```text
.github/workflows/models-refresh.yml       (every 6h via cron-job.org ticker,
                                            GitHub-hosted ubuntu-latest)
  pipeline/collect_models.py           ->   data/models/latest.json
                                            (+ dated history for score deltas)
  pipeline/model_sentiment.py          ->   data/models/sentiment.json
api/models.js + vercel.json rewrite/includeFiles -> /models
.agents/routines/model-pulse/ (own slot) ->  data/models/pulse/<model>.json
config/models.yaml                          source endpoints, model-name
                                            aliases, freshness window, filters
```

All API calls secrets-gated and no-op cleanly when keys are absent
(`AA_API_KEY`, Reddit creds); HF datasets and HN need no secrets. Runtime
data commits via `scripts/git_commit_runtime.sh`. 6h cadence uses ~4-12 AA
requests/day against the 100/day cap.

## Phasing

1. **Phase 1 (shippable alone):** AA + LMArena ingest, `data/models/`,
   `/models` page with Pareto chart + table, 6h workflow.
2. **Phase 2:** DeepSWE + FrontierCode 1.1 overlay from primary sources.
3. **Phase 3:** HN (+ Reddit if cleared) mention stats + the `model-pulse`
   routine in its own slot.

## Key Assumptions to Validate

- [ ] AA free-tier terms permit display-with-attribution of indices on our
      site (read terms before Phase 1 ships).
- [ ] LMArena HF dataset `latest` split updates frequently enough to be the
      Elo source of truth at 6h cadence.
- [ ] Model-name joining across AA / LMArena / benchmarks / stories is
      tractable with a hand-kept alias map in `config/models.yaml`.
- [ ] The page moves weekly returning readers - it's a natural repeat-visit
      surface, but judge against the north star, not novelty.

## Not Doing (and Why)

- **X.com sentiment** - API is paid and read-capped; scraping violates ToS.
  Free-only decision stands.
- **Lexicon/VADER sentiment scores** - fake precision; deterministic layer
  reports volumes and links, judgment belongs to the agent sidecar.
- **Rumored parameter counts for closed models** - anti-hype contract.
- **A 2h ride-along on the feed workflow** - separate concerns, separate
  failure domains; benchmark data does not change hourly.
- **General "AI leaderboard" breadth** (image/video/speech arenas) - the
  audience lens is platform/agent engineers picking text models to build on.

## Open Questions

- Which models qualify for the page: released within N days (90?), or
  top-K on any tracked axis, or both? Affects page finishability.
- Does `/models` get a nav entry immediately or incubate link-only from the
  feed until it proves retention?
- Should score deltas (model moved up/down since last refresh) feed the
  existing `/api/updates` freshness-pill machinery?
