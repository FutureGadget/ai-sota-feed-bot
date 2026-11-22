# Implementation Plan: Korean localized live feed

**Date:** 2026-07-05
**Status:** In progress — Tasks 1-6 implemented; Tasks 7-9 partially pending
**Product contract:** `docs/product-specs/localized-live-feed.md`
**Decision record:** `docs/design-docs/decision-log.md`
**Release shape:** One feature branch; ship reader-first `/ko/` before sitemap
exposure unless the static seed lands in the same pass.

## Overview

Add a Korean `/ko/` feed that serves the latest complete Korean snapshot of the
default Brief feed, up to 20 cards. The work is split so the data contract and
API can be proven before the localized shell, route, and SEO behavior depend on
it. English `/` and `/api/feed` remain unchanged when no locale is requested.

## Architecture Decisions

- **Canonical source is `/api/feed`, not `data/processed/latest.json`.** The
  snapshot builder must select from the same Brief semantics readers see:
  `label=brief`, `limit=20`, KST 7-day `from`/`to`, and Tier-1 blending enabled.
- **Snapshot completeness beats live freshness.** `/ko/` reads the latest
  complete Korean snapshot until its `source_run_at` is older than 24 hours.
  Missing or incomplete new translations keep the prior complete snapshot.
- **Locale data is overlay data.** Korean artifacts translate only display text
  and preserve IDs, URLs, ranks, labels, dates, scores, and story metadata.
- **Request-time data stays narrow.** `api/feed.js` may read
  `data/i18n/ko/feed/{latest,status}.json`; it must not bundle `feed/runs/**`.
- **SEO is gated.** `/ko/` can exist for readers before sitemap exposure. It is
  indexable only when a current complete static Korean seed exists.

## Dependency Graph

```text
Task 1: localized feed selection/hash/status helpers
        │
        v
Task 2: snapshot builder + no-op/failure behavior
        │
        ├───────────────┐
        v               v
Task 3: API overlay   Task 4: renderer ignores feed i18n artifacts
        │               │
        └───────┬───────┘
                v
Task 5: localized /ko shell + route
        │
        v
Task 6: frontend localized feed behavior
        │
        v
Task 7: static seed, sitemap/noindex, language discovery
        │
        v
Task 8: hourly integration, retention, ops signals
        │
        v
Task 9: browser QA and docs finalization
```

Tasks 3 and 4 can proceed in parallel after Task 2. Tasks 5-7 are sequential
because route behavior, shell markup, and SEO gates share the same rendered
output.

## Task 1: Define localized feed helper contract

**Description:** Add pure helper logic for normalized translation keys,
reader-facing source hashes, KST 7-day selector params, completeness/currentness
checks, and status payloads. This creates a testable foundation before any
translation or route behavior exists.

**Acceptance criteria:**

- [x] Normalized URL keys are stable when titles change.
- [x] `source_hash` changes for title/summary/why/related-title changes, but
      not for rank, score, run timestamp, or reader-adjustment changes.
- [x] KST 7-day selector emits timezone-aware `from`/`to` values.
- [x] Currentness expires strictly 24 hours after `source_run_at`.

**Verification:**

```bash
python3 -m unittest tests.test_localized_feed
git diff --check
```

**Dependencies:** None

**Files likely touched:**

- `pipeline/build_localized_feed.py`
- `tests/test_localized_feed.py`

**Estimated scope:** Medium

## Task 2: Build complete Korean snapshot writer

**Description:** Implement the localized feed builder in deterministic mode. It
selects the Brief top set, reuses existing matching translations, accepts a
provider/output injection point for new translations, writes `latest.json` only
when complete, and always writes `status.json`. The first implementation may use
a stub/no-op translator path so missing credentials leave status explicit.

**Acceptance criteria:**

- [x] Builder selects at most 20 eligible Brief cards from the canonical
      `/api/feed` semantics.
- [x] If fewer than 20 cards are eligible, translating all eligible cards is
      marked complete.
