# Data Schema (File-Based Store)

There is no database. All persistent state is versioned JSON/JSONL/Markdown
under `data/`, committed to git by the pipeline. This file documents the
layout (the de-facto "schema"). Vercel serverless functions in `api/` read
these files directly — only paths listed in `vercel.json` `includeFiles` are
available to each function.

## Ingestion
- `data/raw/<YYYY-MM-DD>/items.json` — collector output for the day
  (normalized items: url, title, source, published, summary, …)
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
  `final_score`, `slot_priority`, and `global_score`.
- `data/processed/runs/<Y>/<M>/<run_id>.json` + `runs_index.json`
  — per-run history (retention ~45d)

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
  bundles the agent reads (excluded from deploys)
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
