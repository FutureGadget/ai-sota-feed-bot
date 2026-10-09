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

## 0. The free tier and what shares it

Cloud Translation Basic (v2) is free for the **first 500,000 characters per
month per billing account** (applied as a $10 credit), then $20 per 1M
characters. Billing counts every code point sent, including HTML markup and
whitespace, so the glossary `<span class="notranslate">` wrappers and
`&amp;` escapes count. Two jobs share that one allowance:

| Job | Ledger | Default cap |
|---|---|---|
| Live feed (`build_localized_feed.py`, hourly) | `feed/budget.json` | 400,000 (`GOOGLE_TRANSLATE_MONTHLY_CHAR_CAP`) |
| Static pages (`scripts/translate.py`, daily workflow + local script) | `feed/static_budget.json` | 100,000 (`GOOGLE_TRANSLATE_STATIC_MONTHLY_CHAR_CAP`) |

The two caps sum to the whole free tier. The spend guard (section 4b) is the
exact hard stop, and it charges ambiguous requests (timeouts, retries), so no
safety margin is needed for those.

## 0b. What is sent (and why tags still cost)

Google bills every character in the request, including HTML markup, and does not
translate tags. The only markup we send is our own: glossary terms wrapped in
`<span class="notranslate">` (33 characters per term, about 15% of a typical
feed batch) and `&`, `<`, `>` escaping. To keep the bill down, `translate_texts`:

- skips strings with no Latin letters (numbers, dates, emoji, blanks);
- sends identical strings once and fans the result back out;
- escapes only `&`, `<`, `>` (apostrophes and quotes stay one character).

`estimate_billed_chars` mirrors this exactly, so budget estimates match the bill.

The 2026-10 incident: the static workflow exited non-zero on any failed
candidate, so its commit step never ran and every translation was discarded.
The same pages were re-translated and re-billed each day, outside any ledger.

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

## 4b. The spend guard (the actual hard stop)

Google's quota enforcement lags, so a burst can overshoot it. The authority is
`pipeline/translation_guard.py`, installed by `build_localized_feed.py` and
`scripts/translate.py` in front of every API request:

- **Reserve before send.** Characters are written to
  `data/i18n/spend_guard.json` (day and month counters on the Pacific clock)
  before the request leaves; over the ceiling raises `SpendLimitError`
  and nothing is sent.
- **Ceilings match Google's limits:** 16,000/day (the Console quota) and
  500,000/month (the free tier). The count is exact: Python `len()` counts code
  points, which is what Google bills. 16,000 x 31 days is 496,000, so the daily
  limit binds first; raise the Console quota to 16,129 to reach 500,000 in a
  31-day month. After a few days compare `month_chars` to Console usage.
- **Ambiguous outcomes stay charged.** Timeouts, connection errors, 5xx and each
  retry count as spent; only HTTP 4xx rejections are refunded.
- **Fail closed.** A corrupt ledger blocks requests. If Google reports the daily
  quota exhausted, the guard trips the day shut regardless of its own count.
- **Paced.** At most 4,000 characters per minute leave the process (a single
  larger request passes when the window is empty).
- **Serialized and refreshed.** `i18n-translate.yml` shares the `feed-pipeline`
  concurrency group and refreshes main before spending. A queued workflow's
  triggering SHA can predate an earlier feed publish even with serialization.
  Static publication adds usage deltas to fresh main rather than text-rebasing
  the shared ledger (see section 6).

| Var | Default | Effect |
|---|---|---|
| `GOOGLE_TRANSLATE_HARD_DAILY_CHARS` | 16000 | Daily ceiling |
| `GOOGLE_TRANSLATE_HARD_MONTHLY_CHARS` | 500000 | Monthly ceiling |
| `GOOGLE_TRANSLATE_MAX_CHARS_PER_MINUTE` | 4000 | Pacer; 0 disables |
| `GOOGLE_TRANSLATE_GUARD_PATH` | `data/i18n/spend_guard.json` | Ledger location |
| `GOOGLE_TRANSLATE_GUARD` | 1 | `0` disables the guard (kill switch) |

Mid-month rollout: the ledger starts at zero. Seed it from Console usage by
setting `month` (`YYYY-MM`) and `month_chars` in the file. A feed run stopped by
the guard writes `budget_paused` (`monthly_budget` or `provider_daily_cap`).

## 5. Hard stops that do not depend on this repo

Local ledgers only see our own runs. Set both of these in Cloud Console:

- **APIs & Services -> Cloud Translation API -> Quotas**: "Characters per day"
  to ~16,000 (500,000 / 31) for both v2 and v3 general models (done
  2026-10-04). Google then returns 403 instead of billing.
  The project only calls v2; v3 is set as a precaution.

  The live feed uses 3-16K characters per Pacific day, so it nearly fills this
  quota on busy days. Static-page translation therefore yields to it: before
  each page it computes `16000 - 6000 reserve - feed chars today - static
  chars today` (Pacific day, from the ledger histories) and skips the page if
  it does not fit. Tune with `GOOGLE_TRANSLATE_DAILY_CHAR_QUOTA` and
  `GOOGLE_TRANSLATE_STATIC_FEED_RESERVE`. Static pages are 3-13K characters
  each, so expect them to translate only on quiet days. If the quota is
  raised, raise the env var to match.
- **Billing -> Budgets & alerts**: a budget of $1 with alerts at 50% and 100%.
  Budgets alert, they do not stop spend; the quota above is what stops it.
- Restrict the API key to the Cloud Translation API only.