- [x] Incomplete current translation leaves the previous complete `latest.json`
      untouched.
- [x] Missing credentials emit `localized_feed_missing_credentials` and a
      durable status JSON instead of failing the hourly feed.

**Verification:**

```bash
python3 -m unittest tests.test_localized_feed
python3 pipeline/build_localized_feed.py --locale ko --label brief --limit 20 --dry-run
```

**Dependencies:** Task 1

**Files likely touched:**

- `pipeline/build_localized_feed.py`
- `tests/test_localized_feed.py`
- `data/i18n/ko/feed/.gitkeep` or fixture-only test data

**Estimated scope:** Medium

## Checkpoint: Data Foundation

- [x] Localized snapshot/status tests pass.
- [x] Builder no-ops cleanly without translation credentials.
- [x] No generated runtime artifacts are accidentally required for tests.
- [x] Human review before wiring API or routes.

## Task 3: Add locale-aware feed API overlay

**Description:** Extend `api/feed.js` so English behavior is unchanged, while
`locale=ko&localized_snapshot=latest` overlays a current complete Korean
snapshot and returns explicit localized status. The API must preserve item IDs
and operational metadata.

**Acceptance criteria:**

- [x] Plain `/api/feed` responses are byte-shape compatible with current tests.
- [x] Localized responses include `locale`, `status`, `is_current`,
      `is_complete`, `source_run_at`, `translated_at`, and `expires_at`.
- [x] Localized overlay preserves `id`, `url`, `source`, dates, labels, scores,
      `first_seen`, `last_seen`, and run identifiers.
- [x] Localized responses cannot be cached as current past `expires_at`.

**Verification:**

```bash
node --test tests/test_feed_api.mjs
git diff --check
```

**Dependencies:** Task 2

**Files likely touched:**

- `api/feed.js`
- `tests/test_feed_api.mjs`
- `vercel.json`

**Estimated scope:** Medium

## Task 4: Exclude feed artifacts from static-page i18n collection

**Description:** Update static i18n collection so `data/i18n/<locale>/feed/**`
does not get treated as a static page artifact. This prevents render warnings
and keeps feed snapshots owned by the localized feed path.

**Acceptance criteria:**

- [x] `collect_i18n_pages()` ignores feed artifacts.
- [ ] Existing Korean static pages still collect and render.
- [x] A feed artifact fixture does not produce stale/missing source warnings.

**Verification:**

```bash
python3 -m unittest tests.test_i18n_static_pages
python3 pipeline/render_static_pages.py --base-url https://www.llm-digest.com
```

**Dependencies:** Task 2

**Files likely touched:**

- `pipeline/render_static_pages.py`
- `tests/test_i18n_static_pages.py`

**Estimated scope:** Small

## Checkpoint: API And Renderer Safety

- [x] `node --test tests/test_feed_api.mjs` passes.
- [ ] `python3 -m unittest tests.test_i18n_static_pages` passes.
- [x] `api/feed.js` `includeFiles` are narrow and do not include `feed/runs/**`.
- [x] English feed behavior remains unchanged.

## Task 5: Add `/ko` shell routing

**Description:** Generate or author the localized feed shell and add Vercel
rewrites for `/ko` and `/ko/`. The shell can initially render Korean metadata
and a stale/missing fallback while the client/API integration is completed.

**Acceptance criteria:**

- [x] `web/ko/index.html` or equivalent generated shell exists.
- [x] Shell includes `html lang="ko"`, canonical `/ko/`, Korean title and
      description, and a link back to `/`.
- [x] `vercel.json` routes both `/ko` and `/ko/` to the shell.
- [x] Tests assert the route exists, matching the current static i18n rewrite
      style.

**Verification:**

```bash
python3 -m unittest tests.test_i18n_static_pages tests.test_live_feed_surface
python3 scripts/vercel_build.py
```

**Dependencies:** Tasks 3 and 4

