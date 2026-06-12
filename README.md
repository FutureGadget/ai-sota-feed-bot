# AI SOTA Feed Bot (Prototype)

GitHub-first prototype for AI platform engineering news intelligence.

## What it does
- Collects fresh items from high-signal RSS feeds
- Normalizes and de-duplicates (URL + near-title similarity)
- Mechanical (no-LLM) enrichment (`pipeline/enrich.py`):
  - Release titles get a repo prefix (`0.139.0` → `codex 0.139.0`)
  - Release summaries use extracted changelog bullets (`release_highlights`)
  - `why_it_matters` is only set from real signal (LLM text or matched
    `matched_topics` keywords) — no generic placeholder
  - Cross-source duplicates surface as `also_covered` ("Also covered by …")
    instead of being dropped silently
- Scores/ranks items for AI platform relevance
- Applies diversity-aware ranking (strict minimum mix + caps for paper/news/release)
- Tracks source reliability/health and incorporates it into ranking
- Applies source circuit breaker on repeated failures with cooldown auto-recovery
- Sends low-noise degradation alerts; Telegram delivery is critical-only by default
- Builds a Markdown digest
- Publishes digest as:
  - versioned file in `data/digest/`
  - GitHub Issue (`Daily AI Digest - YYYY-MM-DD`)
  - Telegram mobile-friendly digest (top list + compact remainder)
- Publishes a weekly "What happened in AI this week" recap at `/weekly` (see below)

## Weekly recap (`/weekly`)
A reader-facing weekly summary page rendered from `data/weekly/<week>.json`.
The recap content is produced by an agent (a Claude Code routine) using the
`weekly-summary` skill in `.agents/skills/weekly-summary/` — committing the JSON
to the repo is how it gets "posted".

Pipeline:
```bash
S=.agents/skills/weekly-summary/scripts
python $S/build_weekly_input.py     # 1. bundle the week's unique news items -> data/weekly/input/
#                                      (news-only by default; --types all to include papers/releases)
#                                     2. agent reads the bundle, writes data/weekly/<week>.json
python $S/build_weekly_index.py     # 3. validate + rebuild data/weekly/{index,latest}.json
#                                      (also re-renders static /weekly pages + sitemap, see below)
# 4. git add data/weekly/ web/weekly/ web/sitemap.xml && git commit && git push
```
- Page: `/weekly` (latest), `/weekly/<week>` (archive). API: `/api/weekly[?week=|?list=1]`.
- Smoke-test the UI with a placeholder recap: `bash $S/run_weekly.sh --seed`
- Agent contract + schema: `.agents/skills/weekly-summary/SKILL.md`

## Quick start
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python collectors/collect.py
python pipeline/build_digest.py
python publish/publish_issue.py --repo FutureGadget/ai-sota-feed-bot --date $(date +%F)
```

## Optional Telegram publish
```bash
export TELEGRAM_BOT_TOKEN=xxx
export TELEGRAM_CHAT_ID=xxx
export TELEGRAM_MAX_ITEMS=12    # optional
export TELEGRAM_TOP_WHY=5       # optional
python publish/publish_telegram.py
```

To surface "subscribe to the daily digest" CTAs on the website, set
`DIGEST_TELEGRAM_URL` (a public channel link like `https://t.me/your_channel`)
in the Vercel environment. Optionally set `DIGEST_EMAIL_SIGNUP_URL` (e.g. a
Buttondown/RSS-to-email signup page) to add an email option. The respective
CTAs stay hidden when unset; RSS is always offered.

Current web app behavior:
- Subscribe is a first-class action: a 🔔 menu in the feed header offers
  RSS (`/rss.xml`, always), the Telegram digest, and email signup (when
  configured). Returning visitors get a one-time dismissible subscribe nudge
  after the 3rd story (first visits get topic onboarding instead). Events:
  `subscribe_menu_open`, `subscribe_click` (channel + placement),
  `subscribe_nudge_dismiss`. All pages carry RSS autodiscovery for `/rss.xml`.
- Sends batched `impression` events to PostHog on feed render
- Sends `click` events to PostHog when opening an item link
- One-tap reader feedback on every feed card (`👍 Useful / 👎 Not relevant / 🫧 Hype`),
  persisted in localStorage and sent to PostHog as `item_feedback`
- Feedback is visibly closed-loop: the feed API exposes the auto-tune output
  (`reader_tuning` block + per-item `reader_adjustment` from
  `data/feedback/source_adjustments.json`); clearly boosted sources
  (adjustment ≥ 0.05) get a `👍 Reader-boosted` badge on their cards, and the
  footer states how many sources reader feedback boosted/downweighted and when
