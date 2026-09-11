# ARCHITECTURE.md

## System Overview

```text
Sources (RSS/sitemap/arXiv/GitHub releases)
   -> collectors/collect.py            (cooldown-aware crawl, normalize, dedupe)
   -> data/raw/YYYY-MM-DD/items.json
   -> pipeline/source_health.py        (health score, circuit breaker)
   -> pipeline/build_tier1.py          (fast quick-score snapshot, no LLM)
   -> data/tier1/latest.json
   -> pipeline/build_digest.py         (Tier-0: full ranking via pipeline/ranking.py,
      TIER0_INPUT=tier1, incremental no-delta skip)
   -> data/processed/latest.json       (the feed) + data/digest/YYYY-MM-DD.md

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
  - `feed-full-publish` (hourly): runs `skills/ai-feed-digest-local/scripts/run_full.sh`
    end-to-end (collect → tier1 → tier0 → stories/storylines/static pages →
    prune → commit/push)
  - `feed-ops-summary` (daily): operational health snapshot
  - `feedback-sync` (daily): PostHog feedback/CTR sync + source auto-tuning
- Storage: Git repository (versioned data artifacts; no database)
- Delivery: Website on Vercel (https://www.llm-digest.com), RSS, and the
  separately scheduled email digest; Vercel serverless functions in `api/`
  read committed `data/` files bundled per `vercel.json`

## Current Constraints
- RSS/sitemap-heavy ingestion (API connectors pending)
- LLM labeling/reranking disabled (`config/llm.yaml -> enabled: false`);
  ranking is deterministic + config-driven, with LLM interfaces kept as no-ops
- Feedback learning is limited to capped per-source weight adjustments
  (`pipeline/auto_tune.py`), not per-item personalization
- No persistent DB (git artifacts only; snapshots pruned on retention windows)

## Near-term Evolution
1. Re-enable budgeted LLM labeling/reranking when cost/reliability justify it
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
