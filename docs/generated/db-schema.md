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
  Items from a source configured with `fetch_content: true` also carry
  `content_excerpt`: up to 4000 characters of the article's rendered body text,
  fetched at collection time. It exists for the keyword gates (see
  `docs/ranking-v2-flow.md`), never for display — reader-facing summaries still
  come from the feed's own `summary`. Absent wherever the fetch failed or the
  source is not opted in.
  `youtube_channel` rows additionally carry `type: video`, `video_id`, and
  optional `duration_s` / `transcript_url`. The item URL is `youtu.be/<id>`,
  not `watch?v=<id>`: the pipeline canonicalises URLs by dropping the query
  string, so watch URLs would collapse every video into one item. A
  `transcript_url` points at an official companion podcast transcript
  (`podcast:transcript`), matched by normalized title; video items without one
  fall back to the video description.
- `data/cache/sitemap_meta.json` — sitemap crawl metadata cache
- `data/llm/content_cache.json` — page-body fetch cache keyed by canonical url
  (5000 chars per url), written by `pipeline/content_fetch.py`. Local only:
  gitignored, so a fresh runner refetches. Not committed and not deployed.

## Ranked snapshots
- `data/processed/latest.json` — the production feed (single edition build).
  Ranked items include score diagnostics such as `llm_score`, `source_bias`,
  `source_tune`, `topical_bias`, `editorial_penalty`, `judge_adjustment`,
  `release_boost`, `pre_decay_score`, `time_decay_factor`, `final_score`,
  `slot_priority`, and `global_score`. Editorial fields: `source_role`,
  `story_key`, `story_cluster_id`, `story_cluster_size`, `seen_count`.
  Release fields: `release_tier` (`major` = substantive release, `minor` =
  bare bump/prerelease; used only to order the Releases lane; absent on
  non-release items and older snapshots) and `release_boost` (the Stage C
  score term, 0.45 for major).
  Judge fields:
  `judge_score`, `judge_signals`, `judge_choices`, `judge_category`,
  `judge_category_confidence`, `judge_category_probabilities`,
  `judge_verdict`, `judge_model`, `judge_rubric_version`, `judge_judged_at`.
  Optional `publisher_name` and `publisher_domain` attribution fields pass
  through from collector rows for Google News items.
  Video items carry `type: video`, `video_id`, optional `duration_s`, and
  `transcript_url`. Their `content_excerpt` is a transcript-backed digest
  (show notes plus sampled transcript windows), not the watch-page HTML.
- `data/processed/judgments.json` — durable judgment store for the Jev gate:
  `entries` keyed by item identity + model + rubric + prompt fingerprint +
  evidence bucket, each with score, verdict, signals, category,
  `judge_evidence_chars`, and `judge_judged_at`. The evidence bucket is `thin`
  below `content_fetch.min_evidence_chars`, so a snippet-only judgment is not
  reused after the article body is fetched. Pruned to
  `judgment_store.ttl_days` (default 14) and `max_entries` (default 6000).
  Committed so CI reuses prior judgments and only calls Jev for missing,
  expired, or thin-evidence items.
- `data/processed/classified.json` — compact, committed judge artifact for
  editor-deck routines: model/rubric version, category and verdict counts, and
  up to 120 top-scored judged items (`story_key`, `url`, `title`, `source`,
  `published`, `judge_score`, `judge_verdict`, `judge_evidence_chars`,
  `judge_category`, `judge_category_confidence`). `pipeline/deck_quality.py` joins this file and
  `judgments.json` onto the five editor-deck input bundles, attaches the
  judge fields, filters known drops (release items and release notes are
  exempt for decks with a release lane), and uses the judge category as the
  bundle's starting `category_hint` when an item was judged.
- `data/processed/editorial.json` — deterministic editorial-policy artifact
  read by `api/feed.js` and `api/rss.js`: `source_roles` (source -> role),
  `caps` (per-source caps by role), `role_totals` (cross-source totals),
  `search_quarantine` / `first_party_quarantine` (patterns + rescue keywords),
  `story_clusters.enabled`, and the pipeline's editorial diagnostics.
- `data/processed/runs/<Y>/<M>/<run_id>.json` + `runs_index.json`
  — per-run history (retention ~45d)
- `data/quality/benchmark/` — offline Jev/decision-model benchmark:
  `items.json` (58 stratified items with title, source, excerpt, expected
  label, rationale), `labels.md` (review table), `video_items.json` (the
  frozen 8-item video slice, built from real YouTube/podcast feeds),
  `content_cache.json` (fetched excerpts), `fixture_scores.json` (synthetic
  harness validation only), and generated `runs/`. Not read by any API or the
  static build.
