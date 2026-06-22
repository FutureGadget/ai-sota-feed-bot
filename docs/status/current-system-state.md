# Current System State (as of 2026-06-21 KST)

This file is a snapshot of the **currently deployed behavior** so we can resume quickly in future sessions.

## Runtime mode
- Ranking engine: unified single path in `pipeline/ranking.py` (the old v1/v2
  split, `pipeline/ranking_v2.py`, and `config/ranking_v2.yaml` no longer exist)
- `config/ranking.yaml`:
  - `enabled: true`
  - `preset: balanced` (loads `config/presets/balanced.yaml`, then local overrides deep-merge on top)
  - `candidate_pool_cap: 120`
  - `llm_budget: 8` (inert — see below)
  - `max_items: 24`
  - `slot_merge_strategy: floor_then_dynamic`
  - `dynamic_slot_rerank.enabled: true`, `top_band_constraints.enabled: true`
- **LLM disabled**: `config/llm.yaml -> enabled: false`. All scoring is
  heuristic/deterministic; `pipeline/llm_label.py` / `llm_rerank.py` are no-op
  interfaces kept for future re-enable.
- Reader auto-tuning active: `data/feedback/source_adjustments.json`
  (from `pipeline/auto_tune.py`) is applied as `source_tune` in slot scoring.

## End-to-end behavior (hourly `feed-full-publish` workflow → `run_full.sh`)
1. Collect raw items (`collectors/collect.py`, per-source crawl cooldown)
2. Source health update + local degradation alert artifacts/logs
3. Tier-1 fast snapshot (`pipeline/build_tier1.py` → `data/tier1/latest.json`)
4. Tier-0 full build (`pipeline/build_digest.py`, `TIER0_INPUT=tier1`,
   incremental mode on; exits early with `FULL_RUN_NO_DELTA_SKIP=true` when
   nothing changed)
5. Story store sync + static page render
   (`story_store.py`, `render_static_pages.py`). Storyline generation is
   intentionally excluded from GitHub Actions.
6. Prune runtime snapshots (processed 45d, tier1 3d hard cap)
7. Commit + push `data/` + `web/` (triggers Vercel production deploy, whose
   build command rerenders static pages from the committed data)
8. Finish with `FULL_RUN_OK`; website deployment follows the runtime-data push

Daily companions:
- `feed-ops-summary` (12:30 UTC): ops health snapshot
- `feedback-sync` (12:45 UTC): PostHog feedback + CTR sync, auto-tune apply
- Daily/weekly recaps: agent routines (`.agents/skills/daily-summary`,
  `.agents/skills/weekly-summary`) write `data/daily|weekly/<key>.json`;
  committing is publishing. The repository-owned daily scheduler definition is
  `.agents/routines/daily-recap/harness.yaml`: 09:00 `Asia/Seoul`, targeting
  the previous UTC calendar day. The weekly scheduler definition is
  `.agents/routines/weekly-recap/harness.yaml`: Saturday at 13:00
  `Asia/Seoul`, targeting the current ISO week with a news-only bundle. Each
  scheduler injects only its routine's `prompt.md`.
- Storylines: external Claude Code routine every 5 hours runs
  `storyline-scout` then `storyline-editor`, validates and rebuilds
  `data/storylines/`, and commits/pushes the result. The hourly workflow only
  keeps `data/stories/` current as its input.

## Ranking stages (active)
- Stage A: deterministic prefilter (regex excludes, slot freshness windows,
  health floor, cap to 120)
- Stage B: slot assignment — frontier_official, agent_tooling_releases,
  infra_runtime_releases, vendor_general_updates, practitioner_analysis,
  community_signal, research_watch, overflow
- Stage C: slot scoring/selection — heuristic score (LLM path budgeted but
  disabled), `alpha*score + beta*freshness + source_bias + source_tune +
  topical_bias`, per-slot max and per-source caps
- Global merge: dynamic slot meta-rerank, trim to 24 preserving slot floors
- Top-band constraints: composition floors/caps inside the top 10

## Run health signals (greppable)
- `v2_stats prefilter=A->B llm_used=N/8 slots=... total=T`
- `FULL_RUN_OK` / `FULL_RUN_NO_DELTA_SKIP=true`
- `runtime_commit_done=true` / `runtime_push_skipped=true`
- `latest_json_valid=true`

## Operational notes
- `run_full.sh` holds a lock (`.run_full.lock`) and skips auto-push when the
  worktree was already dirty (commit-hygiene guard).
- Hourly bot commits (`chore(data): refresh feed artifacts …`) land on `main`;
  expect to rebase local work.
- LLM usage is bounded by `llm_budget`, but is zero while LLM stays disabled.

## Next tuning levers
- Re-enable LLM labeling (`config/llm.yaml -> enabled: true`) once
  auth/cost/reliability are settled; budget starts at 8.
- Adjust dynamic slot rerank weights/biases for desired top ordering.
- Tune `auto_tune` caps as reader feedback volume grows.
