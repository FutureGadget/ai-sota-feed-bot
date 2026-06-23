# Implementation plan: shared mobile site chrome

**Date:** 2026-06-23
**Status:** Implementation complete — pending PR review and production merge
**Product contract:** `docs/product-specs/mobile-site-chrome.md`
**Decision record:** `docs/design-docs/decision-log.md`
**Release shape:** One PR, one production merge, all reader-facing surfaces

## Validation evidence

- 70 focused Python surface tests passed.
- 8 feed date/newness Node tests passed.
- `pipeline/render_static_pages.py` rendered all current page families.
- `scripts/vercel_build.py` staged the production output and root shared assets.
- Headless Chrome verified 13 representative routes at 390 × 844 in dark mode
  with reduced motion: zero console errors, zero document overflow, eight
  Browse destinations, one current destination, Browse/More focus restoration,
  and in-viewport site-bar/context controls.
- A separate 320px no-JavaScript run verified visible wrapping fallback
  navigation and no document overflow.
- A 320px run with 200% root text size verified no document overflow and a
  scrollable Browse dialog with a visible Close control.
- Visual screenshots were reviewed for Feed, Daily archive, Knowledge map,
  Subscribe, Browse, and More actions.

## Overview

Replace every horizontally scrolling or page-specific mobile header with one
shared responsive site chrome:

- compact LLM Digest brand/home link;
- visibly labeled Browse control;
- page title and status;
- visible day/week/edition controls where applicable;
- More actions for secondary utilities;
- semantic, wrapping navigation when JavaScript is unavailable.

Implementation is incremental inside a feature branch, but release is atomic.
No task below authorizes merging a partial surface set to `main`.

## Goals

1. Remove horizontal scrolling from global navigation and header actions.
2. Make Daily, Weekly, and Playbook archive selection immediately visible.
3. Use the same destination names, order, current state, and update indicators
   on all pages.
4. Preserve each surface's existing primary controls and content hierarchy.
5. Preserve navigation and actions when JavaScript fails.
6. Apply the system to hand-written shells and all generated pages in one
   production release.

## Non-goals

- Changing routes, APIs, ranking, recap schemas, or archive identifiers
- Redesigning page bodies or page-specific signature elements
- Adding persistent bottom navigation
- Adding a frontend framework or UI dependency
- Replacing the existing theme storage contract
- Changing the current viewport policy
- Adding new destinations
- Hand-editing generated HTML

## Architecture decisions

### Progressive enhancement

Every source page renders a semantic fallback navigation and fallback action
list. Shared JavaScript enables Browse and More actions only after required
elements are found and initialized. The enhanced class hides fallback controls
only after initialization succeeds.

```text
Semantic fallback markup
          │
          ├── JavaScript unavailable/fails ──→ wrapped links remain visible
          │
          └── JavaScript initializes
                    │
                    ├── Browse dialog receives destination links
                    ├── More actions receives page utilities
                    └── fallback rows become visually hidden
```

### Shared assets

- `web/site-chrome.css` owns shared layout, responsive presentation, dialogs,
  action disclosures, focus treatment, safe areas, and no-JavaScript fallback.
- `web/site-chrome.js` owns progressive enhancement, current-route mapping,
  dialog lifecycle, theme actions, update indicators, and optional analytics.
- Existing inline head scripts may continue applying the stored theme before
  paint to avoid a flash.
- `scripts/vercel_build.py` already copies top-level non-HTML assets from
  `web/` to the public root, so no build-script change should be needed.

### Generated pages

`pipeline/render_static_pages.py` owns all generated chrome. Add a shared
renderer helper rather than editing:

- `web/daily/*.html`
- `web/weekly/*.html`
- `web/story/*.html`
- `web/storyline/*.html`
- `web/topic/*.html`
- `web/map.html`

### Destination registry

The canonical order is:

1. Live feed
2. Daily recap
3. Weekly recap
4. Storylines
5. Playbook
6. Knowledge map
7. Voices
8. Email digest

Tests must verify this order in every hand-written source and generated output.
Detail routes map to their parent destination as specified in the product
contract.

### Atomic production release

