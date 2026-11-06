# UI framework migration: Oat → Tailwind CSS v4 + Basecoat

Status: **pilot shipped on `/subscribe`** (2026-11-06), and the whole site moved
to the Precision theme (2026-11-07). Every page except `/subscribe` still
loads Oat for components. Decision records: `decision-log.md`, 2026-11-06 and
2026-11-07.

## The look: Precision

The approved direction keeps llm-digest's structure (masthead, section tabs,
ranked Brief, Editor's Desk, Model and Skill Radar, the end-of-Brief line) and
executes it in a Linear/Vercel style. The mockups live on the design canvas
"LLM Digest — new look directions", Precision page (front page light, dark
and phone; subscribe light and phone). Tokens are in `web/site-chrome.css`;
Basecoat reads them through `ui/site.css`. As each page is rebuilt, drop its
broadsheet leftovers (monospace caps kickers, left-border callouts, square
controls). Screenshots after the theme swap:
`docs/assets/ui-framework-migration/*precision*.jpg`.

Visual status (2026-11-07): every page, the feed front page included, now
renders in the Precision style. The broadsheet devices were removed from page
CSS in one sweep (decision log, "Precision pass over every page"). What
remains below is the component migration: moving each page off Oat onto
Basecoat, which changes markup and removes the Oat reset rules, not the look.

## Why

Oat styles bare elements globally (`article`, `details`/`summary`, `[role=tab]`,
`nav a`, focus outlines). Almost every new surface has needed explicit resets
for it, and several tests exist only to guard them
(`test_map_row_resets_oat_article_box`, `test_no_oat_gray_hover_fill_on_nav`,
the storyline tab/disclosure resets). Oat is also sub-v1 upstream, with breaking
changes expected before 1.0.

Basecoat is opt-in: a component is styled only when it carries a class
(`.btn`, `.input`, `.card`, `.field`). Tailwind utilities handle page layout, so
pages stop growing private `<style>` blocks. The Lyra style pack is square, which
matches the broadsheet look.

## How the layer is built

| File | Role |
|---|---|
| `ui/site.css` | Tailwind input: token bridge, Oat-parity base, broadsheet primitives (`.kicker`, `.message`, touch sizes) |
| `ui/basecoat-components.json` | The Basecoat components bundled. Add one when a page needs it |
| `scripts/build_ui_css.mjs` | Copies the listed components (structure + Lyra section) into `ui/generated/basecoat.css`, runs the Tailwind CLI, stamps the MIT notices |
| `web/ui.css` | Committed output (~70 KB raw, ~8 KB gzip). Served as `/ui.css` |

Commands: `npm run build:css`, `npm run watch:css`, `npm run check:css` (CI
fails with `UI_CSS_STALE` if `web/ui.css` was not rebuilt). The deploy needs no
Node build step, because the output is committed. Versions are pinned exactly in
`package.json`.

### Rules that keep the theme intact

- `site-chrome.css` still owns the palette (`BroadsheetThemeTest` now also
  scans `ui/site.css`). The bridge only derives shadcn tokens from it
  (`--primary: var(--accent)`, `--ring: var(--accent)`, `--radius: 0`, …).
- Basecoat's own `base.css` is never imported. Its `:root` block would reset
  `--accent`, `--muted`, `--card` and `--border` to neutral grays on every page.
- `--accent` and `--muted` mean "brand red" and "secondary text" here, but
  "hover surface" and "muted surface" in shadcn. Tailwind's `--color-accent` and
  `--color-muted` therefore point at `--ui-accent` and `--ui-muted`. Use
  `text-brand` and `text-ink-muted` in markup for the broadsheet meanings.
- Dark mode is `html[data-theme="dark"]` (the `dark:` variant is remapped), not
  shadcn's `.dark` class.
- Load `/ui.css` **before** `/site-chrome.css`. Tailwind's output is layered and
  `site-chrome.css` is not, so the shared header always wins.
- A page loads either Oat or `ui.css`, never both (`test_unmigrated_pages_do_not_load_ui_css`).
- `source(none)`: Tailwind scans only the `@source` files listed in
  `ui/site.css`, not the ~8k generated pages or `data/`.

