# Deploy on Vercel (GitHub-backed content)

## Overview
This deployment serves:
- Web UI: `/` (from `web/index.html`)
- JSON feed API: `/api/feed`
- RSS feed: `/api/rss`

Content source is repository data (`data/processed/latest.json`).
When pipeline commits new data and Vercel redeploys, feed updates.

`vercel.json` runs `python3 pipeline/render_static_pages.py` as the deployment
build command. This regenerates story, storyline, daily, weekly, sitemap, and
robots outputs from the committed data before Vercel packages the site. It is
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

## i18n roadmap (summary support)
Planned extension:
- Store per-item summaries by locale (e.g. `summary_i18n.en`, `summary_i18n.ko`).
- Add `lang` query on feed endpoints:
  - `/api/feed?lang=ko`
  - `/api/rss?lang=ko`
- Fallback chain: requested locale -> English -> original summary.

This can be added without changing the current ranking pipeline core.
