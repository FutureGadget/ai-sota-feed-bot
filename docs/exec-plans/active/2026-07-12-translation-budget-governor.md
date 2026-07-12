# Implementation plan: translation budget governor for the localized live feed

**Date:** 2026-07-12
**Status:** Implemented on this branch (2026-07-12) — pending review, seeding, and console daily-cap setup
**Branch:** `claude/translation-quota-ux-3166a1`
**Product contract:** `docs/product-specs/localized-live-feed.md` (this plan amends it — see Phase 7)
**Decision record:** add an ADR entry to `docs/design-docs/decision-log.md` when merging

## Problem

The Google Translate API integration in the hourly pipeline
(`pipeline/build_localized_feed.py` → `pipeline/google_translate.py`) will
exhaust its monthly character budget before month-end at the current burn
rate. Today the failure mode is a cliff: full hourly freshness until the quota
dies, then `/ko/` freezes on its last snapshot and (after 24h) shows the
generic stale state, which reads as "something is broken."

## Goal

Replace the cliff with a **budget governor**: a local character ledger paces
spending across the month through a graduated degradation ladder, and when a
hard stop does happen, `/ko/` shows an honest, specific "translations paused —
resumes <date>" state with a path to the English feed — never a broken-looking
page, never a page pretending to be current.

Key design insight already agreed: the product contract only promises 24-hour
snapshot freshness, but translation runs hourly. Cutting cadence is free
budget — readers cannot tell the difference.

## Non-goals

- No new Google APIs, credentials, or scopes. Spend is metered locally;
  Google's own quota enforcement (a console-configured daily character cap)
  is the backstop, surfaced to us only as a 403.
- No change to English `/` or `/api/feed` non-locale behavior.
- No re-ranking, no dropping translated fields in v1 (see Economy-mode note).

## Read first

1. `AGENTS.md`
2. `docs/product-specs/localized-live-feed.md` (the full product contract)
3. `pipeline/build_localized_feed.py`, `pipeline/google_translate.py`
4. `api/feed.js` — `readLocalizedFeed` / `localizedStatusBody` /
   `overlayLocalizedFeed` (~lines 120–225)
5. `web/ko/index.html` — the localized feed shell (hand-maintained)
6. `tests/test_localized_feed.py`, `tests/test_feed_api.mjs`

## Architecture

```text
config knobs (env + defaults)          data/i18n/ko/feed/budget.json (ledger)
        \                                   /
         v                                 v
build_localized_feed.py ── governor picks mode ──> normal | conserve | economy | paused
        |                                               |
        | sends chars ──> google_translate.py           |
        |                   (meters input chars,        |
        |                    classifies 403 quota)      |
        v                                               v
data/i18n/ko/feed/latest.json           data/i18n/ko/feed/status.json
                                             |
                                             v
                                   api/feed.js status passthrough
                                             |
                                             v
                                   web/ko/index.html paused/stale UI
```

The ledger lives in `data/` so the existing hourly runtime-data commit
persists it across GitHub Actions runs. Runs are already serialized
(`run_full.sh` lock dir + workflow `concurrency` group), so there is no
double-count race. `budget.json` is pipeline-only: do **not** add it to
`vercel.json` `includeFiles` — everything the API/UI needs travels in
`status.json`.

## Phase 1 — Character metering in `google_translate.py`

1. Make the translate call report **input characters actually sent** to the
   API (the batching loop already computes per-text lengths for
   `_BATCH_CHAR_LIMIT`; sum what is sent, per successful request). Billing
   counts input (English) chars — never count the Korean output.
2. Count a batch's chars only when the request succeeds (2xx). Failed
   requests are not billed by Google; retried-then-successful requests count
   once, on the success.
3. Return the count to the caller (e.g. translate functions return
   `(results, chars_sent)` or accept a mutable stats object — match existing
   code style).

## Phase 2 — Ledger: `data/i18n/ko/feed/budget.json`

Shape:

```json
{
  "month": "2026-07",
  "chars_used": 123456,
  "monthly_cap": 500000,
  "updated_at": "2026-07-12T09:00:00Z",
  "seeded_from": "console 2026-07-12",
  "history": [{ "at": "...", "chars": 812, "run": "snapshot-id" }]
}
```

Rules:

- **Month rollover:** if `month` != current **Pacific** month (aligned to
  Google's billing boundary; resolved during implementation, was UTC in the
  original plan), reset `chars_used` to 0
  and stamp the new month before metering. After the first full month the
  ledger is exact from day one.
- **Seeding (one-off, this month only):** add a builder flag
  `--seed-chars N --seed-note "console 2026-07-12"` that overwrites
  `chars_used` for the current month. The owner reads month-to-date consumed
  characters from Cloud Console (Billing → Reports filtered to the Cloud
  Translation SKU, or Metrics Explorer on the Translation character-count
  metric) and runs the flag once. Document this in the how-to (Phase 7).
- Keep `history` bounded (e.g. last 200 entries) — it is an audit aid, not a
  source of truth.
- `monthly_cap` default comes from env `GOOGLE_TRANSLATE_MONTHLY_CHAR_CAP`
  (pattern matches existing `LOCALIZED_FEED_ENABLED` env toggle in
  `run_full.sh`); the ledger records the cap used so status can report it.

Also write a small **backfill/validation script**
(`scripts/backfill_translation_ledger.py`): walk `git log` for
`data/i18n/ko/feed/latest.json` since a given month start; for each commit,
diff which `translation_key`s got a new `source_hash` (exactly the items sent
to the API); pull the **English** source fields for those keys from
`data/processed/latest.json` at the same commit; sum input chars; print the
total with a suggested `--seed-chars` value inflated by 15% as safety margin.
This is the no-console-access fallback for seeding and a periodic sanity check
of the live ledger. Read-only; never writes the ledger itself.

## Phase 3 — Governor: mode selection in `build_localized_feed.py`

At the start of each run, load the ledger and compute:

```text
days_in_month, day_of_month           (UTC)
month_fraction_elapsed = day_of_month / days_in_month
budget_fraction_used   = chars_used / monthly_cap
remaining              = monthly_cap - chars_used
```

Pick the mode (first matching rule wins):

| Mode | Rule | Behavior |
|---|---|---|
| `paused` | `remaining < 2% of cap`, OR last run recorded a provider quota 403 still in effect | Skip translation entirely. Keep previous complete snapshot. Write `budget_paused` status (Phase 4). |
| `economy` | `budget_fraction_used > month_fraction_elapsed + 0.15` | Translate top **10** instead of 20 (pass through the existing `--limit` machinery; snapshot records `max_items: 10`, `is_complete` per the existing up-to-limit rule). Also apply the conserve cadence rule. |
| `conserve` | `budget_fraction_used > month_fraction_elapsed` | Skip translating this run if the existing snapshot's `source_run_at` is younger than `LOCALIZED_FEED_CONSERVE_MIN_AGE_HOURS` (default 6) — the 24h currency contract keeps `/ko/` "current" regardless. When skipping, still refresh `status.json` (status stays `current`, add `"mode": "conserve"`). |
| `normal` | otherwise | Today's behavior. |

Notes:

- **Economy keeps all translated fields.** Do not drop `why_it_matters` to
  save chars in v1: `source_hash` covers it, so partially-translated items
  would register dirty forever and *waste* budget. Field-tiering is out of
  scope until the hash scheme supports it.
- The existing hardcoded `max_translations = 20` per-run item cap
  (`build_localized_feed.py` ~line 204) stays as a per-run sanity bound; the
  ledger is the monthly authority.
- After a successful run, add the metered chars to the ledger and write it.
- Every run logs one grep-friendly line:
  `localized_feed_budget mode=<mode> chars_used=<n> cap=<n> month=<YYYY-MM>`.
- Mode must **never** affect the English pipeline; all governor failures are
  caught and degrade to keeping the previous snapshot + writing status
  (mirror the existing missing-credentials path).

## Phase 4 — 403 quota classification + `budget_paused` status

1. In `google_translate.py`, when a 403 arrives, parse the error body for
   Google's quota reasons (`dailyLimitExceeded`, `userRateLimitExceeded`,
   `rateLimitExceeded`, `quotaExceeded` — match loosely on
   `"quota"`/`"limit"` in `errors[].reason`/`message`). Raise a distinct
   `QuotaExceededError(ConnectionError)` carrying the reason. Other 403s
   (bad key, API disabled) keep the current generic failure path.
