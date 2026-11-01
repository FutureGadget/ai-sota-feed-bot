# Migrating llm-digest.com from Vercel to Cloudflare

One-time setup. After this, every push to `main` deploys automatically via
`.github/workflows/deploy-cloudflare.yml` (same as Vercel today).

## What changed

- `worker/` — a Cloudflare Worker that serves the static site (staged `public/`)
  and runs the existing `api/*.js` handlers unchanged.
- API data JSON moves from "bundled files on disk" to an R2 bucket
  (`llm-digest-data`). `lib/data-source.js` lets the same handler code read
  from disk (Node/tests/Vercel) or R2 (Worker). All 23 JS test suites pass
  unchanged.
- `scripts/build_served_data.mjs` precomputes the expensive multi-file reads
  (run pool, brief ledger, RSS pool, share index, updates catalog) into
  `data/served/*.json` at deploy time. The handlers use them when present and
  fall back to the old on-disk computation when absent, so Vercel keeps
  working until you cut over.
- `scripts/r2_sync.py` publishes the API's data files to R2 (diff-based, only
  changed files after the first run).

## One-time setup (about 15 minutes)

### 1. Create the R2 bucket

Cloudflare dashboard -> R2 -> Create bucket -> name: `llm-digest-data`.

### 2. Create two credentials

a) **R2 S3 credentials**: R2 -> Manage R2 API Tokens -> Create API token,
   "Object Read & Write", scoped to `llm-digest-data`. Save the Access Key ID
   and Secret Access Key.

b) **Workers API token**: My Profile -> API Tokens -> Create Token ->
   "Edit Cloudflare Workers" template. Under Account Resources make sure it
   includes Workers Scripts, Workers Routes, and Account Settings on your
   account. (If you prefer, `npx wrangler login` in step 4 replaces this for
   the manual deploy; the GitHub secret in step 7 still needs a token.)

Also copy your **Account ID** (dashboard right sidebar).

### 3. Set the Worker's secrets

From `worker/` in this repo:

    npm install
    npx wrangler secret put EMAIL_API_KEY            # your Resend Full-access key
    npx wrangler secret put EMAIL_TOPIC_ID_DAILY
    npx wrangler secret put EMAIL_TOPIC_ID_WEEKLY
    npx wrangler secret put EMAIL_SEGMENT_ID
    npx wrangler secret put EMAIL_SEGMENT_ID_FOLLOWERS   # if you set it on Vercel
    npx wrangler secret put POSTHOG_PROJECT_API_KEY      # if you override the default

(Anything you never set on Vercel, skip. `wrangler secret put` prompts for the
value — paste it, it's not echoed.)

### 4. First deploy (manual, before cutover)

From the repo root:

    python -m venv .venv && .venv/bin/pip install -r requirements.txt
    .venv/bin/python scripts/vercel_build.py        # stages public/
    node scripts/build_served_data.mjs              # builds data/served/

    # seed R2 (first run uploads ~25 MB, ~380 files)
    export CLOUDFLARE_ACCOUNT_ID=... R2_ACCESS_KEY_ID=... R2_SECRET_ACCESS_KEY=...
    python scripts/r2_sync.py

    # deploy the Worker + assets (no custom domain yet)
    cd worker && npm install
    CLOUDFLARE_API_TOKEN=... CLOUDFLARE_ACCOUNT_ID=... npx wrangler deploy

### 5. Verify on the workers.dev URL

Open `https://llm-digest-site.<your-subdomain>.workers.dev` and check the home
page, a daily recap, /api/feed, /rss.xml, /storylines. Everything except email
signup works without a custom domain.

### 6. Cut over llm-digest.com

The domain's DNS is already on Cloudflare (the PostHog proxy worker proves
it), so this is a Worker route change, not a nameserver move:

1. Uncomment the `routes` block in `worker/wrangler.jsonc` and redeploy
   (`npx wrangler deploy`). Cloudflare takes over `www.llm-digest.com` and
   `llm-digest.com` automatically; the apex keeps its 308 -> www redirect.
2. In the Cloudflare dashboard, delete the old Vercel DNS records for
   `llm-digest.com` / `www` (the A/CNAME records pointing at Vercel) if any
   remain - Worker custom domains replace them.
3. Browse the site. When satisfied: in Vercel, remove the domain from the
   project (or delete the project). Keep it around a few days if you want an
   instant rollback path - rollback = remove the routes, restore the Vercel
   DNS records.

### 7. Ongoing auto-deploys

Repo -> Settings -> Secrets and variables -> Actions, add:

    CLOUDFLARE_ACCOUNT_ID      your account id
    CLOUDFLARE_API_TOKEN       the Workers token from step 2b
    R2_ACCESS_KEY_ID           from step 2a
    R2_SECRET_ACCESS_KEY       from step 2a

Every push to `main` now stages the site, rebuilds served data, syncs changed
data files to R2, and deploys the Worker. Vercel's GitHub integration can be
disconnected once you're confident.

## Notes

- Free-tier fit: static traffic (the bot-heavy 750K requests) is unmetered on
  Cloudflare. API traffic shares the Workers free 100K requests/day, resetting
  daily at midnight UTC, and edge caching (5 min, same as Vercel's s-maxage)
  absorbs repeat bot hits.
- The API responses are cached at the edge for 5 minutes like Vercel's CDN
  did; `no-store` endpoints (unfollow pages) are never cached.
- `assets.llm-digest.com` (PostHog proxy worker) is untouched.
