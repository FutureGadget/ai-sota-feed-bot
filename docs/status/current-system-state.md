# Current System State (as of 2026-02-16 KST)

This file is a snapshot of the **currently deployed behavior** so we can resume quickly in future sessions.

## Runtime mode
- Ranking engine: **v2 only** (v1 pipeline bypassed in `pipeline/build_digest.py` when v2 enabled)
- `config/ranking_v2.yaml`:
  - `enabled: true`
  - `shadow_mode: false` (v2 is production path)
  - `candidate_pool_cap: 100`
  - `llm_budget: 8`
  - `max_items: 20`
  - `dynamic_slot_rerank.enabled: true`

## End-to-end behavior
1. Collect raw items (`collectors/collect.py`)
2. Source health + alerts
3. Build digest with v2 pipeline (`pipeline/ranking_v2.py` via `build_digest.py`)
4. Publish GitHub issue + Telegram

Recent stable run signals:
- `sources_ok=24/24`
- `v2_stats prefilter=589->100 ... total=16`
- `llm_used` varies by cache/budget (e.g., `3/8`)
- `updated_issue=#3`
- `telegram_sent=true`
- `FULL_RUN_OK`

## v2 ranking stages (active)
- Stage A: deterministic prefilter
  - regex exclusions
  - slot freshness windows
  - health floor
  - cap to 100 candidates
- Stage B: slot assignment
  - frontier_official, agent_tooling_releases, practitioner_analysis, community_signal, research_watch, overflow
- Stage C: slot scoring/selection
  - v2 label schema (`label_v2_system.txt`)
  - LLM budgeted calls + heuristic fallback
  - per-slot max and per-source caps
- Global merge
  - item score + **dynamic slot meta-rerank** (slot priority)
  - trim to output size while preserving slot minimum floors

## Key docs
- Flow: `docs/ranking-v2-flow.md`
- Plan: `docs/scoring-v2-plan.md`
- Opus implementation plan: `docs/scoring-v2-opus-plan.md`

## Operational notes
- Full runs can occasionally appear stalled after ingest; allow extra time before killing.
- LLM usage is bounded by `llm_budget`, not by prefilter pool size.
- Candidate pool cap (`100`) controls breadth before LLM/slot scoring.

## Next tuning levers
- Increase `llm_budget` gradually (8 -> 20) after stability checks.
- Adjust dynamic slot rerank weights/biases for desired top ordering.
- Raise `candidate_pool_cap` only if needed for coverage and runtime allows.
