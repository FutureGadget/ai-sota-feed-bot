# Spec: Localized Live Feed

`/ko/` is the English home page with Korean UI text and a Korean feed where a
translation exists. This spec covers the translation store, the API overlay, the
builder, the budget cap, and the kill switch.

## One UI for every language

The home page has one source and one feature set in every language. `/ko/` is
not a separate page. A reader gets the English home's sections, features, and
analytics with the interface in Korean. Each feed card is Korean where a current
translation exists and English otherwise.

Build.

- `ui/templates/index.html` is the only hand-edited source.
  `pipeline/render_home.py` writes `web/index.html` and `web/ko/index.html` from
  it. Both are committed, and a test fails when one is stale.
- `render_static_pages.py` runs the build on every run and splices each
  language's crawler-visible feed snapshot into its page. The snapshot is built
  from the English feed. Its chrome is in the page's language, and its items
  carry `lang="en"` on other languages' pages.
- UI text lives in `config/ui/<code>.json`, one flat file per language. HTML text
  is substituted at build time. Script text goes through `t(key, vars)` over a
  dictionary the build embeds as `window.UI`. See
  `docs/how-to/add-ui-text.md`.

Behavior of a localized page.

- It declares `<html lang="ko">`, a canonical URL for `/ko/`, and `hreflang`
  alternates for `en`, `ko` and `x-default`. The English page declares the same
  alternates.
- It requests `/api/feed?locale=ko` and `/api/playbook?locale=ko`. The feed is
  the English home's feed for the same parameters (see "Per-card translations").
- A card with no current translation keeps its English text. Its title and
  summary carry `lang="en"` and a muted "영문" tag, so readers and screen readers
  know the language. A translated card carries neither.
- An internal link goes to a `/ko/...` page only when that file exists and the
  Worker routes it. Every other link keeps its English path. Today that is the
  home page, `/daily`, `/weekly`, `/community`, `/playbook`, per-storyline pages,
  per-story links in the feed seed, and the Korean signup
  (`/subscribe?lang=ko`). A missing page would be a 404 with no fallback.
- The language switch toggles `/` and `/ko/`. `site-chrome.js` shows it to
  readers whose browser prefers the other language.
- Typography comes from the existing `html[lang="ko"]` rules in
  `web/site-chrome.css`.

What stays English on a Korean page.

- Product, model, and source names.
- Text that comes from data and has no translation store: Editor's Desk item
  titles from `/api/updates`, Skill Radar descriptions, watchlist chip labels.
- The pages `/playbook/<date>`, `/playbook/lab/...`, and `/models`, which have no
  Korean version.

What the Korean page does not have.

- No stale, paused, or incomplete banner, no "Newer in English" section, and no
  separate Korean feed. The page always shows the live feed, so nothing is
  frozen and nothing needs explaining.
- No 24-hour freshness rule and no 20-card cap. The page shows what the English
  home shows.

## Objective

A Korean reader opens `/ko/`, reads the same Brief feed as the English home, and
sees each card in Korean when one is available. A card that is not translated yet
shows in English, labeled. The English ranking, items, and links never change.

## Per-card translations

