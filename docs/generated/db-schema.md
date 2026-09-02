# Data Schema (File-Based Store)

There is no database. All persistent state is versioned JSON/JSONL/Markdown
under `data/`, committed to git by the pipeline. This file documents the
layout (the de-facto "schema"). Vercel serverless functions in `api/` read
these files directly — only paths listed in `vercel.json` `includeFiles` are
available to each function.

## Ingestion
- `data/raw/<YYYY-MM-DD>/items.json` — collector output for the day
  (normalized items: url, title, source, published, summary, …). Google News
  RSS entries may also carry optional `publisher_name` and `publisher_domain`
  values copied from the entry's `<source>` element. These are external display
  strings, not verified identity claims, and renderers must escape them.
- `data/cache/sitemap_meta.json` — sitemap crawl metadata cache

## Ranked snapshots
- `data/tier1/latest.json` — fast quick-score snapshot (no LLM)
- `data/tier1/runs/<Y>/<M>/<run_id>.json` + `data/tier1/runs_index.json`
  — per-run history (**3-day hard cap**, no archive tail; these are ~1.5 MB
  each and bundled into the Vercel feed/rss functions, which only read tier1
  for a 24h fresh-blend overlay)
- `data/processed/latest.json` — the production feed (Tier-0 full ranking).
  Ranked items include score diagnostics such as `llm_score`, `source_bias`,
  `source_tune`, `topical_bias`, `pre_decay_score`, `time_decay_factor`,
  `final_score`, `slot_priority`, and `global_score`. Optional
  `publisher_name` and `publisher_domain` attribution fields pass through from
  collector rows for Google News items.
- `data/processed/runs/<Y>/<M>/<run_id>.json` + `runs_index.json`
  — per-run history (retention ~45d)

## Feed API (`/api/feed`)
Response fields served from the accumulated ranked pool above:
- `label_counts` - per-section story counts for the homepage tabs:
  `{brief, platform, research, release, news}` (present on both the normal
  history path and the no-runs `mode: "latest"` fallback). Each value counts
  items inside the request's publish window matching that one section lens
  (`brief` = everything except releases, mirroring the default tab), computed
  from the same pool as `items` before any reader-selected `label=` filter is
  applied - so tabs show what each section WOULD hold. Reflects the date
  window only, never search or client-side state.
- `items[].also_covered` - up to 4 cross-source coverage entries
  `{source, url, title<=160}` per item, deduped by (source, normalized URL
  sans query/trailing slash), same-source and self-referencing entries
  excluded. Two sources feed it: pipeline enrichment (`pipeline/enrich.py`,
  max 4, excludes arxiv<->arxiv pairs) and server-side normalized-title
  clustering (`api/feed.js::clusterCoverage`) over the cached run pool -
  groups of 2-8 items sharing a normalized title of >=30 chars across >=2
  distinct sources (arxiv<->arxiv excluded there too), candidates sorted by
  `v2_final_score ?? score_at_last_seen ?? score`. The cluster merge happens
  only on the English path, AFTER the localized (ko) snapshot overlay: the
  overlay's `source_hash` pins pooled items' own `also_covered`
  (tests/test_feed_api.mjs), so clustered entries must never leak into that
  hash or into the pooled objects themselves.

## Digest + publishing
- `data/digest/<YYYY-MM-DD>.md` — versioned daily digest markdown

## Durable reader-facing stores
- `data/stories/<YYYY-MM>.json` — append-only story store keyed by
  `sid = sha256(normalized url)[:16]`; `data/stories/index.json` is the
  compact index bundled into the share endpoint
- `data/storylines/<slug>.json` + `index.json` — cross-day threads. When an
  agent-written narrative exists, `build_storylines.py` overlays an `editorial`
  block (`tldr` / `whats_new` / `why_it_matters` / `stale`) onto the detail file
  and a `{tldr, stale}` teaser onto the index row, plus a per-item `editor_note`
