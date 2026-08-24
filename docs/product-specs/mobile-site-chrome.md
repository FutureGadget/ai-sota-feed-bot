# Mobile site chrome UX contract

## Status

Implemented on `feature/mobile-site-chrome`; pending PR review and production
merge.

## Objective

Replace the inconsistent, horizontally scrolling mobile headers with one shared
site-navigation system across every reader-facing LLM Digest page.

The system must let a reader answer three questions without horizontal
scrolling:

1. Where am I?
2. What date, week, edition, or feed range am I viewing?
3. How do I move to another LLM Digest surface?

This change serves engineers who use LLM Digest as a finishable reading tool.
Navigation should be calm, compact, and predictable; page content must remain
the dominant visual element.

## Release requirement

This is an **atomic cross-site release**, not a page-by-page experiment.

Implementation may be divided into small internal tasks, but the feature is not
complete and must not be released until the shared chrome is present on every
surface in the scope matrix below. Hand-written shells and generated pages must
change in the same code release so readers never encounter two competing mobile
navigation models.

## Product principles

- **No hidden primary navigation.** A reader must never need to horizontally
  scroll to discover a destination or archive picker.
- **Orientation stays visible.** Page identity and date/week/edition context
  take priority over utilities.
- **Breadth is progressively disclosed.** The full destination list belongs in
  Editor's Desk, alongside page-specific actions that do not deserve a separate
  top-level mobile button.
- **One site, not adjacent microsites.** Destination order, names, interaction,
  and visual treatment are consistent across surfaces.
- **Content keeps priority.** Navigation must not become a large dashboard or
  permanently consume the bottom of the viewport.
- **The web remains resilient.** Core destinations and actions remain reachable
  when JavaScript fails.

## Information architecture

### Global destinations

Editor's Desk presents the same destinations in the same order everywhere:

| Group | Destination | Route | Label |
|---|---|---|---|
| Catch up | Live feed | `/` | Live feed |
| Catch up | Daily recap | `/daily` | Daily recap |
| Catch up | Weekly recap | `/weekly` | Weekly recap |
| Follow | Storylines | `/storylines` | Storylines |
| Apply | Playbook | `/playbook` | Playbook |
| Understand | Knowledge map | `/map` | Knowledge map |
| Understand | Foundations | `/foundations` | Foundations |
| More | Voices | `/voices` | Voices |
| More | Email digest | `/subscribe` | Email digest |

The current destination is marked with `aria-current="page"`. Detail routes
inherit their parent destination:

- `/daily/<date>` → Daily recap
- `/weekly/<week>` → Weekly recap
- `/storyline/<slug>` → Storylines
- `/topic/<slug>` → Knowledge map
- `/story/<sid>` → Live feed
- `/playbook/<date>` → Playbook

The existing navigation update indicators remain supported inside Editor's Desk
for Daily recap, Weekly recap, Storylines, Playbook, and Knowledge map. The
Editor's Desk trigger rolls those visible `New` pills up into a compact count,
so mobile readers can tell there is something worth opening without inspecting
the drawer.

### Page actions

Page utilities must not compete with global navigation or contextual pickers.
They appear in the **Editor's Desk** disclosure unless the surface contract
below keeps one action visible.

Typical drawer actions:

- Share this page
- View as JSON

`Subscribe` is a persistent visible header action because email is the primary
retention channel. The theme toggle is also visible in the header as a compact
icon-only utility whose icon flips with the current theme; its `aria-label` and
hover title name the target theme. The link always goes to `/subscribe`; inline
forms and modal signup are intentionally out of scope for the chrome. Finish-line
subscription CTAs may appear after primary reading content on feed, recap, story,
and storyline pages.

Action labels describe the result. Examples:

- `View daily recap as JSON`
- `Switch to light theme`
- `Share this storyline`

An unexplained ellipsis is not sufficient as the accessible name.

### Context controls

Controls that change the current content context remain visible on the page;
they do not move into Editor's Desk.

- Daily: previous day, current day picker, next day
- Weekly: previous week, current week picker, next week
- Playbook: previous edition, current edition picker, next edition
- Live feed: existing lens and timeframe controls
- Weekly Detailed/Scan mode: existing content-view control

Unavailable previous/next directions are natively disabled or omitted. Context
changes preserve their existing URL and history behavior.

## Shared responsive structure

All pages use the same semantic hierarchy:

```html
<header class="site-chrome">
  <div class="site-bar">
    <a class="site-brand" href="/">LLM Digest</a>
    <div class="site-bar-actions">
      <!-- Optional surface-primary action, such as feed search -->
      <button type="button">Editor's Desk</button>
    </div>
  </div>

  <div class="page-heading">
    <h1>Page title</h1>
    <p>Page status or coverage</p>
  </div>

  <!-- Optional visible contextual picker -->
</header>
```

