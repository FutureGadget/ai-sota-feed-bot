# Scoring v2 Plan (freshness-first + sloted LLM ranking)

## 1) Goals
- Improve ranking quality for **agentic coding / harness / eval / delivery automation**.
- Keep **freshness explicit** (not hidden in a large mixed formula).
- Keep **slot guarantees** for source diversity and strategic coverage.
- Bound LLM cost/context while scaling digest size later.
- Reduce conflicting constraints and make decisions easier to explain.

## 2) Non-goals
- No full-corpus LLM ranking (too expensive/slow today).
- No real-time adaptive learning loop in v2 (feedback loop removed for now).

## 3) Pipeline architecture (v2)

### Stage A — Deterministic prefilter (cheap)
Input: deduped raw items.

Apply:
1. Dedup (URL + near-title).
2. Freshness window by slot/source type.
3. Source health floor (drop only severe degraded sources).
4. Lightweight hard excludes (regex allowlist/denylist as needed).

Output: candidate pool (target cap: 80–120 items).

### Stage B — Slot allocation (deterministic)
Allocate candidates into fixed slots with min/max quotas.

Proposed slots:
- `frontier_official` (OpenAI/Anthropic official blogs/newsroom/engineering)
- `agent_tooling_releases` (Codex/Claude Code and similar)
- `practitioner_analysis` (Simon, Latent, InfoQ)
- `community_signal` (HN + search feeds)
- `research_watch` (arXiv + frontier research pages)

Per-slot controls:
- `min_items`, `max_items`
- per-source cap
- freshness override (optional)
- optional priority source list

### Stage C — LLM scoring in-slot + global rerank
For each slot, run LLM scoring only on its candidates (budgeted).

LLM output schema (strict JSON):
- `fit_agentic_platform` (1-5)
- `actionability` (1-5)
- `novelty` (1-5)
- `evidence_quality` (1-5)
- `hype_risk` (1-5)
- `category` (platform|release|research)
- `why_1line` (<=120 chars)

Compute slot score:
- `llm_score = 0.40*fit + 0.25*actionability + 0.20*novelty + 0.15*evidence_quality - 0.25*max(0,hype_risk-3)`
- `final_slot_score = alpha*llm_score + beta*freshness_score`

Default blend:
- frontier_official: `alpha=0.80`, `beta=0.20`
- agent_tooling_releases: `alpha=0.70`, `beta=0.30`
- practitioner_analysis: `alpha=0.85`, `beta=0.15`
- community_signal: `alpha=0.75`, `beta=0.25`
- research_watch: `alpha=0.85`, `beta=0.15`

Select top items per slot by `final_slot_score`, then global merge/rerank over selected set.

## 4) Constraints (keep minimal)
Hard constraints to keep:
- `max_per_source`
- slot min/max
- optional top-k release cap

Drop/avoid overlapping constraints that fight each other.

## 5) Cost and latency budget
- Candidate pool cap: 100 (default).
- LLM scoring cap: 40 items/run (default).
- Cache by item id/url + prompt version + source fingerprint + rubric version.
- If LLM budget exceeded: deterministic fallback inside slot.

## 6) Diagnostics required per run
Emit machine-readable stats:
- `prefilter_in`, `prefilter_out`
- per-slot candidate count / scored count / selected count
- LLM `cache_hit`, `llm_called`, `llm_failed`, fallback count
- freshness percentile in final top N
- reject reasons (`source_cap`, `slot_full`, `low_score`, etc.)

## 7) Config surface (new)
Create `config/ranking_v2.yaml`:
- `enabled`
- global budgets (`candidate_pool_cap`, `llm_budget`, `max_items`)
- slot definitions and blends
- fallback behavior
- diagnostics verbosity

## 8) Rollout plan (safe)
1. Implement under feature flag `ranking_v2.enabled=false`.
2. Add shadow mode: produce v2 output file without publishing.
3. Compare v1 vs v2 for 3–5 days:
   - top-20 overlap
   - source/category distribution
   - subjective relevance check
4. Enable v2 publish once stable.

## 9) Acceptance criteria
- Digest ranking judged better by user over at least 3 consecutive days.
- No major run hangs under default budget.
- LLM cost remains bounded and predictable.
- Output remains diverse without manual firefighting.

## 10) Open questions (for final tuning)
- Final slot min/max numbers for 20-item digest.
- Exact freshness windows per slot (e.g., releases 7d, practitioner 5d, research 14d).
- Whether `community_signal` should be top-order eligible or always mid/lower section.
- Whether to keep hard regex excludes or convert to soft penalties.
