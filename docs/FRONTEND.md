# FRONTEND.md

The primary user surface is the website at https://www.llm-digest.com, with
RSS and scheduled email as retention channels.

## Shared site chrome

Every reader-facing page uses the same responsive header contract:

1. compact LLM Digest home link;
2. optional surface-primary action (Feed Search is the current example);
3. visibly labeled Browse control;
4. More actions for page utilities;
5. page title/status;
6. visible date/week/edition context controls where applicable.

Source assets:

- `web/site-chrome.css` — layout, dialogs, safe areas, focus, responsive and
  no-JavaScript behavior
- `web/site-chrome.js` — progressive enhancement, destination grouping,
  current-route state, dialog lifecycle, scroll locking, and focus restoration
- `pipeline/render_static_pages.py` — generated-page header, canonical
  destination registry, parent-route mapping, and static archive controls

The canonical Editor's Desk order is Live feed, Daily recap, Weekly recap,
Storylines, Playbook, Agent Know-How, Foundations, Model Radar, Voices, and
Email digest. Do not define a page-specific destination subset or reorder these
links.

### Extension rules

- Put global destinations in `.site-nav-fallback`.
- Put secondary page actions in `.site-actions-fallback`.
- Keep primary content controls outside both disclosures.
- Daily, Weekly, and Playbook selectors use `.site-context` with
  Previous/Current/Next controls.
- The fallback navigation must remain usable before JavaScript initializes.
- Shared JavaScript moves existing semantic nodes into native dialogs; it does
  not create the only copy of a link or action.
- Never add horizontal scrolling to global navigation or page actions.
- Generated pages are changed only through `pipeline/render_static_pages.py`.

Product contract:
`docs/product-specs/mobile-site-chrome.md`.

## Site theme

Every page uses one theme, Precision (2026-11-07): neutral grays, one red
accent, Geist for text and headings, Geist Mono for ranks, scores, prices and
dates, 1px lines, 8px controls, and a dark mode designed alongside light.

- `web/site-chrome.css` owns the palette tokens (`--bg`, `--card`, `--border`,
  `--line-strong`, `--accent`, `--muted`, `--fg`, `--signal`, `--warm`, the
  editorial washes such as `--brief-wash`) for light and dark, plus the type
  tokens `--font-display`, `--font-serif`, `--font-sans` (all Geist) and
  `--font-mono` (Geist Mono). The fonts are self-hosted in `web/fonts/` (SIL
  OFL) and staged by `scripts/build_site.py`. Every page already loads it.
- Every page preloads both woff2 files before `site-chrome.css`, and each
  stack names a metric-matched local face next ("Geist Fallback" on Arial,
  "Geist Mono Fallback" on Courier New, with `size-adjust` and ascent/descent
  overrides). Text keeps its width when the web font swaps in late, so lines
  don't rewrap. A new page needs the two preload tags (`WebFontLoadingTest`).
- Pages and `pipeline/render_static_pages.py` templates consume these tokens
  and never redefine them. Page-local tokens are fine for things that are not
  palette, such as storyline timeline hues (`--t-*`) or layout knobs.
- `tests/test_site_chrome.py` (`BroadsheetThemeTest`, named for the previous
  theme) enforces both rules and checks that text tokens hold 4.5:1 contrast
  on `--bg`, `--card` and the wash.
- Avoid the old broadsheet devices when you touch a page: monospace all-caps
  kickers, left-border callouts, square controls. Use sentence-case labels,
  Geist Mono only for data, and Basecoat components.

## UI framework

Every page loads Tailwind CSS v4 + Basecoat, built into `web/ui.css` from
`ui/site.css` (Oat was retired 2026-11-07). `ui/site.css` supplies the bare
element defaults page CSS builds on; `<html data-ui-base="none">` opts a page
out, as `/subscribe` does. For new markup, use Basecoat classes
(`.btn`, `.input`, `.card`, `.field`, `.label`) for components and Tailwind
utilities for layout, with `text-brand`, `text-ink-muted`, `bg-wash` and
`font-display` for broadsheet colors and type. After editing `ui/site.css`,
the component list or a migrated page's classes, run `npm run build:css` and
commit `web/ui.css` (CI runs `npm run check:css`). Rules, token mapping, page
order and checklist: `docs/design-docs/ui-framework-migration.md`.

## Share images and icons

Share images use the Precision light palette (they appear outside the site)
and Geist.

- `pipeline/og_cards.py` draws the per-edition cards in `web/og/` during the
  feed run: brand mark and dateline, the page's red mono kicker, a Geist
  headline, a one-line summary (the recap's first highlight, or a storyline's
  latest change), and counts. No reading-time claims.
- `scripts/make_og_assets.py` draws the default card (brand, the feed
  masthead, the line under it), the "LD" logo, and the rule-mark icons. Re-run
  it when the brand, masthead or tagline changes.
- Fonts: vendored Geist in `assets/fonts/geist/` (OFL). Korean text falls back
  to Nanum Gothic from the workflow's `fonts-nanum`.
- `web/favicon.svg` is the vector rule mark (a red tile with three ruled
  lines, the same mark the header draws); keep it in step with `MARK_LINES`
  in `make_og_assets.py`. `theme-color` meta tags and `site.webmanifest` use
  the palette's paper.

Examples: `docs/assets/share-images-2026-11-07/` (current) and
`docs/assets/share-images-2026-10-10/` (the broadsheet cards).

## Feed front page

`web/front-page.css` sets the Brief's first five stories as a front page
(a lead with its summary, four headlines beside it) and styles every story card
as a headline plus one source line, with share, hide, feedback and the ranking
reason in a `details.card-more` "⋯" panel. It resets the UI library's boxed
`<details>` styles for that panel. The English and Korean feeds link it after
their inline `<style>` so it wins ties with the ledger rules. It reflows
ordinary cards via `#list:has(> article.fp-lead)` without wrapping them; keep
`#list > article` as the card contract. Contract:
`docs/product-specs/feed-front-page.md`.

## Editorial discovery

`web/nav-updates.js` renders item previews in the Desk, feed and section roots.
`web/editorial-state.js` owns pure opened-version rules; shared row styling is
in `web/editorial-updates.css`. `/updates` (`web/updates.html`) provides the
complete Latest/Unread collection. It is linked as a secondary content action,
not inserted into or reordered within the canonical section navigation.
Dynamic Playbook/Lab pages report successful edition rendering through
`editorial:opened`. Contract: `docs/product-specs/nav-update-indicators.md`.

## Watchlist

`web/watchlist.js` and `web/watchlist.css` add Watch chips and the feed's
watchlist module. Any element with `data-watch-title` (plus optional
`data-watch-source` and `data-watch-context="story"`) is filled with one chip
per matching entity from `/watch-data.json`; an element that matches nothing
stays hidden. The feed renders that slot inside each card's `details.card-more`
panel and owns `#watchHome`; `story_watch_html()` in
`pipeline/render_static_pages.py` emits the slot, stylesheet and script on
story pages that match. The script reuses the `.subscribe-inline` form styles
for its email offer. Contract: `docs/product-specs/watchlist.md`.
