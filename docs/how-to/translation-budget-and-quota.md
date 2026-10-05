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
- **Serialized.** `i18n-translate.yml` shares the `feed-pipeline` concurrency
  group, so the feed and static jobs never run side by side and the committed
  ledger is exact.

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