Work may land as multiple commits on one feature branch. Do not merge the PR
until the final cross-site gate passes. A Vercel preview may expose intermediate
branch commits, but production must receive the complete surface set in one
merge.

## Dependency graph

```text
Task 1: contract tests and inventory
        │
        v
Task 2: shared CSS
        │
        v
Task 3: shared JavaScript
        │
        ├───────────────┬────────────────┐
        v               v                v
Task 4: renderer     Task 5: feed     Task 6: recap shells
        │               │                │
        │               ├────────┐       v
        │               v        │   Task 7: playbook
        │           Task 8       │
        │     storyline + voices │
        │                        v
        │                    Task 9: subscribe
        └───────────────┬────────┘
                        v
             Task 10: cross-site integration
                        │
                        v
             Task 11: browser/accessibility QA
                        │
                        v
             Task 12: docs and release gate
```

Tasks 4–9 may be worked in parallel only after Tasks 1–3 freeze the shared
contract. They must use disjoint file ownership and must not independently edit
the shared assets.

## Task 1: Build the cross-site contract test

**Description:** Add one test module that inventories every in-scope source,
asserts the canonical destination registry and parent-route mapping, and
provides reusable checks for shared asset references, fallback navigation,
Browse/More triggers, picker placement, and forbidden header scrollers.

**Acceptance criteria:**

- [ ] `tests/test_site_chrome.py` enumerates all hand-written shells.
- [ ] Tests can validate HTML returned by the generated-page renderer.
- [ ] Destination order and detail-route parent mapping are represented once in
      the test contract.
- [ ] Header checks are scoped so legitimate content scrollers, such as feed
      lenses or weekly category navigation, are not falsely rejected.

**Verification:**

```bash
python3 -m unittest tests.test_site_chrome
```

During the red phase, failures must identify absent chrome behavior rather than
syntax or fixture errors. Do not commit a permanently failing test-only change;
complete Tasks 1–3 as one green foundation increment if necessary.

**Dependencies:** None
**Files likely touched:** `tests/test_site_chrome.py`
**Estimated scope:** Small

## Task 2: Add the shared presentation layer

**Description:** Create the shared CSS contract with safe default fallback
navigation, enhanced Browse/More surfaces, responsive page-heading structure,
visible contextual controls, focus states, reduced-motion behavior, and mobile
safe-area handling.

**Acceptance criteria:**

- [ ] Fallback destinations and actions wrap without horizontal scrolling.
- [ ] Browse and More triggers are hidden until enhancement succeeds.
- [ ] Enhanced navigation works at 320px without clipped text.
- [ ] Dialog content can become full-height and independently scroll at large
      text sizes.
- [ ] Existing design tokens are consumed rather than replaced.
- [ ] No generic card, heavy shadow, or universal pill treatment is introduced.

**Verification:**

```bash
python3 -m unittest tests.test_site_chrome
git diff --check
```

**Dependencies:** Task 1
**Files likely touched:**

- `web/site-chrome.css`
- `tests/test_site_chrome.py`

**Estimated scope:** Medium

## Task 3: Add shared Browse and More-actions behavior

**Description:** Implement progressive enhancement in vanilla JavaScript.
Initialize only when the required DOM is present; clone or move fallback links
into accessible dialog surfaces; manage focus, Escape, backdrop, focus return,
scroll locking, route current state, theme actions, and update indicators.

**Acceptance criteria:**

- [ ] A failed or unsupported enhancement leaves fallback navigation visible.
- [ ] Browse and More actions open, close, and restore focus correctly.
- [ ] Current-route mapping covers every detail route.
- [ ] Daily, Weekly, Storylines, and Knowledge map update indicators decorate
      Browse links without changing freshness/read semantics.
- [ ] Theme actions preserve the existing `theme` localStorage contract.
- [ ] Optional PostHog calls are defensive and never required for interaction.
- [ ] No third-party dependency is added.

**Verification:**

```bash
node --check web/site-chrome.js
python3 -m unittest tests.test_site_chrome
git diff --check
```

**Dependencies:** Tasks 1–2
**Files likely touched:**

- `web/site-chrome.js`
- `tests/test_site_chrome.py`

**Estimated scope:** Medium

## Checkpoint A: shared contract frozen

