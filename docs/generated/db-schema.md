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
  — per-run history (retention ~14d, max 96 runs)
- `data/processed/latest.json` — the production feed (Tier-0 full ranking)
- `data/processed/runs/<Y>/<M>/<run_id>.json` + `runs_index.json`
  — per-run history (retention ~45d)

## Digest + publishing
- `data/digest/<YYYY-MM-DD>.md` — daily digest markdown (also published as a
  GitHub Issue and optionally to Telegram)

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
  (new or stale), each with its timeline; what the agent reads (excluded from
  deploys)
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

## Feedback loop
- `data/feedback/events.jsonl` — reader feedback events (PostHog sync + manual)
- `data/feedback/ctr_clicks.json` — per-source click counts (PostHog sync)
- `data/feedback/source_adjustments.json` — auto-tune output; applied as
  `source_tune` in ranking

## Ops
- `data/health/source_health.json` — per-source reliability scores
- `data/health/circuit_breaker.json` — open/closed circuit state per source
- `data/health/alerts_state.json`, `latest_alerts.json` — degradation alerts
- `data/health/ingest_runs.jsonl` — per-run ingest status log
- `data/diagnostics/<date>_ranking.json` — per-day ranking diagnostics
- `data/analysis/` — one-off analysis artifacts

## Future (if a real DB is introduced)
Planned tables would mirror the above: sources, raw_items, canonical_items,
item_scores, digests, digest_items, feedback_events.
