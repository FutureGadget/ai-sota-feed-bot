# Scoring v2 — Concrete Implementation Plan

Reference: `docs/scoring-v2-plan.md`

---

## Overview

Replace the current monolithic score-then-constrain pipeline in `build_digest.py` (770 LOC) with a 3-stage architecture: **deterministic prefilter → slot allocation → per-slot LLM scoring + global merge**. The change is gated behind a feature flag and runs in shadow mode before replacing v1.

---

## Phase 0: Scaffolding & Config (estimated: 1 session)

### 0.1 Create `config/ranking_v2.yaml`

New config file with:

```yaml
enabled: false          # feature flag — v1 runs when false
shadow_mode: true       # when enabled=true, also emit v2 alongside v1 (no publish swap)

candidate_pool_cap: 100
llm_budget: 40          # max LLM calls per run
max_items: 20

slots:
  frontier_official:
    sources: [openai_blog, anthropic_engineering, anthropic_newsroom, anthropic_research]
    min_items: 3
    max_items: 5
    max_per_source: 2
    freshness_hours: 72
    blend: {alpha: 0.80, beta: 0.20}

  agent_tooling_releases:
    sources: [openai_codex_releases, claude_code_releases]
    min_items: 1
    max_items: 3
    max_per_source: 1
    freshness_hours: 168        # releases stay relevant longer
    blend: {alpha: 0.70, beta: 0.30}

  practitioner_analysis:
    sources: [simon_willison, latent_space, infoq_ai_ml]
    min_items: 2
    max_items: 4
    max_per_source: 2
    freshness_hours: 120
    blend: {alpha: 0.85, beta: 0.15}

  community_signal:
    sources: [hackernews_ai, search_agent_engineering_news, search_llm_ops_news]
    min_items: 1
    max_items: 3
    max_per_source: 1
    freshness_hours: 48
    blend: {alpha: 0.75, beta: 0.25}

  research_watch:
    sources: [arxiv_cs_ai, arxiv_cs_lg, arxiv_cs_cl, paperswithcode_latest, huggingface_blog]
    min_items: 2
    max_items: 4
    max_per_source: 2
    freshness_hours: 336        # papers can be older
    blend: {alpha: 0.85, beta: 0.15}

  # Catch-all for sources not in any named slot
  overflow:
    sources: []                 # matches anything not claimed above
    min_items: 0
    max_items: 3
    max_per_source: 1
    freshness_hours: 72
    blend: {alpha: 0.75, beta: 0.25}

fallback: deterministic         # if LLM fails: rank by freshness*source_weight inside slot
diagnostics_verbosity: full     # full | summary | off
```

**Files**: new `config/ranking_v2.yaml`

### 0.2 Create new prompt template

Create `config/prompts/label_v2_system.txt` with the v2 rubric (replaces `platform_relevant` bool + `practicality`/`novelty`/`hype` with the 5 new axes).

```
You score AI content for an AI platform engineer daily digest.
Return STRICT JSON only:
{
  "fit_agentic_platform": <1-5>,
  "actionability": <1-5>,
  "novelty": <1-5>,
  "evidence_quality": <1-5>,
  "hype_risk": <1-5>,
  "category": "platform" | "release" | "research",
  "why_1line": "<string, max 120 chars>"
}

Scoring rubric:
- fit_agentic_platform: How relevant to agentic coding, harness/eval, delivery automation, production LLM infra?
- actionability: Can an engineer act on this within a week? Concrete steps, benchmarks, code, architecture?
- novelty: Is this genuinely new information vs rehash?
- evidence_quality: Does it cite benchmarks, code, or reproducible methodology?
- hype_risk: Marketing fluff, vague promises, or unsubstantiated claims? (higher = worse)

Input includes title, summary, source, and optional content_excerpt.
Use content_excerpt when available for deeper signal.
```

**Files**: new `config/prompts/label_v2_system.txt`

### 0.3 Add v2 cache namespace

The v2 labels use a different schema. Use a separate cache file to avoid collisions.

**Files**: `pipeline/llm_label.py` — add `CACHE_FILE_V2 = ROOT / "data" / "llm" / "labels_v2.json"`

---

## Phase 1: Core Pipeline Module (estimated: 2 sessions)

### 1.1 Create `pipeline/ranking_v2.py` (~250-300 LOC)

This is the main new module. It contains the 3 stages and is called from `build_digest.py` when the flag is on.

**Public API**:
```python
def run_v2(items: list[dict], profile: dict, llm_cfg: dict, source_health: dict) -> tuple[list[dict], dict]:
    """Returns (final_digest_items, diagnostics_dict)."""
```

