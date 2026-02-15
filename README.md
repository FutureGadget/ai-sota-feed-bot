# AI SOTA Feed Bot (Prototype)

GitHub-first prototype for AI platform engineering news intelligence.

## What it does
- Collects fresh items from high-signal RSS feeds
- Normalizes and de-duplicates (URL + near-title similarity)
- Scores/ranks items for AI platform relevance
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

## Config
- `config/sources.yaml`: feed list + source weights
- `config/profile.yaml`: platform relevance weights and keywords

## GitHub Actions
- Hourly collect + score commit
- Daily digest + issue publish (+ optional Telegram if secrets are set)

### Repository secrets (optional)
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
