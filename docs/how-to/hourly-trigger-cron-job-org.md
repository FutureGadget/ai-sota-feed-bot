# Reliable Hourly Trigger via cron-job.org

This runbook sets up an external, free, reliable hourly trigger for the
`feed-full-publish.yml` GitHub Actions workflow using [cron-job.org](https://cron-job.org).

## Why this exists
GitHub Actions `schedule` events are **best-effort**: scheduled runs are queued
on shared infrastructure, deprioritized under load, and whole hours are silently
dropped (see `docs/design-docs/decision-log.md`, 2026-06-14). The in-repo cron
was moved off `:00` to `37 * * * *` to dodge the worst congestion, but GitHub
still does not guarantee hourly. This external ticker calls the workflow's
`workflow_dispatch` endpoint on a real hourly tick, independent of GitHub's
schedule queue.

- **Vercel Cron was rejected:** free on Hobby but capped at **once per day**
  (hourly expressions fail at deploy); hourly needs the $20/mo Pro plan.
- **cron-job.org** is free, requires no infrastructure, and fires reliably.

The GitHub `schedule` (`37 * * * *`) stays as a baseline fallback — having both
is harmless because the pipeline short-circuits on no-delta and is guarded by a
lock dir + concurrency group, so overlapping triggers no-op cleanly.

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
3. **Title:** `llm-digest hourly feed publish`.
4. **URL:**
   ```
   https://api.github.com/repos/FutureGadget/ai-sota-feed-bot/actions/workflows/feed-full-publish.yml/dispatches
   ```
5. **Schedule:** *Every hour* — i.e. every day, every hour, at minute `0`
   (cron-job.org's pattern editor: minutes = `0`, hours = `*`).
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
4. After a few hours, the run list should show roughly hourly `workflow_dispatch`
   runs interleaved with any `schedule` runs that still fire.

---

## 4) Operations

- **Monitoring:** cron-job.org emails on repeated failures (enable in the job's
  notification settings). The most likely failure is **PAT expiry**.
- **Rotation:** when the PAT nears expiry, generate a new one (step 1) and update
  the `Authorization` header (step 2). No repo change needed.
- **Pause:** disable the cron-job.org job to stop external triggering; GitHub's
  `:37` schedule continues as fallback.
- **Rollback (remove entirely):** delete the cron-job.org job and revoke the PAT.
  Nothing in the repo references this trigger, so there is no code to revert —
  the workflow's own `schedule:` keeps it running best-effort.

## Related
- `.github/workflows/feed-full-publish.yml` — the dispatched workflow.
- `docs/design-docs/decision-log.md` — 2026-06-14 entries (cron `:37` move; this trigger).
