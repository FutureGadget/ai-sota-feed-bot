# AGENTS.md

Context cache for agents working in this repo. Read this before exploring —
it should answer most "where does X live / how does Y run" questions without
trial-and-error.

## Repo Mission
Build and operate an AI Platform Engineer-focused news intelligence bot
(collect → rank → digest → publish) plus a reader-facing website at
https://www.llm-digest.com (feed, daily/weekly recaps, story permalinks,
storylines).

## System At A Glance
Two-tier deterministic pipeline (LLM currently **disabled** — see Gotchas):

```text
collectors/collect.py                  -> data/raw/YYYY-MM-DD/items.json
pipeline/source_health.py update       -> data/health/* (health, circuit breaker)
pipeline/source_alerts.py              -> degradation alerts (Telegram critical-only)
pipeline/build_tier1.py                -> data/tier1/latest.json (fast quick-score, no LLM)
pipeline/build_digest.py  (Tier-0)     -> data/processed/latest.json + data/digest/*.md
   (TIER0_INPUT=tier1; full ranking via pipeline/ranking.py; incremental no-delta skip)
pipeline/story_store.py sync           -> data/stories/ (durable, append-only store)
pipeline/render_static_pages.py        -> web/{daily,weekly,story}/*.html + sitemap.xml
publish/publish_issue.py               -> GitHub Issue "Daily AI Digest - YYYY-MM-DD"
publish/publish_telegram.py            -> Telegram digest (optional, secrets-gated)

Claude Code storyline routine (every 5h, outside GitHub Actions):
pipeline/build_storylines.py           -> data/storylines/ (deterministic threads)
storyline-scout + storyline-editor      -> links + narratives, validate, rebuild, publish
```

Feed production entry point: `skills/ai-feed-digest-local/scripts/run_full.sh`
(runs the hourly feed chain above, excluding storyline generation; prunes old
snapshots, commits `data/` + `web/`, and pushes when `AUTO_PUSH_RUNTIME=1`).

## Automation (what actually runs)
| Workflow (`.github/workflows/`) | Schedule | Does |
|---|---|---|
| `feed-full-publish.yml` | hourly cron (`37 * * * *`) + external ticker | `run_full.sh` — the production pipeline |
| `feed-ops-summary.yml` | daily 12:30 UTC | `skills/ops-daily-summary/` health snapshot |
| `feedback-sync.yml` | daily 12:45 UTC | PostHog → `feedback.py sync-posthog`, `auto_tune.py sync-ctr` + `apply` |
| `hourly-ingest.yml` | **disabled** (dispatch only) | legacy collect+score |
| `daily-digest.yml` | dispatch only | legacy manual digest+publish |

The GitHub `schedule` is best-effort (deprioritized at `:00`, drops hours), so
`feed-full-publish.yml` also runs at `37 * * * *` and is triggered for *real*
hourly cadence by an external cron-job.org ticker hitting the workflow's
`workflow_dispatch` endpoint — see
`docs/how-to/hourly-trigger-cron-job-org.md`. Both triggers are safe to overlap
(lock dir + `concurrency` group + Tier-0 no-delta skip).

No GitHub Actions workflow builds storylines. The hourly feed workflow only
syncs `data/stories/`; the external Claude Code routine owns
`build_storylines.py`, scout/editor work, validation, and publishing every 5h.

Daily/weekly recaps are produced by **agent routines** (Claude Code), not
workflows: `.agents/skills/daily-summary/` and `.agents/skills/weekly-summary/`
build an input bundle, the agent writes `data/daily/<date>.json` /
`data/weekly/<week>.json`, the index builder validates + re-renders static
pages, and committing the JSON *is* publishing.

Storyline narratives work the same way (`.agents/skills/storyline-editor/`): the
agent reads the mechanically-built threads and writes a durable **narrative
sidecar** `data/storylines/narratives/<slug>.json` (TL;DR arc, what's-new,
why-it-matters, per-item notes). The 5-hour routine runs
`build_storylines.py`, which deterministically *overlays* a fresh sidecar onto
the served files. A `covers_*` snapshot in each sidecar lets the routine detect
and refresh a narrative once the thread moves on.

