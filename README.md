# AI SOTA Feed Bot (Prototype)

GitHub-first prototype for AI platform engineering news intelligence.

## What it does
- Collects fresh items from high-signal RSS feeds
- Normalizes and de-duplicates
- Scores/ranks items for AI platform relevance
- Builds a Markdown digest
- Publishes digest as:
  - versioned file in `data/digest/`
  - optional GitHub Issue (`Daily AI Digest - YYYY-MM-DD`)

## Quick start
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python collectors/collect.py
python pipeline/build_digest.py
python publish/publish_issue.py --repo FutureGadget/ai-sota-feed-bot --date $(date +%F)
```

## Config
- `config/sources.yaml`: feed list + source weights
- `config/profile.yaml`: platform relevance weights and keywords

## GitHub Actions
- Hourly collect + score
- Daily digest + issue publish

Set repository secret:
- `GH_TOKEN` (if needed for issue publishing; GitHub Actions `GITHUB_TOKEN` can also work)