## Troubleshooting

- **`/ko/` shows `budget_paused` unexpectedly** → check
  `data/i18n/ko/feed/status.json`'s `reason`. `provider_daily_cap` means the
  console daily quota tripped (resumes at next Pacific midnight);
  `monthly_budget` means the local ledger's `remaining < 2%` floor was hit
  (resumes first of next month at Pacific midnight — Google's billing
  boundary; the ledger month also rolls on the Pacific calendar so both
  sides reset together).
- **Ledger looks wrong after a manual run or an outage** → run the backfill
  script (step 2) to cross-check `chars_used` against git history, then
  re-seed if they diverge meaningfully.
- **Want to ship without any of this** → `LOCALIZED_FEED_BUDGET_GOVERNOR=0`
  restores full-cadence translation immediately; the ledger keeps counting in
  the background so re-enabling later starts from an accurate number.

## 6. Persist paid static outputs and recover publishing failures

`scripts/persist_static_i18n.py` owns the static workflow's persistence path:

1. Recover unacknowledged attempts before allowing another translation call.
2. Refresh main while the checkout is clean, then save the run identity and
   base commit in `$RUNNER_TEMP/static-i18n/checkpoint.json`.
3. After translation, checkpoint changed translation JSON and the before/after
   versions of both spend ledgers. Save this as an Actions artifact named
   `static-i18n-<run-id>-<attempt>`, retained for 90 days, before rendering.
   These steps also run after partial translation failure or cancellation.
4. Materialize the checkpoint in a disposable worktree on current main. Add
   the shared guard and static ledger deltas to current counters, retain feed
   usage, and rebuild the website with the offline renderer. Retry a rejected
   push only when main advanced; no retry invokes the translator.
5. Commit the outputs, counters, and a receipt together. The guard's
   `static_runs["actions-<run-id>-<attempt>"]` stores the checkpoint SHA-256,
   locale, timestamp, usage periods/deltas, and any acknowledged lost output
   paths/source hashes plus translated-field fingerprints (`lost_payloads`).
   It survives day/month rollover. Replaying the same
   checkpoint is a no-op; reusing an identity for different content fails.

Both paid workflows recover saved attempts from oldest to newest before
spending. The feed workflow also recovers static usage before its next paid
request, so an unpublished static run cannot temporarily disappear from the
shared ceiling. If recovery fails, `STATIC_I18N_RECOVERY_BLOCKED=1` skips the
localized feed builder while English collection/rendering/publishing continues.
Feed workflow dry runs also skip that paid step because they cannot durably
publish usage. No spending ceiling or schedule changes.

A missing, incomplete, or expired checkpoint after the paid step
blocks new calls. Concurrent changes to the same translation artifact also
stop publication and preserve the checkpoint for review. An existing static
usage history entry without a corresponding receipt is an accounting
uncertainty and is not charged again automatically.

For manual recovery, download the saved artifact and inspect its
`checkpoint.json`. In a clean checkout with a configured Git identity:

```bash
# Apply locally for review. This does not push, render, or call any API.
python3 scripts/persist_static_i18n.py apply --checkpoint /path/to/checkpoint.json

# After publication authorization, publish the saved outputs against fresh main.
# This renders offline and pushes; it does not call the translation API.
python3 scripts/persist_static_i18n.py publish --checkpoint /path/to/checkpoint.json
```

Counter merging follows the Pacific accounting period. Recovering an old day
does not add its usage to today's daily counter; recovering an old month does
not change the current month's counter. Historical usage remains in the
receipt and static history. A provider daily-quota trip remains a stop floor,
not an additional billed character count. The hard guard retains ambiguous
request/retry charges even when no translation output was returned. A runner
that is destroyed before uploading a checkpoint can lose its outputs; the
following workflow blocks instead of automatically buying them again.

### October 9, 2026 reconciliation

[Run 37877382078](https://github.com/FutureGadget/ai-sota-feed-bot/actions/runs/37877382078)
generated three Korean storyline translations and recorded 1,509 characters,
zero translation errors, and seven budget skips. Its local commit
`43f71f7e13` was never pushed: rebasing from `b8101e9ccb` onto feed commit
`db6b019363` conflicted in `data/i18n/spend_guard.json`. No recovery artifact
was uploaded, and the commit/output files are unavailable in GitHub and the
inspected local checkouts.

The feed commit added 1,459 characters, moving the shared counters from
8,370 to 9,829 for Pacific October 8 and 49,829 to 51,288 for October. The
missing static run contributes an additional 1,509, rather than replacing
those totals. On that verified snapshot, the reconciled counts are 11,338
and 52,797. The static partition also receives the 1,509 characters and an
original-run timestamp/history entry. These values are evidence for the
reconciliation; the checkpoint publisher adds the delta to whatever main
contains when it is applied.

The original source payloads at `b8101e9ccb` estimate to exactly 726
(Qwen Image 2.1), 611 (Claude 5.5), and 172 (Inference Serving) characters.
The reconciliation receipt acknowledges their missing outputs and records
their source hashes and fingerprints of the actual translated fields.
`scripts/translate.py` skips those billed strings, including under
`--include-fresh` and after metadata-only changes such as `generated_at`, so
they cannot be silently bought again. Changed translation text has a new
fingerprint and can be translated normally. The existing Korean text could
not be recovered; no replacement
translations were generated. Any decision to buy replacements requires a
separate explicit change to this loss acknowledgement while keeping the usage
receipt. Older unrecorded spend and Cloud Console usage remain outside what
this incident's logs can establish.
