# Feedback Loop (v1.3)

## User intent
Let readers rate feed quality in one tap, and let operators add quick manual
signal — accumulating events that future tuning (v1.3 auto-tuning plan) can
consume for source/ranking weight updates.

## Reader feedback (web UI)
Every feed card on `/` shows a one-tap feedback row:
`Was this useful?  👍 Useful · 👎 Not relevant · 🫧 Hype`

- Tap sets the signal; tapping the same button again retracts it; tapping a
  different button changes it.
- The choice is remembered locally (`localStorage` key `ai_feed_feedback_v1`)
  so cards keep showing the reader's rating across visits.
- Each tap emits a PostHog `item_feedback` event with:
  `item_id`, `signal` (useful|irrelevant|hype), `action` (set|unset),
  `prev_signal`, `url`, `source` (feed source), `title`, `rank_position`,
  `run_id`.
- Works in both the live feed and the Saved view. No-op when PostHog is
  disabled (the local UI state still works).

## Manual input (CLI)
`python pipeline/feedback.py add --url <item_url> --signal useful|irrelevant|hype [--note <text>]`

## Sync (PostHog → repo)
`python pipeline/feedback.py sync-posthog [--days N]`

- Pulls `item_feedback` events via the PostHog HogQL query API and appends
  them to `data/feedback/events.jsonl` (de-duplicated by PostHog event uuid;
  re-queries with a 30-minute overlap from the last synced web event).
- Env: `POSTHOG_PERSONAL_API_KEY`, `POSTHOG_PROJECT_ID`, optional
  `POSTHOG_API_HOST` (default `https://us.posthog.com` — the query API host,
  not the `*.i.posthog.com` ingest host). Missing credentials → clean no-op.
- Runs daily via `.github/workflows/feedback-sync.yml` (21:45 KST), which
  commits new events with the standard runtime-data commit script.

## Storage format
`data/feedback/events.jsonl`, append-only, one JSON object per line:

| field | meaning |
| --- | --- |
| `ts` | ISO timestamp |
| `url` | item URL |
| `signal` | `useful` \| `irrelevant` \| `hype` |
| `source` | event channel: `manual` (CLI) or `web` (synced) |
| `note` | optional free text (manual only) |
| `item_id` | feed item key (web only) |
| `item_source` | feed source, e.g. `openai_blog` (web only) |
| `user` | anonymous reader id (web only) |
| `action` | `set` \| `unset` — retractions (web only) |
| `uuid` | PostHog event uuid for sync de-dup (web only) |

## Aggregation
`python pipeline/feedback.py summary [--days N]`

- Reduces raw events to net state (latest set/unset per reader+item; manual
  events count individually) and reports counts by signal and by item source.
- Future tuning consumes these aggregates for source/ranking weight updates.
