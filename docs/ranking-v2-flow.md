# Ranking v2 Flow (Current Production Path)

This is the active pipeline after v1 removal.

## Quick answer: does `prefilter ... -> 100` mean 100 LLM calls?
No.

- `prefilter=589->100` means **589 raw candidates were reduced to 100 prefilter candidates** (`candidate_pool_cap: 100`).
- LLM calls are controlled separately by `llm_budget` in `config/ranking_v2.yaml`.
- Current budget is `llm_budget: 8`.

So at most 8 items should trigger fresh LLM calls per run (cache hits can reduce actual API calls further).

---

## End-to-end flow

```text
[collectors/collect.py]
      |
      v
Raw items (e.g. 589)
      |
      v
Stage A: prefilter (ranking_v2.stage_a_prefilter)
  - title regex excludes
  - per-slot freshness window
  - source health floor
  - cap to candidate_pool_cap (100)
      |
      v
Candidates (<=100)
      |
      v
Stage B: slot assignment (ranking_v2.assign_slots)
  - frontier_official
  - agent_tooling_releases
  - practitioner_analysis
  - community_signal
  - research_watch
  - overflow
      |
      v
Stage C: in-slot scoring + selection (ranking_v2.stage_c_score_and_select)
  - LLM labeling v2 with llm_budget cap
  - fallback heuristic when no LLM / budget exhausted
  - final slot score = alpha*llm_score + beta*freshness
  - enforce slot max_items and max_per_source
      |
      v
Global merge (ranking_v2.global_merge)
  - merge slot picks
  - trim to max_items
  - respect slot minimum floors when trimming
      |
      v
Final digest list (data/processed/latest.json)
      |
      +--> data/digest/YYYY-MM-DD.md
      +--> GitHub issue publish
      +--> Telegram publish
```

---

## Key config knobs

File: `config/ranking_v2.yaml`

- `candidate_pool_cap`: max items after prefilter stage
- `llm_budget`: max LLM calls allocated for v2 labeling stage
- `max_items`: final digest target size before downstream constraints
- `slots.*.min_items / max_items`
- `slots.*.max_per_source`
- `slots.*.freshness_hours`
- `slots.*.blend.alpha / beta`

---

## Runtime logs interpretation

Example:

```text
v2_stats prefilter=589->100 llm_used=8/8 slots=frontier_official:4/... total=16
```

Means:
- 589 raw candidates entered v2 prefilter
- 100 survived prefilter+cap
- 8 of 8 LLM budget consumed in this run
- slot selections shown per slot
- final merged output contains 16 items

---

## Related docs

- Plan: `docs/scoring-v2-plan.md`
- Opus implementation plan: `docs/scoring-v2-opus-plan.md`