2. In `build_localized_feed.py`, catch `QuotaExceededError` and write status
   `budget_paused` instead of a generic batch failure. Two resume flavors:
   - reason indicates a **daily** cap (the console backstop) →
     `resumes_at` = next midnight **US/Pacific** (Google daily quota reset),
     `reason: "provider_daily_cap"`.
   - ledger says the **monthly** budget floor is hit →
     `resumes_at` = first of next month at Pacific midnight,
     `reason: "monthly_budget"`.
   When both apply, the monthly reason wins (it is the later, truer date).
3. Extend `status.json` (superset of the current shape — keep every existing
   field so `api/feed.js` and tests keep working):

```json
{
  "locale": "ko",
  "surface": "feed",
  "status": "budget_paused",
  "reason": "monthly_budget",
  "resumes_at": "2026-08-01T00:00:00Z",
  "mode": "paused",
  "budget": { "chars_used": 492000, "monthly_cap": 500000, "month": "2026-07" },
  "source_run_at": "…", "translated_at": "…", "expires_at": "…",
  "eligible_count": 20, "translated_count": 20, "missing_count": 0
}
```

   `mode` + `budget` are also written in non-paused states so ops can watch
   the ladder. New grep key: `localized_feed_budget_paused` (joins the
   existing `localized_feed_ok` / `localized_feed_stale` / … family).
4. **Interplay with the 24h rule is unchanged:** `budget_paused` never fakes
   currency. Once the frozen snapshot's `expires_at` passes, `is_current`
   goes false exactly as today; `budget_paused` only *explains why* and adds
   `resumes_at`.

## Phase 5 — API passthrough in `api/feed.js`

1. `localizedStatusBody` forwards the new fields when present: `status`
   (may now be `budget_paused`), `reason`, `resumes_at`, `budget`.
   No new logic — pure passthrough of `status.json` fields.
   **Resolved during implementation:** the API response already has a
   top-level `mode: "localized_snapshot"` contract field, so the governor's
   `mode` from `status.json` is exposed as `governor_mode` in the response
   to avoid the collision. `status.json` itself keeps `mode` as specified.
2. Caching: a `budget_paused` + non-current response must obey the existing
   rule that localized responses are never cached as current past
   `expires_at`. Verify the current cache-control path already covers a
   long-frozen snapshot (it should — expiry is computed from
   `source_run_at`) and add a test either way.
3. `vercel.json`: no change expected — `status.json` is already in
   `includeFiles`; confirm, and do **not** add `budget.json`.

## Phase 6 — `/ko/` shell paused-state UI (`web/ko/index.html`)

Three reader-visible changes, all keyed off the API status:

1. **Paused notice (one calm line, not a modal):** when
   `status === "budget_paused"`, render above the feed:
   > 이번 달 번역 예산이 소진되어 {snapshot date} 스냅샷을 보여드리고
   > 있습니다. 새 번역은 {resumes_at, formatted KST}에 재개됩니다 ·
   > 최신 소식은 영어 피드에서 →  (link to `/`)
   For `reason: "provider_daily_cap"`, say "내일" (tomorrow) instead of a
   month date. This state replaces — not stacks with — the generic stale
   banner: budget pause is the more specific explanation. Keep the generic
   stale state for genuinely unexplained staleness.
2. **Dated-edition framing:** when not current, the page heading area shows
   the snapshot as a dated edition ("{M월 D일} 기준 한국어 브리핑" from
   `source_run_at`, KST) rather than a live feed with fine-print staleness.
3. **"Newer in English" strip (flagged, optional — see spec note):** when
   paused/stale, fetch the English feed and list titles of items that entered
   the Brief top-20 *after* the frozen snapshot's `source_run_at`, as a
   clearly-labeled separate section "그 이후 새로 올라온 소식 (영어)",
   linking to `/`. English titles rendered as English — never silently mixed
   into the Korean cards. Gate behind a shell-level constant so it can ship
   dark if review stalls. This is the one piece that touches the spec's
   "Ask first: mixed Korean/English cards" boundary — the spec amendment in
   Phase 7 records the owner's approval of this *labeled-section* form.

SEO hygiene rides the existing rails: non-current `/ko/` already must drop
out of `sitemap.xml`, render `noindex`, and stop advertising `hreflang`
(spec "SEO rules"). Verify `budget_paused` + expired follows that exact path;
add a rendering test if uncovered.

## Phase 7 — Ops backstop + documentation