- Trending badges on feed cards: `🔥 N sources` (cross-source coverage from
  `also_covered`) and `📈 Climbing` (rank improved ≥2 positions between the two
  most recent runs, via `rank_at_last_seen` vs `rank_prev_seen`)
- Pinned "my topics": readers can pin the current label selection as their
  default (localStorage); it auto-applies on visits without `?label=` in the
  URL, with a one-tap re-apply chip after clearing filters (`labels_pin` event)
- Share permalinks (growth loop): the 📤 button shares `/s?u=<source url>`
  (`api/share.js`) instead of the source article, so shares land readers on
  this site. When the story has a durable `/story/<sid>` page (see below) the
  endpoint redirects there, so old share links never go dead. Otherwise it
  serves item-specific OG/Twitter tags to unfurlers and redirects humans to
  `/?item=<url>&utm_source=share`, where the feed scrolls to and highlights
  the story (widening the window once to 30 days if needed; pinned topics are
  suspended so they can't hide it). Events: `item_share`, `share_landing`
- Uses per-item batch/run context for telemetry (`ingest_batch_id` preferred, fallback to run timestamp)
- PostHog tracking for dashboarding (`page_view`, `feed_view`, `impression_batch`, `click`, `item_feedback`)

PostHog env vars (optional):
- `POSTHOG_ENABLED=1`
- `POSTHOG_PROJECT_API_KEY=<project key>`
- `POSTHOG_HOST=https://us.i.posthog.com` (or EU host)

## Reader feedback loop (v1.3)
Reader taps land in `data/feedback/events.jsonl` via a daily PostHog sync
(`.github/workflows/feedback-sync.yml`); future tuning consumes the aggregates.
```bash
python pipeline/feedback.py add --url <item_url> --signal useful|irrelevant|hype  # manual entry
python pipeline/feedback.py summary [--days N]      # net counts by signal/source
python pipeline/feedback.py sync-posthog            # pull web events (needs env below)
```
Sync env vars: `POSTHOG_PERSONAL_API_KEY`, `POSTHOG_PROJECT_ID`, optional
`POSTHOG_API_HOST` (query API host, default `https://us.posthog.com`).
Spec: `docs/product-specs/feedback-loop.md`.

Source weight auto-tuning (v1.3) consumes the feedback plus click-through
signal and writes capped per-source score adjustments the ranking pipeline
applies next to `source_bias` (knobs: `config/ranking.yaml` → `auto_tune:`):
```bash
python pipeline/auto_tune.py sync-ctr   # pull per-source clicks from PostHog
python pipeline/auto_tune.py report     # dry-run: proposed adjustments + inputs
python pipeline/auto_tune.py apply      # write data/feedback/source_adjustments.json
```

Feed API (v1):
- Tier-1 freshness blend options: `blend_tier1=0|1` (default 1), `tier1_fresh_cap` (default 4)
- Additional blend guards: `tier1_insert_after` (default 3), `tier1_min_quick_score` (default 2.6), `tier1_max_per_source` (default 1)
- Per-item rank trajectory: `rank_at_last_seen` (newest run) and `rank_prev_seen` (previous run that included the item)

## SEO / static recap pages (growth loop)
The `/daily` and `/weekly` pages are client-rendered shells, invisible to
crawlers and link unfurlers. `pipeline/render_static_pages.py` therefore
pre-renders every published recap into fully static, indexable pages:
- `web/daily/<date>.html` → served at `/daily/<date>`
- `web/weekly/<week>.html` → served at `/weekly/<week>`
- `web/story/<sid>.html` → served at `/story/<sid>` (story permalinks, below)
- `web/sitemap.xml` → `/sitemap.xml`, `web/robots.txt` → `/robots.txt`

Each page carries a real title, meta description, canonical URL, Open
Graph/Twitter cards, JSON-LD, and RSS autodiscovery, and mirrors the dynamic
pages' design. The index builders (`build_daily_index.py` /
`build_weekly_index.py`) invoke the renderer automatically, so publishing a
recap always refreshes the static pages — commit `web/daily/`, `web/weekly/`,
`web/story/`, and `web/sitemap.xml` alongside `data/`. Base URL override:
`--base-url` or `SITE_BASE_URL` (default `https://www.llm-digest.com`).