- `data/quality/transcript_cache.json` - transcript digests keyed by
  `transcript_url`, plus short-lived failure records for a blocked or
  unavailable host. Local only (gitignored); the durable judgment store is
  what CI reuses.
- `data/quality/cache/` — cached judge responses keyed by payload hash, so
  threshold sweeps and reruns do not make new API calls.
- `data/quality/classified/<date>.json` — full local judged candidate pool for
  the edition (all Stage A candidates), with signals, category probabilities,
  and diagnostics. Gitignored; the compact `data/processed/classified.json`
  is the shared artifact.
- `data/quality/content_cache.json` — paragraph-extraction cache for the judge
  (canonical URL -> article paragraphs). Gitignored.
- `data/quality/pool/<run-date>.json` — committed per-day judged candidate
  pool for the editor decks, written by `pipeline/judged_pool.py` after every
  edition build. Top level: `date`, `schema_version`, `runs`, `updated_at`,
  `item_count`, `items` (keyed by normalized URL). Each row carries the item
  identity (`id`, `title`, `url`, `source`, `source_role`, `type`,
  `published`, `story_key`, `story_cluster_id`), the latest judge fields
  (`judge_score`, `judge_verdict`, `judge_category`,
  `judge_category_confidence`, `judge_signals`, `judge_evidence_chars`,
  `judge_error`, model/rubric/judged_at), `prefilter_score`, `source_tune`,
  `type` and `release_tier` (derived with the Stage C rules for items outside
  the edition), `summary` (280 chars), `excerpt` (400 chars), `echo_count`/`source_count`
  for clustered stories, `summary_1line`, `why_it_matters`, `llm_category`,
  `matched_topics`, `freshness`, `time_decay_factor`, `image_url`, compact
  `also_covered` entries, `slot`, and run counters (`first_seen_run`,
  `last_seen_run`, `runs_seen`, `edition_runs`, `best_edition_rank`,
  `edition_slot`). Unjudged items are included without a score. Keyed by UTC
  run date, so a deck reads the run dates covering its published window and
  filters by `published`. Retention 14 days (`prune_runtime_data.py
  --pool-days`). Not read by any API or the static build.
- `data/quality/deck_benchmark/labels/<deck>-<window>.json` — committed owner
  grades for the deck selector benchmark, written by
  `scripts/deck_replay.py --packet`: `deck`, `window`, `guide`, and `stories`
  keyed by `story_id` (`grade` 0/1/2 or null, `same_as`, `note`, `picked_by`
  published/selector/both, `title`, `url`, `source`, `judge_score`,
  `judge_category`, `summary`, `silver`). Reruns append and never change a
  grade. `runs/<deck>-<stamp>/report.{md,json}` are generated and gitignored.

- `data/brief/<YYYY-MM-DD>.json` - the served Brief admission ledger, written
  by `pipeline/brief_ledger.py` after every feed build. Top level:
  `schema_version`, `date` (UTC), `timezone`, `updated_at`, `items` (keyed by
  story id) and `diagnostics` (gate/quota counters). Each item carries the
  feed card fields (`id`, `title`, `url`, `source`, `source_role`, `type`,
  `published`, `summary_1line`, `why_it_matters`, `content_excerpt`,
  `llm_category`, `v2_slot`, `slot`, `also_covered`, `source_count`), the
  judge fields, the admission fields (`admitted_at`, `first_seen`, `last_seen`,
  `seen_count`, `utility`, `utility_basis`, `freshness_at_admission`,
  `admission_rank`, `score_at_first_seen`, `rank_at_first_seen`), and
  `release_tier` for releases. `admitted_at` is the run timestamp of the build
  that admitted the story; a backfilled ledger reconstructs it from the pool
  `first_seen`. The writer never removes an item, skips a story already
  admitted within the previous 24h (including the previous two day files), and
  updates `last_seen`/coverage in place. Retention 3 days
  (`prune_runtime_data.py --brief-days`). The default `window=arrival`
  `/api/feed` path reads all retained files, keeps the latest admission for a
  story, and applies the same display caps/top-band balance as the run path.
  `pipeline/deck_candidates.py` joins it as `in_brief`.