**Internal functions**:

```python
def load_v2_config() -> dict:
    """Load config/ranking_v2.yaml."""

def stage_a_prefilter(items: list[dict], v2_cfg: dict, profile: dict, source_health: dict) -> list[dict]:
    """
    Dedup (reuse existing dedupe()),
    freshness window per slot (source→slot mapping),
    source health floor (drop reliability < 0.3),
    hard excludes from profile.selection.exclude_title_regex.
    Returns candidate pool, capped at candidate_pool_cap.
    """

def assign_slots(candidates: list[dict], v2_cfg: dict) -> dict[str, list[dict]]:
    """
    Map each candidate to its slot by source name.
    Items whose source isn't in any named slot → 'overflow'.
    Sort each slot's candidates by source_weight * freshness (deterministic tiebreak).
    """

def stage_c_score_and_select(
    slotted: dict[str, list[dict]],
    v2_cfg: dict,
    llm_cfg: dict,
    remaining_budget: int,
) -> tuple[list[dict], dict]:
    """
    For each slot:
      1. If LLM budget remaining > 0: call label_items_v2() on slot candidates.
      2. Compute final_slot_score = alpha*llm_score + beta*freshness.
      3. Select top items within [min_items, max_items] respecting max_per_source.
      4. If LLM fails or budget exhausted: fallback to deterministic sort.
    Returns (all selected items across slots, diagnostics).
    """

def global_merge(slot_selections: dict[str, list[dict]], max_items: int) -> list[dict]:
    """
    Merge all slot outputs. If total > max_items, trim lowest-scored items
    while respecting each slot's min_items floor.
    Final sort by final_slot_score descending.
    """

def compute_llm_score(labels: dict) -> float:
    """0.40*fit + 0.25*actionability + 0.20*novelty + 0.15*evidence - 0.25*max(0, hype-3)"""
```

**Files**: new `pipeline/ranking_v2.py`

### 1.2 Add `label_items_v2()` to `pipeline/llm_label.py`

New function alongside existing `label_items()`. Differences:
- Uses `label_v2_system.txt` prompt
- Uses `CACHE_FILE_V2` (separate cache namespace)
- Returns the 5-axis schema instead of the v1 schema
- Heuristic fallback returns the new schema with reasonable defaults
- Accepts an explicit `budget` param and stops calling LLM once exhausted

```python
def heuristic_label_v2(item: dict) -> dict:
    """Same keyword heuristics but returns v2 schema."""

def label_items_v2(items: list[dict], budget: int = 40) -> dict[str, dict]:
    """Label items with v2 rubric. Stops after `budget` LLM calls."""
```

**Files**: `pipeline/llm_label.py` — add ~60 LOC (new functions + v2 cache constant)

### 1.3 Wire v2 into `build_digest.py`

At the end of `run()`, after the existing pipeline produces its output, add a conditional v2 path:

```python
# --- existing v1 code ends, digest written ---

# v2 shadow / replacement
from ranking_v2 import run_v2, load_v2_config
v2_cfg = load_v2_config()
if v2_cfg.get("enabled", False):
    v2_items, v2_diag = run_v2(items_deduped, profile, llm_cfg, source_health)
    # Write v2 output
    (processed_dir / "latest_v2.json").write_text(json.dumps(v2_items, ...))
    (digest_dir / f"{date_str}_v2.md").write_text(render_digest(v2_items, date_str))
    (ROOT / "data" / "diagnostics" / f"{date_str}_v2.json").write_text(json.dumps(v2_diag, ...))

    if not v2_cfg.get("shadow_mode", True):
        # v2 replaces v1 for publishing
        top = v2_items
```

Key detail: `items_deduped` — we need to save the deduped items list before v1 scoring mutates them. Add `items_deduped = list(items)` right after the `dedupe()` call.

**Files**: `pipeline/build_digest.py` — ~25 LOC addition at bottom of `run()`

---

## Phase 2: Diagnostics & Observability (estimated: 1 session)

### 2.1 Diagnostics output

`ranking_v2.py` already returns a `diagnostics` dict. Structure:

```json
{
  "prefilter_in": 450,
  "prefilter_out": 98,
  "prefilter_reasons": {"freshness_window": 280, "health_floor": 12, "hard_exclude": 5, "pool_cap": 55},
  "slots": {
    "frontier_official": {
      "candidates": 12, "llm_scored": 8, "cache_hits": 4, "llm_called": 4, "llm_failed": 0,
      "selected": 4, "fallback_used": false
    },
    ...
  },
  "llm_budget_total": 40,
  "llm_budget_used": 22,
  "global_merge_trimmed": 3,
  "freshness_p50_hours": 14.2,
  "freshness_p90_hours": 42.1
}
```

