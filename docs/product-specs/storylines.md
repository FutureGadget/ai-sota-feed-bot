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

Following is explicitly browser-local; it is not email or push notification.
The control must explain that updated followed storylines appear on the Live
feed. `/storylines` provides an All/Following filter. The storage contract
remains `ai_feed_storyline_follows_v1`.

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