## Feed API (`/api/feed`)
Response fields served from the admission ledger (rolling 24h) or the
accumulated ranked pool (calendar ranges):
- `filters.window` - `arrival` (rolling 24h by `first_seen`, served from the
  admission ledger when one exists, otherwise the run-pool fallback) or
  `published` (calendar ranges). The default client preset sends `arrival`;
  explicit `from`/`to` ranges and wider presets send `published`.
- `ledger` - present on the `window=arrival` path: `{files, updated_at,
  admitted}` describing the retained ledger files and the pre-window item
  count. Diagnostic only; the client does not render it.
- `label_counts` - per-section story counts for the homepage tabs:
  `{brief, platform, research, release, news}` (present on both the normal
  history path and the no-runs `mode: "latest"` fallback). Each value counts
  items inside the request's date/arrival window matching that one section lens
  (`brief` = everything except releases, mirroring the default tab), computed
  from the same pool as `items` before any reader-selected `label=` filter is
  applied - so tabs show what each section WOULD hold. Reflects the date
  window only, never search or client-side state.
- `items[].beyond_cap` - `true` on a story kept in the window but outside the
  cap-compliant top mix. These stories are still returned in `items` below
  the primary cards; the homepage folds them under "More from ...". The
  primary slice never removes a story to make room for a newer one.
- `items[].score_at_first_seen` / `rank_at_first_seen` - the admission-time
  ranking score and rank from the run when the story first entered the pool.
  The API sorts the served window by these, not by the latest run, so a
  refresh cannot reshuffle an already-visible story. The card's ranked-because
  line displays `score_at_first_seen` for the same reason.
- `items[].also_covered` - up to 4 cross-source coverage entries
  `{source, url, title<=160}` per item, deduped by (source, normalized URL
  sans query/trailing slash), same-source and self-referencing entries
  excluded. Two sources feed it: pipeline enrichment (`pipeline/enrich.py`,
  max 4, excludes arxiv<->arxiv pairs) and server-side normalized-title
  clustering (`api/feed.js::clusterCoverage`) over the cached run pool -
  groups of 2-8 items sharing a normalized title of >=30 chars across >=2
  distinct sources (arxiv<->arxiv excluded there too), candidates sorted by
  `global_score ?? v2_final_score ?? final_score ?? score_at_last_seen ??
  score`. The cluster merge happens
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
  Input bundles also carry the joined judge fields described above, a
  `summary_source`, `deck_category`, `judge_category_hint`, and a `quality`
  audit block. By default (`config/decks.yaml` `decks.<deck>.bundle`, off
  with `--no-pool`) the builders append judged keeps for the window that no
  feed edition held (`pipeline/deck_bundle.py`); those articles carry
  `from_pool: true`, and the bundle's `pool_additions` object reports
  `enabled`, `added`, `capped`, `capped_by_type`, `verdicts`,
  `pool_candidates`, `from_pool_files`, `by_type`, `by_role`, `event_groups`
  (or `error`). Articles whose titles name exactly one configured model family
  at the same version share an `event_group` (`kimi|3.1`;
  `config/decks.yaml` `collapse.event_models`; release items are never
  grouped). With additions off (`--no-pool` or config) the bundle has neither
  `pool_additions` nor `event_group`. With `--selector`, a bundle also carries `selection`
  (`pipeline/deck_select.py`): `deck`, `budget`, `min_utility`, `candidates`,
  `stories`, `eligible`, `shortlist` and `bench` cards (`story_id`, `url`,
  `title`, `source`, `source_role`, `type`, `published`, judge fields,
  `category`, `utility`, `utility_parts`, `source_count`, `member_urls`; bench
  cards add `bench_reason`), `by_category`, `by_role`, `by_source`, `window`
  and `candidate_diag`. The recap skills do not read it yet.
  A daily or weekly recap may also carry `video: {youtube_id, title?, duration_s?}`
  (written by the `daily-video` / `weekly-video` routine after a successful YouTube
  upload; `youtube_id` is the 11-character id). Only the id is stored, never the
  video file. Both validators enforce the id; the weekly index does not carry it.
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
- `data/playbook/lab/<slug>.json` - validated Agent Skill Lab pilot records.
  `state: protocol` is allowed only for edition zero and cannot contain runs or
  a verdict. `state: published` is allowed for result editions 1 through 3 and
  contains the pinned environment, exactly three comparison conditions, at
  least three raw runs per condition, artifact references, limitations, a
  verdict, and a recommendation. Published records pin the reasoning effort and
  the tested skill's public source, revision, and SHA-256 digest; the minimal
  and full instruction artifacts also carry distinct digests. Displayed success
  counts and medians are derived from the raw runs, not authored into the
  record. Artifact links must be credential-free HTTPS URLs without query or
  fragment components, or same-origin paths under `/lab-artifacts/`. Same-origin
  files live in `web/lab-artifacts/`, use only `.json`, `.jsonl`, `.md`, or
  `.txt`, and must exist when the store is built. The deploy stages only files
  referenced by validated records at the root and mirrored `/web/` paths, both
  with sandboxing and MIME-sniffing protections. Local pinned-skill and
  instruction files must match their authored SHA-256 digests.
