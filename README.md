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
