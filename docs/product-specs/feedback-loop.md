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

## Email feedback (one-tap deep link)
Each item in the daily email brief carries `👍 Useful · 👎 Not relevant` links
(`publish/publish_email.py` → `feedback_row`). They point at the feed with the
item highlighted and a feedback signal:
`/?item=<encoded url>&fb=<useful|irrelevant>&utm_source=email`.

- On landing, the feed client (`web/index.html` → `applyEmailFeedback`) resolves
  the item via the existing share-landing `?item=<url>` path and records the
  **same** `item_feedback` event the on-page buttons fire (with `via: 'email'`),
  so no new endpoint or storage is involved — it flows through the same
  PostHog → `sync-posthog` → `auto_tune` loop.
- Idempotent: re-clicking an already-set signal does not re-fire. The vote is
  reflected in the card UI (the reader sees it registered) and remembered in
  the same `localStorage` state as on-page taps.

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

## Consumption: source weight auto-tuning (v1.3)
`pipeline/auto_tune.py` turns accumulated signal into per-source score
adjustments applied by the ranking pipeline:

- **Explicit signal:** net feedback per source within the rolling window;
  score = (useful − irrelevant − hype) / n, scaled by `explicit_weight`.
  Requires `min_explicit_events` before a source moves.
- **Implicit signal (CTR blend):** per-source clicks pulled from PostHog
  (`auto_tune.py sync-ctr` → `data/feedback/ctr_clicks.json`) divided by
  rank-weighted exposure (1/log2(rank+1)) computed from
  `data/processed/runs/` snapshots — the web client only reports batched
  impression counts, so the denominator is derived locally. Empirical-Bayes
  smoothing pulls low-sample CTRs toward the global rate; `ctr_weight` is the
  delta per doubling/halving vs global CTR; requires `min_exposure`.
- **Guardrails:** combined delta hard-capped at `±max_abs_adjustment`
  (default 0.15, below the hand-tuned `source_bias` magnitudes); the rolling
  `window_days` acts as decay; ranking ignores artifacts older than
  `max_age_days`. Knobs live in `config/ranking.yaml` under `auto_tune:`.
- **Flow:** `auto_tune.py report` (dry-run table) / `apply` (writes
  `data/feedback/source_adjustments.json`). The daily feedback-sync workflow
  runs sync → sync-ctr → apply → commit. `pipeline/ranking.py` adds the
  per-item `source_tune` delta into the slot score next to `source_bias`,
  and the daily ops summary reports `source_tuning` (top deltas) for
  observability.