**Files likely touched:**

- `pipeline/render_static_pages.py`
- `web/ko/index.html` if generated/committed
- `vercel.json`
- `tests/test_i18n_static_pages.py`
- `tests/test_live_feed_surface.py`

**Estimated scope:** Medium

## Task 6: Localize the reader-facing feed UI

**Description:** Make the `/ko/` shell/client render the localized snapshot with
Korean feed chrome. Hide or defer non-v1 controls: non-Brief tabs, Saved view,
search, pinned topics, onboarding, subscribe nudges, and Editor's Desk inserts.

**Acceptance criteria:**

- [x] `/ko/` fetches `/api/feed?locale=ko&localized_snapshot=latest`.
- [ ] Korean card text, freshness/meta line, primary badges, feedback labels,
      and stale/missing states render from localized copy.
- [x] English language action returns to `/`.
- [x] `/ko/` does not expose unsupported non-Brief controls in v1.
- [ ] Finish marker distinguishes translated top-20 cap from true completion.

**Verification:**

```bash
python3 -m unittest tests.test_live_feed_surface
node --test tests/test_feed_api.mjs
```

Manual browser check at 390px and desktop:

- `/ko/` current snapshot
- `/ko/` stale/missing snapshot
- `/` Korean-browser language action when current snapshot exists

**Dependencies:** Task 5

**Files likely touched:**

- `web/index.html`
- `pipeline/render_static_pages.py`
- `tests/test_live_feed_surface.py`
- optional `web/site-chrome.js`

**Estimated scope:** Medium

## Task 7: Add static seed, noindex, and sitemap gates

**Description:** Reuse the localized snapshot to render crawler/no-JS-visible
Korean top cards when current. Keep `/ko/` out of `sitemap.xml` and render
`noindex` when the snapshot is missing, incomplete, disabled, or expired.

**Acceptance criteria:**

- [ ] Current complete snapshot renders static Korean seed cards.
- [ ] Expired, missing, incomplete, or disabled snapshot renders noindex.
- [ ] `/ko/` enters `sitemap.xml` only with a current complete static seed.
- [ ] Expiry removes `/ko/` from `sitemap.xml` on the next render.
- [ ] `hreflang` for `/ko/` appears only when current enough to be a useful
      alternate.

**Verification:**

```bash
python3 -m unittest tests.test_i18n_static_pages tests.test_live_feed_surface
python3 pipeline/render_static_pages.py --base-url https://www.llm-digest.com
```

**Dependencies:** Task 6

**Files likely touched:**

- `pipeline/render_static_pages.py`
- `web/sitemap.xml`
- `web/ko/index.html`
- `tests/test_i18n_static_pages.py`
- `tests/test_live_feed_surface.py`

**Estimated scope:** Medium

## Checkpoint: Reader And SEO Surface

- [ ] `/ko` and `/ko/` resolve in Vercel preview.
- [ ] Current `/ko/` has Korean card seed and localized interactive feed.
- [ ] Stale `/ko/` is noindexed and omitted from sitemap.
- [ ] Mobile and desktop smoke checks show no overflow or missing primary copy.

## Task 8: Wire hourly integration, retention, and kill switch

**Description:** Add the localized builder to the hourly feed path after the
English feed build, with a safe no-op when disabled or unconfigured. Add bounded
retention for optional feed i18n run snapshots and grep-friendly logs.

**Acceptance criteria:**

- [x] `run_full.sh` invokes the localized builder after English feed artifacts
      exist and before render/static publish steps that need `/ko/`.
- [x] Missing translation credentials does not fail the hourly run.
- [x] Logs include `localized_feed_ok`, `localized_feed_stale`,
      `localized_feed_incomplete`, `localized_feed_missing_credentials`, or
      `localized_feed_disabled`.
- [x] Optional `data/i18n/ko/feed/runs/**` retention is bounded.
- [ ] Kill switch disables language actions, API overlay, static seed, and
      sitemap inclusion.

