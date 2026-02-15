# Feedback Loop (v1.2)

## User intent
Allow fast signal quality feedback without requiring a full UI.

## Input format (manual)
`python pipeline/feedback.py add --url <item_url> --signal useful|irrelevant|hype`

## Expected effect
- Feedback events are stored in `data/feedback/events.jsonl`
- `summary` command aggregates by signal/source
- Future tuning can consume these aggregates for source/ranking weight updates