1. **Console daily cap (manual, owner action):** document setting the
   Translation API "characters per day" quota to ~`monthly_cap / 31` in the
   Cloud console. This is the authoritative backstop that catches ledger
   drift (e.g. untracked local runs) and converts any residual monthly cliff
   into soft daily ones. New how-to:
   `docs/how-to/translation-budget-and-quota.md` — covers the cap, the
   one-off `--seed-chars` seeding procedure (console read → flag), and the
   backfill script as fallback/validation.
2. **Spec amendment** (`docs/product-specs/localized-live-feed.md`): add the
   `budget_paused` status + `resumes_at`/`mode`/`budget` fields, the
   governor modes table, the ledger artifact, and move the labeled
   "Newer in English" section from "Ask first" to an approved, specified
   fallback state.
3. **`docs/generated/db-schema.md`:** add `data/i18n/ko/feed/budget.json`.
4. **ADR** in `docs/design-docs/decision-log.md`: date, decision (local
   ledger + graduated governor + provider daily-cap backstop over dynamic
   quota APIs), rationale (deterministic, no new credentials; 24h contract
   makes cadence cuts reader-invisible), impact, rollback (env-disable
   governor → prior behavior).
5. **Rollback/kill switch:** `LOCALIZED_FEED_BUDGET_GOVERNOR=0` env forces
   `normal` mode (metering still records; only the ladder is bypassed).

## Testing

Extend `tests/test_localized_feed.py` (and `tests/test_feed_api.mjs` where
noted):

- Ledger: month rollover resets; seeding flag overwrites current month only;
  chars accumulate only on successful batches; history stays bounded.
- Metering counts English input chars, not Korean output.
- Governor mode table: each rule boundary (exactly at pro-rata, +0.15, <2%
  floor), kill-switch env forces normal.
- Conserve skip: young snapshot + over-pace → no translate call, status still
  refreshed with `mode: conserve`.
- Economy: limit drops to 10, `is_complete` semantics per existing
  up-to-limit rule, all fields still translated.
- 403 classification: quota-reason bodies raise `QuotaExceededError`; bad-key
  403 does not; paused status carries the right `resumes_at` per reason;
  monthly reason wins over daily.
- Previous complete snapshot preserved through paused runs (existing
  invariant, re-asserted under the new path).
- API (`test_feed_api.mjs`): `budget_paused` passthrough; frozen snapshot
  past `expires_at` is not served as current (cache rule).
- Shell: paused notice renders with formatted resume date; dated-edition
  heading when non-current; English strip labeled and gated; paused+expired
  page is noindexed / out of sitemap.

Validation commands (from the spec, plus the new ones):

```bash
python3 -m unittest tests/test_localized_feed.py tests/test_live_feed_surface.py tests/test_i18n_static_pages.py
node --test tests/test_feed_api.mjs
python3 pipeline/build_localized_feed.py --locale ko --label brief --limit 20 --dry-run
python3 scripts/backfill_translation_ledger.py --month 2026-07   # prints, never writes
```

## Delivery order & commits

Small shippable steps, code separate from runtime data
(`scripts/git_commit_code.sh`):

1. Phases 1–2 (metering + ledger + backfill script) — no behavior change yet.
2. Phase 3 (governor) behind `LOCALIZED_FEED_BUDGET_GOVERNOR` env, default on
   only after step 3 lands.
3. Phases 4–5 (403 → `budget_paused` → API passthrough).
4. Phase 6 (shell UI) — eyeball on the Vercel PR preview.
5. Phase 7 (docs/ADR/how-to) — in the same PRs as the code they describe,
   per the documentation contract.

The one human-in-the-loop step: the owner reads the month-to-date character
count from Cloud Console and runs the `--seed-chars` seeding once (or accepts
the backfill script's +15% estimate), and sets the console daily cap.

## Boundaries (inherit the spec's; additions)

Always:
- English hourly publish is never blocked by any governor/meter failure.
- `budget.json` stays out of `vercel.json` `includeFiles`.
- Every degraded state is visible in `status.json` + a grep-friendly log key.

Never:
- Claim `/ko/` is current past `expires_at`, regardless of pause reason.
- Count Korean output chars as spend.
- Drop translated fields per-item in v1 (breaks `source_hash` economics).
- Silently serve the English feed at `/ko/` as if it were Korean.