- [ ] `web/site-chrome.css` and `web/site-chrome.js` parse successfully.
- [ ] Fallback and enhanced DOM contracts are documented in the test fixture.
- [ ] Destination order, action hooks, picker hooks, and current-route mapping
      are frozen before page integrations begin.
- [ ] No page has been redesigned beyond the shared header contract.

Do not start parallel surface work before this checkpoint.

## Task 4: Integrate all generated pages through the renderer

**Description:** Add renderer helpers for the site bar, fallback navigation,
Browse dialog hook, More actions, page heading, and optional archive picker.
Replace generated `<menu>` navigation in the shared page template. Apply the
same contract to Daily, Weekly, Story, Storyline, Topic, and Map output.

**Acceptance criteria:**

- [ ] `render_page()` references both shared assets.
- [ ] One helper owns generated destination order and current-state metadata.
- [ ] `render_archive_select()` participates in a visible Previous/Current/Next
      context row for Daily and Weekly archives.
- [ ] Generated Story, Storyline, Topic, and Map pages expose correct parent
      destination state and applicable actions.
- [ ] Generated pages no longer use a horizontally scrolling header `<menu>`.
- [ ] Existing canonical, JSON-LD, sitemap, follow, share, and content markup
      remain unchanged outside the chrome boundary.

**Verification:**

```bash
python3 -m unittest \
  tests.test_site_chrome \
  tests.test_render_story_pages \
  tests.test_daily_recap_surface \
  tests.test_weekly_recap_surface \
  tests.test_wiki_surface
python3 pipeline/render_static_pages.py
git diff --check
```

Inspect generated diffs, but do not hand-edit output. Keep code/docs and runtime
artifact commits separate under the repository's git-hygiene rules.

**Dependencies:** Tasks 1–3
**Files likely touched:**

- `pipeline/render_static_pages.py`
- `tests/test_site_chrome.py`
- `tests/test_render_story_pages.py`
- `tests/test_wiki_surface.py`

**Estimated scope:** Medium

## Task 5: Integrate the Live feed shell

**Description:** Replace the feed's mobile `.quicknav` with shared chrome while
preserving the ranked-ledger hero, lens tabs, timeframe selector, search,
subscription state, Saved view, and all feed behaviors. Search remains the one
visible surface-primary action.

**Acceptance criteria:**

- [ ] The page brand is a home link and the finite-reading promise remains the
      page's semantic heading.
- [ ] Search stays directly visible and preserves `aria-expanded`.
- [ ] Lens and timeframe controls remain in the feed content-control area.
- [ ] The old mobile quicknav rail is removed.
- [ ] Subscription and theme actions remain reachable through the specified
      hierarchy.
- [ ] Existing onboarding, update indicators, and PostHog behavior do not
      regress.

**Verification:**

```bash
python3 -m unittest \
  tests.test_site_chrome \
  tests.test_live_feed_surface
node --test \
  tests/test_feed_date_ranges.mjs \
  tests/test_feed_new_since_visit.mjs
node --check web/site-chrome.js
git diff --check
```

**Dependencies:** Tasks 1–3
**Files likely touched:**

- `web/index.html`
- `tests/test_live_feed_surface.py`
- `tests/test_site_chrome.py`

**Estimated scope:** Medium

## Task 6: Integrate Daily and Weekly latest shells

**Description:** Replace each shell's horizontal `<menu>` with shared chrome.
Build visible Previous/Current/Next context rows from the existing archive
indices while preserving dynamic API loading, local preview fallbacks, sharing,
JSON links, and Weekly Detailed/Scan controls.

**Acceptance criteria:**

- [ ] Day and week pickers appear before recap content and never at the end of
      another navigation row.
- [ ] Previous/next controls use available archive order and correct accessible
      names.
- [ ] Selecting an archive retains existing URL behavior.
- [ ] Weekly Detailed/Scan and categorical focus behavior remain content-level
      controls.
- [ ] Existing recap rendering and Playbook overlays remain unchanged.

**Verification:**

```bash
python3 -m unittest \
  tests.test_site_chrome \
  tests.test_daily_recap_surface \
  tests.test_weekly_recap_surface
git diff --check
```

**Dependencies:** Tasks 1–3
**Files likely touched:**

