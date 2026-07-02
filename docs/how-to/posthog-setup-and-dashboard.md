# PostHog Setup & Dashboard Runbook

This runbook describes how to enable PostHog for `ai-sota-feed-bot`, verify ingestion, build a practical dashboard, and safely roll back.

## Scope
- PostHog is the analytics/dashboard layer for web feed telemetry.
- Current captured web events:
  - `$pageview` (standard posthog-js pageview; powers PostHog **Web
    Analytics** — visitors, sessions, top pages, channels. Superseded the
    legacy custom `page_view` on 2026-07-03)
  - `feed_view`
  - `impression_batch`
  - `click`

---

## 1) Vercel environment setup
Set these env vars on Vercel:

- `POSTHOG_ENABLED=1`
- `POSTHOG_PROJECT_API_KEY=<PostHog project key>`
- `POSTHOG_HOST=https://us.i.posthog.com` (or `https://eu.i.posthog.com`)

Then redeploy production.

---

## 2) Runtime verification checklist

### A. Config endpoint
Open:
- `/api/client-config`

Expected:
- `posthog.enabled: true`
- correct `host`
- non-null `project_api_key`

### B. Live event check in PostHog
In PostHog, open **Activity / Live events** and perform test actions on the feed page:
- open page
- wait for feed render
- click 1–3 article links

Expected events:
- `$pageview`
- `feed_view`
- `impression_batch`
- `click`

### C. Common false-negative causes
If dashboard seems empty but integration is live:
- Dashboard time range too narrow
- Event filters active
- Viewing wrong project
- Region mismatch (`us` vs `eu` host)
- Browser extension/adblock blocking analytics domains

---

## 3) Recommended initial dashboard panels
Create a dashboard with these insights:

1. **Page views (daily)**
   - Event: `$pageview`
   - Interval: day
   - (Or just use the built-in **Web Analytics** product, which now counts
     `$pageview` automatically.)

2. **Feed views (daily)**
   - Event: `feed_view`
   - Interval: day

3. **Clicks (daily)**
   - Event: `click`
   - Interval: day

4. **Approx CTR trend**
   - Formula: `click / impression_batch` (event-count based approximation)
   - Interval: day

5. **Top sources by clicks**
   - Event: `click`
   - Breakdown: property `source`

6. **Top clicked ranks**
   - Event: `click`
   - Breakdown: property `rank_position`

7. **Freshness exposure trend** (optional)
   - Event: `feed_view`
   - Use property `fresh_added` distribution over time

---

## 4) Operational notes
- PostHog is the source of truth for product analytics visibility.
- The one metric the project is currently judged against — **weekly
  returning readers** — is computed from pageview events
  (`event IN ('$pageview', 'page_view')`, bridging the 2026-07-03 rename) by
  `pipeline/north_star_metric.py` (same HogQL query pattern as the panels
  above) and does not need a PostHog dashboard panel to be useful; see
  `docs/status/north-star-metric.md`. Cross-check it in PostHog itself with a
  built-in **Retention** insight (event: `$pageview`, weekly granularity) if
  you want a visual sanity check against the rollup's numbers.

---

## 5) Rollback
To disable PostHog quickly:
- Set `POSTHOG_ENABLED=0`
- Redeploy

Result:
- UI remains functional
- PostHog captures stop
