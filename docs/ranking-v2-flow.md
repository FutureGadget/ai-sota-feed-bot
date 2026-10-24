# Ranking Flow (Current Production Path)

The unified ranking pipeline lives in `pipeline/ranking.py` and is configured
by `config/ranking.yaml` (historically called "ranking v2"; the v1 path and
the `ranking_v2.yaml` filename are gone — this is the only path).

Config layering: `config/ranking.yaml` names a `preset:` (e.g. `balanced`),
which loads `config/presets/<name>.yaml` as the base; top-level keys in
`ranking.yaml` deep-merge over the preset.

## Quick answer: does `prefilter ... -> 140` mean 140 LLM calls?
No.

- `prefilter=589->140` means **589 raw candidates were reduced to 140
  prefilter candidates** (`candidate_pool_cap: 140`).
- The Jev gate runs on that Stage A pool after the prefilter. It can make up to
  140 decisions, but the durable judgment store
  (`data/processed/judgments.json`) is checked first, so unchanged candidates
  make no API call. Only missing or expired entries call Jev.
- The legacy ranking LLM is separate and still disabled
  (`config/llm.yaml -> enabled: false`). Its `llm_budget: 8` is inert; the Jev
  gate has its own `openrouter.max_items`, `max_workers`, and time budget.

---

## End-to-end flow