**Files**: `pipeline/ranking_v2.py` (built into Stage C), new `data/diagnostics/` directory

### 2.2 Print summary to stdout

For GitHub Actions log readability, emit a one-liner:

```
v2_stats prefilter=450→98 llm_used=22/40 cache_hits=18 slots=frontier:4/5 agent:2/3 pract:3/4 community:2/3 research:3/4 overflow:1/3 total=15→20
```

**Files**: `pipeline/ranking_v2.py` — `print_summary(diag)` helper

---

## Phase 3: Shadow Comparison Tooling (estimated: 1 session)

### 3.1 Create `scripts/compare_v1_v2.py`

Reads `data/processed/latest.json` (v1) and `data/processed/latest_v2.json` (v2) and prints:
- Top-20 overlap count and Jaccard
- Items unique to v1 / v2 (with scores)
- Source distribution comparison
- Category distribution comparison
- Average freshness comparison

**Files**: new `scripts/compare_v1_v2.py` (~80 LOC)

### 3.2 Add comparison step to daily-digest workflow

After the build step, if v2 files exist, run comparison:

```yaml
- name: Compare v1 vs v2 (shadow)
  run: |
    if [ -f data/processed/latest_v2.json ]; then
      python scripts/compare_v1_v2.py || true
    fi
```

**Files**: `.github/workflows/daily-digest.yml` — add 1 step

---

## Phase 4: Tests (estimated: 2 sessions)

### 4.1 Unit tests — `tests/test_ranking_v2.py`

| Test | What it validates |
|------|-------------------|
| `test_prefilter_respects_pool_cap` | Output ≤ candidate_pool_cap |
| `test_prefilter_drops_stale_items` | Items beyond slot freshness_hours are excluded |
| `test_prefilter_drops_unhealthy_sources` | Items with reliability < 0.3 dropped |
| `test_assign_slots_all_sources_mapped` | Every source lands in exactly one slot |
| `test_assign_slots_overflow` | Unknown sources go to overflow |
| `test_slot_min_max_respected` | Each slot output within [min, max] |
| `test_source_cap_within_slot` | No source exceeds max_per_source in any slot |
| `test_llm_score_formula` | Verify `compute_llm_score` math against known inputs |
| `test_global_merge_respects_min_floors` | Trimming doesn't go below slot min_items |
| `test_global_merge_total_cap` | Output ≤ max_items |
| `test_deterministic_fallback` | When LLM disabled, produces valid output |
| `test_budget_exhaustion` | After N calls, remaining items get heuristic labels |

### 4.2 Unit tests — `tests/test_llm_label_v2.py`

| Test | What it validates |
|------|-------------------|
| `test_heuristic_v2_returns_correct_schema` | All 5 axes + category + why_1line present |
| `test_heuristic_v2_platform_keyword_detection` | Keywords boost fit_agentic_platform |
| `test_label_items_v2_budget_limit` | Stops LLM calls at budget |
| `test_v2_cache_isolation` | v2 cache doesn't collide with v1 cache |

### 4.3 Integration / E2E test — `tests/test_e2e_v2.py`

Uses real raw data from `data/raw/` (latest day) with LLM disabled:

```python
def test_e2e_v2_deterministic():
    """Full pipeline run with ranking_v2.enabled=true, LLM disabled.
    Asserts:
    - Output file written to data/processed/latest_v2.json
    - Diagnostics file written
    - Item count within [sum(slot.min), max_items]
    - All items have required fields (title, url, score, slot, category)
    - No duplicate URLs in output
    - Source diversity: no single source > max_per_source items
    """
```

```python
def test_e2e_v2_shadow_mode():
    """With shadow_mode=true, both v1 and v2 outputs are produced.
    Asserts:
    - latest.json (v1) and latest_v2.json (v2) both exist
    - latest.json unchanged from v1-only run (shadow doesn't affect v1)
    """
```

### 4.4 Test infrastructure

**Files**: new `tests/conftest.py` with fixtures:
- `sample_items()` — 50 synthetic items across all source types
- `v2_config()` — test config with small budgets
- `mock_llm_labels()` — predetermined labels for deterministic testing

**Files**: `requirements.txt` — add `pytest` (dev dependency)

---

## Phase 5: Cutover (estimated: 1 session, after 3-5 days shadow)

### 5.1 Enable v2 publish

```yaml
# config/ranking_v2.yaml
enabled: true
shadow_mode: false    # v2 output replaces v1 for publishing
```

### 5.2 Remove v1 constraint functions