Storyline **recall** is a second routine (`.agents/skills/storyline-scout/`): the
precision-first clustering only links stories on a shared *rare anchor word*, so
it misses real threads (same launch under different wording; near-miss threads
under the floor). `pipeline/scout_candidates.py` emits candidates; the agent
(Haiku judges) confirms thread **links** to `data/storylines/scout/links.json`;
`build_storylines.py` applies each link as a synthetic candidate **through the
same MIN_ITEMS/DAYS/SOURCES floor** (the deterministic gate — no link bypasses
it) and badges the result `via_scout`. The agent never decides what becomes a
storyline; it only proposes links the floor then judges.

## Repository Structure Index
- `collectors/collect.py` — single ingestion job (RSS/sitemap/arXiv/GitHub
  releases, normalization, dedupe, crawl cooldown per source)
- `pipeline/` — all processing:
  - `ranking.py` — unified ranking engine (stage A prefilter → slot assignment
    → stage C scoring → global merge → top-band constraints)
  - `build_tier1.py` (fast snapshot) / `build_digest.py` (Tier-0 full build)
  - `enrich.py`, `content_fetch.py` — mechanical enrichment, page excerpts
  - `llm_label.py`, `llm_rerank.py` — no-op placeholders while LLM disabled
  - `story_store.py`, `build_storylines.py`, `render_static_pages.py` — durable
    stories, threads, static SEO pages
  - `feedback.py`, `auto_tune.py` — reader feedback loop + source weight tuning
  - `source_health.py`, `source_alerts.py`, `ops_daily_summary.py`,
    `prune_runtime_data.py` — ops
- `publish/` — `publish_issue.py` (GitHub Issue), `publish_telegram.py`
- `api/` — Vercel serverless functions: `feed.js`, `rss.js`, `share.js` (`/s`),
  `daily.js`, `weekly.js`, `storylines.js`, `client-config.js`. They read
  committed `data/` files bundled via `vercel.json` `includeFiles`.
- `web/` — static site. Hand-edited shells: `index.html`, `daily.html`,
  `weekly.html`, `storyline.html`, `voices.html`. **Generated, do not hand-edit:**
  `web/daily/`, `web/weekly/`, `web/story/`, `sitemap.xml` (from
  `render_static_pages.py`). Also `robots.txt`, `llms.txt`, `llm-guide.txt`.
- `config/` — runtime knobs:
  - `ranking.yaml` — canonical ranking config; `preset:` key deep-merges
    `config/presets/<name>.yaml` under local overrides
  - `sources.yaml` (feeds + weights), `profile.yaml` (relevance keywords),
    `llm.yaml` (**enabled: false**), `user_preferences.yaml`, `config/prompts/`
- `scripts/` — `git_commit_runtime.sh` (data-only commits),
  `git_commit_code.sh` (code/docs commits), `llm_bridge.mjs`, `oauth_login.sh`
  (legacy), `compare_v1_v2.py`
- `skills/` — local run helpers: `ai-feed-digest-local/` (`run_full.sh`,
  `run_dev.sh`, `run_tier1_fast.sh`), `ops-daily-summary/`
- `.agents/skills/` — agent recap routines: `daily-summary/`, `weekly-summary/`,
  `storyline-editor/` (narrates cross-day threads into a sidecar the pipeline
  overlays), `storyline-scout/` (proposes thread links the clustering missed,
  applied through the deterministic floor)
  (SKILL.md = agent contract + recap JSON schema)
- `data/` — generated runtime artifacts (committed by bots; see Data Artifacts)
- `docs/` — living documentation:
  - `docs/status/` — operational snapshots (`current-system-state.md`,
    `git-hygiene.md`, `tuning-governance.md`)
  - `docs/how-to/` — playbooks (source/filter debugging, PostHog setup)
  - `docs/deploy/` — Vercel deployment notes
  - `docs/product-specs/` — behavior specs (feedback-loop, llm-ranking, onboarding)
  - `docs/design-docs/` — `decision-log.md` (ADR log), `core-beliefs.md`
  - `docs/exec-plans/` — execution plans (`active/`, `completed/`, tech-debt tracker)
  - `docs/generated/` — derived references (`db-schema.md` = data file layout)
  - `docs/references/` — vendored third-party LLM-friendly references
  - root docs — `ranking-v2-flow.md` (production ranking flow), `DESIGN.md`,
    `FRONTEND.md`, `PRODUCT_SENSE.md`, `QUALITY_SCORE.md`, `RELIABILITY.md`,
    `SECURITY.md`, `PLANS.md`, scoring-v2 plans (historical)