- `data/storylines/narratives/<slug>.json` — durable agent-written narrative
  sidecar (the editorial source of truth; never written by the pipeline, only
  overlaid). Carries a `covers_last_updated` + `covers_member_sids` staleness
  snapshot. Written by the `storyline-editor` routine
- `data/storylines/input/latest.json` — bundle of storylines needing a narrative
  (new or stale), each with its timeline and prior narrative; what the agent
  reads on the inline path (excluded from deploys)
- `data/storylines/input/manifest.json` — the same rows without timelines or
  prior narratives (slug, label, counts, reason, `input_path`); what a fan-out
  orchestrator reads instead of `latest.json` (excluded from deploys)
- `data/storylines/input/by-slug/<slug>.json` — one self-contained work item
  (`{generated_at, window_days, storyline}`) per storyline needing a narrative;
  what a per-slug subagent reads. Cleared of no-longer-needed slugs on every
  builder run (excluded from deploys)
- `data/storylines/scout/candidates.json` — machine-built recall candidates
  (near-miss anchors + co-mention buckets) the `storyline-scout` routine reads;
  includes a `window_sids` validation allowlist so accepted links remain valid
  after they stop appearing as candidates
- `data/storylines/scout/links.json` — agent-confirmed thread links
  (`members` sids + `label_hint`). `build_storylines.py` applies each as a
  synthetic candidate through the same MIN_ITEMS/DAYS/SOURCES floor; a surfaced
  thread is flagged `via_scout`. Both scout files are excluded from deploys
- `data/daily/<YYYY-MM-DD>.json`, `data/weekly/<YYYY-Www>.json` — agent-written
  recaps; `index.json` + `latest.json` per dir; `input/` holds the article
  bundles the agent reads (excluded from deploys). Recap input and output
  articles preserve optional `publisher_name` and `publisher_domain` fields so
  renderers can credit the syndicated outlet instead of the aggregator feed.
- `data/daily/state.json` — `build_daily_input.py`'s automatic-mode cursor:
  `last_checked_date` (latest UTC day published or confirmed empty) and
  `skipped_dates` (audit trail of confirmed-empty days). Only the script's
  no-`--date` mode advances it; excluded from deploys
- `data/playbook/<YYYY-MM-DD>.json` — agent-written **Playbook editions**: a
  batch of actionable cards for agent builders. Every card has
  `{id, kind, title, problem, apply, result}`. `source-backed` cards additionally
  require `{source_url, source_sid, evidence}` and may be embedded in recaps;
  `evergreen` cards require `topic_url` and remain Playbook-only. `index.json` +
  `latest.json` rebuilt by `.agents/skills/playbook/scripts/build_playbook_index.py`;
  `input/` holds the article bundles the agent reads (excluded from deploys).
  Served at `/playbook` via `/api/playbook`
- `data/playbook/source-index.json` — deterministic lookup keyed by durable
  story `source_sid`. Contains only validated source-backed cards plus their
  edition id; consumed by static and dynamic daily/weekly recap renderers.
- `data/i18n/<locale>/<surface>/<id>.json` — pre-translated static-page
  artifacts. Current surfaces are `daily`, `weekly`, `story`, `storyline`,
  `topic`, and `foundations`. Each artifact carries `{locale, source_path,
  source_hash, translated_at, model, review_status, title, description, ...}`;
  daily/weekly artifacts may also carry field-complete translated `intro`,
  `highlights`, `categories[].{name,summary}`, and
  `categories[].articles[].{title,summary}` overlays. `pipeline/render_static_pages.py`
  recomputes `source_hash` from the current English source and renders only
  fresh artifacts to `web/<locale>/...`. APIs remain English in v1. Operating
  guide: `docs/how-to/add-pretranslated-pages.md`; candidate exporter:
  `pipeline/export_i18n_candidates.py`.