The exact generated markup may differ, but the semantic and visual hierarchy
must remain equivalent.

### Mobile presentation

At widths up to and including `640px`:

- The first row contains the compact brand/home link and no more than three
  actions.
- `Editor's Desk` is visibly labeled; it is not an icon-only hamburger.
- The page title and supporting status appear beneath the site bar.
- A contextual picker, when present, appears immediately after the page title
  and before page content.
- Global destinations are not rendered as a horizontal rail.
- Secondary actions are not rendered as a horizontal rail.
- No header label or control is clipped at `320px` CSS viewport width.

Reference structure:

```text
┌──────────────────────────────────┐
│ 📰 LLM Digest     Subscribe Desk │
├──────────────────────────────────┤
│ AI Daily Recap                   │
│ 15 articles · 5 categories      │
│                                  │
│ ‹   Sunday, June 22, 2026     ›  │
└──────────────────────────────────┘
```

### Desktop presentation

Above `640px`, the same information architecture remains authoritative.
Destinations may be displayed inline when space permits, but their order,
labels, current-page state, update indicators, and action hierarchy must match
the mobile system. Desktop must not retain a conflicting destination order.

### Floating bar after scroll

Once the reader scrolls past the header, the bar engages as a fixed,
blurred-background compact bar (`site-bar-fixed`, applied by
`web/site-chrome.js` via an IntersectionObserver sentinel with spacer padding
so content does not jump). Navigation - including the Editor's Desk dialog
that holds every destination - stays reachable from any scroll depth.
On small widths the floating bar collapses to its single-row form (the brand
may truncate); it respects the safe-area inset. Disengaging restores the
in-flow bar exactly.

## Editor's Desk behavior

On mobile, Editor's Desk opens an accessible modal navigation surface. Its visual
treatment may be a bottom sheet at ordinary text sizes, but it must be able to
expand or scroll like a full-height dialog when content, viewport height, or
text zoom requires it.

Required behavior:

- Use a native `<dialog>` when practical, with a robust fallback.
- Provide a visible `Editor's Desk` heading and visible `Close` button.
- Move focus into the dialog when it opens.
- Keep focus within the dialog while open.
- Close on Escape, Close, or backdrop interaction.
- Restore focus to the Editor's Desk button after closing.
- Prevent background interaction and background scrolling without losing the
  reader's previous scroll position.
- Make the dialog content independently scrollable.
- Respect `env(safe-area-inset-bottom)`.
- Do not require drag or swipe gestures.
- Respect `prefers-reduced-motion`.
- Do not nest another disclosure inside Editor's Desk.

Editor's Desk contains ordinary navigation links, not ARIA tabs. Each full
destination row is tappable and includes a short purpose line. Settings/actions
such as theme, JSON, and share sit below the destination groups.

## Context picker behavior

Daily, Weekly, and Playbook use one consistent picker shape:

```text
[Previous]  [Current date/week/edition ▾]  [Next]
```

Requirements:

- The current value is fully visible without horizontal scrolling.
- The center control retains the complete archive list.
- Previous and next controls identify their destination in their accessible
  names, for example `Previous day, June 21`.
- Dates use `<time datetime="YYYY-MM-DD">` where a static date is rendered.
- Full-page archive navigation preserves canonical paths.
- Dynamic latest shells preserve their existing query/API behavior.
- Picker changes update the URL so refresh, history, copying, and sharing remain
  correct.
- The picker uses a minimum 44px touch target.

The live-feed timeframe selector remains part of the feed's content controls;
it must not be duplicated in the site bar.

## Surface contract

| Surface | Source of truth | Visible primary action | Visible context | Editor's Desk actions |
|---|---|---|---|---|
| Live feed `/` | `web/index.html` | Search, Subscribe, Theme icon | Lens + timeframe controls | None |
| Daily `/daily` | `web/daily.html` | Subscribe, Theme icon | Day picker | Share when available, JSON |
| Daily archive `/daily/<date>` | `pipeline/render_static_pages.py` | Subscribe, Theme icon | Day picker | Share, JSON |
| Weekly `/weekly` | `web/weekly.html` | Subscribe, Theme icon | Week picker; Detailed/Scan remains with content | Share when available, JSON |
| Weekly archive `/weekly/<week>` | `pipeline/render_static_pages.py` | Subscribe, Theme icon | Week picker; Detailed/Scan remains with content | Share, JSON |
| Storylines `/storylines` | `web/storyline.html` | Subscribe, Theme icon | Existing All/Following filters remain with content | Share when available, JSON |
| Storyline detail `/storyline/<slug>` | `pipeline/render_static_pages.py` | Subscribe, Theme icon; Follow may remain in content | None | Share, JSON |
| Playbook `/playbook[/<date>]` | `web/playbook.html` | Subscribe, Theme icon | Edition picker | JSON |
| Knowledge map `/map` | `pipeline/render_static_pages.py` | Subscribe, Theme icon | Existing area navigation remains with content | Share, JSON |
| Topic `/topic/<slug>` | `pipeline/render_static_pages.py` | Subscribe, Theme icon | Existing graph links remain with content | Share |
| Voices `/voices` | `web/voices.html` | Subscribe, Theme icon | Existing page filters, if any, remain with content | None |
| Story permalink `/story/<sid>` | `pipeline/render_static_pages.py` | Subscribe, Theme icon; original source remains in content | None | Share |
| Subscribe `/subscribe` | `web/subscribe.html` | Subscribe, Theme icon | Subscription form remains in content | None |