**Verification:**

```bash
python3 pipeline/build_localized_feed.py --locale ko --label brief --limit 20 --dry-run
bash -n skills/ai-feed-digest-local/scripts/run_full.sh
python3 -m unittest tests.test_localized_feed tests.test_i18n_static_pages
```

**Dependencies:** Task 7

**Files likely touched:**

- `skills/ai-feed-digest-local/scripts/run_full.sh`
- `pipeline/build_localized_feed.py`
- `pipeline/prune_runtime_data.py` or localized-builder retention helper
- `tests/test_localized_feed.py`
- docs/status or ops docs if needed

**Estimated scope:** Medium

## Task 9: Final QA, docs, and release gate

**Description:** Run the full relevant validation set, update operator docs,
and record any implementation decisions discovered during build. This task is
also where generated files are reviewed so code/config/docs and runtime data
can be committed separately.

**Acceptance criteria:**

- [ ] Product spec still matches implementation.
- [ ] Decision log has any implementation-time ADR updates.
- [ ] `AGENTS.md` and generated schema docs are updated if new durable data
      artifacts or automation behavior changed.
- [ ] Generated runtime artifacts are separated from code/config/docs in git.
- [ ] Browser QA covers current, stale, disabled, and missing-credentials states.

**Verification:**

```bash
python3 -m unittest tests.test_localized_feed tests.test_i18n_static_pages tests.test_live_feed_surface
node --test tests/test_feed_api.mjs
python3 pipeline/render_static_pages.py --base-url https://www.llm-digest.com
python3 scripts/vercel_build.py
git diff --check
```

**Dependencies:** Task 8

**Files likely touched:**

- `docs/product-specs/localized-live-feed.md`
- `docs/design-docs/decision-log.md`
- `AGENTS.md` if data/automation contracts change
- `docs/generated/db-schema.md` if feed i18n artifacts become durable committed
  data

**Estimated scope:** Small

## Risks And Mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Korean snapshot differs from English default feed | High | Use one selector based on `/api/feed` params; test selector output and record params in artifact. |
| Translation changes item identity | High | Preserve English `id`; use normalized URL `translation_key`; add tests around title changes. |
| Vercel bundle grows from feed history | Medium | Include only `latest/status`; bound or omit `runs/**` from request-time bundles. |
| `/ko/` appears current after expiry because of cache | Medium | Override localized `Cache-Control` or conservatively mark near-expiry responses stale. |
| Static i18n collector treats feed snapshots as pages | Medium | Explicitly ignore `feed/**`; regression fixture. |
| SEO indexes stale fallback page | Medium | Noindex stale/missing/disabled `/ko/`; sitemap add/remove tests. |
| Missing translation provider breaks hourly publish | High | Builder is secrets-gated and non-fatal; status artifact and grep-friendly logs. |
| Scope creep into full localized app | Medium | Hide non-Brief controls in v1; ask before adding lenses, saved view, search, RSS, or mixed fallback. |

## Parallelization Opportunities

Safe after Task 2:

- Task 3 API overlay and Task 4 static i18n collector exclusion can run in
  parallel with disjoint ownership.

Safe after Task 5:

- Browser-copy polish for `/ko/` UI strings and API stale-state tests can run in
  parallel if one owner touches `web/index.html`/renderer and the other touches
  `api/feed.js`/tests.

Must be sequential:

- Snapshot helper contract before builder.
- Builder before API overlay.
- Shell/route before frontend behavior.
- Frontend behavior before SEO sitemap exposure.
- Hourly integration after the reader and SEO surfaces are proven.

## Open Questions

- Which translation system should own production `data/i18n/ko/feed/*`
  generation?
- Should Task 5 generate `web/ko/index.html` immediately, or reuse
  `web/index.html` with locale-aware bootstrapping?
- Should `/ko/` get RSS/JSON later, or stay page-only until reader usage proves
  demand?
