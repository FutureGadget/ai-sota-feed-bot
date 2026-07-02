# North Star Metric: Weekly Returning Readers

Decision record: `docs/design-docs/decision-log.md` (2026-07-02, "One
north-star metric for 60 days: weekly returning readers").

## The rule

From **2026-07-02** through **2026-08-31** (60 days), every product decision
is judged against **one number**: weekly returning readers. Features
shipped, sources added, and recap/editorial quality are explicitly off the
scoreboard for this window — they only matter to the extent they move this
number.

## Definition

For a completed ISO week `W` (Monday 00:00 UTC through the following Monday
00:00 UTC):

- **returning reader** — a PostHog `distinct_id` with a `page_view` event in
  week `W` that also had a `page_view` event in week `W-1`.
- **total_readers** — all distinct `distinct_id`s with a `page_view` in week
  `W`.
- **returning_rate** — `returning_readers / total_readers`.

The identity used is the client-side anonymous id
(`localStorage["ai_feed_anon_user_id"]`, created by `web/posthog-client.js`),
persisted in `localStorage` and passed to `posthog.identify()`. It survives
repeat visits on the same browser but not across devices — same caveat as every
other PostHog-derived metric in this repo (see `pipeline/feedback.py`,
`pipeline/auto_tune.py`).

`web/posthog-client.js` is loaded by every hand-authored shell and by the static
page renderer template, so `page_view` coverage is site-wide: feed, recap,
story, storyline, wiki/topic, Foundations, Playbook, Voices, and Subscribe
surfaces all emit the same event when PostHog is enabled.

The current (in-progress) week is never scored — only completed weeks.

## How to read it

- **Data:** `data/metrics/weekly_returning_readers.json` — durable history,
  one row per completed week, merged forward (never rewritten from scratch).
- **Command:** `python3 pipeline/north_star_metric.py summary --weeks 8`
  prints the tracked history as a table.
- **Where it shows up automatically:** the daily `feedback-sync.yml` workflow
  runs `north_star_metric.py sync` then `summary --weeks 8`, so the latest
  numbers appear in that workflow's logs every day. `pipeline/ops_daily_summary.py`
  also includes the latest week's `returning_readers`/`returning_rate` in its
  `ops_summary` log line and JSON output, so it's visible in the daily ops
  summary without any extra step.

## How it's computed

`pipeline/north_star_metric.py sync` queries PostHog with the same HogQL
`POST /api/projects/{project_id}/query` pattern already used by
`feedback.py::cmd_sync_posthog` and `auto_tune.py::cmd_sync_ctr` (same
`POSTHOG_PERSONAL_API_KEY` / `POSTHOG_PROJECT_ID` / `POSTHOG_API_HOST` env
vars), pulling `(week_start, distinct_id)` pairs for `page_view` events over
the last `WEEKS_LOOKBACK` (16) weeks, then classifies readers per week in
Python. It no-ops cleanly when PostHog credentials aren't configured.

## What this deliberately does not do

- No new public dashboard or `/metrics` page — this is an internal
  decision-making signal, not a reader-facing feature.
- No cross-device identity resolution, no cohort/segment breakdowns, no
  causal attribution of *why* a week moved. Those are BL-002-sized problems
  (`docs/BACKLOGS.md`) that this rollup deliberately does not attempt.
- No automatic alerting on the number moving — check it manually via the
  command above or the daily ops summary.

## After the 60-day window

Revisit this doc: either extend the window, promote the underlying work
toward BL-002 (Metrics-driven optimization agent) for a broader metrics
program, or retire the single-metric discipline. Whichever happens, record
the decision in `docs/design-docs/decision-log.md`.
