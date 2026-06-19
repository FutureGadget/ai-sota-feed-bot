# Nav "new updates" indicators

A small **"New" pill** on the navigation links to **Daily recap**, **Weekly
recap**, **Storylines**, and **Knowledge map** tells a returning reader, at a
glance, which of those sections has something new since they last looked —
without opening each page to check.

This serves the "memory / catch-up" pillar of the product positioning: the
reader should be able to tell what they missed, not just see four static links.

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

## Behaviour

Each section's dot appears when the section is **unread** (its latest content is
newer than what the reader last saw) — but Daily and Weekly add a **time-aware
freshness gate** on top of read history:

| Section | Dot shows when… | Time gate? |
|---|---|---|
| Daily recap | latest recap is newer than last seen **and** the recap is current | yes |
| Weekly recap | latest recap is newer than last seen **and** the recap is current | yes |
| Storylines | any thread moved since last seen | no — read history only |
| Knowledge map | any wiki page edited since last seen | no — read history only |

### Why Daily/Weekly need the time gate

A daily recap that hasn't been produced for two days is **stale**, not fresh —
even if you personally never opened the last one. Showing a "new!" dot for stale
data would be misleading (it implies there's fresh catch-up waiting when there
isn't). So Daily/Weekly only light up when the latest recap actually covers a
**recent** period:

- **Daily** is fresh when its `date` covers today or yesterday
  (`age <= 1` day). A recap older than that is considered stale → no dot.
- **Weekly** is fresh when its `end` date is within the last completed week plus
  a one-day grace (`age <= 8` days). Older → no dot.

Storylines and the knowledge map have no fixed cadence — a thread can go quiet
for a week and then move, and a wiki page is "current" until it's edited again —
so a dot there means purely "there's something you haven't seen," with no
staleness notion.

## How it works

- **`GET /api/updates`** (`api/updates.js`) returns lightweight freshness
  signals read from the small index files:
  ```json
  {
    "now": "2026-06-19T00:48:05Z",
    "daily":      { "date": "2026-06-18", "generated_at": "2026-06-19T00:10:00Z" },
    "weekly":     { "week": "2026-W24", "end": "2026-06-13", "generated_at": "..." },
    "storylines": { "generated_at": "...", "last_updated": "2026-06-16T17:22:07Z" },
    "map":        { "updated": "2026-06-18" }
  }
  ```
  The signals are chosen to be **content-based**, so they don't flicker on every
  rebuild:
  - daily/weekly use the recap `generated_at` (changes only when a new recap is
    written);
  - storylines uses the max thread `last_updated` (moves only when a thread gets
    new material — **not** the index `generated_at`, which the 5-hourly rebuild
    bumps every run);
  - map uses the max per-node `updated` date (a real page edit — **not** the
    wiki `index.json` `generated_at`, which every Vercel build regenerates).

- A small inline script in each shell (`web/{index,daily,weekly,storyline,voices}.html`)
  and in the static-render template (`pipeline/render_static_pages.py`,
  `NAV_UPDATES_JS`) fetches `/api/updates`, compares each signal against a
  per-section "seen" marker in `localStorage`, applies the freshness gate for
  daily/weekly, and decorates any matching nav link with the "New" pill.

- **Read tracking:** when the reader is *on* a section page
  (`/daily[/…]`, `/weekly[/…]`, `/storylines` or `/storyline/<slug>`, `/map` or
  `/topic/<slug>`), the script records that section's current signal as the new
  "seen" marker, so the pill clears on the next page they visit.

### localStorage keys

| Key | Stores |
|---|---|
| `ai_feed_seen_daily_v1` | daily `generated_at` last seen |
| `ai_feed_seen_weekly_v1` | weekly `generated_at` last seen |
| `ai_feed_seen_storylines_v1` | max thread `last_updated` last seen |
| `ai_feed_seen_map_v1` | max wiki node `updated` last seen |

All read/writes are wrapped in try/catch — private-mode / disabled storage just
means dots fall back to "always show when unread."

## Design notes

- **No server-side state.** Like the rest of the site (saved items, follows,
  pinned topics), "what have I seen" lives entirely in the reader's browser.
- **Defensive.** If `/api/updates` fails or returns nothing, no dots render and
  nothing else on the page is affected.
- **Tuning.** The staleness thresholds are the `DAILY_FRESH_MAX_AGE` (1) and
  `WEEKLY_FRESH_MAX_AGE` (8) constants in the inline script / `NAV_UPDATES_JS`.

## Tests / validation

- `node --check api/updates.js`; the handler was run against the live data
  tree and returns the four sections.
- `python3 pipeline/render_static_pages.py` renders generated pages with the
  indicator script embedded (no stray escaping from the raw-string constant).
