# UI framework migration: Oat → Tailwind CSS v4 + Basecoat

Status: **done** (2026-11-07). Oat is retired: every shell and the static-page
template load `/ui.css`, and the Oat files are deleted. `/subscribe` is the only
page built from Basecoat classes and utilities; the others keep their own page
CSS on top of the element defaults described below. Decision records:
`decision-log.md`, 2026-11-06 and 2026-11-07.

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
- Every shell and the render template load `ui.css`; Oat must not come back
  (`test_oat_is_retired_and_every_shell_loads_the_ui_layer`).
- Preflight is a generated copy (`ui/generated/preflight.css`) whose `[hidden]`
  rule is not `!important`, so page rules such as a disabled pager control
  shown with `display:inline-flex` still win (`test_preflight_keeps_hidden_overridable`).
- `source(none)`: Tailwind scans only the `@source` files listed in
  `ui/site.css`, not the ~8k generated pages or `data/`.

### Element defaults (replaced Oat)

Page CSS and the render templates were written on top of Oat's bare-element
rules. `ui/site.css` reproduces the ones they rely on: semibold headings with
1.25 line height, underlined links, `dialog` line height 1.5, heading sizes,
paragraph and list spacing, `code`/`pre`, tables, bordered buttons and inputs,
`details`/`summary` disclosures, `[role="alert"]` boxes and the `[aria-busy]`
spinner. Everything except the heading, link and dialog rules is scoped with
`:where(html:not([data-ui-base="none"]))`, so it has zero specificity and a page
can opt out. `/subscribe` sets `data-ui-base="none"` because it is built from
Basecoat classes alone.

Verified by screenshotting 20 pages at 390px and 1280px in light and dark
against `main`: the only visible change is the Daily/Weekly summary line height,
which now follows those pages' own `line-height:1.58` (Oat had overridden it).
Dialogs open and close with Escape and the backdrop on all six pages that have
them.

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

## Order the pages moved in

All steps are done; step 7 was finished on 2026-11-07 by loading `ui.css` on every
remaining page at once. Next, rebuild individual pages from Basecoat classes
(the per-page checklist) when they are next touched.

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
7. Delete `web/oat.min.css`, `web/oat.min.js`, `web/oat.LICENSE.txt` and
   `docs/references/oat-ui-vendor.md`: done 2026-11-07.

### Per-page checklist

- Add the page to `@source` and to `UTILITY_SHELLS` in `tests/test_ui_layer.py`
  so Tailwind generates the utilities it uses.
- Replace page `<style>` rules with utilities or Basecoat classes; keep only
  what utilities cannot express.
- For an interactive component, use the Basecoat equivalent and its JS from
  `basecoat-css/dist/js/` (vendored, pinned).
- `npm run build:css`, then screenshot 375px and desktop in light and dark,
  measure CLS, keyboard-focus every control, and diff the chrome's computed
  styles against the previous version.
- Bump the `?v=` on `ui.css` whenever `web/ui.css` changes. Every migrated
  page references the same version.
- Add a decision-log entry.

## Rollback

Revert the 2026-11-07 "Retire Oat" commit: it restores the Oat files and the
`oat.min.css` links. A page rebuilt from Basecoat classes is reverted with its
own commit.
