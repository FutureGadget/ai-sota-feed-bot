# Spec: Localized Live Feed

## Objective

Build a Korean live-feed surface at `/ko/` that feels complete in Korean while
preserving the product's finishable-feed promise. The surface is for Korean
readers who want the default LLM Digest Brief experience without relying on
browser translation.

Success means a Korean reader can open `/ko/`, read the default Brief feed in
Korean, understand whether the snapshot is current, and switch back to the
English default Brief feed.

## Product Contract

The localized feed is snapshot-based, not item-by-item mixed live translation.

- Locale: Korean (`ko`) first.
- Route: `/ko/`.
- English route: `/`.
- Eligible set: the default Brief feed only.
- Snapshot size: up to 20 cards. If the current eligible Brief set has fewer
  than 20 cards, translating all eligible cards counts as complete.
- Completeness rule: `/ko/` serves the latest fully translated eligible
  snapshot. It does not normally mix Korean and English cards.
- Freshness rule: a translated snapshot is current for 24 hours from the source
  snapshot timestamp.
- Stale rule: if no complete Korean snapshot is available within 24 hours,
  `/ko/` must show a clear stale/fallback state and a path to the English feed.
- UI scope: localize card content and the main visible feed chrome.
- Source articles: remain linked to the original third-party URLs and are not
  translated.
- Kill switch: a config/env-controlled disable path must prevent `/ko/`
  language actions, localized API overlay, static seed, and sitemap inclusion
  without deleting committed translation artifacts.

The localized feed should reuse the same ranking order as the English Brief
feed snapshot it was translated from. Translation never re-ranks, drops, or
adds feed cards.

## Canonical Eligible Set

The localized snapshot must use one canonical selector so the Korean feed does
not drift from the English feed readers expect.

For v1, the eligible set is equivalent to this default homepage request:

```text
/api/feed?label=brief&limit=20&from=<kst-window-start>&to=<kst-window-end>
```

The window is the last 7 Korea Standard Time calendar days, converted to
explicit timezone-aware `from` and `to` bounds. This makes the translated
snapshot deterministic: it does not depend on each reader's browser timezone.
Tier-1 fresh blending stays enabled with the same defaults as `/api/feed`,
because those inserts are part of the reader-visible default feed.

Do not select from `data/processed/latest.json` sorted by score and do not use
the crawler feed-seed selector as the source of truth; those are static fallback
paths, not the live reader contract. The localized snapshot should record the
API-equivalent params used to produce it (`label`, `limit`, `from`, `to`,
`blend_tier1`, and any non-default Tier-1 config) plus the newest source run id
returned by the feed API.

The `/ko/` surface is a localized default Brief feed. It does not expose
non-Brief lenses, pinned-topic filters, custom date ranges, or search in v1. The
English language action returns to `/`, not to a reconstructed custom query.

## User Experience

When a current Korean snapshot exists:

- `/ko/` loads with Korean metadata and visible Korean feed chrome.
- The feed displays the translated snapshot cards in the same order as the
  source English Brief snapshot.
- Each card preserves source, date, URL, image, story link, and ranking
  metadata from the English source.
- The page shows a Korean freshness line such as "Updated 3 hours ago."
- A language action lets readers switch to the equivalent English feed.

When the Korean snapshot is stale or missing:

- Do not show a mostly English feed as though it is Korean.
- Show a Korean stale/fallback state with the latest known translated timestamp
  if available.
- Link to `/` for the current English live feed.
- Keep the page functional and honest; no silent failure.

The normal `/ko/` experience should not be mixed Korean/English cards. Mixed
fallback may be used only as an explicit fallback state if later approved.

Visible freshness copy must distinguish source freshness from translation
freshness:

- Primary freshness: age of `source_run_at`, because that is what tells readers
  how current the ranked feed snapshot is.
- Secondary detail: `translated_at`, shown in a lower-prominence label or
  tooltip when useful.
- Currentness: computed from `source_run_at`; a late translation of an old
  source snapshot does not reset the 24-hour clock.

The `/ko/` finish line must not claim the whole English Brief range is complete
when the Korean snapshot is capped at 20 and the source response had
`has_more: true`. In that case, show a localized capped-snapshot marker such as
"Showing the translated top 20" and link to the English feed for the current
full Brief view. Show the normal finish line only when the source response had
`has_more: false`.