### Story permalink pages (growth loop)
Every story that makes a published feed snapshot gets a durable, indexable
page at `/story/<sid>` (`sid = sha256(normalized url)[:16]`, derivable from
the URL alone). Feed snapshots are pruned after ~45 days, so
`pipeline/story_store.py sync` first captures each story into an append-only
store (`data/stories/<YYYY-MM>.json` + a compact `index.json` the share
endpoint bundles), and the static renderer turns the store into pages: title
(linking out to the source), why-it-matters, summary or release highlights,
topics, "also covered by", related stories (internal links), and links into
the live feed and that day's recap. Recap pages link each article's `Details`
badge to its story page, and `/s` share links redirect there, so shares and
search hits land on pages that never expire. Both steps run in
`run_full.sh` every cycle:
```bash
python pipeline/story_store.py sync        # upsert stories from processed runs
python pipeline/render_static_pages.py     # render recap + story pages + sitemap
```

LLM discovery endpoints:
- `/llms.txt` (LLM-oriented site map + API usage notes)
- `/llm-guide.txt` (deeper instructions for feed navigation/debugging)

Tier-0 input source toggle:
- `TIER0_INPUT=tier1|raw` (default `tier1`, with automatic raw fallback)
- Incremental diagnostics toggle: `TIER0_INCREMENTAL=1` (default on)
- Optional no-delta short-circuit: `TIER0_INCREMENTAL_SKIP_NO_DELTA=1` (default off)

Collector crawl cooldown controls:
- `COLLECT_DEFAULT_POLL_MINUTES` (default for sources without explicit `poll_interval_minutes`)
- `COLLECT_BYPASS_COOLDOWN=1` to force fetch
- Cooldown-only cycles no longer overwrite raw items; they reuse previous snapshot.

Runtime snapshot retention controls:
- `PROCESSED_RUN_RETENTION_DAYS` (default 45)
- `TIER1_RUN_RETENTION_DAYS` (default 14)
- `WEEKLY_ARCHIVE_AFTER_DAYS` (default 365; older snapshots compact to weekly)
- Prune utility: `python pipeline/prune_runtime_data.py [--processed-days N] [--tier1-days N] [--weekly-archive-after-days N]`

## LLM integration status
LLM labeling/reranking is currently disabled (`config/llm.yaml -> enabled: false`).

The pipeline runs in deterministic/heuristic mode (no external LLM calls). LLM interfaces are kept in code as explicit no-op placeholders for future reimplementation.

## Source health + circuit breaker + alerts (v1.4/v1.5/v1.6)
```bash
python pipeline/source_health.py update
python pipeline/source_health.py report
python pipeline/source_alerts.py
# optional telegram push (critical-only)
python pipeline/source_alerts.py --send-telegram --telegram-min-severity critical
# state files: data/health/circuit_breaker.json, data/health/alerts_state.json
```

## Architecture notes (why this design for now)
- We use a **deterministic + configurable ranking core** first, then selective LLM steps.
- Reason: reliability and cost control. Full-list LLM ranking is still expensive and occasionally unstable for daily runs.
- Source/slot/category/provider constraints are explicit in config so we can tune behavior quickly without rewriting pipeline logic.
- If LLM pricing/reliability improves, we can later move to broader LLM-first ranking and relax hard constraints.
- Current production flow diagram and knob guide: `docs/ranking-v2-flow.md`
- Current operational snapshot (latest behavior/tuning): `docs/status/current-system-state.md`
- Tuning governance playbook: `docs/status/tuning-governance.md`
- Git hygiene guide: `docs/status/git-hygiene.md`
- Source onboarding + filtering debug guide: `docs/how-to/sources-and-filter-debugging.md`
- PostHog setup + dashboard runbook: `docs/how-to/posthog-setup-and-dashboard.md`

## Config
- `config/sources.yaml`: feed list + source weights
- `config/profile.yaml`: platform relevance weights and keywords
- `config/llm.yaml`: LLM config (currently disabled/no-op; keep for future re-enable)
- `config/user_preferences.yaml`: preference profile used by prompts when LLM mode is enabled
- `config/prompts/label_system.txt`, `config/prompts/rerank_system.txt`: prompt templates (inactive while LLM is disabled)
- `scripts/oauth_login.sh`: legacy OAuth helper for future re-enable

## GitHub Actions
- Hourly collect + score commit
- Daily digest + issue publish (+ optional Telegram if secrets are set)
- Daily reader feedback sync from PostHog (no-op if secrets are missing)

### Repository secrets (optional)
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `POSTHOG_PERSONAL_API_KEY` (feedback sync)
- `POSTHOG_PROJECT_ID` (feedback sync)
