# Editorial updates: discovery and reader state

The feed and Editor's Desk show actual published headlines, dates, short
source-derived previews, and direct links. Section names alone do not tell a
reader what changed. This catalog covers future publications automatically.

## Reader surfaces

- The live feed shows at most three fresh, unopened editorial items, newest
  first. These are vertically stacked rows on mobile, never a scrolling chip
  strip. Hide dismisses editorial previews for this browser session without
  marking content opened.
- When Catch me up exists, these rows render inside that card. Otherwise they
  occupy `#freshUpdates`. Feed rendering calls `llmDigestUpdates.renderFeed()`;
  the result is independent of which API responds first. Existing catch-up
  stories, dismissal, filters, and finish-line behavior remain.
- The Desk has three latest items above its existing navigation and a
  **View all updates** link. Its canonical section order is unchanged.
- `/updates` lists the complete published catalog with Latest / Unread and
  section filters. There is no arbitrary API result cap that could silently
  omit an unread item. An empty Unread list says the reader is caught up.
- Daily, Weekly, Storylines, Playbook, Agent Know-How and Foundations section
  roots have a collapsed Latest area with Latest / Unread controls and a
  section-filtered link to `/updates`. Detail pages retain their reading layout.
- Navigation badges count fresh new/updated **items**, including published
  Skill Lab records under Playbook. The Desk count sums these item counts.

**New** means an item absent from the browser's initial catalog baseline.
**Updated** means reader-facing content changed from a known or opened version.
**Unread** includes older baseline items that have not been opened. An opened
version is labeled **Opened**, not claimed to have been read to completion.
Editorial recommendation/relevance remains a separate signal from recency.

## Publishing contract and producer coverage

`lib/editorial-catalog.js::buildEditorialCatalog(dataDir)` builds the catalog
at read time from the same deployment's published content. `/api/updates`
returns it alongside the existing six section signals, preserving compatibility
with older clients. No additional function, background job, generated manifest,
agent-authored promo copy, or shared mutable publication ledger is introduced.

| Surface | Publisher / canonical output | Catalog unit and identity | Update evidence |
|---|---|---|---|
| Daily | `daily-summary` → `data/daily/index.json` + dated JSON | `daily:<date>`; `/daily/<date>` | Recap title, intro, highlights, category/article content |
| Weekly | `weekly-summary` → `data/weekly/index.json` + dated JSON | `weekly:<week>`; `/weekly/<week>` | Recap title, intro, highlights, category/article content |
| Playbook | `playbook` → `data/playbook/index.json` + dated JSON | `playbook:<date>`; `/playbook/<date>` | Edition intro and source-backed cards |
| Skill Lab | `build_skill_lab.py` → `data/playbook/lab/index.json` + published records | `playbook:lab:<slug>`; `/playbook/lab/<slug>` | Validated protocol/results; exact source digest must match index |
| Storylines | External scout/editor routine → `data/storylines/index.json` + served thread JSON | `storylines:<slug>`; `/storyline/<slug>` | Timeline and **overlaid** editorial narrative, including narrative-only edits |
| Agent Know-How | `wiki-curator` + `build_wiki.py` → `data/wiki/index.json` | `map:<slug>`; `/topic/<slug>` | Compiled page prose, evidence and relationships |
| Foundations | `foundations-curator` + `build_foundations.py` → `data/foundations/index.json` | `foundations:<slug>`; `/foundations/<slug>` | Compiled concept prose, evidence and relationships |
| Model Radar | `models-refresh.yml` → model snapshots | Retains existing Radar discovery; no editorial unread badge | Mechanical price/score refreshes are not editorial publications |
| Voices | Existing practitioner directory | Retains existing Desk destination; no editorial unread badge | No versioned editorial publication contract today |
| Live feed / email | Existing ranked feed and recap-based delivery | Retain their own arrival and send cursors | Neither advances editorial opened state |

All indexed editions are read, not just `latest.json`; opening an old edition
must not hide a newer one. Adding a new item within these producer types needs
no catalog registration. Adding a new producer type requires a catalog adapter,
its deployment files, lifecycle coverage and an update to this table.

### Scheduled-run compatibility

The feed workflow does not produce all editorial material. Catalog discovery
is therefore attached to the published deployment, not to `run_full.sh` or one
cron. Each external routine continues to validate, compile, stage and push its
existing outputs. Its next publication becomes discoverable with no extra
skill step or staging path. Existing skill schemas, sidecar ownership, thin
routine prompts, `harness.yaml` schedules/timezones and `COMMON.md` rebase/retry
rules remain authoritative.

