# Translation budget and credentials

How translation spend is capped, how CI authenticates to Anthropic without an API
key, how to preview translations, and how paid static outputs are saved and
recovered. Spec: `docs/product-specs/localized-live-feed.md` ("Translation
Budget Cap"); ledger schema: `docs/generated/db-schema.md`; decision:
`docs/design-docs/decision-log.md` ("Translation moves from Google Translate to
Claude").

Both translation callers use `pipeline/translator.py`, the only module that calls
the Anthropic API:

| Caller | Surface in `config/translation.json` | Job |
|---|---|---|
| Live `/ko/` feed cards (`pipeline/build_localized_feed.py`, every feed run) | `feed` | one per card |
| Static pages (`scripts/translate.py`, daily workflow and local script) | `static` | one per page |

The policy file also holds the model for each surface and `max_context_chars`.
The style guide is `config/translation/<locale>.md`; the do-not-translate list is
`config/glossary.yaml`. Both go into the cached system prompt. Every model in the
policy needs a price in `translator.PRICES`, or translation raises `ValueError`.

## 1. The ledger and the monthly cap

All spend goes into one file, `data/i18n/translation_spend.json`, shared by the
feed and the static run:

```json
{"month": "2026-11", "usd": 1.2345, "history": [{"at": "…", "key": "…", "surface": "feed", "usd": 0.003}]}
```

- `usd` is the spend this UTC month. It resets to 0 when the month changes.
- `history` keeps the last 200 calls. Use it to see which surface spent what.
- The file is re-read on every operation, so a stale view cannot undercount.

Before each call the translator estimates its cost (input tokens at 3 characters
per token, output at twice the field text) and raises `BudgetExceeded` if the
month's spend plus the estimate would pass the cap. After each call it records
the real cost from the response usage. A retry after an unparseable reply is a
second call and is reserved and recorded again.

| Setting | Where | Default |
|---|---|---|
| `TRANSLATION_MONTHLY_USD_CAP` | environment, wins when set | none |
| `monthly_usd_cap` | `config/translation.json` | 60 |

To raise the cap for a month, edit `monthly_usd_cap` in a PR, or set
`TRANSLATION_MONTHLY_USD_CAP` in the workflow's step `env`. No workflow sets it
today. To correct the ledger, edit `usd` in the file and commit it. The cap is
not stored in the ledger, so changing it takes effect on the next run.

The estimate is deliberately high, so a run can stop a few cents under the cap.

## 2. What happens at the cap

- **Feed.** The builder stops translating, keeps the cards it already
  translated, writes `data/i18n/ko/feed/cards.json`, logs
  `localized_feed_budget_cap_reached`, and exits 0. `/ko/` keeps working: cards
  without a translation show in English until the ledger month rolls over (00:00
  UTC on the first). A card is translated whole or not at all.
- **Static pages.** The run stops cleanly with exit code 0 at the first
  `BudgetExceeded`. Each page is written as soon as it is translated, so every
  finished page is checkpointed and committed (section 5). The remaining pages
  wait for the next month.

Any other failure (an unparseable reply after the retry, an API error) fails that
card or page only. The feed run logs it and moves on to the next card, and the
static run exits 1 after the loop, in both cases without discarding finished work.

## 3. Credentials: workload identity, no API key

CI holds no Anthropic API key and no secret. A workflow job that translates
exchanges its GitHub OIDC token for a short-lived Anthropic token:

- The job needs `id-token: write`. `permissions:` on a job replaces the
  defaults, so the translating jobs list `contents: write` and `actions: read`
  as well. Do not drop them.
- The job `env` carries the federation rule, organization, service account, and
  workspace ids, plus `ANTHROPIC_IDENTITY_TOKEN_FILE=/tmp/gha-jwt`. The values are
  identical in `translation-preview.yml`, `feed-full-publish.yml`, and
  `i18n-translate.yml`. They are identifiers, not secrets.
- The step "Fetch GitHub OIDC token and keep it fresh" runs before the translate
  step. GitHub's token lives about 5 minutes and the SDK rereads the file on each
  refresh, so the step rewrites it every 240 seconds in the background. The first
  fetch must succeed. A failed refresh keeps the previous token.
- The federation rule is pinned to `main`. A run from any other ref (a PR branch
  or a manual dispatch on a branch) can fetch a token but Anthropic refuses the
  exchange, so it cannot spend. The static workflow also refuses to publish from
  a non-main ref.
- In `feed-full-publish.yml` the token step is `continue-on-error`. If it fails,
  the localized feed step fails on its own and English publishing continues.

To rotate or change the rule, edit the four ids in all three workflows together.

For a local run (`scripts/run_local_ko_translation.sh`, or any script that
translates), set `ANTHROPIC_API_KEY` in your shell. Local runs write to the same
ledger file, so commit it with the translations.

## 4. Preview translations before changing anything

`translation-preview.yml` is a manual workflow. It translates the English
home's current cards with Claude and writes a table of English, committed, and Claude
text to the run summary. It writes no data and commits nothing; its spend goes to
a temporary ledger.

The same script runs locally:

```bash
python3 scripts/translation_preview.py --limit 2 --dry-run   # prints the jobs, no API call
python3 scripts/translation_preview.py --limit 5             # needs credentials
```

Run it after any change to `config/translation/ko.md` or `config/glossary.yaml`.
A style rule is only done when the preview shows the behavior it asked for.

## 5. Persist paid static outputs and recover publishing failures

The 2026-10 incident: the static workflow exited non-zero on any failed
candidate, so its commit step never ran and every translation was discarded. The
same pages were translated and paid for again each day. The rule since then is to
never discard completed work on a partial failure.

`scripts/persist_static_i18n.py` owns the static workflow's persistence path:

1. Recover unacknowledged attempts before allowing another translation call.
2. Refresh main while the checkout is clean, then save the run identity and base
   commit in `$RUNNER_TEMP/static-i18n/checkpoint.json`.
3. After translation, checkpoint the changed translation JSON and the before and
   after versions of `translation_spend.json`. Save this as an Actions artifact
   named `static-i18n-<run-id>-<attempt>`, retained for 90 days, before
   rendering. These steps also run after a partial failure or cancellation.
4. Materialize the checkpoint in a disposable worktree on current main. Add the
   run's USD delta to the current ledger (so feed spend committed in the
   meantime is kept) and rebuild the website with the offline renderer. Retry a
   rejected push only when main advanced. No retry calls the translator.
5. Commit the outputs, the ledger, and a receipt together. The receipt is
   `static_runs["actions-<run-id>-<attempt>"]` in `data/i18n/static_runs.json`.
   It stores the checkpoint SHA-256, locale, timestamp, usage period and
   dollars, and any acknowledged lost outputs (paths and source hashes, plus
   fingerprints of the translated fields in `lost_payloads`). Replaying the same
   checkpoint is a no-op. Reusing an identity for different content fails.

Both paid workflows recover saved attempts from oldest to newest before
spending. If recovery fails in the feed workflow, `STATIC_I18N_RECOVERY_BLOCKED=1`
skips the localized feed builder while English collection, rendering, and
publishing continue. Feed workflow dry runs also skip that step because they
cannot durably publish usage.

A missing, incomplete, or expired checkpoint after the paid step blocks new
calls. Concurrent changes to the same translation artifact also stop publication
and preserve the checkpoint for review. A history entry already in the ledger
without a matching receipt is an accounting uncertainty and is not charged again
automatically.

For manual recovery, download the saved artifact and inspect its
`checkpoint.json`. In a clean checkout with a configured Git identity:

```bash
# Apply locally for review. This does not push, render, or call any API.
python3 scripts/persist_static_i18n.py apply --checkpoint /path/to/checkpoint.json

# After publication authorization, publish the saved outputs against fresh main.
# This renders offline and pushes; it does not call the translation API.
python3 scripts/persist_static_i18n.py publish --checkpoint /path/to/checkpoint.json
```

Counter merging follows the UTC month. Recovering an old month does not add its
usage to the current month's `usd`. The usage stays in the receipt and the
history. A runner that is destroyed before uploading a checkpoint can lose its
outputs. The following workflow then blocks instead of buying them again.

### October 9, 2026 reconciliation

[Run 37877382078](https://github.com/FutureGadget/ai-sota-feed-bot/actions/runs/37877382078)
generated three Korean storyline translations. Its local commit `43f71f7e13` was
never pushed: rebasing onto a feed commit conflicted in the shared spend file. No
recovery artifact was uploaded, so the outputs are unavailable. The receipt for
that run acknowledges the missing outputs (Qwen Image 2.1, Claude 5.5, and
Inference Serving storylines) with their source hashes and field fingerprints.
`scripts/translate.py` skips those exact texts, including under `--include-fresh`
and after metadata-only changes such as `generated_at`. Changed text has a new
fingerprint and translates normally. Buying replacements needs a separate,
explicit change to the loss acknowledgement that keeps the usage receipt. That
receipt moved from the Google-era guard ledger to
`data/i18n/static_runs.json` when Google was removed. Its character counts are from the Google era and are not
dollars.

## Troubleshooting

- **`/ko/` shows English cards.** Look for `localized_feed_budget_cap_reached` in
  the feed run's log. If it is there, compare `usd` in
  `data/i18n/translation_spend.json` with the cap, and read `history` for which
  surface spent it. Raise the cap (section 1) or wait for the month to roll over.
  If it is not there, the cards are new since the last run, or a card failed and
  will be retried.
- **Turn the Korean cards off.** Set `LOCALIZED_FEED_ENABLED=0` in
  `worker/wrangler.jsonc` and deploy. `/api/feed?locale=ko` then returns plain
  English. `run_full.sh` skips the builder when `LOCALIZED_FEED_ENABLED` is not `1` in the pipeline's
  environment, which stops the spend.
- **A run says it cannot authenticate.** Check that the job has `id-token: write`
  and runs on `main`, that the OIDC step succeeded, and that the ids in the
  workflow match the federation rule.
- **`ValueError: no price for model`.** Add the model to `translator.PRICES`.
- **Static pages stay untranslated.** Candidates must be missing or stale
  (`pipeline/export_i18n_candidates.py`), inside `--days`, and under `--limit`.
  Daily and weekly recaps are written by the recap routines and are skipped unless
  you pass `--surface daily` or `weekly`.
