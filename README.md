# AI SOTA Feed Bot (Prototype)

GitHub-first prototype for AI platform engineering news intelligence.

## What it does
- Collects fresh items from high-signal RSS feeds
- Normalizes and de-duplicates (URL + near-title similarity)
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

## Optional personalization event store (Turso)
Set Vercel env vars:
- `TURSO_DATABASE_URL`
- `TURSO_AUTH_TOKEN`

Then send telemetry events to `POST /api/events` with either a single event object or `{ "events": [...] }`.
Supported `event_type`: `impression`, `click`, `open`, `dismiss`, `save`.
Impression dedupe: same `anon_user_id + item_id + run_id` (or same day fallback when `run_id` missing) is stored once.

Current web app behavior:
- Generates anonymous `anon_user_id` in localStorage (no login)
- Generates per-tab `session_id` in sessionStorage
- Sends batched `impression` events on feed render
- Sends `click` events when opening an item link

Personalized feed API (v1):
- Send `X-Anon-User-Id` header (or `anon_user_id` query) to `/api/feed`
- Optional debug: `debug_personalization=1`
- Modes via env: `PERSONALIZATION_MODE=off|shadow|active` (default `shadow`)
- Useful knobs: `PERSONALIZATION_DAYS`, `PERSONALIZATION_W_SOURCE`, `PERSONALIZATION_W_TOPIC`, `PERSONALIZATION_CAP`, `PERSONALIZATION_MIN_IMPRESSIONS`, `PERSONALIZATION_MIN_CLICKS`, `PERSONALIZATION_EXPLORATION`
- Tier-1 freshness blend options: `blend_tier1=0|1` (default 1), `tier1_fresh_cap` (default 4)
- Additional blend guards: `tier1_insert_after` (default 3), `tier1_min_quick_score` (default 2.6), `tier1_max_per_source` (default 1)

Tier-0 input source toggle:
- `TIER0_INPUT=tier1|raw` (default `tier1`, with automatic raw fallback)

Collector crawl cooldown controls:
- `COLLECT_DEFAULT_POLL_MINUTES` (default for sources without explicit `poll_interval_minutes`)
- `COLLECT_BYPASS_COOLDOWN=1` to force fetch (used by full/dev runs)
- Cooldown-only cycles no longer overwrite raw items; they reuse previous snapshot.

## OAuth LLM mode (local, no API key)
```bash
npm install
./scripts/oauth_login.sh      # one-time OpenAI Codex OAuth login
# ensure config/llm.yaml has: provider: pi_oauth, enabled: true
```

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

## Config
- `config/sources.yaml`: feed list + source weights
- `config/profile.yaml`: platform relevance weights and keywords
- `config/llm.yaml`: LLM label + rerank configuration (supports `pi_oauth` bridge mode)
- `config/user_preferences.yaml`: preference profile injected into LLM prompts
- `config/prompts/label_system.txt`, `config/prompts/rerank_system.txt`: prompt templates
- `scripts/oauth_login.sh`: OAuth login helper (stores creds in `data/llm/auth.json`)

## GitHub Actions
- Hourly collect + score commit
- Daily digest + issue publish (+ optional Telegram if secrets are set)

### Repository secrets (optional)
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