`vercel.json` explicitly bundles all indexed dated editions, served storyline
records, compiled wiki/concept indexes, and top-level published Lab records for
`api/updates.js`. Input directories, raw narratives and Lab drafts are not
included. The Vercel build continues compiling wiki/concepts and rendering
pages before serving the API from that same content snapshot. A failed compiler
retains its existing validated-index fallback behavior. An incomplete source
record is skipped; a missing/corrupt producer does not hide other producers.
No feature build writes back into another routine's source files.

## Versions and dates

Each item includes `id`, `section`, `section_label`, `href`, `title`, `summary`,
`kind`, `version`, `published_at`, `updated_at`, `date_precision` and `period`.
`catalog_version` is 1. `version` is a deterministic hash of reader-facing
content, excluding rebuild timestamps. Key reordering and clock-only reruns do
not reset opened state. Multiple substantive edits on the same source date
produce distinct versions. The hash is a change detector, not an LLM judgment
about significance; prose corrections can also count as updates.

Display dates use existing source metadata. Dated editions use their authored
publication time (or explicit `updated_at` when available). Storylines use the
later of evidence arrival and the overlaid narrative's authored time. Wiki and
Foundations currently expose calendar dates, so the UI shows an actual date,
never an invented “2h ago.” Unknown original publication dates stay null.
Historical items are not stamped with deployment time during rollout.

Fresh feed promotion and navigation badges preserve cadence gates: Daily today
or yesterday, Weekly within eight UTC days of period end, Playbook within ten
UTC days, and Lab within fourteen UTC days. Future-dated periods are excluded.
Evergreen pages and storylines use content/read history without a fixed expiry.
The full catalog and Unread filter retain older items even after promotion ages
out. Ties sort by stable ID.

## Browser state and migration

`ai_feed_editorial_state_v2` contains `{schema: 2, baseline, seen}` maps from
item ID to version. On first use (including migration from the lossy section
keys), baseline the existing catalog without raising new-content alarms. Show
actual latest headlines immediately. Do not pretend section-level history
proves which items were opened; old items remain available under Unread.

Opening a known detail page records only that item's current version. The
pre-rendered Daily/Weekly roots resolve the actual displayed edition from their
JSON link, not whatever happens to be latest in the catalog. Dynamic Playbook
and Lab shells announce `editorial:opened` only after successful rendering and
leave a DOM marker for a late-loading discovery script. Index visits and API
failures never acknowledge an entire section. Storage events synchronize tabs;
blocked/corrupt storage still allows content discovery. Existing knowledge
universe `ai_feed_topic_reads_v1` logging remains compatible.

Localized pages do not acknowledge an English content version, because their
translation can lag the source. The catalog's direct links point to canonical
English content; translation generation and the localized feed's own update
signals remain unchanged.

## Accessibility, failure and analytics

Rows use semantic links and dates; status is textual, not color-only. Controls
have 44px targets and visible focus. Lists wrap within the reading column and
use the site's light/dark variables. No animation is required. Existing
semantic navigation remains available without JavaScript or a successful API.
`/updates` provides loading, empty and fetch-failure copy with section navigation.

Optional PostHog events: `editorial_updates_view` (feed item IDs),
`editorial_update_click` (ID, section, placement, status),
`editorial_update_open` (ID, section), `editorial_updates_dismiss` (placement).
These diagnose discovery; weekly returning readers remains the north-star
metric. Open events do not assert article completion.

## Validation and rollback

- `node tests/test_editorial_catalog.mjs`: every producer, future editions and
  concepts, narrative-only and same-day changes, idempotent reruns, corrupt
  source isolation, Lab digest gates, archive identity, baseline migration,
  opened-version tracking and freshness boundaries.
- Existing Python chrome/feed tests cover shared loading, navigation order,
  bounded layout and deterministic catch-up composition; all JS tests remain
  in the existing CI runner.
- Browser QA: both API response orders, first/returning visits, actual old and
  current edition routes, failed dynamic loads, blocked storage, section
  filters, keyboard navigation, and mobile light/dark layouts.
- Run the production Vercel build to verify compiled indexes, static paths and
  asset staging. Keep generated output changes out of code commits.

Rollback the feature code/config and shared asset versions together. Legacy
API fields and section storage keys remain intact. The v2 browser key can be
ignored by the old client; no canonical content or email cursor needs repair.
