# Frontend redesign handoff — remaining surfaces

**Date:** 2026-06-21
**Branch:** `codex/validate-storyline-eval-results`
**Status:** Redesign complete (pending owner review). All remaining surfaces —
Playbook, Knowledge map, Topic, Voices, Subscribe — have been redesigned and
visually verified one by one, followed by a cross-surface consistency pass. The
worktree contains intentional, uncommitted redesign work.

> **Completion note (2026-06-21).** Sections 1–5 below are done:
> - **/playbook** — change records with a dominant `Apply` block; effort meter;
>   `tests/test_playbook_surface.py`; spec + SKILL editorial note.
> - **/map & /topic** — obstacle→solution adjacency map + problem-readout dossier
>   (renderer-only); `tests/test_wiki_surface.py`; spec updated.
> - **/voices** — annotated reading guide (why-forward, not ranked);
>   `tests/test_voices_surface.py`.
> - **/subscribe** — conversion utility with a focal signup panel + delivery spec;
>   all states verified via real code paths; `tests/test_subscribe_surface.py`.
> - **Consistency pass** — live-feed focus ring + dead-token-block cleanup; verified
>   tokens/type/focus/reduced-motion/themes/Oat collisions across surfaces. Relevant
>   suite 61 green, `git diff --check` clean, no accidental render churn (only the
>   known pre-existing `web/story/*` drift, restored). See the 2026-06-21 ADRs in
>   `docs/design-docs/decision-log.md`. One documented follow-up: accent focus ring
>   for the generated daily/weekly/story pages (needs a full re-render commit).

## Objective

Continue the page-by-page redesign of llm-digest.com without losing the visual
system, behavioral contracts, or lessons established during the Storyline work.

The product is for engineers who build and operate AI systems. Each page must
have one clear job and one page-specific structural device. The site should feel
related across surfaces without making every page a copy of the Storyline trace.

Work on one surface at a time, inspect it in the local browser, fix interaction
and responsive issues, add regression coverage, and only then move to the next.

## Read first

1. `AGENTS.md`
2. The frontend design brief supplied for this redesign:
   `/Users/danu/.codex/attachments/3f846b80-9d51-4723-9995-cb873f74254b/pasted-text.txt`
3. `docs/design-docs/decision-log.md`, especially the 2026-06-21 entries
4. Relevant product spec before changing a surface:
   - `docs/product-specs/playbook.md`
   - `docs/product-specs/agent-wiki.md`
   - `docs/product-specs/email-digest.md`
5. Relevant agent skill before changing agent-authored copy:
   - `.agents/skills/playbook/SKILL.md`
   - `.agents/skills/wiki-curator/SKILL.md`

The design brief requires a two-pass process: establish the page's subject,
audience, single job, compact tokens, layout, and one justified signature
element; critique whether it is generic; then build and visually critique it.

## Current visual direction

The shared system is an **AI operations instrument** rather than a generic card
dashboard:

- Cool instrument-paper background: light `#f5f7fa`; dark near `#11151c`.
- Strong blue accent around `#2457d6`, used selectively.
- Condensed/display typography for editorial titles.
- Monospace utility labels for provenance, state, dates, and measurements.
- Hairline rules, square or lightly rounded structural elements, and restrained
  fills.
- Large rounded cards and pill-heavy navigation are intentionally being removed.
- Hover states must not introduce Oat's default gray fills.
- Light and dark themes, visible keyboard focus, 44 px actions, mobile layout,
  and reduced motion are mandatory.

This is a family resemblance, not a single template. Spend the expressive idea
once per page:

| Surface | Reader job | Signature already established |
|---|---|---|
| Storyline detail | Understand how a story changed | Evidence trace |
| Storyline index | Choose which evolving story to inspect | Lifecycle ledger |
| Daily recap | Finish today's catch-up | Reading route + finish line |
| Weekly recap | Understand the week's accumulated shifts | Pattern report |
| Story permalink | Decide whether to open the source and where it fits | Source dossier |
| Live feed | Read the shared ranking and stop | Numbered ranking ledger |

Do not reuse the evidence trace, finish line, or numbered ranking where the
content is not actually chronological, finite, or ranked.

## Completed in this worktree

### Storylines

- Redesigned `/storylines` and `/storyline/<slug>`.
- Reordered detail UX around current state → latest change → builder action →
  earlier context → evidence.
- Fixed Oat tab/disclosure CSS collisions and gray hover states.
- Changed uncovered beat fallback from trailing “More in this thread” to
  chronological context.
- Tightened `storyline-editor` copy and validation, including exact beat
  coverage.
- Updated Storyline product spec and decision log.

Primary files:

- `web/storyline.html`
- `pipeline/render_static_pages.py`
- `.agents/skills/storyline-editor/`
- `docs/product-specs/storylines.md`
- `tests/test_storyline_index_surface.py`
- `tests/test_storyline_narrative_validation.py`
- `tests/test_render_story_pages.py`

