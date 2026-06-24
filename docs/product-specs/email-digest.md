# Email digest (subscribe → daily brief → weekly recap)

A subscribe-by-email channel that pushes the **finishable daily brief** and the
**weekly recap** straight to an AI platform engineer's inbox — the channel where
this persona actually does morning triage. Website-only discovery does not serve
the "read this every morning, 10 minutes a day" job; email is the supported
**retention loop** on top of an already-strong engine.

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
  allowed — and **is** a signup choice (see *Per-digest selection* below) — but
  per-reader *content* filtering is not; that would violate the "one shared
  ranking, not a filter bubble" stance. Pinned topics remain a client-side lens
  on the site, not an email segmentation key. The cadence choice maps to which
  digests a reader receives, never to which stories appear inside one.
- **No hourly email.** The hourly pipeline keeps committing data; email sends on
  its own daily/weekly schedule reading whatever is already committed.

## Contents

### Daily brief (post-recap morning cron)

Sourced from **`data/daily/latest.json`** — the *same curated recap the `/daily`
page serves* (decided 2026-06-23; previously the raw ranked feed
`data/processed/latest.json`). The email and the page now show one editorial
recap, so a reader who clicks through sees more of what hooked them, not a
different-looking firehose. The recap is written by the `daily-summary` agent
routine (intro, highlights, themed categories); the email renderer in
`publish/publish_email.py` mirrors the page's intro → "In 30 seconds" highlights
→ themed categories.

1. **Subject** that sells finishable:
   `Your AI brief — {N} picks · ~{mins} min · {top headline}`.
2. **Editorial lead** — the recap's `intro` paragraphs and an **"In 30 seconds"**
   TL;DR built from `highlights` (the same lead the `/daily` page shows).
3. **Themed categories** — each recap category (name + summary) with its
   articles: title → `/story/<sid>` permalink, source, the one-line recap
   summary, and a one-tap 👍/👎 feedback link (feeds the auto-tune loop).
4. **Continuing threads** (1–3): storylines that **moved since the last send**
   (see "Change detection") — each shows the narrative `whats_new` line and a
   `/storyline/<slug>` link. Change-driven, so it never repeats a quiet thread.
5. **Hard end marker** — `✅ You're caught up` — reinforces *finishable*.
6. **Footer** — read on the web (`/daily/<date>`), full feed, this week's
   recap, manage-subscription (provider).

The knowledge map is **not** in the daily brief — it moves slowly and is
evergreen, so it would dilute finishability.

**Idempotency keys off the recap's date, not the calendar day.** The send guard
compares `data/email/state.json` → `daily.last_sent_date` to the recap's own
`date`: the latest committed recap sends once and re-sends only when a *newer*
recap appears. If no new recap exists (the agent routine has not run), the send
is a **clean no-op** — it never falls back to mailing the raw feed. The cron
runs at 01:30 UTC (10:30 KST), after the 09:00 KST daily recap routine, so the
email normally sends the prior UTC day's just-completed curated recap.

### Weekly recap (post-recap Saturday cron)

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

- **Subscribe surface.** Two paths, picked by which env is configured:
  - *In-page (Resend, shipped):* `api/subscribe.js` holds the Resend key
    server-side and POSTs the address to the global `/contacts` endpoint —
    Resend contacts are global, so **registration needs only `EMAIL_API_KEY`**,
    no segment id (sending targets a Segment, formerly "Audience").
    `api/client-config.js`
    exposes `digest.email_subscribe_enabled`. The canonical `/subscribe` page
    renders the form when it is true, or links to
    `digest.email_signup_url` when an external provider is configured. The
    homepage subscribe menu keeps the same inline form as a fast path. All
    other user-facing subscription CTAs route to `/subscribe`; RSS remains
    available through autodiscovery and its direct endpoint but is not promoted
    as a competing subscription action. Successful in-page signup stores
    `ai_feed_email_subscribed_v1=1` locally to suppress promotional nudges.
    Honeypot + email validation; single opt-in (Resend carries unsubscribe).
    `/api/subscribe`
    is filesystem-routed (no rewrite); a `functions` entry excludes `data/**`.
  - *External page (e.g. Buttondown):* set `DIGEST_EMAIL_SIGNUP_URL` and the menu
    links out instead. The in-page form is suppressed when this is set.
