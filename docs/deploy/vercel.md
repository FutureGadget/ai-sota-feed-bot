# Deploy on Vercel (GitHub-backed content)

## Overview
This deployment serves:
- Web UI: `/` (from `web/index.html`)
- JSON feed API: `/api/feed`
- RSS feed: `/api/rss`

Content source is repository data (`data/processed/latest.json`).
When pipeline commits new data and Vercel redeploys, feed updates.

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
