# AGENTS.md

Context cache for agents working in this repo. Read this before exploring —
it should answer most "where does X live / how does Y run" questions without
trial-and-error.

## Repo Mission
Build and operate an AI Platform Engineer-focused news intelligence bot
(collect → rank → digest → publish) plus a reader-facing website at
https://www.llm-digest.com (feed, daily/weekly recaps, story permalinks,
storylines, Agent Builder Foundations).

## System At A Glance
Two-tier deterministic pipeline (LLM currently **disabled** — see Gotchas):

```text
collectors/collect.py                  -> data/raw/YYYY-MM-DD/items.json
pipeline/source_health.py update       -> data/health/* (health, circuit breaker)
pipeline/source_alerts.py              -> local degradation alert artifacts/logs
pipeline/build_tier1.py                -> data/tier1/latest.json (fast quick-score, no LLM)
pipeline/build_digest.py  (Tier-0)     -> data/processed/latest.json + data/digest/*.md
   (TIER0_INPUT=tier1; full ranking via pipeline/ranking.py; incremental no-delta skip)
pipeline/story_store.py sync           -> data/stories/ (durable, append-only store)
pipeline/render_static_pages.py        -> web/{daily,weekly,story}/*.html + sitemap.xml
pipeline/build_foundations.py          -> data/foundations/index.json (deterministic concept compiler)

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
| `feed-full-publish.yml` | cron-job.org external ticker (hourly) | `run_full.sh` — the production pipeline |
| `feed-ops-summary.yml` | daily 12:30 UTC | `skills/ops-daily-summary/` health snapshot |
| `feedback-sync.yml` | daily 12:45 UTC | PostHog → `feedback.py sync-posthog`, `auto_tune.py sync-ctr` + `apply`, `north_star_metric.py sync` + `summary` (the one metric — see below) |
| `email-digest.yml` | cron-job.org (daily 23:00 UTC + weekly Fri 23:00 UTC → 08:00 KST) | `publish/publish_email.py` — finishable daily brief to the subscriber list, rendered from the **curated `/daily` recap** (`data/daily/latest.json`), NOT the raw feed (secrets-gated; the newsletter provider owns the list). Runs on its OWN schedule after the recap agent routines, NOT the hourly pipeline. Weekly recap is exec-plan v2.2 Phase 4 |

Both `feed-full-publish.yml` and `email-digest.yml` have **no GitHub `schedule:`
trigger** — they are dispatched exclusively by cron-job.org external tickers
hitting their `workflow_dispatch` endpoints (see
`docs/how-to/hourly-trigger-cron-job-org.md`). Overlapping manual dispatches are
safe (lock dir + `concurrency` group + Tier-0 no-delta skip for the feed;
cursor-based idempotency guard for email).

No GitHub Actions workflow builds storylines. The hourly feed workflow only
syncs `data/stories/`; the external Claude Code routine owns
`build_storylines.py`, scout/editor work, validation, and publishing every 5h.

Daily/weekly recaps are produced by **agent routines** (Claude Code), not
workflows: `.agents/skills/daily-summary/` and `.agents/skills/weekly-summary/`
build an input bundle, the agent writes `data/daily/<date>.json` /
`data/weekly/<week>.json`, the index builder validates + re-renders static
pages, and committing the JSON *is* publishing. The **Playbook**
(`.agents/skills/playbook/` → `/playbook`) follows the same shape — the agent
writes dated editions of actionable problem→apply→result cards to
`data/playbook/<date>.json`, validated by `build_playbook_index.py` (no static
render; the `/playbook` shell reads `/api/playbook`). The index builder also
writes `data/playbook/source-index.json`; recap renderers use it to overlay
exact-source Playbook takeaways without duplicating editorial content.

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

Agent Builder **Foundations** works like the wiki/playbook agent loop:
`.agents/skills/foundations-curator/` writes durable concept pages under
`data/foundations/concepts/*.md`; `pipeline/build_foundations.py` validates
evidence tiers and compiles `data/foundations/index.json`; `render_static_pages.py`
serves `/foundations` and `/foundations/<slug>`. The scheduled routine config is
`.agents/routines/foundations-curator-weekly/`.

**North star metric (2026-07-02, 60-day window):** every product decision is
judged against **weekly returning readers** and nothing else — see
`docs/status/north-star-metric.md` for the definition and
`docs/design-docs/decision-log.md` (2026-07-02) for the rationale.
`pipeline/north_star_metric.py sync` pulls `page_view` events from PostHog
(same HogQL pattern as `feedback.py`/`auto_tune.py`) into
`data/metrics/weekly_returning_readers.json`; `summary` prints the tracked
history. Runs daily inside `feedback-sync.yml`; the latest week also shows up
in `ops_daily_summary.py`'s log line.

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
    stories, threads, static SEO pages (incl. pre-rendered latest `/daily` and
    `/weekly` and the crawler-visible feed seed in `web/index.html`)
  - `og_cards.py` — per-edition Open Graph share cards → `web/og/*.png`
    (Pillow-optional; no-ops gracefully where Pillow is absent)
  - `build_wiki.py` — compiles the agent-engineering wiki markdown pages
    (`data/wiki/`) into the served `data/wiki/index.json` (deterministic; LLM
    synthesis is the `wiki-curator` routine's job)
  - `build_foundations.py` — compiles Agent Builder Foundations concept pages
    (`data/foundations/concepts/`) into the served `data/foundations/index.json`
  - `feedback.py`, `auto_tune.py` — reader feedback loop + source weight tuning
  - `north_star_metric.py` — weekly returning readers rollup (the one metric;
    PostHog `page_view` → `data/metrics/weekly_returning_readers.json`)
  - `telemetry.py` — server-side operational telemetry: captures pipeline
    events to PostHog over the HTTP ingestion API (`collect_run_completed`,
    `collect_source_failed`, `feed_build_completed`, `feed_build_skipped`,
    `circuit_breaker_opened`) so the feed-pipeline health scout can see cadence,
    build-skip rate, source-failure clusters, and circuit trips. Optional +
    non-fatal (no-ops without `POSTHOG_PROJECT_API_KEY`); uses `requests` and
    the project write key (`phc_…`), NOT the personal API key the read-side
    helpers use
  - `source_health.py`, `source_alerts.py`, `ops_daily_summary.py`,
    `prune_runtime_data.py` — ops
- `publish/` — `publish_email.py` (daily email brief via Buttondown/Resend broadcast;
  daily renders the curated `/daily` recap `data/daily/latest.json`, weekly the
  `/weekly` recap; secrets-gated no-op; reads/advances the
  `data/email/state.json` cursor — daily guard keys off the recap's `date`)
- `api/` — Vercel serverless functions: `feed.js`, `rss.js`, `share.js` (`/s`),
  `daily.js`, `weekly.js`, `storylines.js`, `topics.js`, `foundations.js`,
  `client-config.js`,
  `subscribe.js` (POST → Resend contacts for the email digest; reads no `data/`).
  The rest read committed `data/` files bundled via `vercel.json` `includeFiles`.
- `web/` — static site. Hand-edited shells: `index.html`, `daily.html`,
  `weekly.html`, `storyline.html` (now only the `/storylines` *index*; individual
  `/storyline/<slug>` is served from the static page below), `playbook.html`,
  `voices.html`, `subscribe.html`. Shared responsive navigation lives in
  top-level `site-chrome.css` + `site-chrome.js`: semantic fallback links are
  progressively moved into Browse/More dialogs, while date/week/edition
  controls remain visible. Generated pages receive the same chrome through
  `pipeline/render_static_pages.py`. `nav-updates.js` (shared, deferred) owns
  the "new updates" freshness signal: nav "New" pills for unread editorial
  sections plus the feed-only "Fresh from the Editor's Desk" chip strip for
  returning readers (spec: `docs/product-specs/nav-update-indicators.md`).
  **Generated, do not hand-edit:** `web/daily/`, `web/weekly/`, `web/story/`,
  `web/storyline/`, `web/topic/`, `web/foundations/`, `web/map.html`,
  `web/foundations.html`, `sitemap.xml` (from
  `render_static_pages.py`). The bare `/daily` and `/weekly` URLs serve the
  pre-rendered latest edition (`web/daily/index.html`, `web/weekly/index.html`),
  not the client shells, so shares/crawlers see content; the `index.html` feed
  shell contains a generated `<!-- feed-seed:start/end -->` region (crawler/
  no-JS snapshot of the top ranked items — hand-edit outside the markers only).
  `web/og/` holds per-edition Open Graph share cards from `pipeline/og_cards.py`
  (Pillow-optional; degrades to the committed/default card where absent).
  Brand assets:
  `favicon.svg` (hand-authored), `og-default.png` + `logo.png` (from
  `scripts/make_og_assets.py`). Also `robots.txt`, `llms.txt`, `llm-guide.txt`.
  `mascot/mascot.js` — "Bubble Buddy", the decorative WebGL/Three.js mascot
  (lazy-loaded on idle, motion-respecting, parks render loop between random
  appearances; loader snippet lives in the five shells + the
  `render_static_pages.py` template). Fully defensive — any failure no-ops.
  **Portable/modular**: a `createBubbleBuddy(options)` factory (ESM export) —
  drop-in (auto floating mascot), declarative (`[data-bubble-buddy]` anchors),
  or programmatic (`mount`/`position`/`colors`/instance API). Multiple instances
  OK; Three.js imported once and shared. Usage docs: `web/mascot/README.md`.
- `config/` — runtime knobs:
  - `ranking.yaml` — canonical ranking config; `preset:` key deep-merges
    `config/presets/<name>.yaml` under local overrides
  - `sources.yaml` (feeds + weights), `profile.yaml` (relevance keywords),
    `llm.yaml` (**enabled: false**), `user_preferences.yaml`, `config/prompts/`
  - `wiki_schema.md` — contract for the agent-engineering wiki (obstacle areas,
    page format, ingest/lint/query ops, `build_wiki.py` invariants)
  - `foundations_schema.md` — contract for Agent Builder Foundations concept
    pages, evidence tiers, and `build_foundations.py` invariants
- `scripts/` — `git_commit_runtime.sh` (data-only commits),
  `git_commit_code.sh` (code/docs commits), `llm_bridge.mjs`, `oauth_login.sh`
  (legacy), `compare_v1_v2.py`, `make_og_assets.py` (regenerates the social
  card + logo PNGs; run only when the brand/tagline changes)
- `skills/` — local run helpers: `ai-feed-digest-local/` (`run_full.sh`,
  `run_dev.sh`, `run_tier1_fast.sh`), `ops-daily-summary/`
- `.agents/skills/` — agent recap routines: `daily-summary/`, `weekly-summary/`,
  `storyline-editor/` (narrates cross-day threads into a sidecar the pipeline
  overlays), `storyline-scout/` (proposes thread links the clustering missed,
  applied through the deterministic floor), `wiki-curator/` (LLM-wiki routine:
  ingests new stories into the cross-linked obstacle→solution markdown pages
  under `data/wiki/`, then `build_wiki.py` compiles + validates them — serves
  `/map` and `/topic/<slug>`), `playbook/` (writes dated **Playbook editions** —
  actionable problem→apply→result cards for agent builders — to
  `data/playbook/<date>.json`, validated by `build_playbook_index.py`; serves
  `/playbook`), `foundations-curator/` (writes durable evidence-tiered concept
  explanations to `data/foundations/concepts/*.md`, validated by
  `build_foundations.py`; serves `/foundations`), `add-source/` (add a feed source
  end-to-end + `validate_source.py` to prove it clears the ranking exposure
  gates and reaches the feed), `writing-style/` (no scripts — the shared prose
  contract referenced by the reader-facing content skills above: BLUF, one
  idea per paragraph, scannability, specifics over generalities)
  (SKILL.md = agent contract + recap JSON schema; some symlinked into `.claude/skills/`)
- `.agents/routines/` — repository-owned external scheduler definitions.
  Each routine directory separates scheduler-only `harness.yaml` metadata from
  the agent-visible `prompt.md`; `COMMON.md` owns shared checkout, validation,
  commit, rebase/retry, and direct-to-`main` publishing rules. Harness metadata
  must not be injected into agent context.
- `data/` — generated runtime artifacts (committed by bots; see Data Artifacts)
- `docs/` — living documentation:
  - `docs/status/` — operational snapshots (`current-system-state.md`,
    `git-hygiene.md`, `tuning-governance.md`, `north-star-metric.md`)
  - `docs/how-to/` — playbooks (source/filter debugging, PostHog setup)
  - `docs/deploy/` — Vercel deployment notes
  - `docs/product-specs/` — behavior specs (feedback-loop, llm-ranking, onboarding)
  - `docs/design-docs/` — `decision-log.md` (ADR log), `core-beliefs.md`
  - `docs/ideas/` — confirmed concept one-pagers before backlog ideas become
    implementation-ready specs or execution plans
  - `docs/exec-plans/` — execution plans (`active/`, `completed/`, tech-debt tracker)
  - `docs/generated/` — derived references (`db-schema.md` = data file layout)
  - `docs/references/` — vendored third-party LLM-friendly references
  - root docs — `ranking-v2-flow.md` (production ranking flow), `DESIGN.md`,
    `FRONTEND.md`, `PRODUCT_SENSE.md`, `QUALITY_SCORE.md`, `RELIABILITY.md`,
    `SECURITY.md`, `PLANS.md` (current roadmap), `BACKLOGS.md` (durable,
    unscheduled product/engineering ideas with promotion criteria), scoring-v2
    plans (historical)
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
- `data/wiki/` — agent-engineering knowledge wiki: `{obstacles,solutions}/*.md`
  source pages (LLM-curated; the source of truth), `index.json` (compiled by
  `build_wiki.py`; the only file served/bundled), `index.md` (catalog), `log.md`
  (append-only activity), `input/` ingest bundles. Schema: `config/wiki_schema.md`
- `data/daily/`, `data/weekly/` — recap JSONs + `input/` bundles + indices
- `data/foundations/` — Agent Builder Foundations: `concepts/*.md` source pages
  (agent-curated source of truth), `index.json` compiled by
  `build_foundations.py`, and `input/` bundles for the curator routine. Served at
  `/foundations` and `/foundations/<slug>`. Schema: `config/foundations_schema.md`
- `data/playbook/` — agent-written **Playbook editions** (`<date>.json`:
  actionable problem→apply→result cards) + `index.json`/`latest.json` +
  `source-index.json` (source-backed cards keyed by story sid) + `input/`
  bundles (excluded from deploys). Served at `/playbook`; source-backed cards
  may appear inline in capped daily/weekly recap overlays
- `data/feedback/` — `events.jsonl`, `ctr_clicks.json`, `source_adjustments.json`
- `data/metrics/` — `weekly_returning_readers.json`: durable weekly history for
  the north-star metric (`pipeline/north_star_metric.py`). Schema/rationale:
  `docs/status/north-star-metric.md`
- `data/health/` — `source_health.json`, `circuit_breaker.json`,
  `alerts_state.json`, `ingest_runs.jsonl`
- `data/email/state.json` — email-digest send cursor (high-water marks for
  daily/storyline/wiki deltas; **no subscriber PII** — the provider owns the list)
- `data/llm/labels.json` (cache), `data/cache/`, `data/diagnostics/`, `data/analysis/`
- Retention: processed 45d (daily/weekly archive tail), tier1 **3d hard cap**
  (deleted outright, no archive tail — tier1 snapshots are ~1.5–1.9 MB each).
  Env-tunable via `prune_runtime_data.py`, run automatically in `run_full.sh`.
  **Heavy runtime dirs are kept out of Vercel via `.vercelignore`**
  (`data/raw`, `data/tier1/runs`, `data/llm`, `data/health`, `data/digest`,
  `data/diagnostics`, `data/cache`, `data/analysis`). Vercel bundles the whole
  uploaded project into *each* serverless function, so once `data/` grew
  (`tier1/runs` ~175 MB at ~30 runs/day, `data/raw` ~125 MB) functions blew
  past the 250 MB unzipped limit and froze all deploys. These dirs are read by
  neither the static build nor any function at request time (`feed.js` falls
  back to `tier1/latest.json` when the runs are absent), so they stay in git
  (audit/replay) but ship out of the deployment. See the 2026-06-19 ADR.

## Web Surface (vercel.json rewrites)
`/` feed · `/daily[/<date>]` · `/weekly[/<week>]` · `/storylines` ·
`/storyline/<slug>` · `/story/<sid>` (sid = sha256(url)[:16]) · `/subscribe`
(email digest signup) · `/map` (wiki index) · `/topic/<slug>` (wiki node) ·
`/foundations` / `/foundations/<slug>` (evidence-tiered concept explanations) ·
`/playbook` (actionable agent-builder cards) ·
`/voices` · `/s?u=<url>` share redirect ·
`/rss.xml` · `/sitemap.xml` · `/llms.txt` ·
APIs: `/api/feed`, `/api/rss`, `/api/share`, `/api/daily`, `/api/weekly`,
`/api/storylines`, `/api/topics`, `/api/foundations`, `/api/playbook`,
`/api/client-config`, `/api/updates`
(lightweight freshness signals powering the nav "new updates" pills and
the feed's "Fresh from the Editor's Desk" strip),
`/api/subscribe` (POST email → Resend global contacts; needs only EMAIL_API_KEY,
503 when unconfigured).

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

## Product Positioning (decided 2026-06-13; audience widened 2026-06-21)
The target audience is **engineers who build and operate AI systems** —
**AI platform engineers and agent builders/engineers**. These overlap heavily
(the person standing up RAG, tool-calling, evals, and inference infra is usually
the same person shipping agents on top of it), and we already curate for agent
builders via the agent-engineering wiki (`/map`, `/topic/<slug>`). Danu (the
owner) is one himself and built llm-digest.com from his own need, so "would the
owner read this every morning and save time" is the primary quality bar.

This widening is a **rename of who we already serve, not a broadening of scope**.
The audience explicitly does NOT include prompt hobbyists, no-code agent users,
or general AI-news readers. Agent-builder content means the engineering of agent
systems (orchestration, tool use, evals, memory, cost/latency, safety) — never
framework churn, prompt-tip listicles, or "10 prompts" content. The quality bar
is unchanged; only the audience label is wider.

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

Tagline shape: "The finishable AI feed for platform & agent engineers —
10 minutes a day, with memory."

Implications for any change in this repo:
- Site copy, source selection, and ranking tuning (`config/profile.yaml`)
  optimize for the platform-/agent-engineer lens and the catch-up job — never
  for breadth, engagement, or generic AI news. Niche drift erases the advantage.
- The audience widening is **copy-only for now** (2026-06-21): no ranking or
  source re-tune was made. Adding agent-engineering sources/keywords is a
  deliberate, separate change — keep it to the engineering-of-agents lens above.
- Storylines and recap pages are the shareable growth artifacts (shared *into*
  HN/Slack/Reddit); invest there before feed features.
- Distribution targets places platform & agent engineers already are; we don't
  build community features.

## Working Rules
- Keep changes small and shippable.
- Prefer deterministic ranking logic before LLM layers.
- Never commit secrets or tokens (email/PostHog config comes from env/secrets).
- Add/update docs with every meaningful feature change.
- If you add a new feature or a new document category, update docs index/links
  in the same PR.
- Follow git hygiene: commit code/config/docs separately from generated runtime data.
- Keep agent-facing prompts (`.agents/routines/*/prompt.md`, `.agents/skills/*/SKILL.md`)
  imperative: state what to do, not why. Rationale belongs in
  `docs/design-docs/decision-log.md` (or a code comment next to the logic it
  explains) — not in the prompt the agent reads on every run.

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
- Fail gracefully when optional integrations are missing (email/PostHog
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
- Vercel runs `python3 scripts/vercel_build.py` as its build command. It
  regenerates static story/recap/storyline pages from committed data and stages
  `web/` under the configured `public/` output directory. This keeps code-only
  renderer PR previews accurate without committing 1,000+ generated files.
- Every PR gets an automatic **Vercel preview deployment** — use the preview
  URL posted on the PR to eyeball UI changes before merge.
- Merging to `main` triggers the production deploy. The hourly data commits
  also trigger deploys — that is how fresh feed data reaches the site (the
  serverless functions read committed `data/` files; there is no database).