### Daily and weekly recaps

- Redesigned both client shells and generated archive pages.
- Added localhost JSON fallbacks.
- Tightened recap agent guidance and current sample copy.

Primary files:

- `web/daily.html`
- `web/weekly.html`
- `pipeline/render_static_pages.py`
- `.agents/skills/daily-summary/SKILL.md`
- `.agents/skills/weekly-summary/SKILL.md`
- `tests/test_daily_recap_surface.py`
- `tests/test_weekly_recap_surface.py`

### Story permalinks

- Redesigned generated `/story/<sid>` pages as source dossiers.
- Added `docs/product-specs/story-permalinks.md`.

Primary renderer areas:

- `render_story_body`
- `STORY_PAGE_CSS`
- `story_hero`
- `render_story_pages`

### Live feed

- Redesigned `/` as “The AI brief that ends.”
- Added explicit ranked ledger rows and restrained utility metadata.
- Suppressed mechanical `Matches feed focus:` text from editorial context.
- Fixed a hidden reader-tuning banner that still occupied space.
- Added localhost fallback to `data/processed/latest.json`.
- Disabled the decorative WebGL mascot only in local preview for deterministic
  QA; production behavior is unchanged.
- Added `docs/product-specs/live-feed.md`.

Primary files:

- `web/index.html`
- `tests/test_live_feed_surface.py`

### Current validation state

The following passed at handoff:

```bash
node -e 'const fs=require("fs"); const h=fs.readFileSync("web/index.html","utf8"); for (const m of h.matchAll(/<script>([\s\S]*?)<\/script>/g)) new Function(m[1]);'

python -m unittest \
  tests.test_live_feed_surface \
  tests.test_render_story_pages \
  tests.test_weekly_recap_surface \
  tests.test_daily_recap_surface \
  tests.test_storyline_index_surface \
  tests.test_storyline_narrative_validation

git diff --check
```

Result: **27 tests passed**.

## Remaining work, in recommended order

### 1. Agent Builder's Playbook

**URL:** `/playbook`
**Source:** `web/playbook.html`
**Contract:** `docs/product-specs/playbook.md`
**Editorial skill:** `.agents/skills/playbook/SKILL.md`

Single job: answer **“What should I change in my agent because of this?”**

Recommended design hypothesis:

- Make `Apply` the dominant instruction, not an equal third inside a generic
  three-card layout.
- Treat each entry as an engineering change sheet:
  problem signal → concrete intervention → expected result.
- Use effort and area as quiet utility data.
- A plausible page-specific signature is a compact
  **before → intervention → expected state** change path, but only if it improves
  scanning and does not become a decorative process diagram.
- Preserve archive selection, API behavior, update indicators, source links,
  dark mode, and empty/error states.

Potential skill update:

- Only change `.agents/skills/playbook/SKILL.md` if the new visual hierarchy
  exposes recurring copy problems.
- Keep `apply` concrete and dominant; keep `problem` and `result` compact.
- Do not change the JSON schema merely to support styling.

Add a focused surface test such as `tests/test_playbook_surface.py`.

### 2. Knowledge map and topic pages

**URLs:** `/map`, `/topic/<slug>`
**Source of truth:** `pipeline/render_static_pages.py`
**Generated outputs:** `web/map.html`, `web/topic/*.html`
**Contract:** `docs/product-specs/agent-wiki.md` and `config/wiki_schema.md`
**Editorial skill:** `.agents/skills/wiki-curator/SKILL.md`

Important: **do not hand-edit `web/map.html` or `web/topic/*.html`.** Change the
renderer and regenerate.

Reader jobs:

- `/map`: choose an obstacle and understand the obstacle→solution structure.
- `/topic/<slug>`: understand the current state of one engineering problem in
  about 60 seconds and trust the evidence.

Recommended design hypothesis:

- `/map` should feel like a navigable systems map, not a grid of topic cards.
- Encode the real obstacle→solution relationship structurally.
- Keep the graph understandable on mobile; do not build a canvas visualization
  that becomes inaccessible or impossible to scan.
- `/topic` should foreground the current state, what changed, practical
  implications, linked solutions/obstacles, and evidence.
- A topic page is semantic memory, not another Storyline. Avoid chronology as
  the dominant device.
- Preserve all cross-links, evidence sids, related storylines, canonical URLs,
  sitemap behavior, and deterministic rendering.

Renderer entry points:

- `render_topic_body`
- `render_topic_pages`
- `render_map_page`
- The shared `PAGE_CSS` may need careful extension or page-specific CSS.

Potential skill update:

- Update `wiki-curator` only if visual QA shows that agent-authored sections are
  too long, duplicative, or structurally inconsistent.
- Keep `config/wiki_schema.md` authoritative.

Run:

```bash
python pipeline/build_wiki.py --check
python pipeline/render_static_pages.py
```