Store: `data/i18n/<locale>/feed/cards.json`, one entry per English card, keyed by
the translation key (the card's URL without a trailing slash):

```json
{"locale": "ko", "updated_at": "<iso>", "cards": {"<translation_key>": {
  "source_hash": "<sha256 of the English title, summary, why, also_covered>",
  "model": "<translator model>", "translated_at": "<iso>", "last_seen": "<iso>",
  "title": "", "summary_1line": "", "why_it_matters": "",
  "also_covered": [{"url": "", "title": ""}]}}}
```

A card is translated whole or not at all. Its title, summary, why-it-matters
line, and also-covered titles come from one call, so a card never mixes
languages. This file is the only localized feed artifact. `scripts/r2_sync.py`
publishes it and the Worker preloads it for `/api/feed?locale=<l>`.

## Overlay contract

`/api/feed?locale=ko` returns the normal English response for the same params.
Each item whose stored `source_hash` equals the hash of the item as served (after
coverage decoration) gets `title`, `summary_1line`, `why_it_matters`, and
`also_covered[].title` from the store. Every item carries
`i18n: {"locale": "ko", "translated": true|false}`. A stale or missing entry
leaves the English text with `translated: false`. The two hash implementations
(`_source_hash` in Python, `sourceHash` in `api/feed.js`) are pinned together by
`tests/test_source_hash_parity.py`. The default locale and unknown locales get no
overlay and no `i18n` field.

## Translation pipeline

`pipeline/build_localized_feed.py` runs in the hourly feed workflow after the
English feed is built. Per run:

1. Fetch the English home's default `/api/feed` request: Brief, rolling 24-hour
   arrival window, limit 200. `home_params` mirrors `buildFeedUrl()` in
   `ui/templates/index.html`, and a test fails when they drift.
2. Skip each card whose stored `source_hash` and `model` still match.
3. Translate the rest, one call per card, at most `MAX_TRANSLATIONS` (60) per
   run. A card that fails is skipped and retried next run.
4. Set `last_seen` on every card of the fetched set, drop entries unseen for 14
   days, and write the store.

Translation failure never blocks the English publish. `run_full.sh` logs
`localized_feed_step_failed=1` and goes on. Every run logs one line:

```text
localized_feed_budget usd_spent=<n> cap=<n> month=<YYYY-MM>
```

## Translation Budget Cap

Each card is translated by Claude (`pipeline/translator.py`, model from
`config/translation.json`). Spend is metered in USD by one ledger,
`data/i18n/translation_spend.json`, shared with the static-page translator.
When the month's spend plus the next call's estimate would pass `monthly_usd_cap`
(policy default, or `TRANSLATION_MONTHLY_USD_CAP`), the translator raises
`BudgetExceeded`.

At the cap the builder keeps the cards it already translated, writes the store,
logs `localized_feed_budget_cap_reached`, and exits 0. There is no status file and
no banner. Cards without a translation show in English until the month rolls over.
The cap is a hard stop, not a ladder: the hourly run translates only cards whose
`source_hash` changed, so a normal month costs far less than the cap.

The ledger is pipeline-only: `r2_sync.py` does not publish it. Shape
and rollover rules are in `docs/generated/db-schema.md`. Operations are in
`docs/how-to/translation-budget-and-quota.md`.

## Kill switch

`LOCALIZED_FEED_ENABLED` is read by `api/feed.js`. When it is `0`, `false`, `no`,
or `off`, `/api/feed?locale=ko` returns the plain English feed: no overlay and no
`i18n` field. Committed translations stay on disk, and `/ko/` keeps its Korean UI
text. The Worker sets it in `worker/wrangler.jsonc`.

## Routing and SEO

- `/ko/` is served from `web/ko/index.html`. The Worker routes it, and
  `web/sitemap.xml` lists it next to `/`.
- Both home pages declare a self-canonical and the same `hreflang` set (`en`,
  `ko`, `x-default`). `/ko/` is not `noindex`.
- `render_static_pages.py` ignores `data/i18n/<locale>/feed/**`. It writes the
  sitemap entry for each language's home from `config/locales.json`.

## Commands

```bash
python3 pipeline/build_localized_feed.py --dry-run   # fetch and count, translate nothing
python3 pipeline/build_localized_feed.py --locale ko # needs credentials
python3 scripts/translation_preview.py --limit 2 --dry-run
python3 pipeline/render_home.py --check
node --test tests/test_feed_card_translations.mjs
python3 -m pytest -q tests/test_localized_feed.py tests/test_card_store.py
```

## Project structure

```text
pipeline/build_localized_feed.py   # fetch the home feed, translate, write the store
pipeline/card_store.py             # store shape, freshness, 14-day prune
pipeline/translator.py             # Claude calls and the USD ledger
api/feed.js                        # per-card overlay and the kill switch
data/i18n/<locale>/feed/cards.json # the store
ui/templates/index.html            # the one home template
```

## Testing

- `tests/test_localized_feed.py`: translate only what changed, retranslate on a
  new model, prune, `MAX_TRANSLATIONS`, ledger spend, cap behavior, failed cards,
  dry run.
- `tests/test_card_store.py`: store shape, freshness, prune.
- `tests/test_feed_card_translations.mjs`: overlay (run pool and arrival-window ledger
  paths), untranslated cards stay English, no overlay for the default locale, kill switch.
- `tests/test_source_hash_parity.py`: Python and JS hashes agree.

## Boundaries

Always:

- Preserve the English ranking order, item identity, and source URLs.
- Fail open for the English feed when translation fails or the cap is reached.
- Mark an untranslated card as English.

Never:

- Re-rank or drop items during translation.
- Let a localized title change item identity for Saved, hidden, feedback, or
  analytics events.
- Commit translation API keys or provider secrets.
- Translate non-Brief lenses or other languages' feeds without a request: the
  store covers the home's default request only.