- `web/daily.html`
- `web/weekly.html`
- `tests/test_daily_recap_surface.py`
- `tests/test_weekly_recap_surface.py`
- `tests/test_site_chrome.py`

**Estimated scope:** Medium

## Task 7: Integrate Playbook and its edition picker

**Description:** Apply shared chrome to Playbook and replace the existing
full-width but page-specific edition control with the shared
Previous/Current/Next context contract.

**Acceptance criteria:**

- [ ] Edition selection is visible before Playbook content.
- [ ] Dynamic route/query behavior and API loading remain unchanged.
- [ ] Existing problem → apply → result hierarchy and source links remain
      untouched.
- [ ] JSON, theme, and email actions remain reachable.

**Verification:**

```bash
python3 -m unittest \
  tests.test_site_chrome \
  tests.test_playbook_surface \
  tests.test_playbook_linking
git diff --check
```

**Dependencies:** Tasks 1–3
**Files likely touched:**

- `web/playbook.html`
- `tests/test_playbook_surface.py`
- `tests/test_site_chrome.py`

**Estimated scope:** Small

## Task 8: Integrate Storylines and Voices

**Description:** Apply shared chrome to the Storylines index and Voices shell.
Keep Storyline All/Following filters and Follow controls in content. Preserve
Voices as an annotated reading guide rather than treating its entries as global
navigation.

**Acceptance criteria:**

- [ ] Storylines marks Storylines current and keeps update indicators.
- [ ] Existing All/Following, lifecycle, Follow, and API behavior remain.
- [ ] Voices marks Voices current and preserves its curated links and tracking.
- [ ] Neither page retains a horizontal header menu.
- [ ] JSON/share/theme/email actions remain reachable where applicable.

**Verification:**

```bash
python3 -m unittest \
  tests.test_site_chrome \
  tests.test_storyline_index_surface \
  tests.test_voices_surface
git diff --check
```

**Dependencies:** Tasks 1–3
**Files likely touched:**

- `web/storyline.html`
- `web/voices.html`
- `tests/test_storyline_index_surface.py`
- `tests/test_voices_surface.py`
- `tests/test_site_chrome.py`

**Estimated scope:** Medium

## Task 9: Integrate the Subscribe utility

**Description:** Apply the same brand and Browse model to `/subscribe` while
keeping the signup form as the dominant page action. Do not add subscription to
its own More actions list.

**Acceptance criteria:**

- [ ] Subscribe marks Email digest current.
- [ ] The form, cadence preference, honeypot, validation, provider fallback,
      success/error states, and localStorage keys are unchanged.
- [ ] Theme remains reachable.
- [ ] Browse does not compete visually with the form submission action.

**Verification:**

```bash
python3 -m unittest \
  tests.test_site_chrome \
  tests.test_subscribe_surface \
  tests.test_subscription_surface
git diff --check
```

**Dependencies:** Tasks 1–3
**Files likely touched:**

- `web/subscribe.html`
- `tests/test_subscribe_surface.py`
- `tests/test_site_chrome.py`

**Estimated scope:** Small

## Checkpoint B: every source path integrated

- [ ] All seven hand-written shells reference the shared assets.
- [ ] `pipeline/render_static_pages.py` emits shared chrome for every generated
      page family.
- [ ] No source-level header navigation uses the old `.quicknav` or scrolling
      `<menu>` model.
- [ ] Every page retains its specified primary and contextual controls.
- [ ] Focused tests for Tasks 4–9 pass.

This checkpoint still does not authorize production merge.

## Task 10: Run cross-site integration and production-build validation

**Description:** Exercise all source paths together, verify shared assets are
staged at root, detect duplicate IDs/listeners, ensure legacy inline navigation
scripts have been removed or made harmless, and verify generated pages produced
by the actual Vercel build.

**Acceptance criteria:**

- [ ] Shared assets exist at `public/site-chrome.css` and
      `public/site-chrome.js` after the Vercel build.
- [ ] No page initializes theme, update indicators, Browse, or More actions
      twice.
- [ ] No generated route references missing assets.
- [ ] No unexpected generated-file churn is staged with the code change.
- [ ] All focused surface tests pass together.

**Verification:**

