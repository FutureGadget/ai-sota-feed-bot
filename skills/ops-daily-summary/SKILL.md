---
name: ops-daily-summary
description: Generate and review daily operational summary for ai-sota-feed-bot (Tier-1 runs, Tier-0 runs, latest item counts, ingest status distribution) and use it to validate no-delta skip / cooldown behavior.
---

Produce a concise operations health snapshot from local runtime artifacts.

## Quick command
- `bash skills/ops-daily-summary/scripts/run_ops_daily_summary.sh`

## What it checks
- Tier-0 processed run count over last 24h
- Tier-1 fast run count over last 24h
- Latest processed and Tier-1 run timestamps/item counts
- Ingest status distribution in last 24h (`ok`, `skipped_cooldown`, `skipped_open_circuit`, `error`)

## Interpretation hints
- High `skipped_cooldown` with stable Tier-1 item count can be healthy (reuse path working).
- Zero processed runs in 24h may indicate excessive no-delta skips or scheduler issue.
- Rising `error` count in ingest statuses needs source-level check.

## Follow-up actions
- If freshness seems stale, run:
  - `FULL_RUN_BYPASS_COOLDOWN=1 bash skills/ai-feed-digest-local/scripts/run_full.sh`
- If source errors rise, inspect health artifacts:
  - `data/health/source_health.json`
  - `data/health/circuit_breaker.json`
