# ARCHITECTURE.md

## System Overview

```text
Sources (RSS/API)
   -> collectors/collect.py
   -> data/raw/YYYY-MM-DD/items.json
   -> pipeline/build_digest.py (dedupe + scoring + ranking)
   -> data/processed/latest.json
   -> data/digest/latest.md
   -> publish/publish_issue.py / publish/publish_telegram.py
```

## Runtime
- Scheduler: GitHub Actions (`hourly-ingest`, `daily-digest`)
- Storage: Git repository (versioned data artifacts)
- Delivery: GitHub Issues + optional Telegram

## Current Constraints
- RSS-heavy ingestion (API connectors pending)
- Heuristic relevance scoring (no feedback learning loop yet)
- No persistent DB (git artifacts only)

## Near-term Evolution
1. Better signal balancing (papers/news/releases quotas)
2. Feedback loop from Telegram reactions/buttons
3. Optional DB-backed storage (Postgres + vector index)