Generated HTML under `web/daily/`, `web/weekly/`, `web/story/`,
`web/storyline/`, `web/topic/`, and `web/map.html` is never hand-edited.

## Non-JavaScript behavior

JavaScript enhances the presentation but does not own the only copy of the
navigation.

Before enhancement:

- A semantic global `<nav>` with every destination exists in the document.
- Its links wrap vertically or across lines; they never form a horizontal
  scroller.
- Page actions and archive controls remain reachable.

After enhancement:

- Shared JavaScript may place or clone destination links into Editor's Desk.
- The fallback navigation is hidden only after enhancement succeeds.
- A script error leaves usable navigation rather than an inert Editor's Desk button.

## Visual contract

- Use the existing page color tokens: `--bg`, `--fg`, `--muted`, `--border`,
  `--accent`, and surface-specific wash tokens.
- Continue the restrained instrument/ledger visual language: hairline borders,
  minimal fills, no large shadows, and no universal pill treatment.
- The brand is compact and does not compete with the page title.
- Icons and emoji are decorative aids; visible or accessible text carries the
  meaning.
- Every interactive target is at least `44 × 44px`.
- Unrelated controls have at least `8px` visual separation.
- Focus indicators remain visible in light and dark themes.

## Shared implementation contract

The implementation should introduce shared top-level assets:

- `web/site-chrome.css`
- `web/site-chrome.js`

Top-level placement lets `scripts/vercel_build.py` stage them at the public
root without adding another build-path exception.

`pipeline/render_static_pages.py` owns generated-page markup and must reference
the same shared assets as the hand-written shells. A shared renderer helper
should own generated header markup, Editor's Desk destinations, context controls, and
action placement.

Hand-written shells may contain minimal semantic fallback markup, but shared
CSS and JavaScript own presentation and interaction. Destination names and
order must be validated against the canonical information architecture above
to prevent drift.

The existing navigation-update script must recognize links inside Editor's
Desk, must preserve current read/freshness behavior, and the shared chrome may
count decorated links to badge the Editor's Desk trigger.

## Tech stack

- Static HTML and CSS for document structure and fallback navigation
- Vanilla browser JavaScript for Editor's Desk and focus management
- Python (`pipeline/render_static_pages.py`) for generated pages
- Python `unittest` surface-contract tests under `tests/`
- Vercel static build and rewrites through `scripts/vercel_build.py` and
  `vercel.json`

No UI framework, package dependency, server-side session, or new API is
required.

## Project structure

```text
web/site-chrome.css              Shared responsive presentation
web/site-chrome.js               Shared progressive enhancement
web/*.html                       Hand-written page shells and fallback markup
pipeline/render_static_pages.py  Generated-page chrome and archive controls
tests/test_site_chrome.py        Cross-surface structure and routing contract
docs/product-specs/              Product behavior contract
docs/design-docs/decision-log.md Architecture decision and rollback context
```

## Code style

Use semantic HTML and small progressive-enhancement functions. State belongs in
the URL or existing storage contracts; do not introduce a global client store.

```js
const deskButton = document.querySelector('[data-site-browse-open]');
const deskDialog = document.querySelector('[data-site-browse-dialog]');

if (deskButton && deskDialog instanceof HTMLDialogElement) {
  deskButton.addEventListener('click', () => deskDialog.showModal());
  deskDialog.addEventListener('close', () => deskButton.focus());
  document.documentElement.classList.add('site-chrome-enhanced');
}
```

The enhanced class is added only after required controls are found and wired,
so fallback navigation is never hidden behind a broken interaction.

## Commands

Run from the repository root:

```bash
python3 -m unittest tests.test_site_chrome
python3 pipeline/render_static_pages.py
python3 scripts/vercel_build.py
python3 -m http.server 8765
git diff --check
```

Use the local server to test hand-written and generated pages. The Vercel build
must complete because it is the production path that regenerates and stages
all static outputs.

## Testing strategy

### Automated checks

- Assert every in-scope source template references the shared chrome assets.
- Assert Editor's Desk contains every canonical destination in the required order.
- Assert parent-route current-state mapping covers detail routes.
- Assert no mobile rule applies `overflow-x:auto` to global header navigation
  or page-action navigation.