- `data/i18n/<locale>/feed/latest.json` — feed-specific localized live-feed
  overlay, separate from static-page artifacts. For Korean v1 this is a
  complete `/ko/` snapshot of the default Brief feed, up to 20 eligible cards,
  with `{locale, surface, source_run_at, translated_at, expires_at, selector,
  source_item_count, translated_item_count, is_complete, target_keys[],
  items[]}`. `items[]` stores translated display fields keyed by normalized
  source URL while `/api/feed` preserves English item IDs, URLs, dates,
  scores, labels, and story metadata. `target_keys[]` (build-time ranked
  top-N order) plus per-item `source_meta {url, source, published, type}`
  let `/api/feed` serve the frozen snapshot as dated Korean cards
  (`frozen_snapshot: true`) when the snapshot is paused/stale; neither field
  is covered by `source_hash`.
- `data/i18n/<locale>/feed/status.json` — durable localized-feed build status
  for missing, stale, incomplete, disabled, current, or `budget_paused`
  snapshots. Includes `{locale, surface, status, reason, resumes_at, mode,
  budget: {chars_used, monthly_cap, month}, source_run_at, translated_at,
  expires_at, eligible_count, translated_count, missing_count}`. `mode`
  (`normal`|`conserve`|`economy`|`paused`) and `budget` are written on every
  run, not only `budget_paused`, so ops can watch the governor ladder.
  `pipeline/render_static_pages.py` ignores `data/i18n/<locale>/feed/**`;
  Vercel bundles only `latest.json` and `status.json` for `api/feed.js`.
- `data/i18n/<locale>/feed/budget.json` — **pipeline-only** local character
  ledger backing the translation budget governor; never added to
  `vercel.json` `includeFiles` (everything `api/feed.js` and `/ko/` need
  travels through `status.json` instead). Shape:
  `{month: "YYYY-MM", chars_used, monthly_cap, updated_at, seeded_from,
  history: [{at, chars, run}]}`. `chars_used` resets to 0 on UTC month
  rollover; `monthly_cap` defaults from env `GOOGLE_TRANSLATE_MONTHLY_CHAR_CAP`
  and is recorded on the ledger so status can report the cap in effect;
  `seeded_from` records the one-off `--seed-chars`/`--seed-note` provenance
  (e.g. `"console 2026-07-12"`) when the owner seeds mid-month spend from
  Cloud Console; `history[]` is a bounded (last 200 entries) audit trail, not
  a source of truth. See `docs/product-specs/localized-live-feed.md`
  ("Translation Budget Governor") and
  `docs/how-to/translation-budget-and-quota.md`.