```bash
python3 -m unittest \
  tests.test_site_chrome \
  tests.test_live_feed_surface \
  tests.test_daily_recap_surface \
  tests.test_weekly_recap_surface \
  tests.test_storyline_index_surface \
  tests.test_playbook_surface \
  tests.test_wiki_surface \
  tests.test_voices_surface \
  tests.test_subscribe_surface \
  tests.test_render_story_pages
node --test \
  tests/test_feed_date_ranges.mjs \
  tests/test_feed_new_since_visit.mjs
python3 scripts/vercel_build.py
test -f public/site-chrome.css
test -f public/site-chrome.js
git diff --check
```

**Dependencies:** Tasks 4–9
**Files likely touched:** No planned new files; fixes remain in the owning task's
files.
**Estimated scope:** Medium

## Task 11: Complete browser and accessibility QA

**Description:** Test representative dynamic and generated routes in a real
browser. Use the repository's browser-testing workflow. Test interaction,
layout bounds, focus, themes, content zoom/text scaling, safe areas, reduced
motion, no-JavaScript fallback, and console/network failures.

**Representative routes:**

- `/`
- `/daily` and one `/daily/<date>`
- `/weekly` and one `/weekly/<week>`
- `/storylines` and one `/storyline/<slug>`
- `/playbook`
- `/map` and one `/topic/<slug>`
- `/voices`
- one `/story/<sid>`
- `/subscribe`

**Viewport matrix:**

- 320 × 568
- 390 × 844
- mobile landscape
- 768px tablet
- desktop

**Acceptance criteria:**

- [ ] `document.documentElement.scrollWidth === clientWidth` on every mobile
      route.
- [ ] Every header control's bounding box remains within the viewport.
- [ ] Browse, More actions, Close, Escape, backdrop, and focus restoration work.
- [ ] Keyboard order follows brand → primary action → Browse → More → page
      context → content.
- [ ] Light/dark theme and stored theme initialization work without a flash
      regression.
- [ ] Reduced motion removes sheet transition without changing behavior.
- [ ] With JavaScript disabled, wrapped global navigation and actions remain
      usable.
- [ ] 200% text size and browser zoom do not clip controls or prevent dialog
      scrolling.
- [ ] No console errors or unexpected 4xx/5xx asset requests occur.
- [ ] Oat styles, weekly sticky controls, and Bubble Buddy do not overlap or
      override the shared chrome.

**Verification artifacts:**

- Mobile screenshots for every representative route
- At least one desktop screenshot per page family
- Console/network error summary
- Automated viewport-bounds result

**Dependencies:** Task 10
**Files likely touched:** No planned files; defects return to the owning task.
**Estimated scope:** Medium

## Task 12: Update documentation and pass the atomic release gate

**Description:** Reconcile documentation with the implemented behavior, record
final validation evidence, and prepare the complete change for one production
merge.

**Acceptance criteria:**

- [ ] Product spec status changes from Proposed to Implemented only after the
      complete acceptance gate passes.
- [ ] This plan records completion evidence and moves to
      `docs/exec-plans/completed/` after production verification.
- [ ] `AGENTS.md` documents `site-chrome.css`/`.js` and generated-page ownership.
- [ ] `docs/FRONTEND.md` documents the shared chrome hierarchy and extension
      rules.
- [ ] Decision-log impact reflects actual files and any deviations from plan.
- [ ] `docs/status/current-system-state.md` is updated if it describes current
      navigation behavior.
- [ ] Code/config/docs remain separate from generated runtime-data commits.

**Verification:**

```bash
git diff --check
git status --short
```

Review the final PR diff and Vercel preview before merging.

**Dependencies:** Tasks 10–11
**Files likely touched:**

- `AGENTS.md`
- `docs/FRONTEND.md`
- `docs/product-specs/mobile-site-chrome.md`
- `docs/design-docs/decision-log.md`
- `docs/status/current-system-state.md` when applicable

**Estimated scope:** Medium

## Final release gate

All boxes must pass before merge:

