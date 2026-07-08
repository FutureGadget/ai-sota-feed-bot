# PostHog Setup & Dashboard Runbook

This runbook describes how to enable PostHog for `ai-sota-feed-bot`, verify ingestion, build a practical dashboard, and safely roll back.

## Scope
- PostHog is the analytics/dashboard layer for web feed telemetry.
- Current captured web events:
  - `$pageview` (standard posthog-js pageview; powers PostHog **Web
    Analytics** — visitors, sessions, top pages, channels)
  - `page_view` (legacy compatibility event for existing custom insights)
  - `feed_view`
  - `impression_batch`
  - `click`

---

## 1) Vercel environment setup
Set these env vars on Vercel:

- `POSTHOG_ENABLED=1`
- `POSTHOG_PROJECT_API_KEY=<PostHog project key>`
- `POSTHOG_HOST=https://assets.llm-digest.com` (default; reverse-proxied
  through the `llm-digest-proxy-worker` Cloudflare Worker in `infra/` so
  ingestion/asset requests are first-party and less adblock-prone — set to
  `https://us.i.posthog.com`/`https://eu.i.posthog.com` to bypass the proxy)
- `POSTHOG_UI_HOST=https://us.posthog.com` (default; must stay PostHog's real
  domain, never the proxy, so in-app features like the toolbar link correctly)

Then redeploy production.

The proxy Worker itself lives in `infra/llm-digest-proxy-worker/` (see
`src/index.js`); it forwards `/static/*` and `/array/*` to PostHog's asset
host (cached at the edge) and everything else to the ingest API, stripping
cookies and setting `X-Forwarded-For`. Custom domain `assets.llm-digest.com`
is configured via `routes` in `wrangler.jsonc`. The Worker also owns CORS for
the proxy: it answers browser preflights and adds `Access-Control-Allow-Origin`
for `https://www.llm-digest.com`, `https://llm-digest.com`, and localhost
development origins on both cached asset responses and ingest responses.

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
- `page_view`
- `feed_view`
- `impression_batch`
- `click`

### C. Common false-negative causes
If dashboard seems empty but integration is live:
- Dashboard time range too narrow
- Event filters active
- Viewing wrong project
- Region mismatch (`us` vs `eu` host)
- Proxy CORS regression: browser console shows `assets.llm-digest.com/array/...`
  blocked even though the request has `200 OK`
- Browser extension/adblock blocking analytics domains

---

## 3) Recommended initial dashboard panels
Create a dashboard with these insights:

1. **Page views (daily)**
   - Event: `$pageview`
   - Interval: day
   - (Or just use the built-in **Web Analytics** product, which now counts
     `$pageview` automatically.)
   - Existing dashboards pinned to the legacy custom event can continue using
     `page_view`.

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
  (`event IN ('$pageview', 'page_view')`) by
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
