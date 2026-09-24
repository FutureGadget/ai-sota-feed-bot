# Storylines UX contract

Storylines answer one reader question: **what happened next?** They are a
finishable memory surface for platform and agent engineers, not an infinite
topic feed or an internal agent dashboard.

## Index

Each `/storylines` card should be decidable without reading a full recap:

1. specific storyline title;
2. lifecycle (`Active`, `Tracking`, `Quiet`, or editor-declared `Resolved`);
3. compact evidence counts and recency;
4. the latest consequential change;
5. an optional operational implication for builders;
6. a clear link to the full arc.

The index presents these as trace-ledger rows rather than independent cards.
Each row uses the same state colors and typography as the detail page, and may
show a compact state-history rail when `status.track` is available. The index
hero explains the continuity job; it does not repeat the product's generic
feed positioning.

The index does not promote clustering machinery. Scout/editor/fact-check
provenance belongs in the detail page's collapsed evidence section.

`Active`/`Tracking`/`Quiet` are presentation labels derived from
`last_updated`; they do not alter membership or retention. `Resolved` is an
editorial state (`status.tone == resolved`) because only editorial judgment can
say a developing event has actually ended.

## Detail page

The default reading order is:

1. **Current state** — where the tracked event stands.
2. **Latest change** — what moved since the prior beat.
3. **Builder action** — an operational action or decision.
4. **Earlier context** — collapsible chronological context.
5. **Evidence trace / Source timeline** — editorial beats with source evidence, or the raw
   date sequence.
6. **Open questions** — concrete facts worth watching.
7. **How this thread was built** — collapsed provenance.

The page should let a returning follower understand the delta before rereading
history. Avoid repeating the same launch/current-state facts in status,
`whats_new`, `tldr`, and the builder takeaway.

## Follow behavior

The Follow button itself is browser-local: the control must explain that
updated followed storylines appear on the Live feed. `/storylines` provides an
All/Following filter. The storage contract remains
`ai_feed_storyline_follows_v1`.

### Follow by email (2026-09-24)

Once a reader follows on a static `/storyline/<slug>` page, an inline form
offers "Get an email when this story moves" (`web/subscribe-inline.js`, only
when in-page email signup is enabled). It posts `{ email, slug, hp,
reader_id }` to `/api/subscribe` with `action: "follow"` (`lib/follow.js`), which:

- stores the slug in the Resend contact property `followed_storylines`
  (comma-separated, newest 25 kept) and adds the contact to the
  **"Storyline followers"** segment (created on first use, or
  `EMAIL_SEGMENT_ID_FOLLOWERS`);
- creates a new contact in that segment only — following a story never
  subscribes anyone to the daily/weekly digest.

`publish/publish_follows.py` runs after the daily digest in
`email-digest.yml`. It picks storylines whose `last_updated` passed
`data/email/state.json → follows.sent_through`, and sends each follower one
batch transactional email covering only the followed stories that moved (the
editor's `whats_new` when current, else the latest title). Every email carries
a signed per-story unfollow link, a "stop all story emails" link and a
one-click `List-Unsubscribe` header, all served by `GET|POST /api/subscribe?c=&s=&t=`
(HMAC keyed by `EMAIL_API_KEY`). Contacts that unsubscribed globally are
skipped. The first run only initializes the cursor. Browser state
`ai_feed_storyline_email_follows_v1` remembers email follows so the page shows
a confirmation instead of the form. Events: `follow_email_view`,
`follow_email_success`. The form sits under a hairline beneath the Follow
button with a monospace "Email alert · this story only" kicker, so it reads as
part of the Follow control rather than a second signup.

The page-end CTA stays a digest signup and says so ("Catch the next turn in
the daily brief"): per-story alerts belong to the Follow control, and the
digest copy must not promise a per-thread email it does not send.

Limits: followers are read one contact at a time (about 1.2 s each at
Resend's default rate limit), which suits hundreds of followers, not tens of
thousands; the dynamic `/storylines` list keeps the browser-only Follow.

## Accessibility and responsive behavior

- Primary controls have at least a 44 px touch target.
- Evidence trace/Source timeline uses tab roles, selected state, keyboard arrow navigation, and
  associated tabpanels.
- Focus indicators remain visible.
- State and provenance never rely on color alone.
- Every access-track phase has a text label; narrow screens use a legend rather
  than squeezing endpoint labels.

## Editorial contract

`whats_new` is the primary summary on both index and detail pages.
`take_for_builders` is operational, not generic significance language.
`tldr` is concise collapsible background. Failures, regressions, suspensions,
and recoveries should receive explicit beats when supported by evidence.

The editor sidecar remains durable source-of-truth. The deterministic builder
copies `whats_new`, `why_it_matters`, `take_for_builders`, and `status` into the
index so the list does not need one API request per storyline.

## Publishing routine

The repository-owned scheduler definition is
`.agents/routines/storyline-five-hourly/harness.yaml`. It runs at minute zero
every five hours in `Asia/Seoul`, in the cloud, against
`FutureGadget/ai-sota-feed-bot`. The scheduler provisions unrestricted push
permission for this repository and injects only
`.agents/routines/storyline-five-hourly/prompt.md` into agent context.

The prompt runs `storyline-scout` before `storyline-editor`, validates both
sidecar types, rebuilds deterministic storyline outputs, and publishes one
data-only commit directly to `main`. It retries push races up to three times;
generated-output conflicts are handled by preserving agent-authored sidecars
and rebuilding rather than manually merging generated JSON.