### Oat parity block

`site-chrome.css` and the render templates were written on top of Oat's base
rules: semibold headings with 1.25 line height, underlined links with a 2px
offset, and `dialog` line height 1.5. `ui/site.css` reproduces exactly those
rules so the shared header and the Editor's Desk dialog compute identically on
migrated and unmigrated pages. The pilot verified this by diffing computed
styles of every chrome element (brand, page heading, Subscribe, theme toggle,
Desk button, the open dialog and its links) at 375px and 1280px; after the
parity block there were no differences. Delete the block when no page loads
`oat.min.css`.

## Pilot result: `/subscribe`

The page now uses Basecoat `.card`, `.input`, `.btn`, `.label` and radio
components and Tailwind utilities. Its private `<style>` block went from about
90 lines to the honeypot's single rule. Behavior is unchanged (same JS, same
config branches, same events), and `tests/test_subscribe_surface.py` still pins
it. Measured on the local preview with the form enabled:

| | Before (Oat) | After (Basecoat) |
|---|---|---|
| CLS, 375px light / dark | 0.062 / 0.069 | 0.054 / 0.054 |
| CLS, desktop light / dark | 0.027 / 0.027 | 0.024 / 0.023 |
| Email field and Subscribe height | 51px | 48px |
| Horizontal overflow at 375px | none | none |
| Framework CSS bytes (raw, gzip) | 31.6 KB + 10.4 KB JS | 69.7 KB, 8.0 KB gzip, no JS |

Screenshots: `docs/assets/ui-framework-migration/subscribe-*-{before,after}.jpg`.

## Order for the remaining pages

Smallest and most self-contained first, the feed last:

1. `updates.html`, `voices.html`, `playbook-lab.html` (small shells)
2. `models.html`, `models-compare.html` (tables: add `table`)
3. `daily.html`, `weekly.html`, `storyline.html` (index), `playbook.html`
4. `pipeline/render_static_pages.py` templates: story, daily/weekly archives,
   storyline, topic, foundations, skills, models. Add the renderer to
   `@source` (Tailwind reads class names from `.py` files) and re-render.
   Remove the Oat reset tests as each surface moves.
5. `index.html` and `ko/index.html` (feed, `front-page.css`, swipe-to-hide),
   rebuilt to the Precision front-page mockup. Now the next step, ahead of
   the smaller shells, because the owner approved the design on it; watch the
   north-star metric (weekly returning readers) after it ships.
6. Share cards (`pipeline/og_cards.py`): done 2026-11-07 (Precision palette,
   Geist, rule-mark icons).
7. Delete `web/oat.min.css`, `web/oat.min.js`, `web/oat.LICENSE.txt`,
   `docs/references/oat-ui-vendor.md`, the Oat hash test and the parity block.

### Per-page checklist

- Swap the `oat.min.css` (and `oat.min.js`) link for
  `/ui.css?v=<date>-<slug>` placed before `site-chrome.css`; add the page to
  `@source`, `UI_SHELLS` in `tests/test_site_chrome.py` and `tests/test_ui_layer.py`.
- Replace page `<style>` rules with utilities or Basecoat classes; keep only
  what utilities cannot express.
- If the page used an Oat web component (`oat.min.js`), replace it with the
  Basecoat equivalent and its JS from `basecoat-css/dist/js/` (vendored, pinned).
- `npm run build:css`, then screenshot 375px and desktop in light and dark,
  measure CLS, keyboard-focus every control, and diff the chrome's computed
  styles against the Oat version.
- Bump the `?v=` on `ui.css` whenever `web/ui.css` changes. Every migrated
  page references the same version.
- Add a decision-log entry.

## Rollback

Per page: restore the `oat.min.css` link and the page's previous markup and
`<style>` (git revert of that page's commit). The layer itself is additive:
deleting `ui/`, `scripts/build_ui_css.mjs`, `web/ui.css`, the CI step and the
three devDependencies leaves every Oat page untouched.
