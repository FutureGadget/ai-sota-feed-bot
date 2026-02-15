# AI SOTA Feed Bot (Prototype)

GitHub-first prototype for AI platform engineering news intelligence.

## What it does
- Collects fresh items from high-signal RSS feeds
- Normalizes and de-duplicates (URL + near-title similarity)
- Scores/ranks items for AI platform relevance
- Applies diversity-aware ranking (strict minimum mix + caps for paper/news/release)
- Supports lightweight feedback capture for relevance tuning
- Auto-tunes source weights from accumulated feedback
- Tracks source reliability/health and incorporates it into ranking
- Applies source circuit breaker on repeated failures with cooldown auto-recovery
- Sends low-noise degradation alerts; Telegram delivery is critical-only by default
- Builds a Markdown digest
- Publishes digest as:
  - versioned file in `data/digest/`
  - GitHub Issue (`Daily AI Digest - YYYY-MM-DD`)
  - Telegram mobile-friendly digest (top-5 with why + compact remainder)

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

## Feedback capture (v1.2)
```bash
python pipeline/feedback.py add --url "https://example.com/item" --signal useful --source arxiv_cs_ai
python pipeline/feedback.py summary
```

## Auto-tuning (v1.3)
```bash
python pipeline/auto_tune.py report
python pipeline/auto_tune.py apply
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

## Config
- `config/sources.yaml`: feed list + source weights
- `config/profile.yaml`: platform relevance weights and keywords
- `config/llm.yaml`: LLM label + rerank configuration (disabled by default)

## GitHub Actions
- Hourly collect + score commit
- Daily digest + issue publish (+ optional Telegram if secrets are set)

### Repository secrets (optional)
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
