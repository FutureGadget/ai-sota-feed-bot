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
- Builds a Markdown digest
- Publishes digest as:
  - versioned file in `data/digest/`
  - GitHub Issue (`Daily AI Digest - YYYY-MM-DD`)
  - optional Telegram push

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

## Source health + circuit breaker (v1.4/v1.5)
```bash
python pipeline/source_health.py update
python pipeline/source_health.py report
# circuit state file: data/health/circuit_breaker.json
```

## Config
- `config/sources.yaml`: feed list + source weights
- `config/profile.yaml`: platform relevance weights and keywords

## GitHub Actions
- Hourly collect + score commit
- Daily digest + issue publish (+ optional Telegram if secrets are set)

### Repository secrets (optional)
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