- **Per-digest selection (Resend Topics).** The `/subscribe` form offers an
  explicit two-way cadence choice (radio buttons): **"Daily brief + \<weekday\>
  recap"** (default) or **"\<weekday\> recap only — less email"**. The selection
  maps to the same `weekly_only` boolean as before (the second option sets it
  true); explicit radios replace the prior opt-down checkbox, whose unchecked
  state was easy to misread.
  - *Timezone-adaptive labels.* The recap weekday and the daily time-of-day are
    rendered client-side from the reader's own timezone, not hardcoded. The
    sends are fixed UTC crons (daily 01:30 UTC; weekly **Saturday 05:30 UTC** —
    see `.github/workflows/email-digest.yml`), but that instant is a different
    local weekday/time per reader (Sat 05:30 UTC is Sat 14:30 in Seoul yet Fri
    22:30 in Los Angeles), so a hardcoded weekday would be wrong somewhere.
    `web/subscribe.html` computes the upcoming Saturday-05:30-UTC instant and the
    daily-01:30-UTC instant, formats the local weekday (English,
    `Intl.DateTimeFormat`) and a time-of-day word (morning/afternoon/evening/
    night from the local hour), and fills the `[data-weekly-day]`,
    `[data-weekly-day-plural]`, and `[data-daily-time]` spans plus the
    form/success copy. Falls back to neutral "weekly"/"weekends"/"morning" if
    `Intl` throws. **Note:** these instants mirror the workflow crons — if the
    `email-digest.yml` schedule changes, update `SEND_SCHEDULE`.
  Daily and weekly are modelled as two Resend **Topics**
  (`EMAIL_TOPIC_ID_DAILY`, `EMAIL_TOPIC_ID_WEEKLY`):
  - *Signup* (`api/subscribe.js`) opts the contact into the **weekly** topic
    always, and into the **daily** topic with `status: opt_in` unless
    `weekly_only` is set, in which case `status: opt_out`.
  - *Send* (`publish_email.py` → `resolve_topic_id(kind)`) scopes each broadcast
    to its kind's topic, so Resend suppresses the daily send for weekly-only
    contacts and the hosted preference page manages the choice thereafter.
  - *Fallback:* with the per-kind ids unset, both sides fall back to the legacy
    single `EMAIL_TOPIC_ID` (both digests, one topic) — the prior behavior.
    Topics are why the cadence choice never touches *content*: it selects which
    broadcasts reach a reader, not which stories sit inside one.
- **List + compliance.** The provider. Nothing in git.
- **Send.** `publish/publish_email.py` reads committed artifacts and uses a
  secrets-gated no-op: it returns cleanly when `EMAIL_API_KEY` is unset.
  It renders email-safe HTML and calls the provider's
  **broadcast** endpoint (the provider fans out and appends the unsubscribe
  footer).
- **Schedule.** `.github/workflows/email-digest.yml` — a **daily** post-recap
  morning cron (brief) and a **Saturday** post-recap cron (weekly recap).
  Secrets-gated; no-ops without keys.
- **Attribution.** Every email link carries `?utm_source=email` (or routes
  through `/s?u=`) so clicks attribute into the existing PostHog / CTR →
  `auto_tune` loop. Otherwise we go blind on the best channel.

## Subscribe page design (redesigned 2026-06-21)

`/subscribe` (`web/subscribe.html`) belongs to the "AI operations instrument"
family but is a **conversion utility first** — clarity and trust outrank novelty.

- **One bold move: the signup panel.** An accent-ruled, washed, square panel
  (not a rounded card) placed directly under the hero so the email field and the
  accent **Subscribe** button are the unmistakable action. Everything else stays
  quiet.
- **No generic feature cards.** The previous three benefit cards are replaced by
  a **"what arrives" delivery spec** — hairline rows naming the real deliverables
  (the daily brief, the Friday recap, the one transparent ranking) with their
  cadence as a monospace label and a **"see a sample" link** into the live
  `/daily`, `/weekly`, and `/` pages, so the reader can preview the product
  before subscribing (clarity + trust).
- **Behavior preserved, states verified.** The redesign is CSS + markup only; the
  signup JS is unchanged. All states were exercised against real code paths
  (mocked responses, never a page-level fake success): configured form,
  provider-config **external-signup** fallback (`digest.email_signup_url`,
  `target=_blank rel=noopener`), **unavailable** (the natural local state when
  `/api/client-config` is absent), **submitting**, **success** (sets
  `ai_feed_email_subscribed_v1` + `ai_feed_subscribe_nudge_done_v1`, disables the
  field, removes the button), client-side **validation-error**, and **API-error**
  (button re-enabled for retry). Honeypot, email validation, status messages, the
  privacy/provider copy, and the local-storage keys are intact. Light/dark themes,
  visible keyboard focus, an email-field focus ring, reduced motion, and 50px
  touch targets are covered. No editorial-skill change. Regression coverage:
  `tests/test_subscribe_surface.py`.

## Validation

- `python3 publish/publish_email.py --dry-run` renders both emails from the live
  `data/` tree to stdout/HTML without sending (no `EMAIL_API_KEY` ⇒ no-op send).
  The daily renders from `data/daily/latest.json`; with no recap committed it
  prints `email_send_skipped=true kind=daily reason=no_recap` and never the feed.
- Cursor round-trip: run twice against an unchanged tree ⇒ the second run emits
  **no** "Continuing threads" / "New in the knowledge map" (no repeats); advance
  a storyline's `last_updated` and confirm exactly that thread reappears.
- `node --check api/subscribe.js`; API tests cover invalid input, success,
  duplicate/idempotent signup, provider failure, and network failure.
- Render static pages and confirm subscription links resolve to `/subscribe`,
  `/subscribe` is in the sitemap, and no generated page carries `/#subscribe`
  or a visible RSS subscription CTA.
- Confirm no email send is wired into `run_full.sh` / the hourly workflow.