Main visible feed chrome means:

- localized: page title/subtitle, feed hero copy, freshness/meta line, Brief
  label, top-20/caught-up marker, stale/missing states, language action labels,
  Save/Share/Hide accessible labels, feedback controls, and card badges such as
  Fresh, New, Developing, Climbing, and Reader-boosted.
- hidden or deferred in v1: non-Brief lens tabs, Saved view, search, pinned
  topics, onboarding prompts, subscribe nudges, and Editor's Desk inserts unless
  those flows receive locale-specific copy and data.

## Data Model

Add a feed-specific i18n artifact separate from the static-page artifacts:

```text
data/i18n/ko/feed/latest.json
data/i18n/ko/feed/status.json
data/i18n/ko/feed/runs/<snapshot-id>.json
```

Proposed `latest.json` shape:

```json
{
  "locale": "ko",
  "surface": "feed",
  "source_path": "/",
  "target_path": "/ko/",
  "snapshot_id": "20260705-060221-brief-top20",
  "source_run_at": "2026-07-05T06:02:21Z",
  "translated_at": "2026-07-05T06:12:00Z",
  "expires_at": "2026-07-06T06:02:21Z",
  "model": "translation-system-id",
  "review_status": "machine",
  "eligible_label": "brief",
  "selector": {
    "endpoint": "/api/feed",
    "label": "brief",
    "limit": 20,
    "days": 7,
    "blend_tier1": true
  },
  "max_items": 20,
  "source_item_count": 18,
  "translated_item_count": 18,
  "is_complete": true,
  "items": [
    {
      "translation_key": "https://example.com/story",
      "id": "existing-feed-item-id-if-present",
      "source_hash": "sha256-of-translated-source-fields",
      "title": "Translated title",
      "summary_1line": "Translated summary.",
      "why_it_matters": "Translated why, when present.",
      "also_covered": [
        { "url": "https://example.com/other", "title": "Translated related title" }
      ]
    }
  ],
  "ui": {
    "title": "Korean page title",
    "description": "Korean page description",
    "feed_title": "Korean feed heading"
  }
}
```

The stable translation key should be normalized-URL-first. The localized API
response must also preserve the English feed item's existing `id` when present.
This is required because the browser uses item identity for Saved, hidden,
feedback, sharing, and impression events; translating the title must never
change those keys. If a story sid is available, it may be stored as additional
metadata, but the translation overlay should not depend on rank.

`source_hash` must cover only reader-facing English fields that feed the
translated card:

- `title`
- `summary_1line`
- `why_it_matters`
- `also_covered[].title` for preserved `also_covered[].url`

It must not include ranking scores, run timestamps, reader-adjustment fields,
or other metadata that would make translations stale without changing the text
readers see.

Because `data/i18n/<locale>/` is also scanned by the static-page i18n renderer,
feed artifacts under `data/i18n/<locale>/feed/**` must be explicitly ignored by
the static-page translation collector. They are consumed only by the localized
feed builder/API/renderer.

Retention:

- `latest.json` and `status.json` are the only feed i18n artifacts required at
  request time.
- `runs/` history is optional audit data and must have a bounded retention
  policy before the hourly pipeline writes it repeatedly.
- Vercel function `includeFiles` must include only the request-time artifacts
  unless archive access is explicitly implemented.

## API Contract

`/api/feed` remains the source for English live feed behavior.

Canonical v1 read path:

```text
/api/feed?locale=ko&localized_snapshot=latest
```

The endpoint overlays the current complete Korean snapshot onto its source
English items and returns explicit localized status. Do not make `/ko/` fetch
`/data/i18n/ko/feed/latest.json` directly unless the Vercel build is changed to
publish that file under `web/` with an explicit route and cache contract.

The endpoint must return enough status for the page to render honestly:

```json
{
  "locale": "ko",
  "mode": "localized_snapshot",
  "source_run_at": "2026-07-05T06:02:21Z",
  "translated_at": "2026-07-05T06:12:00Z",
  "expires_at": "2026-07-06T06:02:21Z",
  "is_current": true,
  "is_complete": true,
  "status": "current",
  "items": []
}
```

