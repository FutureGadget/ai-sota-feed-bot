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

Every page uses one broadsheet theme: warm paper with an ink-red accent, a
matching dark variant, and serif headlines.

- `web/site-chrome.css` owns the palette tokens (`--bg`, `--card`, `--border`,
  `--accent`, `--muted`, `--fg`, `--signal`, `--warm`, the editorial washes
  such as `--brief-wash`) for light and dark, plus the type tokens
  `--font-display` (titles), `--font-serif` (headlines, reading text) and
  `--font-sans` (UI). Every page already loads it.
- Pages and `pipeline/render_static_pages.py` templates consume these tokens
  and never redefine them. Page-local tokens are fine for things that are not
  palette, such as storyline timeline hues (`--t-*`) or layout knobs.
- `tests/test_site_chrome.py` (`BroadsheetThemeTest`) enforces both rules and
  checks that text tokens hold 4.5:1 contrast on `--bg`, `--card` and the wash.

## Share images and icons

Share images follow the same theme (light palette only, since they appear
outside the site).

- `pipeline/og_cards.py` draws the per-edition cards in `web/og/` during the
  feed run: nameplate and dateline, the page's red kicker, a Playfair headline,
  a one-line summary (the recap's first highlight, or a storyline's latest
  change), and counts. No reading-time claims.
- `scripts/make_og_assets.py` draws the default card (nameplate, the feed
  masthead, the line under it), the "LD" logo, and the stack-mark icons. Re-run
  it when the brand, masthead or tagline changes.
- Fonts: vendored Playfair in `assets/fonts/playfair/` (OFL). Korean text
  falls back to Nanum Myeongjo/Gothic from the workflow's `fonts-nanum`.
- `web/favicon.svg` is the vector stack mark; keep its colours in step with
  `MARK_*` in `make_og_assets.py`. `theme-color` meta tags and
  `site.webmanifest` use the palette's paper and red.

Examples: `docs/assets/share-images-2026-10-10/`.

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
