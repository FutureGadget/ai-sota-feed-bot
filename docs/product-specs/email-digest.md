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
runs at 23:00 UTC (08:00 KST next morning), after the 06:00 KST daily recap
routine, so the email lands in the reader's inbox by 8am Seoul time. Because
08:00 KST is *before* the UTC date rollover (09:00 KST), the recap built that
morning covers the last *complete* UTC day — i.e. the brief intentionally trails
the freshest possible UTC day by one, in exchange for the earlier delivery slot.

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
  "weekly":     { "last_sent_week": "2026-W24",
                  "sent_skill_lab_ids": ["lab-protocol"] },
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
intended. Weekly storyline/wiki selection therefore has no high-water mark;
`last_sent_week` remains the recap idempotency guard.

The Agent Skill Lab pilot is the one additive weekly cursor. A Lab record can
be published just after Friday's send, so strict recap-window selection could
drop it forever. The sender therefore selects the newest unsent Lab record whose
date is no later than the recap end and whose `featured_until` still covers that
end. After a successful broadcast, its bounded ID is appended to
`weekly.sent_skill_lab_ids`. This state is PII-free and capped to the four pilot
records. Before selection, the sender runs the same read-only full-store check
as deployment, including the contiguous protocol-first edition sequence,
source/index digests, derived snapshots, and local artifact availability. Daily
email, storyline windowing, and wiki windowing are unchanged.

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
    sends are fixed UTC crons (daily 23:00 UTC; weekly **Friday 23:00 UTC** —
    see `.github/workflows/email-digest.yml`), but that instant is a different
    local weekday/time per reader (Fri 23:00 UTC is Sat 08:00 in Seoul yet Fri
    15:00 in Los Angeles), so a hardcoded weekday would be wrong somewhere.
    `web/subscribe.html` computes the upcoming Friday-23:00-UTC instant and the
    daily-23:00-UTC instant, formats the local weekday (English,
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
- **Reader identity (2026-09-24, Resend only).** Every tracked on-site link
  also carries `rid={{{contact.reader_id|none}}}`, a per-contact Resend
  property. `api/subscribe.js` sets it at signup to the signup browser's
  anonymous id (or mints one); `publish/backfill_reader_ids.py` backfills
  older contacts once. `web/posthog-client.js` adopts a valid `rid` as the
  browser's reader id and strips it from the URL, so a subscriber reading from
  a mail app's in-app browser stays one reader across weeks instead of a new
  one per click. The send ensures the property exists first and falls back to
  untagged links on any provider error (`email_reader_links=on|off`). Toggle:
  `config/email.yaml → reader_id_links`.

## Storyline follow alerts (2026-09-24)

Per-story emails for readers who followed a storyline by email — see
`docs/product-specs/storylines.md` ("Follow by email") for the full contract.
They run after the daily digest (`publish/publish_follows.py`, `config/email.yaml
→ follows.enabled`), use batch transactional sends rather than broadcasts
(per-follower content), and keep their own cursor `follows.sent_through`.

## Inline signup at finish points (2026-09-24)

The finish-point CTAs — the feed's "You're all caught up" marker
(`feed_finish`) and the ends of story, daily, weekly and storyline pages
(`story_end`, `daily_end`, `weekly_end`, `storyline_end`) — carry
`data-subscribe-inline`. `web/subscribe-inline.js` (loaded by `web/index.html`
and the static page template) swaps each one for an in-place email form, so the
ask lands where the reader just got value, without a second page load.

- **Progressive enhancement.** The CTA stays a plain `/subscribe` link unless
  `/api/client-config` reports `digest.email_subscribe_enabled` and no external
  `digest.email_signup_url`; any failure keeps the link.
- **Same contract as `/subscribe`.** Posts `{ email, weekly_only: false, hp,
  reader_id }` to `/api/subscribe`; a filled honeypot gets the neutral success
  UI without counting; success sets `ai_feed_email_subscribed_v1` and the
  nudge-done key. "weekly only" links to `/subscribe` for the cadence choice.
- **Already subscribed.** When this browser is marked subscribed, the CTA is
  hidden instead of asking again.
- **Measurement.** `subscribe_form_view` fires once per placement when the form
  is half in view; `subscribe_success` carries `placement` and
  `surface: "inline"`, so conversion per finish point is
  `subscribe_success / subscribe_form_view`.
- The feed re-renders its finish marker on filter changes; a
  `MutationObserver` enhances CTAs as they appear.
- **Visual treatment (instrument family).** The form borrows the `/subscribe`
  panel rather than inventing a new component: square field and button joined
  edge to edge, 46 px targets, accent spent once (the button), monospace
  utility fine print ("Daily + weekly · unsubscribe anytime · Weekly only →"),
  a visible focus ring, and dark ink on the button in dark mode (white on the
  light dark-theme accent fails contrast). Static-page CTAs are square
  accent-ruled washes with the form on its own line under the heading; the
  feed's finish line adds a monospace kicker ("The next brief, by email")
  because it has no heading of its own. Styles live in `web/site-chrome.css`.

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

## Layout (2026-11-19)
- **Subject** leads with the news: the daily's top story then
  `· {N} picks, ~{mins} min`; the weekly's first highlight then
  `· Your AI week, {range}` (Korean: `· {N}개, 약 {mins}분`, `· AI 위클리 {range}`).
- **Order:** header (readable date), 30-second summary, video link, intro,
  the community card, then the themes, continuing threads, the "caught up"
  marker, a "Forward it" mailto link, and the footer. The weekly puts the
  community card right after its highlights.
- **Length:** each theme shows its first `daily.full_items_per_theme`
  (`config/email.yaml`, default 2) items with their summary; the rest are
  one-line headlines under "Also in this theme".
- **Feedback:** the 👍 / 👎 links sit on each item's source line (words on
  full items, icons on headline rows), so every item still feeds the
  auto-tune loop without a row of its own. They are dropped from the
  plain-text part.
