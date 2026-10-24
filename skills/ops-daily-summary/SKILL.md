---
name: ops-daily-summary
description: Generate and review the daily operational summary for ai-sota-feed-bot (edition runs, latest item counts, Jev gate verdicts/categories, ingest status distribution) and use it to validate no-delta skip / cooldown behavior.
---

Produce a concise operations health snapshot from local runtime artifacts.

## Quick command
- `bash skills/ops-daily-summary/scripts/run_ops_daily_summary.sh`

## What it checks
- Processed edition run count over last 24h
- Latest edition run timestamp/item count
- Today's Jev verdict counts (`keep`/`review`/`drop`) and top categories
- Ingest status distribution in last 24h (`ok`, `skipped_cooldown`, `skipped_open_circuit`, `error`)

## Interpretation hints
- A rising `drop` share with a healthy `keep` set is the judge doing its job; a near-total `drop` share is a model/config regression.
- `judge_judged=0` means the judge was disabled or `OPENROUTER_API_KEY` was missing; the feed still ran deterministically.
- Zero processed runs in 24h may indicate excessive no-delta skips or scheduler issue.
- Rising `error` count in ingest statuses needs source-level check.

## Follow-up actions
- If freshness seems stale, run:
  - `FULL_RUN_BYPASS_COOLDOWN=1 bash skills/ai-feed-digest-local/scripts/run_full.sh`
- If source errors rise, inspect health artifacts:
  - `data/health/source_health.json`
  - `data/health/circuit_breaker.json`
