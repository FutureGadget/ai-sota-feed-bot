# Multilingual pre-translated pages

## Goal

Make high-value LLM Digest pages discoverable and readable in non-English
languages by publishing pre-translated static pages. Do not depend on live
browser translation controls or client-side translation APIs.

The first target locale is Korean (`ko`). Additional locales use the same data
and routing contracts once the Korean path is proven.

## Non-goals

- Live client-side translation UI.
- Browser `Translator` API integration.
- Fully localized application chrome in v1.
- Translating source articles hosted by third parties.
- Personal language preference or account state.

## URL Contract

Localized pages live under a locale prefix and keep the English page shape:

| English | Korean |
|---|---|
| `/daily/2026-07-05` | `/ko/daily/2026-07-05` |
| `/weekly/2026-W27` | `/ko/weekly/2026-W27` |
| `/story/<sid>` | `/ko/story/<sid>` |
| `/storyline/<slug>` | `/ko/storyline/<slug>` |
| `/foundations/<slug>` | `/ko/foundations/<slug>` |
| `/topic/<slug>` | `/ko/topic/<slug>` |

The canonical URL remains the current page's language. Each localized page
emits `hreflang` alternates for available languages plus `x-default` pointing to
English.

## Data Model

Store translations as generated-but-reviewable artifacts separate from the
English source data:

```text
data/i18n/
  ko/
    manifest.json
    daily/2026-07-05.json
    weekly/2026-W27.json
    story/<sid>.json
    storyline/<slug>.json
    foundations/<slug>.json
    topic/<slug>.json
```

Each translation file includes:

- `locale`
- `source_path`
- `source_hash`
- `translated_at`
- `model`
- translated fields keyed by the source field name
- optional `review_status`: `machine`, `reviewed`, or `needs_update`

`source_hash` is computed from the English fields that feed the localized page.
If it changes, the translation is stale and the localized page should either be
regenerated or omitted from the localized manifest.

## Translation Scope

Translate reader-facing editorial text:

- recap titles, intros, highlights, category names, summaries, and article
  summaries
- story brief titles, summaries, why-it-matters text, release highlights, and
  related-section labels
- storyline editorial overlays and item notes
- wiki/foundation page prose

Preserve exact technical terms unless the locale has an established translation:

- model names, company names, product names, library names
- acronyms such as RAG, MCP, RLHF, GPU
- code identifiers, URLs, dates, prices, percentages, and benchmark names

## Prioritization

Translate pages in this order:

1. Pages with the highest 60-day page views from PostHog.
2. Current daily and weekly recap pages.
3. Storyline and foundation pages with recent updates.
4. Story permalinks linked from the translated recaps.
5. Long-tail archive pages as budget allows.

The selector should write an input bundle with `path`, `surface`, `views_60d`,
`last_modified`, `source_hash`, and current translation status so the translation
routine can spend model calls only where they improve reader reach.

## Publishing Flow

1. Build an i18n candidate bundle from committed English data plus recent
   PostHog page-view counts. Use `pipeline/export_i18n_candidates.py` to filter
   by `--locale` and `--surface` before loading full source payloads.
2. Translate missing or stale candidates with a small language model.
3. Validate JSON shape, placeholder preservation, URL preservation, and
   `source_hash` alignment.
4. Render locale-prefixed static pages from `data/i18n/<locale>/`.
5. Emit `hreflang` alternates and include localized pages in `sitemap.xml`.
6. Commit translation data and rendered pages separately from runtime feed data
   when practical.

Agents should use `.agents/skills/add-translated-page/SKILL.md` for one-page
translation publishing. Do not add or refresh translated pages unless the user
explicitly asks for that work.

## Fallback Behavior

If a translation is missing or stale, do not serve a half-translated page. Link
to the English page and let normal browser translation remain a reader-owned
fallback outside the site UI.

APIs remain English in v1. Localized static pages are the first product surface
because they give crawlers, shares, and readers stable translated content.

## Acceptance Criteria

- No page loads `web/local-translate.js` or exposes live translation controls.
- `/ko/daily/<date>` can be generated from a checked-in translation artifact.
- English and Korean pages include reciprocal `hreflang` links.
- The sitemap includes localized URLs only when translations are fresh.
- Translation validation fails on lost URLs, placeholders, model names, or stale
  `source_hash` values.
