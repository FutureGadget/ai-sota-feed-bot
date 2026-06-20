# Email digest (subscribe → daily brief → weekly recap)

A subscribe-by-email channel that pushes the **finishable daily brief** and the
**weekly recap** straight to an AI platform engineer's inbox — the channel where
this persona actually does morning triage. Today's distribution (a GitHub Issue
and an optional Telegram post) does not serve the "read this every morning, 10
minutes a day" job; email does, and it is the missing **retention loop** on top
of an already-strong engine.

This serves all three positioning pillars at once:

- **Finishable** — a bounded, ranked brief with a hard "you're caught up" end
  marker, in the inbox, vs. an infinite feed you must remember to visit.
- **Transparent / anti-hype** — the same deterministic ranking, 🫧 hype flags,
  source reliability, and Reader-boosted badges carried into the email; no
  per-recipient personalization (see "What we deliberately do NOT do").
- **Memory** — the email is the *push* channel for storylines ("what happened
  next with X") and the weekly "what you missed," which are far stronger as a
  send than as a page the reader has to navigate to.

## What we deliberately do NOT do

- **No subscriber PII in git.** The repo is public and has no database. A
  third-party newsletter provider (Buttondown or Resend) owns the subscriber
  list, double-opt-in, unsubscribe, and CAN-SPAM/GDPR compliance. We only hold
  an API key in env/secrets and call the provider's broadcast endpoint.
- **No topic personalization.** Cadence preference (daily vs. weekly-only) is
  allowed; per-reader topic filtering is not — it would violate the "one shared
  ranking, not a filter bubble" stance. Pinned topics remain a client-side lens
  on the site, not an email segmentation key.
- **No hourly email.** The hourly pipeline keeps committing data; email sends on
  its own daily/weekly schedule reading whatever is already committed.

## Contents

### Daily brief (morning cron)

Sourced from `data/processed/latest.json` (+ `data/digest/<date>.md`), reusing
the item helpers in `publish/publish_telegram.py` (`signal_label`, `short_why`,
hype flag, Reader-boosted badge).

1. **Subject** that sells finishable:
   `Your AI brief — {N} items · ~{mins} min · {top headline}`.
2. **Ranked top items** (cap ~12): title → `/story/<sid>` permalink, source +
   reliability, one-line *why-it-matters*, 🫧 hype flag and *Reader-boosted*
   badge where present.
3. **Continuing threads** (1–3): storylines that **moved since the last send**
   (see "Change detection") — each shows the narrative `whats_new` line and a
   `/storyline/<slug>` link. Change-driven, so it never repeats a quiet thread.
4. **Hard end marker** — `✅ You're caught up` — reinforces *finishable*.
5. **Footer** — full feed, this week's recap, manage-subscription (provider).

The knowledge map is **not** in the daily brief — it moves slowly and is
evergreen, so it would dilute finishability.

### Weekly recap (Friday cron)

Sourced from `data/weekly/<week>.json` (the `/weekly` page as a push):

1. **Week rollup** — top storylines of the week, categorized highlights,
   "what you missed."
2. **Storylines that moved this week** — the full set of thread deltas since the
   last weekly send (not just 1–3).
3. **New in the knowledge map** — new obstacle areas / solutions added this week,
   each with a `/topic/<slug>` link, sourced from the `data/wiki/log.md` entries
   (and per-node `updated`) since the last weekly send. This is differentiated,
   evergreen content — it answers "what did we *learn* this week," which nothing
   else in the inbox does.

## Change detection (storylines + knowledge map)

Both surfaces rebuild on noisy cadences (storylines every 5h, wiki per curator
run), so the email must surface **only what genuinely moved** since the last
send — using the **content-based** timestamps that already power the nav "new
updates" dots (`api/updates.js`), never `generated_at`.

| Surface | "Did it move?" signal | "What's new" copy | Link |
|---|---|---|---|
| Storyline | `index.json` entry `last_updated` + new `member_sids` | narrative sidecar `editorial.whats_new` (fallback `latest_title`) | `/storyline/<slug>` |
| Knowledge map | node `updated` (and `data/wiki/log.md` lines) | the `log.md` note for the slug | `/topic/<slug>` |

> The trap `api/updates.js` warns about: **never key off `generated_at`** — the
> 5-hourly storyline rebuild and every wiki compile bump it, so the email would
> announce "new!" on every send. Diff on `last_updated` (storylines) and per-node
> `updated` / `log.md` (wiki).

**Narration-lag guard.** The storyline editor routine can trail a thread by up
to 5h. If a thread's `last_updated` moved but the sidecar's `covers_last_updated`
is older (narrative not refreshed yet), fall back to `latest_title` or hold the
thread for the next send — never ship a "new" badge over stale narration.

### Send cursor (the only new state)

To avoid repeats, the send step remembers what subscribers were last told. This
is **not PII**, so it lives in git as committed runtime state —
`data/email/state.json` — exactly mirroring how `data/health/alerts_state.json`
prevents re-alerting. The email workflow commits the bumped cursor after a
successful send.

```json
{
  "daily":      { "last_sent_date": "2026-06-19" },
  "weekly":     { "last_sent_week": "2026-W24" },
  "storylines": { "sent_through": "2026-06-18T11:47:13+00:00",
                  "seen_sids": ["c5cd09a4f478ae3e", "…"] }
}
```

**Daily** "Continuing threads": a storyline qualifies only when
`last_updated > storylines.sent_through` **and** it has `member_sids` not in
`seen_sids`; the cursor advances on each successful daily send.

**Weekly** "Storylines that moved this week" / "New in the knowledge map" are
**window-based**, not cursor-based: they select threads (`last_updated`) and wiki
nodes (`updated`) inside the recap's `[start, end]`. The daily send advances the
shared `storylines` cursor every day, so a cursor-based weekly would be starved
by Friday; windowing also matches the recap period and lets a thread appear in
both a daily ("new today") and the Friday roundup ("what happened this week") —
intended. So the weekly cursor stores only `last_sent_week` (idempotency); there
is no wiki high-water mark.

## Architecture

- **Subscribe surface.** `api/client-config.js` already exposes a
  `DIGEST_EMAIL_SIGNUP_URL` hook; the subscribe CTA renders only when it is set.
  - *v0 (zero code):* point it at a provider-hosted form → acquisition live.
  - *v1 (in-page):* `api/subscribe.js` holds the provider key server-side, POSTs
    the address to the provider (triggers double-opt-in); add `/api/subscribe` to
    `vercel.json` rewrites and a small footer form in the page shells. Honeypot
    field + basic validation; double-opt-in is the real abuse guard.
- **List + compliance.** The provider. Nothing in git.
- **Send.** `publish/publish_email.py`, mirroring `publish/publish_telegram.py`
  (same artifact inputs, same secrets-gated no-op: return cleanly when
  `EMAIL_API_KEY` is unset). Renders email-safe HTML and calls the provider's
  **broadcast** endpoint (the provider fans out and appends the unsubscribe
  footer).
- **Schedule.** `.github/workflows/email-digest.yml` — a **daily** morning cron
  (brief) and a **Friday** cron (recap). Secrets-gated; no-ops without keys.
- **Attribution.** Every email link carries `?utm_source=email` (or routes
  through `/s?u=`) so clicks attribute into the existing PostHog / CTR →
  `auto_tune` loop. Otherwise we go blind on the best channel.

## Validation

- `python3 publish/publish_email.py --dry-run` renders both emails from the live
  `data/` tree to stdout/HTML without sending (no `EMAIL_API_KEY` ⇒ no-op send).
- Cursor round-trip: run twice against an unchanged tree ⇒ the second run emits
  **no** "Continuing threads" / "New in the knowledge map" (no repeats); advance
  a storyline's `last_updated` and confirm exactly that thread reappears.
- `node --check api/subscribe.js` (when added); subscribe POST hits the provider
  sandbox and returns a pending-confirmation state.
- Confirm no email send is wired into `run_full.sh` / the hourly workflow.