- [ ] Every in-scope hand-written and generated page uses the new chrome.
- [ ] No old horizontal header rail remains.
- [ ] All eight destinations appear in canonical order.
- [ ] Detail routes mark the correct parent destination.
- [ ] Daily, Weekly, and Playbook context controls remain visible.
- [ ] Feed Search remains visible.
- [ ] Existing update indicators, theme, share, JSON, email, and Follow behavior
      remain available where specified.
- [ ] No-JavaScript fallback works.
- [ ] Focus and dialog behavior pass keyboard testing.
- [ ] Mobile viewport bounds pass at 320px and 390px.
- [ ] Relevant Python and Node tests pass.
- [ ] `python3 scripts/vercel_build.py` passes.
- [ ] Vercel preview is visually approved.
- [ ] Rollback is one complete revert, not a page-level rollback.

## Parallelization plan

After Checkpoint A:

| Workstream | Ownership | May run in parallel with |
|---|---|---|
| Generated pages | `pipeline/render_static_pages.py`, renderer tests | All shell workstreams |
| Feed | `web/index.html`, feed surface test | Generated and other shells |
| Recaps | `web/daily.html`, `web/weekly.html`, recap tests | Generated and other shells |
| Playbook | `web/playbook.html`, Playbook surface test | Generated and other shells |
| Storylines/Voices | Their two shells and existing tests | Generated and other shells |
| Subscribe | `web/subscribe.html`, subscribe surface test | Generated and other shells |

Coordination rules:

- Only the foundation owner edits `web/site-chrome.css`,
  `web/site-chrome.js`, or the canonical destination contract.
- Surface workers update their existing focused tests; the integration owner
  owns final edits to `tests/test_site_chrome.py`.
- Workers must not regenerate or hand-edit shared generated HTML.
- Integration occurs only after all workstreams report focused tests passing.

## Commit strategy

Suggested branch commits:

1. `test: define shared site chrome contract`
2. `feat: add progressive site chrome assets`
3. `feat: render shared chrome on generated pages`
4. `feat: migrate live feed to shared chrome`
5. `feat: migrate recap and playbook shells`
6. `feat: migrate storyline voices and subscribe shells`
7. `test: verify site chrome across public surfaces`
8. `docs: record shared site chrome implementation`

Commits may be reorganized to keep each green and reviewable. Production
exposure occurs only when the complete PR merges.

## Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Browse JavaScript fails and hides navigation | High | Hide fallback only after successful initialization; test with JS disabled and forced script failure |
| Generated template change affects 1,000+ pages | High | Change renderer helper only; sample every generated family; rely on production build regeneration; inspect churn |
| Update indicators disappear after links move | High | Move selector support into shared JS before shell migration; preserve existing storage/freshness tests |
| Archive behavior diverges between latest shells and static archives | High | Keep URL behavior surface-specific behind one visual picker contract; test both route types |
| Focus trap or scroll lock breaks mobile Safari | High | Prefer native dialog, explicit Close/Escape/focus return, restore scroll position, test Safari/VoiceOver |
| Weekly sticky controls collide with site chrome | Medium | Keep site chrome non-sticky initially; test z-index and scroll behavior on Weekly |
| Existing Oat styles leak into dialog/details | Medium | Use scoped `.site-chrome-*` resets and real-browser inspection |
| Theme flashes or toggles twice | Medium | Retain pre-paint theme initialization; centralize only interaction; remove duplicate listeners per surface |
| Mascot overlaps Browse or More actions | Medium | Dialog/top-layer behavior and z-index test; suppress mascot interaction while modal is open if required |
| Root assets are not staged | Medium | Assert `public/site-chrome.{css,js}` after `scripts/vercel_build.py` |
| Partial merge creates mixed navigation | High | One feature branch, one PR, explicit final gate, no page-level production merge |
| Large generated diff mixes code and runtime data | Medium | Do not hand-edit outputs; review status after render; keep runtime artifacts in a separate commit if required |

## Rollback plan

1. Revert the complete implementation merge.
2. Run `python3 pipeline/render_static_pages.py`.
3. Run `python3 scripts/vercel_build.py`.
4. Verify old headers are restored consistently on representative routes.
5. Do not revert individual surface migrations while leaving shared assets or
   renderer changes active.

## Approval required

Owner approval of this plan authorizes implementation in a feature branch. It
does not authorize production merge until the final release gate passes.