The localized response must preserve operational fields from the source English
items: `id`, `url`, `source`, `published`, `type`, labels, scores, story links,
`also_covered.url`, `first_seen`, `last_seen`, and run identifiers. Only
reader-facing display text is overlaid.

If the snapshot is missing, stale, or incomplete, the response should make that
explicit rather than returning a silently mixed feed.

Localized API responses must not be cached beyond `expires_at`. If the endpoint
uses the shared `/api/*` cache headers, it must either override `Cache-Control`
for localized responses or conservatively return stale status near expiry so an
edge-cached `is_current: true` response cannot outlive the 24-hour window.

## Rendering And Routing

Vercel should route `/ko/` to a localized feed shell. Two implementation options
are acceptable:

1. Generate `web/ko/index.html` from `pipeline/render_static_pages.py`.
2. Reuse `web/index.html` with locale-aware bootstrapping, if it can still emit
   correct metadata and fallback content for `/ko/`.

The shell must include:

- `<html lang="ko">`
- canonical URL for `/ko/`
- `hreflang` alternates for `ko`, `en`, and `x-default`
- Korean title and description
- a localized no-JS or stale/fallback region
- a language action back to `/`

`vercel.json` must add rewrites for both `/ko` and `/ko/` to the localized feed
shell, for example `/web/ko/index.html`. Generating `web/ko/index.html` is not
enough; without the rewrite it is not reachable at the intended URL.

For SEO/crawler readiness, the translated snapshot should also be renderable as
static feed-seed markup in `web/ko/index.html`. SEO exposure is not the first
shipping priority, but the data model should avoid blocking it.

Do not add `/ko/` to `sitemap.xml` until the static/crawler-visible Korean seed
exists and a current complete snapshot is available.

SEO rules:

- Current complete snapshot with static Korean seed: `/ko/` may be indexable and
  included in `sitemap.xml`.
- Missing, incomplete, disabled, or expired snapshot: `/ko/` must be omitted
  from `sitemap.xml` and render `noindex` if served.
- Expiry must remove `/ko/` from the sitemap on the next render; sitemap logic
  must not only add the URL once.
- `hreflang` alternates should appear only when the localized feed is current
  enough to be a useful alternate. A stale fallback page should not advertise
  itself as the Korean equivalent of `/`.

## Translation Pipeline

The feed localization job runs after the English feed build has produced the
ranked feed snapshot.

Suggested flow:

1. Read the current English feed through the same Brief semantics the frontend
   uses.
2. Select up to 20 eligible Brief cards.
3. Compute per-card source hashes from reader-facing fields.
4. Reuse existing translations when hashes match.
5. Translate missing/stale cards.
6. Write a complete snapshot only when all selected cards have valid Korean
   translations.
7. Keep the previous complete snapshot when the current one is incomplete.
8. Mark the active Korean snapshot stale once it is older than 24 hours.

Translation failure must not block the English hourly feed publish. It should
leave the prior Korean snapshot in place and emit machine-readable status for
ops.

Required machine-readable status:

- Durable status file: `data/i18n/ko/feed/status.json`.
- Grep-friendly log keys: `localized_feed_ok`, `localized_feed_stale`,
  `localized_feed_incomplete`, `localized_feed_missing_credentials`, and
  `localized_feed_disabled`.
- Status fields: `locale`, `status`, `source_run_at`, `translated_at`,
  `expires_at`, `eligible_count`, `translated_count`, `missing_count`, and
  `reason`.

## Commands

Current validation commands relevant to this feature:

```bash
python3 -m unittest tests/test_live_feed_surface.py tests/test_i18n_static_pages.py
node --test tests/test_feed_api.mjs
python3 pipeline/render_static_pages.py --base-url https://www.llm-digest.com
```

Future implementation should add a dedicated command for building the localized
feed snapshot, for example:

```bash
python3 pipeline/build_localized_feed.py --locale ko --label brief --limit 20
```

The final command name is not fixed by this spec, but it must be scriptable by
the hourly pipeline and safe to run when translation credentials are absent.

## Project Structure

Expected files and ownership:

```text
pipeline/build_localized_feed.py        # candidate selection + snapshot writer
api/feed.js                             # locale-aware overlay/status
web/index.html                          # locale-aware client behavior, if reused
web/ko/index.html                       # generated localized feed shell, if static
pipeline/render_static_pages.py         # localized shell/seed rendering
vercel.json                             # /ko and /ko/ rewrites + includeFiles
data/i18n/ko/feed/                      # generated localized feed snapshots
tests/test_localized_feed_*.py|mjs      # data/API/rendering coverage
docs/product-specs/localized-live-feed.md
```

