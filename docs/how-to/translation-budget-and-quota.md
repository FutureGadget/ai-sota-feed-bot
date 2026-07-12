# Translation budget and quota operations

How to seed the translation ledger, reconstruct spend when you don't have
console access, and set the Google Cloud Console daily-cap backstop. Spec:
`docs/product-specs/localized-live-feed.md` ("Translation Budget Governor");
plan: `docs/exec-plans/active/2026-07-12-translation-budget-governor.md`;
ledger schema: `docs/generated/db-schema.md`.

The governor paces `/ko/` translation spend against
`data/i18n/ko/feed/budget.json`, a local character ledger. Getting that
ledger's starting count right — and setting the console daily cap — is the
one owner action this feature needs; everything else runs unattended.

## 1. Seed the ledger from Cloud Console (mid-month, one-off)

Do this once, the first time the governor goes live mid-month, so the ledger
starts from the actual month-to-date spend instead of zero.

1. Read month-to-date consumed characters from Google Cloud Console. Either
   works:
   - **Billing → Reports**, filtered to the Cloud Translation API SKU, summed
     from the start of the current month.
   - **Monitoring → Metrics Explorer**, on the Translation character-count
     metric, summed since month start.
2. Run the builder's seeding flag with that count:

   ```bash
   python3 pipeline/build_localized_feed.py --seed-chars 245000 --seed-note "console 2026-07-12"
   ```

   This overwrites `chars_used` for the **current month only** in
   `data/i18n/ko/feed/budget.json` and stamps `seeded_from` with the note, so
   the ledger's provenance is auditable later. It does not translate anything
   by itself — run it before or alongside a normal build.

Re-seeding is safe (it always targets the current month); after the first
full month under the governor, the ledger is exact from day one and this step
is not needed again.

## 2. No console access: backfill from git history (fallback + sanity check)

If you don't have Cloud Console access, or want to sanity-check the live
ledger against reality:

```bash
python3 scripts/backfill_translation_ledger.py --month 2026-07
```

This walks `git log` for `data/i18n/ko/feed/latest.json` since the given
month's start, and for each commit diffs which `translation_key`s got a new
`source_hash` — exactly the items sent to the API that run. It pulls the
**English** source fields for those keys from `data/processed/latest.json` at
the same commit, sums input characters, and prints the total plus a suggested
`--seed-chars` value inflated by **+15%** as a safety margin (the walk can
miss edge cases the live meter wouldn't).

It is read-only: it never writes `budget.json`. Feed its suggested value into
the `--seed-chars` command above if you want to apply it.

## 3. Set the console daily-cap backstop

In addition to the local ledger, set the Translation API's **characters per
day** quota in Cloud Console to roughly:

```text
monthly_cap / 31
```

for example ~16,000/day for a 500,000/month cap. This is the **authoritative**
backstop — it catches drift the local ledger cannot see (untracked local
runs, a ledger that fell out of sync) and converts any residual monthly cliff
into soft, explained daily pauses instead of a hard mid-month stop.

When the daily cap trips, Google returns a 403 with a daily-quota reason
(`dailyLimitExceeded` or similar). The pipeline classifies this distinctly
from other 403s and writes `status.json` as `budget_paused` with
`reason: "provider_daily_cap"` and `resumes_at` set to next midnight
**US/Pacific** (Google's daily quota reset) — not a month-end date. `/ko/`
shows "내일" (tomorrow) rather than a dated resume in this case. See the spec's
"Translation Budget Governor" section for the full resume-date logic,
including how a simultaneous monthly-floor pause takes precedence.

## 4. Env knobs

| Var | Default | Effect |
|---|---|---|
| `GOOGLE_TRANSLATE_MONTHLY_CHAR_CAP` | — | The ledger's `monthly_cap`. Set this to match (or sit slightly under) the actual monthly quota/budget you want the governor to pace against. Pattern matches the existing `LOCALIZED_FEED_ENABLED` env toggle in `run_full.sh`. |
| `LOCALIZED_FEED_CONSERVE_MIN_AGE_HOURS` | `6` | In `conserve` mode, skip translating this run if the existing snapshot is younger than this many hours. The 24-hour freshness contract keeps `/ko/` "current" regardless of the skip. |
| `LOCALIZED_FEED_BUDGET_GOVERNOR` | on | Set to `0` to force `normal` mode unconditionally — the kill switch. Metering still records spend into the ledger; only the degradation ladder is bypassed. Use this to roll back the whole feature without touching code. |

## Troubleshooting

- **`/ko/` shows `budget_paused` unexpectedly** → check
  `data/i18n/ko/feed/status.json`'s `reason`. `provider_daily_cap` means the
  console daily quota tripped (resumes at next Pacific midnight);
  `monthly_budget` means the local ledger's `remaining < 2%` floor was hit
  (resumes first of next month UTC).
- **Ledger looks wrong after a manual run or an outage** → run the backfill
  script (step 2) to cross-check `chars_used` against git history, then
  re-seed if they diverge meaningfully.
- **Want to ship without any of this** → `LOCALIZED_FEED_BUDGET_GOVERNOR=0`
  restores full-cadence translation immediately; the ledger keeps counting in
  the background so re-enabling later starts from an accurate number.
