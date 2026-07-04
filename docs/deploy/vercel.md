# Deploy on Vercel (GitHub-backed content)

## Overview
This deployment serves:
- Web UI: `/` (from `web/index.html`)
- JSON feed API: `/api/feed`
- RSS feed: `/api/rss`

Content source is repository data (`data/processed/latest.json`).
When pipeline commits new data and Vercel redeploys, feed updates.

`vercel.json` runs `python3 scripts/vercel_build.py` as the deployment build
command and uses `public/` as the static output directory. The helper
regenerates story, storyline, daily, weekly, sitemap, and robots outputs from
the committed data, then copies the complete `web/` tree to `public/web/`
before Vercel packages the site. API functions remain under `api/`. This is
intentional redundancy with `run_full.sh`: production data commits still keep
generated artifacts in git, while code-only PR previews no longer serve stale
HTML from before a renderer change.

## One-time setup
1. Connect repository to Vercel project.
2. Ensure auto-deploy on `main` is enabled.
3. Deploy.

CLI:
```bash
vercel
vercel --prod
```

## i18n roadmap (pre-translated pages)
Planned extension:
- Store generated translation artifacts under `data/i18n/<locale>/`.
- Render static locale-prefixed pages such as `/ko/daily/<date>` and
  `/ko/story/<sid>`.
- Add reciprocal `hreflang` links and localized sitemap entries only for fresh
  translation artifacts.
- Prioritize translation candidates by recent page views, then current recaps
  and updated storyline/foundation pages.

APIs and RSS remain English in v1. Localized static pages come first because
they are shareable, crawlable, and do not depend on live browser translation.
