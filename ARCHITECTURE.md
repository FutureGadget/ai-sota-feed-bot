# ARCHITECTURE.md

## System Overview

```text
Sources (RSS/sitemap/arXiv/GitHub releases)
   -> collectors/collect.py            (cooldown-aware crawl, normalize, dedupe)
   -> data/raw/YYYY-MM-DD/items.json
   -> pipeline/source_health.py        (health score, circuit breaker)
   -> pipeline/build_digest.py         (single edition builder:
      editorial policy -> Jev gate/category -> ranking via pipeline/ranking.py,
      incremental no-delta skip)
   -> data/processed/latest.json       (the feed)
   -> data/processed/classified.json   (judge verdicts/categories; joined into the editor-deck input bundles by pipeline/deck_quality.py)
   -> data/digest/YYYY-MM-DD.md

Reader-facing derivatives (built from the durable story store):
   pipeline/story_store.py sync      -> data/stories/   (/story/<sid> permalinks)
   pipeline/build_storylines.py      -> data/storylines/ (/storylines cross-day threads)
   pipeline/render_static_pages.py   -> web/ static pages + sitemap

Agent Skill Lab editorial pilot:
   pipeline/build_skill_lab.py       -> data/playbook/lab/ (validated protocol/results)
                                     -> /api/playbook?lab=...
                                     -> Playbook, feed promotion, weekly email

Reader feedback loop (daily):
   PostHog events -> pipeline/feedback.py sync-posthog -> data/feedback/events.jsonl
                  -> pipeline/auto_tune.py (CTR + feedback)
                  -> data/feedback/source_adjustments.json
                  -> applied as source_tune in the next ranking run
```

## Runtime
- Scheduler: GitHub Actions —
  - `feed-full-publish` (every two hours): runs `skills/ai-feed-digest-local/scripts/run_full.sh`
    end-to-end (collect -> single edition build -> stories/storylines/static
    pages -> prune -> commit/push)
  - `feed-ops-summary` (daily): operational health snapshot
  - `feedback-sync` (daily): PostHog feedback/CTR sync + source auto-tuning
- Storage: Git repository (versioned data artifacts; no database)
- Delivery: Website on Vercel (https://www.llm-digest.com), RSS, and the
  separately scheduled email digest; Vercel serverless functions in `api/`
  read committed `data/` files bundled per `vercel.json`

## Current Constraints
- RSS/sitemap-heavy ingestion (API connectors pending)
- The legacy ranking LLM is disabled (`config/llm.yaml -> enabled: false`);
  ranking is deterministic + config-driven, with the old LLM interfaces kept
  as no-ops. The separate Jev decision-model gate (`config/judge.yaml`) is
  active, fail-open, and reused through `data/processed/judgments.json`.
- Feedback learning is limited to capped per-source weight adjustments
  (`pipeline/auto_tune.py`), not per-item personalization
- No persistent DB (git artifacts only; snapshots pruned on retention windows)

## Near-term Evolution
1. Tune the Jev gate and category taxonomy; re-enable the legacy ranking LLM
   separately when cost/reliability justify it
2. Deepen the feedback loop beyond per-source weights (topic/item-level signals)
3. Optional DB-backed storage (Postgres + vector index) if git artifacts stop scaling

## Editorial discovery across publishing paths

`lib/editorial-catalog.js` derives item-level metadata and content versions from
published recap/Playbook indexes and their edition records, served storylines
(including editorial overlays), compiled wiki/Foundations pages, and validated
Skill Lab records. `/api/updates` returns this catalog alongside its legacy
section signals. Its explicit Vercel file bundle is part of the producer
contract. The browser renders it in the feed, Editor's Desk, section roots and
`/updates`, and stores opened item versions locally.

No producer writes a second shared manifest. Independently scheduled skill
publications reach discovery through their existing commits and deployment;
feed-only, model-refresh and email jobs keep their existing responsibilities.
See `docs/product-specs/nav-update-indicators.md` for coverage and lifecycle rules.

## Model Radar pricing

`model-prices-refresh.yml` refreshes OpenRouter catalog and provider endpoint JSON
every 15 minutes into `data/models/pricing.json`. The six-hour benchmark job
continues to write `data/models/latest.json` independently. Static rendering joins
the two, replaces served token prices, and recomputes token-price frontiers.
`/models/compare` estimates spend from user-selected token/cache volumes against
AA intelligence or coding scores. No new API function is added. See the
[pricing and comparison contract](docs/product-specs/model-radar-comparison.md).
