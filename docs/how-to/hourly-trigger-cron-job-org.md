# Reliable Workflow Triggers via cron-job.org

This runbook sets up external, free, reliable cron triggers for GitHub Actions
workflows using [cron-job.org](https://cron-job.org). Currently used for:

- **Feed publish** (`feed-full-publish.yml`) — every two hours
- **Email digest** (`email-digest.yml`) — daily at 23:00 UTC (08:00 KST) + weekly Friday at 23:00 UTC (Saturday 08:00 KST)

## Why this exists
GitHub Actions `schedule` events are **best-effort**: scheduled runs are queued
on shared infrastructure, deprioritized under load, and whole hours are silently
dropped (see `docs/design-docs/decision-log.md`, 2026-06-14). The in-repo cron
was moved off `:00` to `37 * * * *` to dodge the worst congestion, but GitHub
still does not guarantee a dependable cadence. This external ticker calls the
workflow's `workflow_dispatch` endpoint on a real two-hour tick, independent of GitHub's
schedule queue.

- **Vercel Cron was rejected:** free on Hobby but capped at **once per day**
  (hourly expressions fail at deploy); hourly needs the $20/mo Pro plan.
- **cron-job.org** is free, requires no infrastructure, and fires reliably.

The GitHub `schedule:` trigger has been **removed** from both workflows —
cron-job.org is the sole trigger. The workflows only expose `workflow_dispatch`.

---

## 1) Create a GitHub fine-grained Personal Access Token

The ticker authenticates as you to dispatch the workflow. Use a **fine-grained**
PAT scoped to *only this repo* with the minimum permission.

1. GitHub → Settings → Developer settings → **Fine-grained tokens** → *Generate new token*.
2. **Resource owner:** `FutureGadget`.
3. **Repository access:** *Only select repositories* → `FutureGadget/ai-sota-feed-bot`.
4. **Repository permissions:** **Actions → Read and write**. (Leave everything
   else "No access". `workflow_dispatch` requires Actions: write.)
5. **Expiration:** pick a date you'll remember to rotate (e.g. 90 days). Set a
   calendar reminder — when it expires the trigger silently stops and you fall
   back to GitHub's best-effort `:37` schedule.
6. Generate and **copy the token** (`github_pat_…`). You won't see it again.

> ⚠️ This token is a secret. It lives only in cron-job.org — never commit it,
> and never paste it into the repo.

---

## 2) Create the cron job on cron-job.org

1. Sign up / log in at [cron-job.org](https://console.cron-job.org).
2. **Create cronjob**.
3. **Title:** `llm-digest feed publish`.
4. **URL:**
   ```
   https://api.github.com/repos/FutureGadget/ai-sota-feed-bot/actions/workflows/feed-full-publish.yml/dispatches
   ```
5. **Schedule:** *Every two hours* at minute `0`
   (cron-job.org's pattern editor: minutes = `0`, hours = `*/2`).
6. Expand **Advanced settings**:
   - **Request method:** `POST`
   - **Headers** (add each as a key/value):
     | Header | Value |
     |---|---|
     | `Accept` | `application/vnd.github+json` |
     | `Authorization` | `Bearer github_pat_…` (your token from step 1) |
     | `X-GitHub-Api-Version` | `2022-11-28` |
     | `User-Agent` | `cron-job.org` |
   - **Request body:**
     ```json
     {"ref":"main"}
     ```
   - **Treat as success:** HTTP status `200-299`. A successful dispatch returns
     **`204 No Content`** with an empty body.
7. **Save** and enable.

> `User-Agent` is required — GitHub's API rejects requests without one.

---

## 3) Verify

1. In cron-job.org, use **Run now** (or **Test run**) on the job.
2. Expect HTTP **204**. (Common failures: `401` = bad/expired token; `403` =
   token missing Actions:write or wrong repo scope; `404` = workflow filename or
   `owner/repo` typo; `422` = bad `ref` or malformed JSON body.)
3. In GitHub → Actions → **AI Feed Full Publish**, confirm a new run appears
   with event **`workflow_dispatch`** (not `schedule`).
4. After several hours, the run list should show one `workflow_dispatch` run
   about every two hours.

---

## 4) Operations

- **Monitoring:** cron-job.org emails on repeated failures (enable in the job's
  notification settings). The most likely failure is **PAT expiry**.
- **Rotation:** when the PAT nears expiry, generate a new one (step 1) and update
  the `Authorization` header (step 2). No repo change needed.
- **Pause:** disable the cron-job.org job to stop external triggering. The feed
  workflow has no in-repository `schedule:` fallback.
- **Rollback (remove entirely):** delete the cron-job.org job and revoke the PAT.
  To keep publishing, first restore a GitHub `schedule:` trigger or arrange a
  replacement dispatcher.

---

## Email Digest Trigger

The email digest workflow (`email-digest.yml`) is dispatched on UTC crons
(daily `0 23 * * *`, weekly `0 23 * * 5`) chosen so the mail lands at 08:00 KST
(Seoul morning). cron-job.org is the sole trigger; adding these jobs guarantees
the email sends reliably. The workflow's idempotency guard (cursor in
`data/email/state.json`) makes duplicate triggers safe — the script no-ops
when the recap has already been sent.

### Job 1: Daily email digest (23:00 UTC -> 08:00 KST)

1. **Title:** `llm-digest daily email`
2. **URL:**
   ```
   https://api.github.com/repos/FutureGadget/ai-sota-feed-bot/actions/workflows/email-digest.yml/dispatches
   ```
3. **Schedule:** Every day at 23:00 UTC
   (cron-job.org pattern: minutes = `0`, hours = `23`).
4. **Request method:** `POST`
5. **Headers:** same four as the hourly feed job (reuse the same PAT).
6. **Request body:**
   ```json
   {"ref":"main","inputs":{"kind":"daily"}}
   ```
7. Save and enable.

### Job 2: Weekly email digest (Friday 23:00 UTC -> Saturday 08:00 KST)

1. **Title:** `llm-digest weekly email`
2. **URL:** same as Job 1.
3. **Schedule:** Every Friday at 23:00 UTC
   (cron-job.org pattern: minutes = `0`, hours = `23`, day of week = `5`/Friday).
4. **Request method:** `POST`
5. **Headers:** same four.
6. **Request body:**
   ```json
   {"ref":"main","inputs":{"kind":"weekly"}}
   ```
7. Save and enable.

### Verify

Same procedure as the hourly feed job:
1. **Run now** on each job → expect HTTP **204**.
2. In GitHub → Actions → **AI Feed Email Digest**, confirm new
   `workflow_dispatch` runs appear.
3. The `inputs.kind` value drives mode selection, bypassing the cron-expression
   sniffing in the workflow (the `INPUT_KIND` env var takes priority).

### Notes

- The same GitHub PAT works for all three jobs (it has Actions:write on the repo).
- The GH `schedule:` entries have been **removed** from both workflows.
  cron-job.org is the sole trigger. If you need to pause email sends, disable
  the jobs on cron-job.org (or trigger manually via `workflow_dispatch`).

---

## Related
- `.github/workflows/feed-full-publish.yml` — the hourly feed workflow.
- `.github/workflows/email-digest.yml` — the email digest workflow.
- `docs/design-docs/decision-log.md` — 2026-06-14 entries (cron `:37` move; this trigger).
