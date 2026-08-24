# "New updates" indicators (nav pills + feed strip)

One shared freshness signal tells a returning reader which editorial sections —
**Daily recap**, **Weekly recap**, **Storylines**, **Playbook**, **Knowledge
map**, and **Foundations** — have something new since they last looked, without
opening each page to check. It surfaces in two places:

1. A small **"New" pill** on each section's navigation link (the semantic nav
   that shared chrome moves into the Editor's Desk dialog; visible pills roll
   up into a count on the Desk trigger).
2. A one-line **"Fresh from the Editor's Desk" strip** at the top of the live
   feed that *names* the unread sections as directly clickable chips — the
   count on the Desk trigger says "6", the strip says *what*.

This serves the "memory / catch-up" pillar of the product positioning: the
reader should be able to tell what they missed while they're already reading,
not discover it behind a dialog.

All logic lives in one shared script, **`web/nav-updates.js`**, loaded with
`defer` by every hand-edited shell and by the generated static pages
(`pipeline/render_static_pages.py`, `NAV_UPDATES_TAG`). There are no inline
copies anymore — a regression test (`tests/test_site_chrome.py`) enforces
this.

### Visual treatment (why a pill, not a red dot)

The first version was a bare red dot. Two problems: red reads as
*alert / error / action-required* (Gmail and iOS notification badges), which
clashes with the product's calm, anti-hype positioning; and a dot carries no
**information scent** — it says "something" but not "new what?", so readers
weren't sure there was anything to *read*.

The indicator is now a small uppercase **"New" pill** in the site's **accent
color** (`--accent`, theme-aware) on a faint accent tint with a 1px accent
border — the same chip styling already used for badges elsewhere on the site.
It fades/scales in on load (gated behind `prefers-reduced-motion`) so a
returning eye catches it without a nagging perpetual pulse. This follows the
established "label pill" pattern for *informational* newness (Linear, Notion,
Vercel) and reserves red for action-required counts. The accent-text-on-tint
treatment keeps adequate contrast in both light and dark themes, unlike
white-on-accent.

The feed strip uses the same accent-tinted chip language, with a subtle accent
rule rather than a heavy panel. It lives in the feed's reading column, above
the ranked cards and separate from the wide-screen model rail, so readers see
it while continuing the brief rather than treating it as a competing column.

## Behaviour

Each section's indicator appears when the section is **unread** (its latest
content is newer than what the reader last saw) - and only when the reader has
**visited that section before** (a seen marker exists). A brand-new reader
sees no pills anywhere; onboarding happens through content, not alarms. Daily,
Weekly, and Playbook add a **time-aware freshness gate** on top of read history:

| Section | Indicator shows when… | Time gate? |
|---|---|---|
| Daily recap | latest recap is newer than last seen **and** the recap is current | yes |
| Weekly recap | latest recap is newer than last seen **and** the recap is current | yes |
| Storylines | any thread moved since last seen | no — read history only |
| Playbook | latest edition is newer than last seen **and** the edition is current | yes |
| Agent Know-How (`/map`) | any wiki page edited since last seen | no — read history only |
| Foundations | any concept page edited since last seen | no — read history only |

### Why dated editions need the time gate