```text
[collectors/collect.py] -> data/raw/<date>/items.json
  - per-source title blocklist (sources.yaml `exclude_title_regex`) drops
    matches before they reach data/raw (`excluded_title` in ingest_runs.jsonl)
      |
      v
Editorial policy (pipeline/editorial.py, config/editorial.yaml)
  - source roles: first_party / practitioner / aggregator / community / search
  - search quarantine: business/gossip/SEO patterns, title-only engineering
    rescue, at most 2 candidates per query
  - first-party quarantine: ads/customer stories/partnerships/appointments,
    title-only engineering rescue
  - story clusters: one representative per event, with also_covered echoes
  - seen-memory: recent processed editions retire repeats and add an
    editorial_penalty to the rest
  - writes data/processed/editorial.json for the feed/RSS APIs
      |
      v
Stage A: prefilter (ranking.stage_a_prefilter)
  - `editorial_penalty` is subtracted from the prefilter score
  - title regex excludes (selection.exclude_title_regex)
  - positive relevance floor (profile.relevance_floor): for the mixed-topic
    sources listed there, title+summary (HTML and URLs stripped) must carry at
    least one AI/ML keyword (prefilter_reasons.no_topic_signal). Opt-in per
    source: a dedicated source's terse release notes carry no keyword at all.
  - off-topic relevance gate (profile.off_topic): anchored-phrase blocklist
    over title+summary, with a word-boundary platform rescue clause
    (prefilter_reasons.off_topic)
  - per-slot freshness window
  - source health floor
  - reserve up to each configured source's `max_per_source` candidates
    (`candidate_pool_coverage`)
  - fill the remaining pool by prefilter score up to `candidate_pool_cap` (140)
      |
      v
Jev gate + category (pipeline/editorial_judge.py, config/judge.yaml)
  - runs on the Stage A candidate pool, not raw items and not the final 24
  - fetches paragraph excerpts for candidates whose feed teaser is too short
  - one OpenRouter System One request per item:
      keep, platform_relevant, release_lane, corporate_marketing (noul)
      category (choice with criteria)
  - hybrid score: `keep` is primary; release/marketing highs and low
    platform relevance clamp it; the category and verdict are joined into the
    editor-deck input bundles by `pipeline/deck_quality.py`
  - durable judgment store `data/processed/judgments.json`, keyed by item
    identity + model + rubric + prompt fingerprint; only missing or expired
    items call Jev
  - fail-open: missing key, timeout, or malformed response leaves the item
    unjudged and the deterministic ranking continues
  - writes data/processed/classified.json (compact, committed) and
    data/quality/classified/<date>.json (full local pool)
      |
      v
Stage B: slot assignment (ranking.assign_slots)
  - frontier_official (engineering/research voices)
  - frontier_corporate (newsroom/policy/partnership, max 1)
  - agent_tooling_releases
  - infra_runtime_releases
  - open_weight_releases
  - vendor_general_updates
  - cloud_platform_updates
  - practitioner_analysis
  - community_signal
  - research_watch
  - overflow
      |
      v
Stage C: in-slot scoring + selection (ranking.stage_c_score_and_select)
  - legacy ranking LLM labeling (off; `llm_budget` inert)
  - heuristic scoring for the deterministic features
  - judge_score adds a continuous semantic weight
  - pre-decay score = alpha*llm_score + beta*freshness
                      + source_bias + source_tune + topical_bias
                      - editorial_penalty
                      + judge_weight * judge_score
    (source_tune = learned feedback/CTR adjustment from
     data/feedback/source_adjustments.json via pipeline/auto_tune.py,
     gated by auto_tune.enabled + max_age_days staleness cutoff)
  - final slot score = pre-decay score * time_decay_factor
    (`time_decay_factor` is a smooth half-life multiplier from
    `time_decay.*`, with optional per-slot overrides and a floor)
  - enforce slot max_items and max_per_source
      |
      v
Global merge (ranking.global_merge)
  - dynamic slot meta-rerank (slot priority) when enabled
  - merge slot picks, trim to max_items (24)
  - respect slot minimum floors when trimming
  - `editorial_caps.max_search_items` caps the search signal across slots
  - headroom skips judged-low items (`judge_ranking.headroom_min_score`) and
    low off-topic categories unless the slot floor still needs a candidate
      |
      v
Top-band constraints (ranking.enforce_top_band_constraints)
  - e.g. min frontier_official items and max research items in the top 10
  - `min_anthropic_frontier` now counts only frontier_official (engineering);
    frontier_corporate cannot satisfy it
  - promotion skips `judge_verdict: drop` and low-score candidates
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

## Editorial policy (pre-ranking)

File: `config/editorial.yaml`, implementation: `pipeline/editorial.py`.

This is deterministic bookkeeping, not the LLM ranking layer:

- `source_roles` / `source_role_prefixes`: classify every source. Search
  queries are quarantined; first-party blogs get a marketing filter; practitioner
  and release sources keep their own caps.
- `search_quarantine`: drops obvious gossip/business/SEO titles from search
  results unless the title carries a concrete engineering signal.
- `first_party_quarantine`: drops ads, customer stories, partnerships, and
  appointments from first-party blogs unless the title carries an engineering
  signal.
- `story_clusters`: collapses the same event reported under different headlines
  into one representative and records the echoes in `also_covered`.
- `seen.max_editions`: retires an item after a bounded number of recent
  editions; `editorial_penalty` softens the rest. `source_overrides` gives
  corporate newsroom posts a shorter run.
- `caps` / `role_totals`: the per-source and per-role caps the API applies to
  its accumulated run pool.

The pipeline writes `data/processed/editorial.json` (roles, caps, quarantine
patterns, diagnostics) so `api/feed.js` and `api/rss.js` apply the same policy
without a YAML parser. `data/processed/**` is already bundled into the feed
function.

## Key config knobs

File: `config/ranking.yaml` (over `config/presets/<preset>.yaml`)

- `preset`: base preset to layer under local overrides
- `candidate_pool_cap`: normal max items after prefilter stage (140); source
  coverage reserves can make the pool larger only when their configured reserve
  cannot fit inside this value
- `candidate_pool_coverage.enabled`: preserve configured source representation
  before the global cap (true in production)
- `candidate_pool_coverage.per_source`: optional fixed reserve per source;
  omitted means each slot's `max_per_source`
- `llm_budget`: legacy ranking LLM calls (8; inert while `config/llm.yaml` is disabled)
- `judge_ranking.weight`: continuous Stage A/C judge-score weight
- `judge_ranking.headroom_min_score`: minimum judge score for discretionary headroom
- `judge_ranking.headroom_drop_categories` / `headroom_category_min_score`:
  stronger bar for off-topic categories
- `judge_gate.enabled`: optional hard drop (off by default; release items exempt)
- `max_items`: final feed target size before downstream constraints (24)
- `slot_merge_strategy`: `floor_then_dynamic`
- `slots.*.sources / min_items / max_items / max_per_source / freshness_hours`
- `slots.*.blend.alpha / beta` (llm-or-heuristic score vs freshness)
- `time_decay.*`: smooth age-down multiplier applied after normal Stage C
  scoring (`half_life_hours`, `floor`, `start_after_hours`, optional
  `slot_overrides`)
- `dynamic_slot_rerank.*`: slot priority weights and per-slot base bias
- `top_band_constraints.*`: composition floors/caps for the top N
  (incl. `lead_excludes_research`: keep position 1 off niche research papers)
- `source_bias`, `topical_bias`: static score adjustments
- `auto_tune.*`: gates for the learned `source_tune` adjustment

### Jev gate knobs (`config/judge.yaml`)

- `enabled`: gate on/off; fail-open without `OPENROUTER_API_KEY`
- `openrouter.model`, `endpoint`, `api_key_env`: OpenRouter System One target
- `openrouter.questions`: `keep`, `platform_relevant`, `release_lane`,
  `corporate_marketing`, plus the `category` choice
- `openrouter.hybrid`: primary score and gate thresholds
- `content_fetch.*`: paragraph-fetch budget for short teasers
- `judgment_store.path`, `ttl_days`, `max_entries`: durable judgment reuse
- `ranking.drop_below`, `keep_at`, `max_drop_share`: verdict thresholds and
  the batch safety cap

---

## Why a source may not reach the feed (exposure gates)

A source can be collected fine and still never appear. Every item runs this
gauntlet, and any gate can silently drop it. Use the `add-source` skill
(`.agents/skills/add-source/`) and its `validate_source.py` to see exactly
which gate a source dies at.

1. **Collection / health** — the source must be in `config/sources.yaml`, and
   its `source_health` reliability must stay ≥ 0.3 (the circuit breaker can
   disable a flaky source; `prefilter_reasons.health_floor`). A source-scoped
   `exclude_title_regex` (used where only a site-wide feed exists, e.g.
   `databricks_blog`) drops matching titles here, before `data/raw` — so an
   item filtered at this gate never appears in any later diagnostic.
2. **Slot mapping** — a source not listed in any `slots.*.sources` falls into
   the `overflow` slot (base_bias −0.20, `max_items` 3, `freshness_hours` 72)
   and almost never surfaces. **Adding a source to `sources.yaml` is not
   enough — map it to a slot.**
3. **Per-slot freshness window** (`freshness_hours`) — items older than the
   window are dropped (`prefilter_reasons.freshness_window`). Low-volume
   sources can be perpetually stale against a short window.
4. **Candidate pool cap** (`candidate_pool_cap`, 140) — reserve each configured
   source's Stage C capacity first, then fill the remaining pool by global
   `freshness + reliability` score. The freshness decay is **slot-scaled**
   (`freshness_hours/3`). Sources in short-window slots (vendor/cloud, 96h)
   decay ~2.5× faster than frontier (240h), so fresher short-window posts can
   be crowded out of the pool by older long-window posts
   (`prefilter_reasons.pool_cap`). `pool_coverage_reserved` reports the
   reserved count. This prevents an individual source from disappearing before
   its source and topical scoring signals are applied.
5. **Slot caps** (`max_items`, `max_per_source`) — the slot may already be full
   of higher-scored items (`reject_slot_cap` / `reject_source_cap`).
6. **Time decay** (`time_decay`) — after normal relevance/source/topic scoring,
   older items are multiplied down by a smooth half-life factor. This lets the
   7-day live feed remain available while repeated two-hour builds gradually make
   room for newer stories. Strong evergreen items can still compete above the
   configured floor, but they no longer keep their day-one score all week.
7. **Global merge** (`max_items` 24) — per-slot `min_items` floors are reserved
   first, then remaining capacity fills by `global_score`
   (`final_score + slot_priority`).
8. **Top-band constraints** — frontier/research promotion/demotion can reorder
   (but not drop) the visible top N. Includes the **lead rule**
   (`lead_excludes_research`): the band is sorted by `global_score`, so a fresh
   high-quality arXiv paper can outscore everything and land at position 1; this
   lifts the best-scoring non-research item to the lead instead (only the lead
   moves; no-op when the whole band is research). The daily email renders
   position 1 as a hero, so a niche paper leading is especially costly.

### Content-thin feeds (`fetch_content`)

Several of these gates score an item's **rendered text** — `relevance_floor`
(gate 1's opt-in allowlist) and the `heuristic_label` token counts that produce
`llm_score` while the ranking LLM is disabled. A feed that publishes a
one-line teaser gives them almost nothing to read: archerhume's "I probed Jev
with 10,000 API calls" names no AI vocabulary at all, so a post about
transformer serving architecture floored at `llm_score` 2.0 and would have
failed `relevance_floor` outright. The Jev gate also needs real article text
and fetches paragraph excerpts for short teasers before judging.

Setting `fetch_content: true` on a source in `config/sources.yaml` makes the
collector fetch each item's page and store up to 4000 characters of body text
as `content_excerpt`. Opt-in per source, never global — it is a network fetch
per item, and a feed that already carries full content gains nothing.

Two asymmetries keep the excerpt from moving anything it shouldn't:

- **Positive signals only.** It raises `fit_agentic_platform` and
  `evidence_quality`, and can rescue an item at `relevance_floor` (an
  allowlist). It is deliberately *not* fed to `off_topic` or `topical_bias`'s
  negative keywords, nor to `hype_risk` or `novelty` — a penalty sourced from a
  passing mention in the body is a false positive, and "new" appears in almost
  any 1200 characters of prose.
- **Whole-word matching.** Title and summary keep their historical substring
  match; the excerpt is matched whole-word, so "decoder" in the body is not
  evidence of "code". Same failure `relevance_floor` was fixed for.

Page boilerplate can defeat the excerpt in the other direction. Kun Chen's
Substack prints his bio ("...field notes about frontier agentic engineering")
on every post, so his Nix and career posts would pass `relevance_floor` on the
bio alone. A source can list `content_exclude_regex` patterns in
`config/sources.yaml`; the collector removes matches from the excerpt before
storing it.

An item with no `content_excerpt` scores exactly as it did before the feature
existed, so enabling it for one source cannot move another's ranking.

When adding a *new slot*, also add a `dynamic_slot_rerank.base_bias.<slot>`
entry — a missing entry defaults to `0.0`, which is a higher priority than most
existing slots and will over-expose the source.

---

## Runtime logs interpretation

Example:

```text
ranking_stats prefilter=589->140 llm_used=0/8 slots=frontier_official:4/... total=24
```

Means:
- 589 raw candidates entered the prefilter
- 140 survived prefilter+cap
- 0 of 8 legacy ranking LLM budget consumed (always 0 while it is disabled);
  Jev calls are reported separately as `judge_stats ...`
- slot selections shown per slot
- final merged output contains 24 items

---

## Related docs

- Operational snapshot: `docs/status/current-system-state.md`
- Tuning governance: `docs/status/tuning-governance.md`
- Historical plans: `docs/scoring-v2-plan.md`, `docs/scoring-v2-opus-plan.md`
