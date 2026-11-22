# Spec: Localized Live Feed

`/ko/` is the English home page with Korean UI text, a Korean feed, and a Korean
Editor's Desk where a translation exists. This spec covers the translation
stores, the API overlays, the builders, the budget cap, and the kill switch.

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
- It requests `/api/feed?locale=ko`, `/api/playbook?locale=ko`, and
  `/api/updates?locale=ko`. The feed is the English home's feed for the same
  parameters (see "Per-card translations"). The Editor's Desk strip and panels
  read `/api/updates` (see "Per-item translations: the Editor's Desk").
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
- Text that comes from data and has no translation store: Skill Radar
  descriptions, watchlist chip labels, and the storyline notice's thread title.
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

## Per-item translations: the Editor's Desk

The "Latest from the Editor's Desk" strip and the updates panels list the
editorial catalog (`lib/editorial-catalog.js`, served by `/api/updates`): recap,
storyline, topic, foundation, and playbook items. Each shows a title and a
one-line summary. On `/ko/` each item is Korean where a current translation
exists and English otherwise.

Store: `data/i18n/<locale>/updates/titles.json`, one entry per catalog item,
keyed by the item id (`daily:2026-11-22`, `storylines:<slug>`):

```json
{"locale": "ko", "updated_at": "<iso>", "items": {"<item id>": {
  "source_hash": "<sha256 of the English title and summary>",
  "translated_at": "<iso>", "title": "", "summary": "",
  "origin": {"title": "artifact | <translator model>", "summary": "artifact | <translator model>"}}}}
```

An item is translated whole or not at all: an entry holds both fields, and the
builder writes none while either is missing. The hash covers the title and the
summary because the desk shows both, so a storyline whose summary changes is
stale until the next build.

Overlay. `/api/updates?locale=ko` returns the normal catalog with each item whose
stored `source_hash` equals `updateHash(item)` (`lib/update-translations.js`)
given the stored `title` and `summary`. `id`, `href`, `version`, and the dates
never change, so read state, links, and "new" dots behave as in English. Every
item carries `i18n: {"locale": "ko", "translated": true|false}`. A stale or
missing entry leaves the English text with `translated: false`. The default
locale and unknown locales get no overlay and no `i18n` field.
`LOCALIZED_FEED_ENABLED` switches this overlay off with the feed's, through one
shared `localizedFeedEnabled()` in `lib/locales.js`. The two hash
implementations (`source_hash` in Python, `updateHash` in JS) are pinned together
by `tests/test_updates_hash_parity.py`.

Page. `web/nav-updates.js` requests `/api/updates?locale=<l>` when the page's
`window.UI` names a language other than the default, so only a localized home
page asks for translated items. An item with `translated: false` gets
`lang="en"` on its title and summary and the same "영문" tag the feed cards use.

Builder. `pipeline/build_localized_updates.py` runs after the card builder, inside
the same `LOCALIZED_FEED_ENABLED` gate in `run_full.sh`. For each catalog item it
takes each field from the first source that has it:

1. A current Korean artifact of the same page (`data/i18n/<locale>/daily|weekly|
   playbook|storyline|topic|foundations/`), fresh by its own `source_hash` as
   `render_static_pages.i18n_hash_matches` defines it. A text identical to the
   English (a storyline label the agent left in English) does not count. The
   summary is reused only where the catalog's choice of summary field is
   mirrored exactly: recap and playbook `highlights[0]` or `intro[0]`, and a
   current storyline's `whats_new` or `tldr`.
2. The entry from the last run, while its English text is unchanged.
3. One `translator.translate` call (surface `feed`, shared ledger, style guide
   `config/translation/<locale>.md`) for the fields still missing. The call
   carries the English summary as context, so a terse label such as "Activation
   Steering" is translated with its meaning. Only the newest
   `DESK_PER_SECTION` (6) items of each section are eligible, because the strip
   and panels show only those, and at most `MAX_TRANSLATIONS` (24) items are
   translated per run. Older items stay English unless an artifact covers them.

At the budget cap the builder keeps what it has, logs
`localized_updates_budget_cap_reached`, and exits 0. A failed item is skipped and
retried next run. A run that changes nothing does not rewrite the file. Entries
for items that left the catalog are dropped. `scripts/r2_sync.py` publishes the
store, and the Worker preloads it for `/api/updates?locale=<l>`.

## Translation Budget Cap

Each card and desk item is translated by Claude (`pipeline/translator.py`, model from
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

`LOCALIZED_FEED_ENABLED` is read through `lib/locales.js` by `api/feed.js` and
`lib/update-translations.js`. When it is `0`, `false`, `no`, or `off`,
`/api/feed?locale=ko` and `/api/updates?locale=ko` return the plain English
response: no overlay and no `i18n` field. Committed translations stay on disk, and `/ko/` keeps its Korean UI
text. The Worker sets it in `worker/wrangler.jsonc`.

## Routing and SEO

- `/ko/` is served from `web/ko/index.html`. The Worker routes it, and
  `web/sitemap.xml` lists it next to `/`.
- Both home pages declare a self-canonical and the same `hreflang` set (`en`,
  `ko`, `x-default`). `/ko/` is not `noindex`.
- `render_static_pages.py` ignores `data/i18n/<locale>/feed/**` and
  `updates/**`. It writes the
  sitemap entry for each language's home from `config/locales.json`.

## Commands

```bash
python3 pipeline/build_localized_feed.py --dry-run   # fetch and count, translate nothing
python3 pipeline/build_localized_feed.py --locale ko # needs credentials
python3 pipeline/build_localized_updates.py --dry-run # count desk items, translate nothing
python3 pipeline/build_localized_updates.py --locale ko # needs credentials
python3 scripts/translation_preview.py --limit 2 --dry-run
python3 pipeline/render_home.py --check
node --test tests/test_feed_card_translations.mjs tests/test_update_translations.mjs tests/test_nav_updates_locale.mjs
python3 -m pytest -q tests/test_localized_feed.py tests/test_card_store.py tests/test_localized_updates.py
```

## Project structure

```text
pipeline/build_localized_feed.py   # fetch the home feed, translate, write the store
pipeline/card_store.py             # store shape, freshness, 14-day prune
pipeline/build_localized_updates.py # the desk's artifact reuse, translation, store
pipeline/translator.py             # Claude calls and the USD ledger
api/feed.js                        # per-card overlay
lib/update-translations.js         # per-item desk overlay (/api/updates)
lib/locales.js                     # locales and the kill switch
web/nav-updates.js                 # the desk strip and panels
data/i18n/<locale>/feed/cards.json # the card store
data/i18n/<locale>/updates/titles.json # the desk store
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
- `tests/test_localized_updates.py`: desk items reuse current artifacts, translate
  only missing fields of the newest items, `MAX_TRANSLATIONS`, ledger and cap
  behavior, dry run.
- `tests/test_updates_hash_parity.py`: Python and JS desk hashes agree.
- `tests/test_update_translations.mjs`: desk overlay, stale entries, kill switch,
  default locale, Worker preload.
- `tests/test_nav_updates_locale.mjs`: the locale reaches `/api/updates` on `/ko/`
  only, and an untranslated item is marked `lang="en"`.

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