- Root: `Makefile` (minimal legacy targets; prefer `skills/` scripts),
  `vercel.json` (rewrites + function data bundles), `requirements.txt` (Python
  deps: feedparser/PyYAML/dateutil/requests), `package.json` (LLM bridge dep only)

## Data Artifacts (committed runtime state)
- `data/raw/<date>/items.json` — collector output
- `data/tier1/` — `latest.json`, `runs/`, `runs_index.json` (fast tier)
- `data/processed/` — `latest.json` (the feed), `runs/`, `runs_index.json`
- `data/digest/<date>.md` — daily digest markdown
- `data/stories/<YYYY-MM>.json` + `index.json` — durable story store
- `data/storylines/<slug>.json` + `index.json` — threads (with `editorial`
  overlay when narrated, `via_scout` when surfaced by the scout);
  `narratives/<slug>.json` agent-written sidecars + `input/` bundles;
  `scout/{candidates,links}.json` recall candidates + confirmed links
- `data/daily/`, `data/weekly/` — recap JSONs + `input/` bundles + indices
- `data/feedback/` — `events.jsonl`, `ctr_clicks.json`, `source_adjustments.json`
- `data/health/` — `source_health.json`, `circuit_breaker.json`,
  `alerts_state.json`, `ingest_runs.jsonl`
- `data/llm/labels.json` (cache), `data/cache/`, `data/diagnostics/`, `data/analysis/`
- Retention: processed 45d (daily/weekly archive tail), tier1 **3d hard cap**
  (deleted outright, no archive tail — tier1 snapshots are ~1.5 MB each and
  bundled into the Vercel feed/rss functions, which only read tier1 for a 24h
  fresh-blend). Env-tunable via `prune_runtime_data.py`, run automatically in
  `run_full.sh`.

## Web Surface (vercel.json rewrites)
`/` feed · `/daily[/<date>]` · `/weekly[/<week>]` · `/storylines` ·
`/storyline/<slug>` · `/story/<sid>` (sid = sha256(url)[:16]) · `/voices` ·
`/s?u=<url>` share redirect · `/rss.xml` · `/sitemap.xml` · `/llms.txt` ·
APIs: `/api/feed`, `/api/rss`, `/api/share`, `/api/daily`, `/api/weekly`,
`/api/storylines`, `/api/client-config`.

## Gotchas (cache these, they cost tokens to rediscover)
- **LLM is disabled** (`config/llm.yaml → enabled: false`). The pipeline runs
  fully deterministic/heuristic; `llm_label.py`/`llm_rerank.py` are kept as
  explicit no-op interfaces for future re-enable. Don't "fix" missing LLM calls.
- The ranking engine was renamed from "v2" to the only path: module is
  `pipeline/ranking.py`, config is `config/ranking.yaml`. Any reference to
  `ranking_v2.yaml` or `pipeline/ranking_v2.py` is historical.
- `web/story/`, `web/daily/`, `web/weekly/`, `web/sitemap.xml` are build
  outputs of `render_static_pages.py` — regenerate, never hand-edit.
- API functions only see `data/` files listed in `vercel.json` `includeFiles`;
  a new data dir an API needs requires a `vercel.json` change in the same PR.
- `run_full.sh` takes a lock dir (`.run_full.lock`), skips push on a dirty
  worktree, and short-circuits when Tier-0 reports no delta
  (`FULL_RUN_NO_DELTA_SKIP=true`) — these are intentional safety behaviors.
- Hourly data commits (`chore(data): refresh feed artifacts …`) are bot
  traffic on `main`; expect rebases when pushing. Keep code commits separate
  from runtime-data commits (`scripts/git_commit_code.sh` vs
  `scripts/git_commit_runtime.sh`; see `docs/status/git-hygiene.md`).

