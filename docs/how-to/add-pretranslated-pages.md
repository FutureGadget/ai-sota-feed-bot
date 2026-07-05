# Add pre-translated pages

Use this when adding or refreshing localized static pages such as
`/ko/daily/<date>`, `/ko/weekly/<week>`, `/ko/story/<sid>`,
`/ko/storyline/<slug>`, `/ko/topic/<slug>`, or `/ko/foundations/<slug>`.

The product contract lives in
`docs/product-specs/multilingual-pretranslated-pages.md`. This is the operating
checklist.

## 1. Pick the English source page

Choose a page whose English source is already committed:

- daily recap: `data/daily/<YYYY-MM-DD>.json`
- weekly recap: `data/weekly/<YYYY-Www>.json`
- story: durable story store under `data/stories/`
- storyline: `data/storylines/<slug>.json`
- topic: compiled wiki node from `data/wiki/index.json`
- foundation: compiled concept from `data/foundations/index.json`

Prefer high 60-day page-view pages, current daily/weekly recaps, recently
updated storylines/foundations, and stories linked from translated recaps.

## 2. Create the translation artifact

Put the artifact under the matching path:

```text
data/i18n/<locale>/daily/<YYYY-MM-DD>.json
data/i18n/<locale>/weekly/<YYYY-Www>.json
data/i18n/<locale>/story/<sid>.json
data/i18n/<locale>/storyline/<slug>.json
data/i18n/<locale>/topic/<slug>.json
data/i18n/<locale>/foundations/<slug>.json
```

Required fields:

```json
{
  "locale": "ko",
  "source_path": "/weekly/2026-W27",
  "source_hash": "<hash from current English source>",
  "translated_at": "2026-07-05T00:00:00Z",
  "model": "<translation model>",
  "review_status": "machine",
  "title": "...",
  "description": "..."
}
```

Daily and weekly artifacts should be field-complete when possible:

- `title`
- `description`
- `intro`
- `highlights`
- `categories[].name`
- `categories[].summary`
- `categories[].articles[].title`
- `categories[].articles[].summary`

Do not translate or rewrite URLs, source names, publication dates, slugs, story
links, model names, product names, code identifiers, benchmark names, or other
evidence fields.

## 3. Compute and verify `source_hash`

`pipeline/render_static_pages.py` recomputes the source hash from the committed
English source. If the artifact hash is stale, the localized page is omitted.

The fastest verification path is:

```bash
python3 -m unittest tests.test_i18n_static_pages
```

If the test reports a stale hash, inspect the expected value with the renderer
helpers or refresh the artifact from the current English source.

## 4. Render static pages

Regenerate static output:

```bash
python3 pipeline/render_static_pages.py
```

Keep the commit scoped. The renderer can touch many generated pages and OG
cards. If the only intended output is a localized page, restore unrelated
generated output before staging:

```bash
git restore -- web/daily web/weekly web/story web/storyline web/topic web/foundations web/og web/index.html web/map.html web/foundations.html web/sitemap.xml
```

Do not restore the intended `web/<locale>/...` page.

## 5. Validate exposure

Run:

```bash
python3 -m py_compile pipeline/render_static_pages.py
python3 -m unittest tests.test_i18n_static_pages tests.test_site_chrome
git diff --check
```

Check the rendered page contains:

- `<html lang="<locale>">`
- canonical URL for the localized page
- `hreflang` links for localized, English, and `x-default`
- `data-language-link` action back to English
- translated body fields for daily/weekly pages

English source pages expose the localized language action only when the artifact
is fresh. `web/site-chrome.js` reveals that action only when the reader's
browser language matches the target locale.

## 6. Playbook overlays

Do not show English Playbook overlay cards on localized recaps.

Today `data/playbook/source-index.json` is English-only and there is no
`data/i18n/<locale>/playbook/source-index.json` contract. Localized daily and
weekly pages suppress Playbook overlays until a locale-specific source index
exists.

## 7. Commit

Stage only the intended files:

- translation artifact under `data/i18n/<locale>/...`
- rendered localized page under `web/<locale>/...`
- renderer/test/doc changes, if any

Keep these changes separate from runtime feed data commits.