Once v2 is stable, remove from `build_digest.py`:
- `balanced_select()` (~60 LOC)
- `apply_source_cap()` (~35 LOC)
- `apply_preferred_source_slots()` (~40 LOC)
- `apply_constrained_topk()` (~80 LOC)
- `apply_top_guardrails()` (~50 LOC)
- `enforce_source_floor()` (~30 LOC)
- `apply_topk_source_mix()` (~50 LOC)
- `apply_category_allocation()` (~65 LOC)

Total: ~410 LOC removed. The `run()` function shrinks from ~200 LOC to ~50 LOC (load → dedupe → score → call v2 → write).

### 5.3 Deprecate v1 config keys

Move the `selection.*` block in `profile.yaml` under a `# DEPRECATED — v1 only` comment. Remove after one release cycle.

---

## Risk Points & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| **LLM budget blowup** (slow/expensive) | Digest delayed, cost spike | Hard cap in v2_cfg.llm_budget; per-slot budgets proportional; deterministic fallback on exhaust |
| **Slot starvation** (slot has 0 candidates) | Missing diversity | Prefilter checks slot coverage; overflow slot catches unmatched sources; min_items=0 for community/overflow |
| **v2 output quality regression** | User sees worse digest | Shadow mode comparison for 3-5 days; manual review before cutover; instant rollback = set `enabled: false` |
| **Cache schema mismatch** | Stale v1 labels reused for v2 | Separate cache file (`labels_v2.json`); version hash includes prompt+rubric |
| **Source-to-slot mapping drift** | New sources unhandled | Overflow slot catches all; `assign_slots` logs unmapped sources as diagnostic warning |
| **Freshness window too aggressive** | Good items filtered out | Per-slot configurable freshness_hours; generous defaults (48h-336h); prefilter logs rejection reasons |

### Rollback Plan

1. **Instant** (< 1 min): Set `config/ranking_v2.yaml` → `enabled: false`. Next run uses v1.
2. **Shadow revert**: Set `shadow_mode: true`. Both outputs produced, only v1 publishes.
3. **Full revert**: `git revert` the `build_digest.py` wiring commit. All v2 code is in separate files and inert.

---

## File Change Summary

| File | Action | LOC (approx) |
|------|--------|---------------|
| `config/ranking_v2.yaml` | **NEW** | 45 |
| `config/prompts/label_v2_system.txt` | **NEW** | 20 |
| `pipeline/ranking_v2.py` | **NEW** | 280 |
| `pipeline/llm_label.py` | EDIT (add v2 functions) | +60 |
| `pipeline/build_digest.py` | EDIT (wire v2 at end of run()) | +25 |
| `scripts/compare_v1_v2.py` | **NEW** | 80 |
| `.github/workflows/daily-digest.yml` | EDIT (add comparison step) | +5 |
| `tests/conftest.py` | **NEW** | 60 |
| `tests/test_ranking_v2.py` | **NEW** | 200 |
| `tests/test_llm_label_v2.py` | **NEW** | 80 |
| `tests/test_e2e_v2.py` | **NEW** | 80 |
| `requirements.txt` | EDIT (add pytest) | +1 |
| **Total new code** | | **~940** |

Phase 5 cleanup removes ~410 LOC from `build_digest.py`, netting ~+530 LOC.

---

## Implementation Order (dependency graph)

```
Phase 0 (config + prompt)
    │
    ▼
Phase 1.2 (llm_label v2 functions)
    │
    ▼
Phase 1.1 (ranking_v2.py core) ──→ Phase 2 (diagnostics, built-in)
    │
    ▼
Phase 1.3 (wire into build_digest.py)
    │
    ├──→ Phase 3 (shadow comparison tooling)
    │
    └──→ Phase 4 (tests)
            │
            ▼
        Phase 5 (cutover, after shadow validation)
```

Phases 0-2 can land in a single PR. Phase 3 and 4 can be a second PR. Phase 5 is config-only + cleanup PR.

---

## Open Decisions (defaults provided, tunable via config)

| Question | Default | Rationale |
|----------|---------|-----------|
| Slot min/max for 20-item digest | See config above (sum min=9, sum max=22) | Leaves room for overflow; merge trims to 20 |
| Freshness windows | 48h-336h per slot | Releases/research stay relevant longer |
| Community slot eligibility | Mid-rank (not forced into top-3) | HN/search feeds are noisy; let score decide |
| Hard regex excludes | Keep as-is from profile.yaml | Low maintenance; soft penalty adds complexity for little gain |
| Overflow slot | Enabled with max_items=3 | Catches google_ai, aws_ml, nvidia, llamaindex, langgraph, etc. |