If `api/feed.js` reads feed i18n data, update `vercel.json` `includeFiles` for
that function in the same change. Prefer narrow includes such as
`data/i18n/ko/feed/{latest,status}.json`; do not bundle `data/i18n/**` or
`data/i18n/ko/feed/runs/**` unless there is a specific request-time need.

## Code Style

Prefer small overlay helpers over branching throughout the feed code. The
localized snapshot should be applied as data transformation:

```js
function overlayLocalizedText(item, translated) {
  if (!translated) return item;
  return {
    ...item,
    title: translated.title || item.title,
    summary_1line: translated.summary_1line || item.summary_1line,
    why_it_matters: translated.why_it_matters || item.why_it_matters,
  };
}
```

Do not duplicate ranking logic in the localization path. Select from the feed
output; do not recompute ranking.

## Testing Strategy

Unit tests:

- source-hash stability ignores ranking metadata changes
- up-to-20 selection treats fewer than 20 eligible cards as complete
- incomplete current snapshot preserves the previous complete snapshot
- stale snapshot is detected after 24 hours
- overlay preserves URL/source/date/score/labels/story metadata

API tests:

- `/api/feed?locale=ko&localized_snapshot=latest` returns localized status
- missing/stale/incomplete snapshots are explicit
- English `/api/feed` behavior is unchanged
- localized responses cannot be served as current past `expires_at`

Rendering tests:

- `/ko/` shell has Korean metadata and language alternates
- localized shell includes a stale/fallback state
- static Korean seed is emitted only from a current complete snapshot, once SEO
  support is implemented
- `vercel.json` rewrites `/ko` and `/ko/` to the localized shell
- expired localized feed snapshots are omitted from `sitemap.xml` and noindexed

Manual/browser checks:

- Korean browser sees the `/` to `/ko/` language action only when a current
  complete Korean feed snapshot exists.
- `/ko/` renders without layout overflow on mobile.
- Missing translation credentials no-op cleanly.

## Boundaries

Always:

- Preserve the English ranking order.
- Preserve source URLs and third-party article language.
- Fail open for the English feed if Korean translation fails.
- Make stale/missing/incomplete Korean state visible.
- Keep generated runtime data separate from code commits when practical.
- Keep feed i18n request-time bundles narrow and bounded.

Ask first:

- Showing mixed Korean/English cards as the normal `/ko/` feed.
- Adding `/ko/` to `sitemap.xml`.
- Translating non-Brief lenses such as Research, Releases, All, or pinned
  topics.
- Adding new paid translation providers or persistent external services.
- Exposing `/ko/` to search engines before the static seed and expiry-removal
  rules are implemented.

Never:

- Re-rank items during translation.
- Hide current English feed items globally because Korean translation failed.
- Claim `/ko/` is current when its active snapshot is older than 24 hours.
- Commit translation API keys or provider secrets.
- Let a localized title change item identity for Saved, hidden, feedback, or
  analytics events.

## Success Criteria

- A complete Korean snapshot can be generated for the current Brief top set, up
  to 20 items.
- If the eligible set has fewer than 20 items, all eligible items translated is
  accepted as complete.
- `/ko/` renders Korean UI chrome and Korean card text from the latest current
  complete snapshot.
- If the latest complete Korean snapshot is older than 24 hours, `/ko/` shows a
  clear stale/fallback state instead of pretending to be live.
- English `/` and `/api/feed` behavior remain unchanged.
- Translation failures are observable and non-fatal to the English hourly
  publish path.
- `/ko` and `/ko/` are routed by Vercel to the localized shell.
- Feed i18n artifacts do not create warnings in the static-page i18n collector.
- Expired or disabled `/ko/` is noindexed and omitted from `sitemap.xml`.

## Open Questions

- Which translation system owns `data/i18n/ko/feed/*` generation?
- Should the first implementation generate static `web/ko/index.html`
  immediately, or ship reader-first API/shell behavior before sitemap exposure?
- Should `/ko/` have a separate RSS or JSON endpoint later, or stay page-only?