- **Type:** body text 15–16px, item titles 16–17px, footer 13px.
- **Reading time** (`reading_minutes`): words the brief itself shows (summary,
  intro, themes; not feedback links, storylines or the footer) at about 230
  space-separated words a minute, so English and Korean agree.
- **Storylines** ("Storylines that moved today" / "this week"): each row links
  the thread's newest story title (the cluster label is a machine keyword),
  adds the narrative's what-happened-next when it differs, and a
  "Storyline · N stories over D days" line. The Korean edition shows only rows
  whose narrative is in Korean and drops the section when none are.
- **Click attribution:** every tracked site link carries `utm_medium=email`,
  `utm_campaign=<kind>-<id>-<locale>` (e.g. `daily-2026-11-18-ko`) and
  `utm_content` for its section: `story` (items with a summary), `headline`
  (one-line items), `community`, `storylines`, `wiki`, `video`, `footer`.
  PostHog records these on the landing page view, so per-issue and
  per-section clicks are a breakdown away; feedback links keep their `fb=`.
- **Dark mode:** the email is a full HTML document that declares
  `color-scheme: light dark`; `add_dark_classes` tags every inline colour
  with a class that a `prefers-color-scheme: dark` block restyles. Clients
  that ignore the media query keep the light design or invert it themselves.
- **Footer:** web/feed/week links, the language switch, "Manage preferences or
  unsubscribe" (Resend's per-contact page, which also holds the daily/weekly
  choice), and "You're getting this because you subscribed at llm-digest.com."
  Resend Broadcasts add the List-Unsubscribe headers themselves.

## Send times and welcome email (2026-11-19, send times revised 2026-11-20)
- **Send times:** two. The original send at 23:00 UTC (08:00 KST; weekly
  Friday 23:00 UTC) goes to every Korean reader and to English readers on the
  original time, which includes every subscriber from before the choice
  existed, so nobody's delivery time changed. English readers can pick the
  US-morning send at 11:30 UTC (06:30 EST / 07:30 EDT; weekly Saturday 12:00
  UTC), which goes to the `EMAIL_SEGMENT_ID_EN_US` segment. Korean has one
  send time. One cron-job.org job per send time passes `inputs.slot`
  (`docs/how-to/hourly-trigger-cron-job-org.md`); no `slot` means the original
  send. Storyline follow alerts ride the original daily run only.
- **Editions and cursors:** `publish_email.py` builds one edition per language
  and send time (`EDITIONS`): `daily`/`weekly` (English, original),
  `daily_ko`/`weekly_ko`, and `daily_en_us`/`weekly_en_us`, each with its own
  already-sent cursor. The US-morning edition also keeps its own storyline
  cursor (`storylines_en_us`, seeded from the shared one) and Skill Lab ids,
  so the earlier send does not use them up.
- **Choosing a time:** `/subscribe` shows a Delivery time choice for English
  once `/api/client-config` lists `email_send_slots: ["kst","us"]` (that is,
  once `EMAIL_SEGMENT_ID_EN_US` is set in the Worker). Each option is labelled
  in the reader's own clock ("8:00 AM" / "8:30 PM" in Seoul, "6:00 PM" /
  "6:30 AM" in New York), and the default is the one that lands in their
  morning, or else arrives overnight. `?time=kst|us` preselects one.
  `api/subscribe.js` puts the contact in the matching segment; an existing
  subscriber who signs up again with another time (or language) is moved,
  joining the new segment first and then leaving every other edition segment.