## Agent-engineering wiki (`data/wiki/`)
LLM-curated obstacle→solution knowledge graph (Karpathy's LLM-wiki pattern).
Source of truth is markdown; `index.json` is the only file served/bundled.
- `data/wiki/obstacles/<slug>.md`, `data/wiki/solutions/<slug>.md` — node pages.
  YAML front matter (`slug`, `kind` obstacle|solution, `title`, `area` for
  obstacles, `status`, edge lists `solutions:`/`obstacles:`, `related_storylines:`,
  `evidence:` real story sids, `updated`, `covers_evidence` staleness snapshot) +
  a markdown body with known `## ` sections. Format/invariants in
  `config/wiki_schema.md`.
- `data/wiki/index.json` — compiled by `pipeline/build_wiki.py`: `{generated_at,
  areas:[{area,label,obstacles:[slug]}], nodes:{slug:{kind,title,area,status,
  summary,sections:[{heading,html}],solutions:[{slug,title}],obstacles:[…],
  related_storylines:[{slug,label}],evidence:[{sid,title}],updated}}}`. The build
  symmetrizes edges and fails on dangling edges / unresolved evidence sids or
  storyline slugs. Served by `/api/topics` and rendered to `web/map.html` +
  `web/topic/<slug>.html`.
- `data/wiki/index.md` — human catalog. `data/wiki/log.md` — append-only activity
  log. `data/wiki/input/latest.json` — `wiki-curator` ingest bundle (recent
  stories grouped by obstacle area; excluded from deploys).

## Model Release Radar (`data/models/`)
Deterministic model-release data joined from LMArena (keyless), Artificial
Analysis (when `AA_API_KEY` is configured), and DeepSWE / Datacurve
(keyless, scraped - see below). Written by `pipeline/collect_models.py
collect`; config in `config/models.yaml`.
- `data/models/latest.json` - `{generated_at, sources: {lmarena,
  artificial_analysis, deepswe}, models: [...], axis_metric_options: [...]}`.
  `sources.*` carries `{available, attribution, url, publish_date?}` per
  source (Artificial Analysis and DeepSWE attribution are mandatory wherever
  their data is displayed); `sources.deepswe` additionally carries
  `{generated_at, n_tasks_in_set}` - the DeepSWE leaderboard run's own
  metadata, not this collector's run time. Each model row: `{slug, name,
  base_slug, variant_label, organization, license, open_weights,
  release_date, context_window_tokens, parameters_total, parameters_active,
  price_input_per_1m, price_output_per_1m, price_blended_per_1m,
  arena_elo_overall, arena_elo_coding, arena_votes, arena_rank_overall,
  arena_rank_coding, aa_intelligence_index, aa_coding_index,
  median_output_tokens_per_second, official_url, joined_sources,
  display_name, benchmarks, url_slug, frontier, deepswe_pass_at_1,
  deepswe_ci_lo, deepswe_ci_hi, deepswe_n_runs, deepswe_cost_per_task_usd,
  deepswe_median_cost_usd, deepswe_output_tokens}`.
  `url_slug` (added 2026-08-16, corrected to per-base-model grouping the
  same day - see `docs/design-docs/decision-log.md`) is the stable,
  human-readable, URL-safe identifier `/models/<slug>` detail pages and
  `api/models.js`'s `?slug=` lookup use - matches `SLUG_RE`
  (`^[a-z0-9][a-z0-9-]{0,80}$`) and is assigned ONE PER BASE MODEL
  (`base_slug` group), never per row: every reasoning-effort variant of the
  same underlying model (`"claude-opus-5-max"`, `"claude-opus-5-high"`, ...)
  shares the SAME `url_slug` (`"claude-opus-5"`), matching the one detail
  page per real model the product needs and the collapse
  `web/models.html`'s "+N variants" badge already performs. A collision
  (a numeric `-2`/`-3`/... suffix, never dropped, never random) can only
  happen between two genuinely DIFFERENT base models whose clean names
  match - not between variants of one model, which can never collide with
  each other since they already share one slug. `url_slug` is STABLE
  across refresh runs: derived purely from a `base_slug` group's own
  identity (a deterministically-chosen representative row's
  `display_name` -> `name` -> `slug` fallback chain), never from list
  position/order/run timestamp, so retiring one upstream variant never
  renumbers its surviving siblings or any unrelated model - see
  `pipeline/collect_models.py::assign_url_slugs`. Distinct from the
  existing `slug` field (a normalized JOIN key, e.g. `"claudeopus5max"`,
  one per ROW, never guaranteed human-readable or dash-separated);
  `url_slug` is the presentation/routing identifier, one per MODEL (e.g.
  `"claude-opus-5"`).
  `frontier` (added 2026-08-16, per-base-model correction same day; scope
  narrowed 2026-08-17 to metrics with a MEASURED per-task cost) is the
  server-side Pareto frontier answer, computed once so the ranked list,
  detail pages, static renderer, and chart all read one answer instead of
  independently re-deriving it (and risking disagreement) - shape:
  `{<metric_key>: {cost_field, cost_basis, on_frontier, dominated_by:
  [<url_slug>, ...]}, ...}`, one entry per BASE MODEL (one per `url_slug`,
  matching the grouping above) per metric in `config/models.yaml`'s
  `frontier_metrics` list (config-driven). `cost_field` names which model
  field was paired against that metric as its cost axis; `cost_basis` names
  what KIND of cost that is, and is now the gate on whether a metric may
  claim a frontier at all - a raw per-1M-token price is NOT a fair X axis
  for an agentic benchmark score, because the cost of running a task
  depends on how many tokens and steps a model actually spends, not just
  its per-token rate (proof from live DeepSWE data, 2026-08-16:
  claude-opus-5 costs $11.84/task at "max" reasoning effort and $3.29/task
  at "medium", yet both price identically at $10/1M tokens). As of
  2026-08-17, `frontier_metrics` names exactly ONE entry -
  `deepswe_pass_at_1`, paired with `deepswe_cost_per_task_usd` under
  `cost_basis: "measured_per_task"` (DeepSWE's own real dollar cost per
  task - see the `deepswe_*` fields below). Every prior entry
  (`aa_intelligence_index`, `aa_coding_index`, and the raw AA benchmarks,
  all under `cost_basis: "per_token_price_proxy"` paired with
  `price_blended_per_1m`) was REMOVED, not relabeled - those scores still
  display everywhere they always have (the ranked list still ranks by AA
  intelligence index by default, the scores table still shows every AA
  benchmark - see `pipeline/render_static_pages.py`'s `model_scores_section`),
  they simply no longer carry an "on/behind frontier" claim, since that
  claim rested on a cost that does not actually track per-task spend.
  Coverage dropped accordingly: DeepSWE covers roughly two dozen of the
  ~150+ tracked models (verified live 2026-08-16), a smaller but honest
  frontier. The `cost_basis` machinery itself is unchanged and stays
  config-driven for exactly this reason - a future benchmark that gains a
  real per-task cost source lights up here automatically with a
  `config/models.yaml` change, never a code change. Computed in two phases:
  (1) per-variant Pareto-optimality (no OTHER row - excluding a sibling
  variant of the SAME model, which can never count as a dominator now that
  variants share a slug - is cheaper-or-equal AND at least as capable, with
  at least one strict improvement); (2) per-model aggregation, where a base
  model is `on_frontier` if ANY of its variant rows is, and `dominated_by`
  is the deduplicated, nearest-cost-first union of every non-frontier
  variant's dominators (themselves mapped to their own per-model
  `url_slug`), capped at `config/models.yaml`'s `frontier_dominated_by_cap`
  (5 today) - populated only when the model itself is off the frontier, so
  it can never name itself. A model missing either the metric or its
  paired cost field on every one of its variant rows is simply ABSENT from
  that metric's entry - never written with a null/false placeholder,
  matching the `price_blended_per_1m`/zero-price precedent below: a missing
  value is never treated as a comparable number. See
  `pipeline/collect_models.py::compute_frontier` for the full contract,
  including the documented, verified agreement with `web/models.html`'s
  client-side `paretoFrontier()` walk.
  `deepswe_pass_at_1`, `deepswe_ci_lo`, `deepswe_ci_hi`, `deepswe_n_runs`,
  `deepswe_cost_per_task_usd`, `deepswe_median_cost_usd`,
  `deepswe_output_tokens` (added 2026-08-17) are DeepSWE / Datacurve's
  measured agentic-coding-benchmark result for this model, sourced from
  `sources.deepswe` (scraped from a React Flight payload embedded in
  DeepSWE's leaderboard page HTML - no documented JSON API exists, see
  `pipeline/collect_models.py::parse_deepswe_html` and
  `config/models.yaml`'s `sources.deepswe` comment). `deepswe_pass_at_1` is
  a 0-1 fraction (DeepSWE's pass@1 on its held-out agentic coding task set);
  `deepswe_cost_per_task_usd` (DeepSWE's `mean_cost_usd`) is the ONLY
  measured-not-proxied cost field in this artifact and is what
  `frontier_metrics` pairs `deepswe_pass_at_1` against;
  `deepswe_median_cost_usd` is kept alongside it for reference.
  `deepswe_ci_lo`/`deepswe_ci_hi` are the 95% run-to-run confidence interval
  on `pass_at_1`; `deepswe_n_runs` is how many repeated whole-benchmark
  passes that interval is computed over; `deepswe_output_tokens` is
  DeepSWE's median output-token count for the task set. Joined on
  `(url_slug, variant_label)` directly against DeepSWE's own
  `(model, reasoning_effort)` values, which already match this module's
  naming conventions (verified live 2026-08-16, no normalization/alias
  layer needed, unlike the LMArena/AA join) - falling back to any DeepSWE
  row for the same model when the row's own reasoning-effort variant has no
  exact match. All seven fields are null (never invented) for a model
  DeepSWE has not measured.
  `benchmarks` (added 2026-08-16) is a dict of raw Artificial Analysis
  per-model benchmark scores (`{"livecodebench": 0.878, "tau2": 0.657, ...}`),
  stored exactly as AA reports them - purely additive alongside the existing
  `aa_intelligence_index`/`aa_coding_index` blended composites, which are
  unchanged. WHICH benchmarks are persisted is config-driven
  (`config/models.yaml`'s `sources.artificial_analysis.benchmarks` list,
  never hardcoded in `pipeline/collect_models.py`, since AA adds/renames
  benchmarks over time) via `extract_aa_benchmarks`. A benchmark AA reports
  as null for a model is OMITTED from that model's `benchmarks` dict (never
  zero-filled or invented); a model with no benchmark data gets `{}`. SCALE
  WARNING: every value in `benchmarks` is a 0-1 fraction, a completely
  different scale from the ~0-100 `aa_intelligence_index`/`aa_coding_index`
  composites - `web/models.html` rescales its chart axis per the active
  metric's own domain rather than assuming either scale (see
  `config/models.yaml`'s `axis_metric_options` below and the 2026-08-16
  decision-log entry).
  `axis_metric_options` (added 2026-08-16, top-level array alongside
  `models`, not per-row) is the config-driven list of capability metrics
  `web/models.html`'s chart Y-axis toggle offers - `config/models.yaml`'s
  `axis_metric_options`, emitted verbatim by `build_output`. Each entry is
  `{key, label, source, scale}`: `source` is `"top"` for the default
  `aa_coding_index` field or `"benchmarks"` for a key read from a model row's
  `benchmarks` dict; `scale` is `"index"` (~0-100) or `"fraction"` (0-1) and
  drives axis-tick/tooltip formatting. The page only actually offers a
  benchmark-sourced entry once it clears `web/models.html`'s
  `MIN_METRIC_COVERAGE` gate computed from the live data (a benchmark almost
  nothing reports is hidden, never shown as a misleadingly sparse chart) -
  it falls back to a small hardcoded mirror of the same list
  (`DEFAULT_AXIS_METRIC_OPTIONS`) only for an older cached artifact written
  before this field existed.
  `display_name` (added 2026-08-06) is the clean, human-readable BASE model
  name for presentation only - the row's `name` field is whichever source's
  raw string a collapsed row's representative happened to come from (an
  Artificial Analysis verbose variant string, or a LMArena lowercase-dashed
  slug), so a single list otherwise mixes naming conventions and repeats
  variant text the `variantCount`/`"+N variants"` presentation already
  communicates. Computed once by
  `pipeline/collect_models.py::derive_display_name`: prefers Artificial
  Analysis's own name (title-cased, human-written) when the model has any AA
  contribution, stripping only a *recognized* variant (the same
  `variant_vocabulary` match as `base_slug`/`variant_label`, so the three
  fields never disagree); otherwise conservatively titlecases a LMArena
  slug via `config/models.yaml`'s `acronym_casing` map (never a hardcoded
  Python list), never re-casing a word that already carries a capital
  letter and never losing a version number. Additive only - `name` is
  unchanged and remains the join key / raw source string; `display_name`
  falls back to `name` verbatim if the computation ever yields nothing
  usable, so it is never null while a name exists.
  `base_slug`/`variant_label` (added 2026-08-06) split a row's `name` into
  the model's identity with any reasoning-effort variant stripped
  (`base_slug`, e.g. `"gpt56sol"`) and that variant's label (e.g.
  `"medium"`, or null when the name carries no recognized variant) - see
  `pipeline/collect_models.py::derive_base_variant` and `config/models.yaml`'s
  `variant_vocabulary`. A parenthetical may also carry configuration-only
  clauses alongside the effort clause ("Claude Fable 5.1 (Adaptive Reasoning,
  High Effort, Default Fallback)"); those are dropped first via
  `variant_vocabulary.ignorable_qualifiers` (also config-driven) so the effort
  clause still matches - otherwise the whole parenthetical stays in
  `base_slug` and each effort level becomes its own "model" on `/models`.
  Every row keeps its own full identity and is still
  emitted; `web/models.html` and the feed sidebar use these as grouping keys
  to collapse variant-spam rows to one per real model for presentation only.
  `organization` is normalized through `config/models.yaml`'s
  `organization_aliases` so the same real-world lab never splits into two
  values across the two sources. `price_input_per_1m`/`price_output_per_1m`/
  `price_blended_per_1m` are null both when a source never published a price
  AND when a source published exactly `0` (treated as "undisclosed," not
  "free" - see `zero_price_to_null`) - a price of 0 is otherwise undefined on
  the /models page's log-scale price axis. `open_weights` is null unless
  derivable (an explicit Artificial Analysis boolean, or a classifiable
  LMArena `license` string); `parameters_*` is null for undisclosed closed
  models (no rumored figures, per the anti-hype contract). `joined_sources`
  lists which source(s) contributed the row (`["lmarena"]`,
  `["artificial_analysis"]`, or both) so join gaps stay visible.
- `data/models/history/<YYYY-MM-DD>.json` - one dated snapshot of the same
  shape per collector run, for score-delta tracking.

## Feedback loop
- `data/feedback/events.jsonl` — reader feedback events (PostHog sync + manual)
- `data/feedback/ctr_clicks.json` — per-source click counts (PostHog sync)
- `data/feedback/source_adjustments.json` — auto-tune output; applied as
  `source_tune` in ranking

## North star metric
- `data/metrics/weekly_returning_readers.json` — `{generated_at, weeks: [...]}`,
  one row per completed ISO week (`week_start`, `total_readers`,
  `returning_readers`, `new_readers`, `returning_rate`), merged forward by
  `pipeline/north_star_metric.py sync` from PostHog pageview events
  (`$pageview` and legacy `page_view`). See
  `docs/status/north-star-metric.md`.

## Ops
- `data/health/source_health.json` — per-source reliability scores
- `data/health/circuit_breaker.json` — open/closed circuit state per source
- `data/health/alerts_state.json`, `latest_alerts.json` — degradation alerts
- `data/health/ingest_runs.jsonl` — per-run ingest status log. One record per
  source per run: `ts`, `source`, `url`, `status` (`ok` / `error` /
  `skipped_cooldown` / `skipped_open_circuit`), `items`, plus
  `excluded_title` when a source's `exclude_title_regex` dropped titles
- `data/email/state.json` — email-digest send cursor (NOT subscriber PII; the
  provider owns the list). Keys: `daily.last_sent_date`, `weekly.last_sent_week`
  (idempotency guards), and `storylines.{sent_through,seen_sids}` — the
  high-water marks the **daily** brief uses to mail only storyline deltas with no
  repeats. The **weekly** recap is window-based (`[start,end]` of the recap),
  so it needs no storyline/wiki high-water mark.
- `data/diagnostics/<date>_ranking.json` — per-day ranking diagnostics
- `data/analysis/` — one-off analysis artifacts

## Future (if a real DB is introduced)
Planned tables would mirror the above: sources, raw_items, canonical_items,
item_scores, digests, digest_items, feedback_events.
