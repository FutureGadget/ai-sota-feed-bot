# Current System State (as of 2026-10-24 UTC)

This file is a snapshot of the **currently deployed behavior** so we can resume quickly in future sessions.

## Runtime mode
- Ranking engine: unified single path in `pipeline/ranking.py` (the old v1/v2
  split, `pipeline/ranking_v2.py`, and `config/ranking_v2.yaml` no longer exist)
- `config/ranking.yaml`:
  - `enabled: true`
  - `preset: balanced` (loads `config/presets/balanced.yaml`, then local overrides deep-merge on top)
  - `candidate_pool_cap: 140`
  - `llm_budget: 8` (legacy ranking LLM; inert while disabled)
  - `max_items: 24` (the edition may return fewer on a quiet day)
  - `slot_merge_strategy: floor_then_dynamic`
  - `time_decay.enabled: true` (smooth half-life age-down after Stage C scoring)
  - `dynamic_slot_rerank.enabled: true`, `top_band_constraints.enabled: true`
- **Ranking LLM disabled**: `config/llm.yaml -> enabled: false`.
  `pipeline/llm_label.py` / `llm_rerank.py` are no-op interfaces kept for a
  future re-enable.
- **Jev gate active**: `config/judge.yaml` runs the OpenRouter System One
  hybrid gate + category after Stage A. It is fail-open without
  `OPENROUTER_API_KEY`. Prior judgments are reused from
  `data/processed/judgments.json`; only new or expired items call Jev.
  `data/processed/classified.json` is the compact artifact for the editor
  decks.
- The Tier-1 snapshot and API fresh blend no longer exist. `api/feed.js`,
  `api/rss.js`, and `api/share.js` read `data/processed/**` only.
- Reader auto-tuning active: `data/feedback/source_adjustments.json`
  (from `pipeline/auto_tune.py`) is applied as `source_tune` in slot scoring.

## End-to-end behavior (two-hour `feed-full-publish` workflow → `run_full.sh`)
1. Collect raw items (`collectors/collect.py`, per-source crawl cooldown)
2. Source health update + local degradation alert artifacts/logs
3. Single edition build (`pipeline/build_digest.py`):
   deterministic editorial policy (`pipeline/editorial.py`) -> Stage A
   prefilter -> Jev gate/category (`pipeline/editorial_judge.py`) -> ranking.
   Incremental mode exits early with `FULL_RUN_NO_DELTA_SKIP=true` when
   nothing changed.
4. Story store sync + static page render
   (`story_store.py`, `render_static_pages.py`). Storyline generation is
   intentionally excluded from GitHub Actions.
5. Prune runtime snapshots (processed 45d)
6. Commit + push `data/` + `web/` (triggers Vercel production deploy, whose
   build command rerenders static pages from the committed data)
7. Finish with `FULL_RUN_OK`; website deployment follows the runtime-data push

Daily companions:
- `feed-ops-summary` (12:30 UTC): ops health snapshot
- `feedback-sync` (12:45 UTC): PostHog feedback + CTR sync, auto-tune apply
- GitHub workflow execution: all seven workflows use GitHub-hosted standard
  `ubuntu-latest` runners. The repository is public, so standard hosted runner
  usage is free and unlimited. Each job runs on a fresh x64 VM; publishing no
  longer depends on the owner's Mac or Docker Desktop. The full-publish
  workflow retains a no-push `dry_run` mode. The former self-hosted runner is
  retained only as documented rollback infrastructure under
  `infra/actions-runner/`.
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
  `data/storylines/`, and commits/pushes the result. The two-hour workflow only
  keeps `data/stories/` current as its input.

## Ranking stages (active)
- Stage A: deterministic prefilter (regex excludes, slot freshness windows,
  health floor, `editorial_penalty`, cap to 140)
- Jev gate (after Stage A): four typed questions plus a category choice;
  attaches `judge_score`, `judge_signals`, `judge_category`, `judge_verdict`;
  writes `data/processed/classified.json`
- Stage B: slot assignment — frontier_official, frontier_corporate,
  agent_tooling_releases,
  infra_runtime_releases, vendor_general_updates, practitioner_analysis,
  community_signal, research_watch, overflow
- Stage C: slot scoring/selection — heuristic score (legacy LLM path budgeted
  but disabled), `alpha*score + beta*freshness + source_bias + source_tune +
  topical_bias + judge_weight*judge_score`, then `time_decay_factor`; per-slot
  max and per-source caps
- Global merge: dynamic slot meta-rerank, trim to 24 preserving slot floors;
  discretionary headroom skips judged-low items
- Top-band constraints: composition floors/caps inside the top 10

## Quality judge benchmark (2026-10-24)
- Jev 1.14 via OpenRouter System One is evaluated offline on 50 labeled
  candidates. The hybrid four-question gate (`keep` plus
  `platform_relevant`/`release_lane`/`corporate_marketing`) scores AUC 0.969,
  F1 0.927 at threshold 0.25, Brier 0.095, ECE 0.114, $0.0027 for 50 requests.
- The hybrid judge is wired into the edition builder after Stage A. It fails
  open when `OPENROUTER_API_KEY` is missing; the deterministic policy and
  ranking continue.
- Full report: `docs/status/jev-quality-benchmark-2026-10-24.md`.

## Run health signals (greppable)
- `ranking_stats prefilter=A->B llm_used=N/8 slots=... total=T`
- `judge_stats enabled=1 selected=N judged=N store_hits=N store_misses=N content_fetched=N verdicts=...`
- `FULL_RUN_OK` / `FULL_RUN_NO_DELTA_SKIP=true`
- `runtime_commit_done=true` / `runtime_push_skipped=true`
- `latest_json_valid=true`

## Operational notes
- `run_full.sh` holds a lock (`.run_full.lock`) and skips auto-push when the
  worktree was already dirty (commit-hygiene guard).
- Scheduled bot commits (`chore(data): refresh feed artifacts …`) land on `main`;
  expect to rebase local work.
- The legacy ranking LLM is disabled; the Jev gate is a separate decision
  model and fails open.

## Next tuning levers
- Tune the Jev gate: `config/judge.yaml` rubric, `judge_ranking.weight`,
  `headroom_min_score`, verdict thresholds, category taxonomy, and
  `judgment_store.ttl_days`.
- Re-enable the legacy ranking LLM (`config/llm.yaml -> enabled: true`)
  separately once auth/cost/reliability are settled; budget starts at 8.
- Adjust dynamic slot rerank weights/biases for desired top ordering.
- Tune `time_decay.half_life_hours`, `floor`, and slot overrides if the live
  feed still feels too static or becomes too freshness-biased.
- Tune `auto_tune` caps as reader feedback volume grows.