- **Switching from an email:** English footers link to `/subscribe` with the
  other time preselected ("Get it in the US morning instead (11:30 UTC)" /
  "Get it at 8:00 Seoul time instead (23:00 UTC)"), shown once the US segment
  exists.
- **Welcome email:** `api/subscribe.js` sends one welcome email when a signup
  creates a new contact (never on a re-subscribe), in the signup's language:
  what arrives and when (daily brief, weekly recap, storyline memory;
  weekly-only signups hear about the weekly only), one button to the latest
  brief or recap, and where to switch to weekly only or unsubscribe. A card
  layout with light and dark mode, in the digest's palette. No "add us to your
  contacts" and no reply prompt. Best-effort: a failed send never fails the
  signup. Needs `EMAIL_FROM` in the Worker (`worker/wrangler.jsonc` vars).

## Korean edition (2026-11-19)

Every daily and weekly send goes out in two editions. The English recap is the
single source; the Korean edition reads the agent-written translation of it.

- **Where the Korean text comes from.** The `daily-summary` and
  `weekly-summary` routines translate their own recap in the same run
  (`.agents/skills/recap-translation/`) into
  `data/i18n/ko/<kind>/<id>.json`, the artifact the `/ko/daily` and
  `/ko/weekly` pages already render. The community post's `ko` thread fills
  the community block. Storyline and Agent Know-How rows use their Korean page
  translation when one is fresh, and stay in English otherwise. Nothing is
  translated at send time.
- **Template.** Same layout as English with Korean labels, subject
  (`AI 브리프 — {N}개 · 약 {mins}분 · {headline}` / the Korean weekly title),
  and links to `/ko/daily/<date>`, `/ko/weekly/<week>`, `/ko/community/...`,
  `/ko/`. Story links stay on the English `/story/<sid>` permalink.
- **Korean line breaking.** The Korean edition's outer container carries
  `lang="ko"`, `word-break:keep-all` and Hangul fonts first, so lines break
  between words instead of mid-word (the same rule as the `/ko/` pages).
- **Fallback.** No fresh Korean recap for the edition → the Korean list gets
  the English email that day (`email_locale_fallback=en` in the log).
- **Recipients.** Korean readers are in the Resend segment
  `EMAIL_SEGMENT_ID_KO`; English readers stay in `EMAIL_SEGMENT_ID`. A contact
  is in one of the two. Daily/weekly Topics apply to both editions. Without
  `EMAIL_SEGMENT_ID_KO` the Korean send is skipped (`reason=no_segment`).
- **Signup.** `/subscribe` has a Language choice (English / 한국어),
  preselected by `?lang=ko` or a Korean browser; every Korean page links to
  `/subscribe?lang=ko`, and the inline form on Korean pages signs up for Korean.
  `api/subscribe.js` puts a `locale: "ko"` signup in the Korean segment, or in
  the English one when the Korean segment is not configured.
- **Switching editions.** An existing subscriber who signs up again with the
  other language is moved: `api/subscribe.js` adds the contact to the
  requested edition's segment, then removes it from the other one (join first,
  so a failure never leaves them with no edition; a failed join returns 502).
  Every email footer links to the signup page with the other language
  preselected (`/subscribe?lang=ko` from English, `?lang=en` from Korean) once
  `EMAIL_SEGMENT_ID_KO` is set, and the signup page says that re-subscribing
  switches.
- **Cursor.** Each edition has its own already-sent guard:
  `daily`/`weekly` (English) and `daily_ko`/`weekly_ko` in
  `data/email/state.json`. Editions send English first, then Korean; a Korean
  failure exits non-zero but never re-sends the English edition, and the
  workflow commits the cursor even when a step failed.
- **Preview.** `python publish/publish_email.py --kind daily --locale ko --dry-run`.
- **Test send.** Run the `AI Feed Email Digest` workflow by hand with
  `test_send: true` (and `kind`, `locale`). Each edition goes only to the
  `EMAIL_TEST_TO` repository secret as a normal Resend email with a
  `[TEST <kind> <locale>]` subject: no segment, no topic, no already-sent
  guard, no cursor change, no follow alerts. Locally:
  `EMAIL_TEST_TO=you@example.com python publish/publish_email.py --kind daily --test`.

