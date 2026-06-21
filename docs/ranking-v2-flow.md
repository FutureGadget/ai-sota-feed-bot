# Ranking Flow (Current Production Path)

The unified ranking pipeline lives in `pipeline/ranking.py` and is configured
by `config/ranking.yaml` (historically called "ranking v2"; the v1 path and
the `ranking_v2.yaml` filename are gone — this is the only path).

Config layering: `config/ranking.yaml` names a `preset:` (e.g. `balanced`),
which loads `config/presets/<name>.yaml` as the base; top-level keys in
`ranking.yaml` deep-merge over the preset.

## Quick answer: does `prefilter ... -> 120` mean 120 LLM calls?
No.

- `prefilter=589->120` means **589 raw candidates were reduced to 120
  prefilter candidates** (`candidate_pool_cap: 120`).
- LLM calls are controlled separately by `llm_budget` in `config/ranking.yaml`
  (currently `8`) — and only matter when `config/llm.yaml -> enabled: true`.
- **LLM is currently disabled**, so every item scores via the heuristic
  fallback and zero LLM calls happen regardless of budget.

---

## End-to-end flow

```text
[collectors/collect.py] -> [pipeline/build_tier1.py]
      |
      v
Candidates (TIER0_INPUT=tier1 by default, raw fallback)
      |
      v
Stage A: prefilter (ranking.stage_a_prefilter)
  - title regex excludes (selection.exclude_title_regex)
  - off-topic relevance gate (profile.off_topic): anchored-phrase blocklist
    over title+summary, with a word-boundary platform rescue clause
    (prefilter_reasons.off_topic)
  - per-slot freshness window
  - source health floor
  - cap to candidate_pool_cap (120)
      |
      v
Stage B: slot assignment (ranking.assign_slots)
  - frontier_official
  - agent_tooling_releases
  - infra_runtime_releases
  - vendor_general_updates
  - cloud_platform_updates
  - practitioner_analysis
  - community_signal
  - research_watch
  - overflow
      |
      v
Stage C: in-slot scoring + selection (ranking.stage_c_score_and_select)
  - LLM labeling with llm_budget cap (no-op while LLM disabled)
  - heuristic fallback scoring (the active path today)
  - final slot score = alpha*llm_score + beta*freshness
                       + source_bias + source_tune + topical_bias
    (source_tune = learned feedback/CTR adjustment from
     data/feedback/source_adjustments.json via pipeline/auto_tune.py,
     gated by auto_tune.enabled + max_age_days staleness cutoff)
  - enforce slot max_items and max_per_source
      |
      v
Global merge (ranking.global_merge)
  - dynamic slot meta-rerank (slot priority) when enabled
  - merge slot picks, trim to max_items (24)
  - respect slot minimum floors when trimming
      |
      v
Top-band constraints (ranking.enforce_top_band_constraints)
  - e.g. min frontier_official items and max research items in the top 10
  - lead rule: position 1 is never a research paper when a non-research item
    exists (the best-scoring non-research item is lifted to the lead)
      |
      v
Final feed list (data/processed/latest.json)
      |
      +--> data/digest/YYYY-MM-DD.md
      +--> story store / storylines / static pages (downstream of latest.json)
```

---

## Key config knobs

File: `config/ranking.yaml` (over `config/presets/<preset>.yaml`)

- `preset`: base preset to layer under local overrides
- `candidate_pool_cap`: max items after prefilter stage (140)
- `llm_budget`: max LLM calls for the labeling stage (8; inert while LLM disabled)
- `max_items`: final feed target size before downstream constraints (24)
- `slot_merge_strategy`: `floor_then_dynamic`
- `slots.*.sources / min_items / max_items / max_per_source / freshness_hours`
- `slots.*.blend.alpha / beta` (llm-or-heuristic score vs freshness)
- `dynamic_slot_rerank.*`: slot priority weights and per-slot base bias
- `top_band_constraints.*`: composition floors/caps for the top N
  (incl. `lead_excludes_research`: keep position 1 off niche research papers)
- `source_bias`, `topical_bias`: static score adjustments
- `auto_tune.*`: gates for the learned `source_tune` adjustment

---

## Why a source may not reach the feed (exposure gates)

A source can be collected fine and still never appear. Every item runs this
gauntlet, and any gate can silently drop it. Use the `add-source` skill
(`.agents/skills/add-source/`) and its `validate_source.py` to see exactly
which gate a source dies at.

1. **Collection / health** — the source must be in `config/sources.yaml`, and
   its `source_health` reliability must stay ≥ 0.3 (the circuit breaker can
   disable a flaky source; `prefilter_reasons.health_floor`).
2. **Slot mapping** — a source not listed in any `slots.*.sources` falls into
   the `overflow` slot (base_bias −0.20, `max_items` 3, `freshness_hours` 72)
   and almost never surfaces. **Adding a source to `sources.yaml` is not
   enough — map it to a slot.**
3. **Per-slot freshness window** (`freshness_hours`) — items older than the
   window are dropped (`prefilter_reasons.freshness_window`). Low-volume
   sources can be perpetually stale against a short window.
4. **Candidate pool cap** (`candidate_pool_cap`, 140) — global top-N by
   `freshness + reliability`, where the freshness decay is **slot-scaled**
   (`freshness_hours/3`). Sources in short-window slots (vendor/cloud, 96h)
   decay ~2.5× faster than frontier (240h), so fresher short-window posts can
   be crowded out of the pool by older long-window posts
   (`prefilter_reasons.pool_cap`). This is what hid the Google Cloud OKF post.
5. **Slot caps** (`max_items`, `max_per_source`) — the slot may already be full
   of higher-scored items (`reject_slot_cap` / `reject_source_cap`).
6. **Global merge** (`max_items` 24) — per-slot `min_items` floors are reserved
   first, then remaining capacity fills by `global_score`
   (`final_score + slot_priority`).
7. **Top-band constraints** — frontier/research promotion/demotion can reorder
   (but not drop) the visible top N. Includes the **lead rule**
   (`lead_excludes_research`): the band is sorted by `global_score`, so a fresh
   high-quality arXiv paper can outscore everything and land at position 1; this
   lifts the best-scoring non-research item to the lead instead (only the lead
   moves; no-op when the whole band is research). The daily email renders
   position 1 as a hero, so a niche paper leading is especially costly.

When adding a *new slot*, also add a `dynamic_slot_rerank.base_bias.<slot>`
entry — a missing entry defaults to `0.0`, which is a higher priority than most
existing slots and will over-expose the source.

---

## Runtime logs interpretation

Example:

```text
v2_stats prefilter=589->120 llm_used=0/8 slots=frontier_official:4/... total=24
```

Means:
- 589 raw candidates entered the prefilter
- 120 survived prefilter+cap
- 0 of 8 LLM budget consumed (always 0 while LLM is disabled)
- slot selections shown per slot
- final merged output contains 24 items

---

## Related docs

- Operational snapshot: `docs/status/current-system-state.md`
- Tuning governance: `docs/status/tuning-governance.md`
- Historical plans: `docs/scoring-v2-plan.md`, `docs/scoring-v2-opus-plan.md`