- Assert rendered static pages contain the shared app bar, Editor's Desk navigation,
  current destination, and expected context picker.
- Preserve navigation-update indicator tests and extend selectors to Editor's Desk.
- Run `python3 pipeline/render_static_pages.py` and
  `python3 scripts/vercel_build.py` without errors.

### Browser checks

Test representative pages from every source path:

- `/`
- `/daily` and one `/daily/<date>`
- `/weekly` and one `/weekly/<week>`
- `/storylines` and one `/storyline/<slug>`
- `/playbook`
- `/map` and one `/topic/<slug>`
- `/voices`
- one `/story/<sid>`
- `/subscribe`

Test each at:

- 320px mobile portrait
- 390px mobile portrait
- mobile landscape
- 768px tablet
- desktop
- light and dark themes
- 200% text size and 400% browser zoom
- keyboard-only navigation
- VoiceOver/Safari and TalkBack/Chrome where available
- reduced motion

### Cross-site acceptance gate

The release fails if any representative route:

- horizontally scrolls because of its header;
- clips a destination, action, or current picker value;
- lacks Editor's Desk or the fallback global navigation;
- uses a different destination order;
- loses its page-specific picker or primary action;
- has an inert disclosure when JavaScript fails;
- produces a keyboard-focus trap or fails to restore focus;
- loses a navigation update indicator;
- renders console errors.

## Analytics and success measures

No analytics dependency is required to ship the change. If existing PostHog
event infrastructure is extended, record:

- `site_editor_desk_opened`
- `site_editor_desk_destination_selected`
- `site_context_changed`

Useful post-release signals:

- destination selection no longer depends on horizontal-scroll interaction;
- increased mobile visits from secondary surfaces to Daily, Weekly,
  Storylines, Playbook, and Knowledge map;
- no increase in rapid back navigation from destination pages;
- no regression in subscription, share, or feed-search use.

## Boundaries

### Always

- Update every in-scope surface in the same release.
- Preserve existing routes, APIs, localStorage contracts, themes, update
  indicators, and content controls.
- Use semantic links and buttons.
- Keep generated-page changes in `pipeline/render_static_pages.py`.
- Validate the production Vercel build and real mobile browser behavior.
- Add an ADR-style decision-log entry and update this spec when behavior
  changes.

### Ask first

- Changing the canonical destination set or destination labels.
- Making a bottom navigation bar persistent.
- Removing any page action instead of relocating it.
- Adding a third-party UI or focus-management dependency.
- Changing archive URL behavior.
- Altering desktop content hierarchy beyond what shared chrome requires.

### Never

- Reintroduce horizontally scrolling global navigation.
- Hide day/week/edition selection behind Editor's Desk.
- Make JavaScript the only route to another site surface.
- Hand-edit generated HTML.
- Use icon or color alone to communicate destination or state.
- Ship only a subset of surfaces.

## Success criteria

The specification is satisfied when:

1. Every in-scope route uses the shared site bar, page-heading hierarchy,
   Editor's Desk model, and action hierarchy in one production release.
2. No mobile header requires horizontal scrolling at 320px.
3. Daily, Weekly, and Playbook context pickers are visible before content.
4. Editor's Desk exposes all canonical destinations in a stable order.
5. Detail pages mark the correct parent destination as current.
6. Search remains directly available on the Live feed.
7. JSON, Share, Theme, and Email actions remain reachable where applicable;
   Theme is a compact header icon rather than Editor's Desk content.
8. Navigation update indicators work inside Editor's Desk.
9. Core navigation remains usable without JavaScript.
10. Keyboard, screen-reader, text-zoom, reduced-motion, theme, and safe-area
    checks pass.
11. `python3 pipeline/render_static_pages.py` and
    `python3 scripts/vercel_build.py` complete successfully.
12. No public route mixes the old scrolling-rail model with the new chrome.

## Rollback

Revert the shared chrome commit and regenerate static pages. Because the change
ships atomically, rollback must also restore all hand-written shells and the
generated-page renderer together; a partial rollback is not allowed.

## Alternatives rejected

- **Improved horizontal rails:** preserves hidden destinations and the picker
  discovery failure.
- **Wrapped navigation grid:** consumes too much vertical space and assigns
  equal visual weight to every destination.
- **Persistent bottom navigation:** the site has more than five meaningful
  destinations, creates arbitrary winners, and adds permanent viewport and
  safe-area cost.
- **Section switcher as global navigation:** Daily/Weekly can behave as related
  contexts, but Feed, Storylines, Playbook, Knowledge map, and Voices are
  distinct reader jobs.

## Open questions

None block implementation. Whether Share remains directly visible on high-share
recap and storyline pages can be evaluated after the shared hierarchy ships;
the current contract places it in Editor's Desk.
