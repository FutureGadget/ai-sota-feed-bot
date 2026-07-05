---
name: add-translated-page
description: Add or refresh one pretranslated static page for ai-sota-feed-bot for a specific locale and page type. Use only when the user explicitly asks to create translated pages, localize a specific page/surface, refresh stale translations, or publish language-prefixed pages under data/i18n and web locale directories.
---

You publish one pretranslated static page for a chosen locale and surface. Do
not add or refresh translations opportunistically during unrelated work; run
this skill only when the user explicitly asks for translated pages.

Supported static surfaces: `daily`, `weekly`, `story`, `storyline`, `topic`,
`foundations`. The live feed `/` is excluded until it has a localized feed-data
or API contract.

## Routine

### 1. Filter candidates first
Use the exporter before reading broad source data:

```bash
python pipeline/export_i18n_candidates.py --locale ko --surface daily --limit 20
```

Repeat `--surface` to include several page types. The exporter prints compact
candidate rows: `surface`, `id`, `source_path`, `target_path`, `artifact_path`,
`status`, `source_hash`, `title`, `description`, and the translation contract.

Pick the exact page the user requested. If the user asked for "latest" or a
batch, prioritize `stale` before `missing`, then current `daily`/`weekly`, then
recent `storyline`/`foundations`, then stories linked by translated recaps.

Only after choosing the page, export the full source for that one candidate:

```bash
python pipeline/export_i18n_candidates.py \
  --locale ko \
  --surface daily \
  --include-source \
  --limit 1 \
  --output /tmp/i18n-ko-daily-candidate.json
```

If the first row is not the requested page, use the compact output to identify
the id, then load only the needed English source file directly.

### 2. Write the translation artifact
Create or replace:

```text
data/i18n/<locale>/<surface>/<id>.json
```

Required fields:

```json
{
  "locale": "ko",
  "source_path": "/daily/2026-07-05",
  "source_hash": "<copy from exporter>",
  "translated_at": "<ISO-8601 UTC timestamp>",
  "model": "<translator/model name>",
  "review_status": "machine"
}
```

Add translated fields using the candidate `contract.translated_fields`.
Preserve every `contract.preserve_fields` value exactly: URLs, source ids,
dates, story ids, slugs, graph links, evidence ids, and technical identifiers.

For `daily` and `weekly`, translate the full recap structure, not just the page
title: `intro`, `highlights`, category names/summaries, article titles, and
article summaries. Keep the category/article order and all source URLs intact.

For `story`, `storyline`, `topic`, and `foundations`, preserve the English page
layout contract and translate only reader-facing prose. Keep model names,
company names, product names, code identifiers, benchmark names, prices, dates,
percentages, and acronyms such as RAG, MCP, RLHF, and GPU unless the locale has
an established local rendering.

### 3. Validate and render
Run focused validation:

```bash
python3 -m py_compile pipeline/export_i18n_candidates.py pipeline/render_static_pages.py
python3 -m unittest tests.test_i18n_candidate_export
python pipeline/export_i18n_candidates.py --locale ko --surface daily --limit 5
python pipeline/render_static_pages.py
```

If the renderer updates unrelated generated English pages, restore them before
committing unless the user asked for a full render refresh:

```bash
git restore -- web/daily web/weekly web/story web/storyline web/topic web/foundations web/og web/index.html web/map.html web/foundations.html web/sitemap.xml
```

Then keep only the localized artifacts/pages needed for the requested
translation.

### 4. Publish to main
Use the same routine hygiene as other page-publishing skills:

```bash
git status --short
git add data/i18n/<locale>/<surface>/<id>.json web/<locale>/<surface>/<id>.html web/sitemap.xml
git diff --staged --check
git -c user.name="Claude" -c user.email="noreply@anthropic.com" \
  commit -m "i18n: add <locale> <surface> <id>"
git fetch origin
git rebase origin/main
git push origin HEAD:main
```

If the branch is not intended to publish directly to `main`, push the current
branch and create a PR instead. Never force-push `main`. If a rebase conflicts,
resolve generated-file conflicts by regenerating from committed data; abort and
report if source artifacts conflict in a way that changes the requested page.

## Where It Shows Up

Localized static pages live at `/<locale>/<surface>/<id>`, for example
`/ko/daily/2026-07-05`. English pages should expose a language switch only when
a fresh translation artifact exists and matches the reader's browser language.