## Product Positioning (decided 2026-06-13)
The target audience is **AI platform engineers** — and only them. Danu (the
owner) is one himself and built llm-digest.com from his own need, so "would the
owner read this every morning and save time" is the primary quality bar.

We deliberately do NOT compete with SNS/X (freshness), Google News (algorithmic
personalization), or HN/GeekNews (community). The position is built on the jobs
those products are structurally bad at:

1. **Finishable** — a ranked, deduped daily brief that *ends* ("read 12 items,
   you're caught up"), vs. infinite engagement-optimized feeds.
2. **Transparent / anti-hype** — one shared deterministic ranking for everyone,
   🫧 hype flagging, source reliability tracking, and visible reader-tuning
   (Reader-boosted badges). Explicitly not a personalized filter bubble; pinned
   topics are a lens, not a bubble.
3. **Memory** — storylines ("what happened next with X"), daily/weekly recaps
   ("what did I miss this week"), and durable `/story/<sid>` permalinks. This
   continuity layer is the structural moat: timelines and community threads
   forget; we don't.

Tagline shape: "The finishable AI feed for platform engineers — 10 minutes a
day, with memory."

Implications for any change in this repo:
- Site copy, source selection, and ranking tuning (`config/profile.yaml`)
  optimize for the platform-engineer lens and the catch-up job — never for
  breadth, engagement, or generic AI news. Niche drift erases the advantage.
- Storylines and recap pages are the shareable growth artifacts (shared *into*
  HN/Slack/Reddit); invest there before feed features.
- Distribution targets places platform engineers already are; we don't build
  community features.

## Working Rules
- Keep changes small and shippable.
- Prefer deterministic ranking logic before LLM layers.
- Never commit secrets or tokens (Telegram/PostHog config comes from env/secrets).
- Add/update docs with every meaningful feature change.
- If you add a new feature or a new document category, update docs index/links
  in the same PR.
- Follow git hygiene: commit code/config/docs separately from generated runtime data.

## Documentation Contract
When implementing a feature:
1. Update architecture/flow docs if system flow/components changed
   (`ARCHITECTURE.md`, `docs/ranking-v2-flow.md` and related docs).
2. Update at least one of:
   - `docs/product-specs/*` for product behavior
   - `docs/design-docs/*` for design decisions
   - `docs/exec-plans/*` for execution tracking
   - `docs/status/*` for current operating state changes
3. If the data artifact layout changes, update `docs/generated/db-schema.md`.
4. If you add a new documentation category (new subdirectory under `docs/`),
   add it to the Repository Structure Index in this file and link it from
   README where relevant.

## Project Memory Rule (Working Directory Scope)
- While working in this repository, treat this `AGENTS.md` as mandatory context
  before making changes.
- Keep a running decision log in `docs/design-docs/decision-log.md` for
  architecture/ranking/publishing choices.
- For each non-trivial change, write a short ADR-style entry: date, decision,
  rationale, impact, rollback plan.

## Engineering Guardrails
- Keep workflows idempotent and observable (pipelines log machine-greppable
  `key=value` signals like `FULL_RUN_OK`, `v2_stats`, `runtime_commit_done`).
- Fail gracefully when optional integrations are missing (Telegram/PostHog
  secrets) — every publish/sync step must no-op cleanly without them.
- Prefer config-driven behavior (`config/*.yaml`) over hardcoding.

## Release Rhythm
- `main` always runnable.
- The hourly `feed-full-publish` workflow must remain green.
- New features should include a validation path (local run via
  `skills/ai-feed-digest-local/scripts/run_dev.sh` or a workflow run).

## Deployment (Vercel)
- The site (`web/` pages + `api/` serverless functions) auto-deploys to Vercel.
  Config lives in `vercel.json`. Production domain: `https://www.llm-digest.com`
  (apex redirects to www).
- Every PR gets an automatic **Vercel preview deployment** — use the preview
  URL posted on the PR to eyeball UI changes before merge.
- Merging to `main` triggers the production deploy. The hourly data commits
  also trigger deploys — that is how fresh feed data reaches the site (the
  serverless functions read committed `data/` files; there is no database).