A daily recap or Playbook edition that has not been produced recently is
**stale**, not fresh — even if you personally never opened the last one. Showing
a "new!" dot for stale data would be misleading (it implies there's fresh
catch-up waiting when there isn't). So dated editions only light up when the
latest artifact actually covers a **recent** period:

- **Daily** is fresh when its `date` covers today or yesterday
  (`age <= 1` day). A recap older than that is considered stale → no dot.
- **Weekly** is fresh when its `end` date is within the last completed week plus
  a one-day grace (`age <= 8` days). Older → no dot.
- **Playbook** is fresh when its edition `date` is within ten days
  (`age <= 10` days). Older → no dot.

Storylines, the knowledge map, and Foundations have no fixed cadence — a
thread can go quiet for a week and then move, and a wiki/concept page is
"current" until it's edited again — so an indicator there means purely
"there's something you haven't seen," with no staleness notion.

## The "Fresh from the Editor's Desk" strip (feed only)

The strip is the answer to "the reader is *on the feed*, where do they
naturally click into editorial content?" It renders once, directly above the
story list, and only when there is something to say:

- **Feed page only** (`/`). Section pages keep the nav pills; the strip never
  follows the reader around the site.
- **Returning readers only.** A chip appears for a section only when that
  section is unread + fresh **and already has a "seen" marker** — i.e. the
  reader has visited it before. A first-time visitor (or a reader who never
  opens, say, Playbook) is introduced to sections through the Editor's Desk
  pills and the contextual in-feed cards; the strip never nags about a section
  the reader hasn't engaged with, so it cannot become a permanent banner.
- **Self-clearing.** Chips link straight to their section; arriving there
  records the "seen" marker, so the chip is gone on the next feed visit. When
  everything is read, the strip doesn't render at all — the caught-up state is
  *empty*, matching the finishable-feed promise.
- **Dismissible.** The × hides the strip for the browser session
  (`sessionStorage`), without marking anything as read.
- **Day-aware daily label.** The daily chip reads "Today's recap" /
  "Yesterday's recap" instead of a generic "Daily recap", so the chip itself
  carries the information scent.
- **No double-promotion.** When the strip is showing the daily chip, the
  feed's deeper Editor's Desk "Today's recap is ready" insert is suppressed
  (`web/index.html` checks `window.llmDigestUpdates.stripSections`).
- **One "since your last visit" module.** When the feed renders the Catch-me-up
  card, it claims that slot and the strip stands down (and vice versa if the
  strip landed first) - at most one pre-story promo module shows per page load.

PostHog events (all optional/no-op without PostHog): `whats_new_view`
(`sections`), `whats_new_click` (`section`), `whats_new_dismiss` (`sections`).

## How it works

- **`GET /api/updates`** (`api/updates.js`) returns lightweight freshness
  signals read from the small index files:
  ```json
  {
    "now": "2026-07-01T23:35:45Z",
    "daily":       { "date": "2026-07-01", "generated_at": "2026-07-01T23:10:00Z" },
    "weekly":      { "week": "2026-W26", "end": "2026-06-27", "generated_at": "..." },
    "storylines":  { "generated_at": "...", "last_updated": "2026-07-01T04:46:21Z" },
    "playbook":    { "date": "2026-06-26", "generated_at": "..." },
    "map":         { "updated": "2026-07-01" },
    "foundations": { "updated": "2026-07-01" }
  }
  ```
  The signals are chosen to be **content-based**, so they don't flicker on every
  rebuild:
  - daily/weekly use the recap `generated_at` (changes only when a new recap is
    written);
  - storylines uses the max thread `last_updated` (moves only when a thread gets
    new material — **not** the index `generated_at`, which the 5-hourly rebuild
    bumps every run);
  - playbook uses the latest edition `generated_at` and gates freshness by its
    edition `date`;
  - map uses the max per-node `updated` date (a real page edit — **not** the
    wiki `index.json` `generated_at`, which every Vercel build regenerates);
  - foundations uses the max per-concept `updated` date, for the same reason.

- **`web/nav-updates.js`** (shared, deferred) fetches `/api/updates` once,
  compares each signal against a per-section "seen" marker in `localStorage`,
  applies the freshness gate for daily/weekly/playbook, skips decorating the
  current section before marking it seen, decorates matching
  `.site-nav-fallback` links, and renders the feed strip. Shared site chrome
  moves that same semantic navigation node into Editor's Desk and rolls
  visible pills up onto the trigger, so the signal remains visible without
  duplicating freshness logic.

- **`window.llmDigestUpdates`** exposes the fetch (`promise`), the raw payload
  (`data`), read-state helpers (`unread(section)`, `fresh(section)`), and
  `stripSections` — the feed page's Editor's Desk inserts consume these
  instead of fetching `/api/updates` again or re-implementing "unread".

- **Read tracking:** when the reader is *on* a section page
  (`/daily[/…]`, `/weekly[/…]`, `/storylines` or `/storyline/<slug>`,
  `/playbook[/…]`, `/map` or `/topic/<slug>`, `/foundations[/…]`), the script
  records that section's current signal as the new "seen" marker, so the
  indicator clears immediately and remains cleared on the next page they visit.

### Storage keys

| Key | Stores |
|---|---|
| `ai_feed_seen_daily_v1` | daily `generated_at` last seen |
| `ai_feed_seen_weekly_v1` | weekly `generated_at` last seen |
| `ai_feed_seen_storylines_v1` | max thread `last_updated` last seen |
| `ai_feed_seen_playbook_v1` | playbook `generated_at` last seen |
| `ai_feed_seen_map_v1` | max wiki node `updated` last seen |
| `ai_feed_seen_foundations_v1` | max concept `updated` last seen |
| `ai_feed_whats_new_dismissed_v1` | (sessionStorage) strip hidden this session |

All read/writes are wrapped in try/catch — private-mode / disabled storage just
means indicators fall back to "always show when unread" and the strip stays
gated off (no seen markers → no chips).

## Design notes

- **No server-side state.** Like the rest of the site (saved items, follows,
  pinned topics), "what have I seen" lives entirely in the reader's browser.
- **Defensive.** If `/api/updates` fails, returns nothing, or the script
  doesn't load, no indicators render and nothing else on the page is affected
  (the feed's desk inserts skip their freshness-dependent cards).
- **Tuning.** The staleness thresholds are the `DAILY_FRESH_MAX_AGE` (1),
  `WEEKLY_FRESH_MAX_AGE` (8), and `PLAYBOOK_FRESH_MAX_AGE` (10) constants in
  `web/nav-updates.js`.

## Tests / validation

- `tests/test_site_chrome.py` — shells load the shared script and embed no
  private fork of it; the script keeps the core invariants (decorates the
  semantic nav, skips-then-marks the current section, covers all six sections
  including foundations, gates the strip to returning readers).
- `node --check` on `api/updates.js` and `web/nav-updates.js`; the handler run
  against the live data tree returns all six sections.
- Playwright pass against a local static+API server covering: first visit (no
  strip, pills in the Desk dialog), returning reader (strip with day-aware
  chips), chip click → seen marker → chip cleared, session dismiss, mobile +
  dark theme rendering, and no strip outside the feed.
