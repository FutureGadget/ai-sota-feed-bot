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

- **reader** — a PostHog `distinct_id` with **at least 2 pageviews** in week
  `W` (`MIN_PAGEVIEWS_PER_WEEK`). One pageview is not a reader; it is what a
  JS-rendering crawler produces. See *The pageview floor* below.
- **returning reader** — a reader in week `W` that was also a reader in week
  `W-1`.
- **total_readers** — all readers in week `W`.
- **returning_rate** — `returning_readers / total_readers`.
- **single_page_readers** — distinct ids with exactly one pageview in week
  `W`. Excluded from every headline number; recorded so a crawler wave stays
  visible instead of silently vanishing from the denominator.

### The pageview floor (2026-10-31)

Until 2026-10-31 any `distinct_id` with one pageview counted as a reader. A
JS-rendering crawler walks sitemap permalinks in a fresh browser profile, so it
fired `$identify` then `$pageview`, took a new anonymous id each time, and
could never be a returning reader. From 2026-10-05 the crawler grew from ~90 to
2,157 single-page visits per week, inflating `total_readers` from 100 to 1,576
while `returning_readers` stayed at 5-7. The rate collapsed to 0.3% for
arithmetic reasons, not because readers left.

Evidence, 2026-10-31: 1,113 of 1,302 visitors (85%) fired exactly `$identify`
then `$pageview` and nothing else; 1,219 distinct IPs for 1,289 visitors; 854
distinct `/story/<sid>` permalinks against 5,707 in `web/sitemap.xml`; all
`$direct`, no `utm_*`, geo and browser timezone matched per visitor (Hong Kong,
Shanghai, Singapore, Mexico, Brazil, Colombia, Bangladesh). Preview deployments
got 3 visitors in the same six weeks, so it is not this repo's agent testing.

Requiring 2 pageviews keeps every returning reader the old definition found
(one 2026-10-12 reader had a single pageview in the prior week and drops out)
and cuts the last scored week from 1,576 to 32. Do **not** replace this with an
engagement filter based on `scroll_depth` or `$web_vitals`: the crawler runs a
real browser and emits both.

"Pageview" here means the standard posthog-js `$pageview`, emitted by
`web/posthog-client.js` (this also powers PostHog Web Analytics). The rollup
query still matches the legacy custom `page_view` as well — it was dual-emitted
until 2026-07-13, then removed because it duplicated every `$pageview` — so
weeks recorded before the removal still count with no gap. The rollup groups by
`(week_start, distinct_id)`, so the overlap during the dual-emission window did
not double-count weekly readers.

The identity used is the client-side anonymous id
(`localStorage["ai_feed_anon_user_id"]`, created by `web/posthog-client.js`),
persisted in `localStorage` and passed to `posthog.identify()`. It survives
repeat visits on the same browser but not across devices — same caveat as every
other PostHog-derived metric in this repo (see `pipeline/feedback.py`,
`pipeline/auto_tune.py`).

`web/posthog-client.js` is loaded by every hand-authored shell and by the static
page renderer template, so pageview coverage is site-wide: feed, recap,
story, storyline, wiki/topic, Foundations, Playbook, Voices, and Subscribe
surfaces all emit the same event when PostHog is enabled.

The current (in-progress) week is never scored — only completed weeks.

### Email attribution (diagnostic, added 2026-09-24)

Email links carry the subscriber's pseudonymous reader id (`rid=`, a Resend
contact property; see `docs/product-specs/email-digest.md`), which
`web/posthog-client.js` adopts as the browser's id before PostHog loads. A
subscriber who reads from a mail app's in-app browser is therefore one
`distinct_id` across weeks instead of a "new reader" per click — before this,
the channel built for retention was structurally counted as acquisition.

Each synced week also records:

- **email_readers** — readers with at least one pageview in week `W` that
  landed from a digest link (`utm_source = 'email'`).
- **email_returning_readers** — returning readers in `W` who are also email
  readers in `W`.

These sit next to the headline numbers and never change them. Weeks synced
before 2026-09-24 show `-` in `summary`; the next sync backfills them within
the 16-week lookback, but only visits after the change carry `rid`, so expect
the email-returning count to climb as subscribers click through.

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
vars), pulling `(week_start, distinct_id)` pairs for pageview events
(`event IN ('$pageview', 'page_view')`) over
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