- `data/playbook/lab/{index,latest}.json` - deterministic derived views written
  by `pipeline/build_skill_lab.py` only after every root-level Lab record passes
  validation. Each index row carries `content_sha256`, and each derived file is
  replaced atomically. The Vercel build and serving boundaries reject stale
  source/index pairs. `data/playbook/lab/drafts/` is ignored by the builder and
  excluded from deployment. Served through `/api/playbook?lab=...`; the full
  reader surface is `/playbook/lab/<slug>`.
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
- `data/i18n/<locale>/feed/static_budget.json` — pipeline-only character ledger
  for static-page translation (`scripts/translate.py`); same shape as
  `budget.json`, separate allowance (env
  `GOOGLE_TRANSLATE_STATIC_MONTHLY_CHAR_CAP`, default 100,000). Kept under
  `feed/` so the static renderer ignores it. Candidates whose estimated billed
  characters exceed the remaining allowance are skipped.

- `data/i18n/spend_guard.json` — pipeline-only, fail-closed hard spend ledger
  shared by every Google Translate caller (locale-agnostic because the Console
  quota is project-wide). Shape: `{month, month_chars, day, day_chars,
  updated_at, tripped_at?}` on the Pacific clock. Written *before* each API
  request by `pipeline/translation_guard.py`. Not served or bundled.

