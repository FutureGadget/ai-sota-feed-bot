# Deploying to Cloudflare

One-time setup (bucket, credentials, secrets, DNS cutover) lives in
`MIGRATION-CLOUDFLARE.md` at the repo root. This is the steady-state deploy.

## What runs

`.github/workflows/deploy-cloudflare.yml` runs on every push to `main` and on
manual dispatch. There is no PR preview deployment.

```text
scripts/build_site.py        -> public/   (regenerates static pages, stages web/)
scripts/build_served_data.mjs-> data/served/*.json (precomputed multi-file reads)
scripts/r2_sync.py           -> R2 data/<key>      (EXACT_FILES + TOP_LEVEL_DIRS only)
wrangler deploy              -> Worker + Workers Assets
```

Order matters: the Worker preloads R2 keys synchronously, so a handler whose key
was not published reads as a missing file.

## What each surface costs

- **Pages** are static assets served before the Worker runs. `/skills`,
  `/daily`, `/models` and friends are pre-rendered; adding a page means adding a
  route to `worker/src/index.js` (`STATIC_REWRITES`) and nothing else.
- **APIs** are modules the Worker imports from `api/`. Each route's `preload([...])`
  list must be a subset of the R2 allowlist.
- **Data** is only what `scripts/r2_sync.py` publishes. Heavy runtime dirs
  (`data/raw`, `data/quality`, `data/cache`, ...) never reach R2 or `public/`.

## Checks

`python scripts/check_deploy_artifacts.py` (CI) enforces requirements hygiene,
the Worker bundle budget, the Workers Assets 20,000-file ceiling, and that no
`api/` subdirectories creep in.

## Limits worth knowing

- Workers Assets: 20,000 files, 25 MiB per file. `web/` is ~8.1k files today.
- Worker script: 10 MB compressed (ours is ~60 KB).