Add renderer tests for both the map and topic hierarchy.

### 3. AI Voices

**URL:** `/voices`
**Source:** `web/voices.html`

Single job: help a reader decide **who is worth following and why**.

Recommended design hypothesis:

- The current equal rounded-card list is generic.
- Treat the list as a curated reading index or annotated field guide.
- Make the editor's reason for inclusion more important than social-link chips.
- Preserve the hand-curated `PEOPLE` data and outbound links.
- Avoid ranking numbers unless the list is intentionally ranked—it currently is
  not.

Add a focused surface test. No agent skill currently owns this page.

### 4. Email subscription

**URL:** `/subscribe`
**Source:** `web/subscribe.html`
**Contract:** `docs/product-specs/email-digest.md`

Single job: explain the finite email product and successfully collect an email.

Recommended design hypothesis:

- This is a conversion utility, so clarity and trust outrank novelty.
- Connect the page visually to the daily brief and weekly pattern report without
  turning the three benefits into generic feature cards.
- Keep the email field and primary action unmistakable.
- Preserve the provider-config fallback, external signup option, honeypot,
  validation, status messages, local-storage keys, and privacy copy.
- Test configured, unavailable, submitting, success, validation-error, and API
  error states. Do not fake success in local preview.

Add a focused surface test. No editorial skill change should be required.

### 5. Final cross-surface consistency pass

After the four surfaces above:

- Compare header, quick navigation, theme control, content width, typography,
  focus states, and footer rhythm across all pages.
- Check that each page still has its own job and signature.
- Verify nav update dots and local-storage behavior remain intact.
- Check light/dark themes at desktop and mobile widths.
- Check keyboard operation and visible focus.
- Check `prefers-reduced-motion`.
- Check Oat CSS does not override component hover, disclosure, tab, or panel
  styles.
- Run the complete relevant test suite and `git diff --check`.
- Regenerate static pages once from the renderer and inspect the diff for
  accidental global churn.
- Update `docs/design-docs/decision-log.md` and add/update product specs for each
  meaningful page decision.

## Local visual QA workflow

The current local server is expected at:

```text
http://127.0.0.1:8765/web/
```

If it is not running:

```bash
python3 -m http.server 8765
```

Run that command from the repository root. Because the server exposes the repo
root, local URLs include `/web/`, while production URLs do not.

For each surface:

1. Open the page in the local browser.
2. Inspect the real rendered content, not only HTML/CSS.
3. Test one meaningful interaction.
4. Test both themes.
5. Test a narrow/mobile viewport.
6. Inspect hover/focus states, especially where Oat supplies defaults.
7. Fix the source file, refresh, and repeat.
8. Add a regression test for the structural decisions or bugs found.

Local API routes usually return 404 under `http.server`. Existing redesigned
client shells use localhost-only committed-data fallbacks where necessary.
Follow that pattern only for visual QA and leave production API behavior
unchanged.

## Generated-file and git cautions

- The worktree is intentionally dirty. Do not reset or restore existing changes.
- `web/daily/`, `web/weekly/`, `web/story/`, `web/storyline/`, `web/topic/`,
  `web/map.html`, and `web/sitemap.xml` are renderer outputs.
- Make durable generated-page changes in `pipeline/render_static_pages.py`.
- Existing generated daily, weekly, Storyline, and one Story preview file are
  changed because they were used for visual QA.
- Keep source/code/docs changes separate from runtime-data commits when
  committing.
- The current data changes are intentional examples and skill-aligned copy,
  not unrelated bot churn.
- Do not alter ranking, clustering, API schemas, or data schemas as part of this
  visual continuation unless a concrete UX defect requires it and the decision
  is documented.

## Completion criteria

The redesign continuation is complete when:

- Playbook, Knowledge map, Topic, Voices, and Subscribe have been redesigned and
  visually verified one by one.
- Each page has a clear reader job and a distinct structural signature.
- Existing interactions and data contracts still work.
- Agent skills are updated only where generated copy needs a durable constraint.
- Generated pages are changed through the renderer.
- Light/dark, mobile, keyboard focus, reduced motion, empty/error states, and
  Oat style collisions have been checked.
- Focused regression tests exist for each redesigned surface.
- Product specs and the decision log reflect meaningful decisions.
- The relevant test suite and `git diff --check` pass.

## Suggested Claude Code kickoff prompt

```text
Read AGENTS.md and
docs/exec-plans/active/2026-06-21-frontend-redesign-handoff.md completely.
Continue the frontend redesign from the current dirty worktree without
reverting existing changes. Start with /playbook only. Follow the two-pass
design process in the attached frontend brief, inspect the page in the local
browser at http://127.0.0.1:8765/web/playbook.html, preserve behavior and data
contracts, update the playbook skill only if the visual hierarchy requires a
durable editorial rule, add focused tests and documentation, and stop after
Playbook is visually verified so I can review it before proceeding to /map.
```