## Agent-engineering wiki (`data/wiki/`)
LLM-curated obstacle→solution knowledge graph (Karpathy's LLM-wiki pattern).
Source of truth is markdown; `index.json` is the only file served/bundled.
- `data/wiki/obstacles/<slug>.md`, `data/wiki/solutions/<slug>.md` — topic
  pages. YAML front matter (`slug`, `kind` obstacle|solution, `title`, `area` for
  obstacles, `status`, edge lists `solutions:`/`obstacles:`, `related_storylines:`,
  optional overview `evidence:`, `updated`, `themes: [{key,title,summary}]`) + a
  word-capped body with only `TL;DR`, `State of the art`, `Trade-offs`
  (solutions), `Why it matters for platform engineers`.
- `data/wiki/entries/<slug>/<YYYY-MM-DD>-<name>.md` — one dated development per
  file: front matter `title`, `date` (= filename date), `theme` (a key on the
  topic page), `evidence` (1-6 story sids), optional `also` (other topic slugs);
  body ≤130 words. The file stem is the entry's anchor on `/topic/<slug>`.
  Format/invariants in `config/wiki_schema.md`.
- `data/wiki/index.json` — compiled by `pipeline/build_wiki.py`: `{generated_at,
  areas:[{area,label,obstacles:[slug]}], latest_entries:[{id,topic,topic_title,
  kind,date,title}], nodes:{slug:{slug,kind,title,area,status,summary,
  sections:[{heading,html}], themes:[{key,title,summary,count}],
  entries:[{id,topic,date,title,theme,html,evidence:[{sid,title}],
  also:[{slug,title}]}], cross_entries:[{id,topic,topic_title,date,title}],
  entry_count, latest_entry_date, solutions:[{slug,title}], obstacles:[…],
  related_storylines:[{slug,label}], evidence:[{sid,title}], updated}}}`.
  `entries` are newest first; `evidence` is the de-duplicated union of overview
  and entry sources; `updated` is the later of the page's `updated` and its
  newest entry. The build symmetrizes edges and fails on any schema violation.
  Served by `/api/topics` and rendered to `web/map.html` +
  `web/topic/<slug>.html`.
- `data/wiki/index.md` — human catalog, generated by `build_wiki.py` (do not
  hand-edit). `data/wiki/log.md` — append-only activity log (one short line per
  curator run). `data/wiki/input/latest.json` — `wiki-curator` ingest bundle
  (recent stories grouped by obstacle area with `filed_in`, judge annotations,
  and an optional per-topic `focus` dossier; excluded from deploys).

## Agent Builder Foundations (`data/foundations/`)
Agent-curated concept explanations; markdown is the source of truth and
`index.json` is the only file served/bundled.
- `data/foundations/concepts/<slug>.md` — one concept. Front matter: `slug`,
  `title`, `question`, `summary` (≤45 words), `status`, `cluster`, `updated`,
  `audience`, `math_depth`, `related_topics`, `related_playbook_cards`,
  `related_storylines`, and `evidence` (1-12 entries: `id`, `kind`, `title`,
  `url`, optional `sid`, `added` date, `note` ≤80 words; `story` entries carry
  `sid`, `storyline` entries `slug`). Body: word-capped sections (no
  `Evidence` section). Contract: `config/foundations_schema.md`.
- `data/foundations/index.json` — compiled by `pipeline/build_foundations.py`:
  `{generated_at, clusters:[{slug,label,concepts}], recent_evidence:[{concept,
  concept_title,id,title,tier,kind,added}], concepts:{slug:{slug,title,
  question,summary,status,cluster,cluster_label,updated,latest_evidence_added,
  audience,math_depth,sections:[{heading,html}],evidence:[{id,kind,tier,title,
  note,added,url?,sid?,slug?}],related_topics,related_playbook_cards,
  related_storylines}}}`. Evidence is newest `added` first; `updated` is the
  later of the page's `updated` and its newest evidence. Served by
  `/api/foundations` and rendered to `web/foundations.html` +
  `web/foundations/<slug>.html`.
- `data/foundations/input/` — curator input bundles (candidate stories with
  `cited_in`, judge annotations, current concepts with evidence dates);
  excluded from deploys.

## Model Release Radar (`data/models/`)
Deterministic model-release data joined from first-party announcements,
LMArena (keyless), Artificial Analysis (when `AA_API_KEY` is configured),
and DeepSWE / Datacurve
(keyless, scraped - see below). Written by `pipeline/collect_models.py
collect`; config in `config/models.yaml`.
- `data/models/latest.json` - `{generated_at, sources: {lmarena,
  artificial_analysis, first_party, deepswe}, models: [...], axis_metric_options: [...]}`.
  `sources.*` carries `{available, attribution, url, publish_date?}` per
  source (Artificial Analysis and DeepSWE attribution are mandatory wherever
  their data is displayed); `sources.artificial_analysis.url` is the public
  attribution link, and the source additionally carries `{api_url, tier,
  intelligence_index_version}` from the v2 list response (2026-10-06);
  `sources.deepswe` additionally carries
  `{generated_at, n_tasks_in_set}` - the DeepSWE leaderboard run's own
  metadata, not this collector's run time. Each model row: `{slug, name,
  base_slug, variant_label, organization, license, open_weights,
  release_date, context_window_tokens, parameters_total, parameters_active,
  price_input_per_1m, price_output_per_1m, price_blended_per_1m,
  arena_elo_overall, arena_elo_coding, arena_votes, arena_rank_overall,
  arena_rank_coding, aa_intelligence_index, aa_coding_index (retired
  2026-10-24 - still collected for history, no longer any reader surface),
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
  2026-10-24, `frontier_metrics` names two entries: `aa_intelligence_index`
  paired with `price_blended_per_1m` under
  `cost_basis: "per_token_price_proxy"` (the token-efficiency frontier
  restored 2026-09-24), and `deepswe_pass_at_1` paired with
  `deepswe_cost_per_task_usd` under `cost_basis: "measured_per_task"`
  (DeepSWE's own real dollar cost per task - see the `deepswe_*` fields
  below). `aa_coding_index` was removed from this list on 2026-10-24: AA
  froze that field on 2026-09-11, so a coding frontier would have contained
  only pre-September models. The raw AA benchmarks were removed 2026-08-17
  and remain out. The displaced scores still display where they always have
  (the ranked list still ranks by AA intelligence index by default, and
  the detail score table still shows the AA intelligence index - see
  `pipeline/render_static_pages.py`'s `model_scores_section`);
  `aa_coding_index` is no longer rendered on any reader-facing surface.
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
  stored exactly as AA reports them - purely additive alongside
  `aa_intelligence_index` (the blended composite still rendered) and the
  retired `aa_coding_index` (history only). WHICH benchmarks are persisted
  is config-driven
  (`config/models.yaml`'s `sources.artificial_analysis.benchmarks` list,
  never hardcoded in `pipeline/collect_models.py`, since AA adds/renames
  benchmarks over time) via `extract_aa_benchmarks`. A benchmark AA reports
  as null for a model is OMITTED from that model's `benchmarks` dict (never
  zero-filled or invented); a model with no benchmark data gets `{}`. The
  Artificial Analysis Free endpoint carries no per-benchmark scores, so on
  that tier every row's `benchmarks` is `{}` (2026-10-06). SCALE
  WARNING: every value in `benchmarks` is a 0-1 fraction, a completely
  different scale from the ~0-100 `aa_intelligence_index`/`aa_coding_index`
  composites. No surface renders the dict today: the model detail page's
  Artificial Analysis table lists only the intelligence index (raw
  per-benchmark rows were removed 2026-10-24 after the v2 Free migration
  left them permanently empty), and `/models` has no chart. The collection
  path stays in place as the slot a higher tier would populate.
  `axis_metric_options` (added 2026-08-16, top-level array alongside
  `models`, not per-row) is the config-driven list of capability metrics a
  chart Y-axis toggle once offered - `config/models.yaml`'s
  `axis_metric_options`, emitted verbatim by `build_output`. Each entry is
  `{key, label, source, scale}`: `source` is `"benchmarks"` for a key read
  from a model row's `benchmarks` dict; `scale` is `"index"` (~0-100) or
  `"fraction"` (0-1). The `aa_coding_index` entry was removed on
  2026-10-24 (AA froze the field on 2026-09-11). No page reads the list
  today: the `/models` ranked list has no chart, and the model detail page's
  chart is fixed to DeepSWE pass@1 vs. measured cost per task
  (`frontier_metrics`). It remains in the artifact so a future
  benchmark-backed capability selector would not need a schema change.
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
  `["artificial_analysis"]`, `["first_party"]`, or a combination) so join
  gaps stay visible. `first_party` records are derived from configured
  vendor-owned sitemap pages and provide only `release_date` and
  `official_url`; benchmark, price, and capability fields remain null until
  independent sources publish them.
- `data/models/history/<YYYY-MM-DD>.json` - one dated snapshot of the same
  shape per collector run, for score-delta tracking.

## Feedback loop
- `data/feedback/events.jsonl` — reader feedback events (PostHog sync + manual)
- `data/feedback/ctr_clicks.json` — per-source click counts (PostHog sync)
- `data/feedback/source_adjustments.json` — auto-tune output; applied as
  `source_tune` in ranking

## North star metric
- `data/metrics/weekly_returning_readers.json` — `{generated_at,
  reader_definition, weeks: [...]}`, one row per completed ISO week
  (`week_start`, `total_readers`, `returning_readers`, `new_readers`,
  `returning_rate`, `single_page_readers`, plus diagnostic `email_readers` /
  `email_returning_readers` on weeks synced since 2026-09-24), merged forward
  by `pipeline/north_star_metric.py sync` from PostHog pageview events
  (`$pageview` and legacy `page_view`). A reader needs
  `MIN_PAGEVIEWS_PER_WEEK` (2) pageviews in the week; `total_readers` counts
  only those, and `single_page_readers` records the excluded cohort (a
  JS-rendering crawler produces one pageview per fresh `distinct_id`).
  `reader_definition` states the rule that produced the file. See
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
  so it needs no storyline/wiki high-water mark. `follows.sent_through` is
  the storyline `last_updated` high-water mark for storyline follow alerts
  (`publish/publish_follows.py`); the follower list itself lives in Resend.
- `data/diagnostics/<date>_ranking.json` — per-day ranking diagnostics
- `data/analysis/` — one-off analysis artifacts

## Future (if a real DB is introduced)
Planned tables would mirror the above: sources, raw_items, canonical_items,
item_scores, digests, digest_items, feedback_events.

## Editorial discovery response (derived, no new persisted data file)

`GET /api/updates` retains `now`, `daily`, `weekly`, `storylines`, `playbook`,
`map`, and `foundations`, and adds `catalog_version: 1` and `items[]`.
Each item has `id`, `section`, `section_label`, `href`, `title`, `summary`,
`kind` (`article`, `edition`, `lab`), `version` (24-character content hash),
`published_at` (nullable), `updated_at`, `date_precision` (`day` or `time`),
and `period` (nullable date). It is derived from existing published artifacts
by `lib/editorial-catalog.js`; no agent-authored field is newly required.
See `docs/product-specs/nav-update-indicators.md` for source mappings, cadence,
migration, inclusion/exclusion rules and browser state.
