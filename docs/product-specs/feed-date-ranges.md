# Feed Date Ranges

Homepage date presets have two bases. The default `Past 24h` is a rolling
24-hour **feed-arrival** window; `Last 3d`, `Last 7d`, `Last 30d`, `All`, and
explicit date ranges are calendar-day **publish-age** filters in the reader's
local timezone.

## Request contract

- The default `Past 24h` sends `from=<now - 24h>`, `to=<now>`, and
  `window=arrival`. The API filters on `first_seen`, the run when the story
  first entered the feed, so a slow RSS post or arXiv paper published
  yesterday but admitted this morning is still part of today's brief, and the
  window does not reset to empty at midnight.
- Calendar presets and explicit ranges send local start/end boundaries as ISO
  timestamps with `Z` and omit `window` (default `published`).
- `from` is local midnight at the start of the first included day.
- `to` is the final millisecond before the next local midnight and is inclusive.
- Calendar presets include exactly the displayed number of local calendar
  dates: `Last 3d` is today plus the previous two dates.
- The feed API rejects timezone-naive `from` or `to` values with HTTP 400.

Constructing both local midnights before converting to UTC keeps ranges correct
across daylight-saving transitions.

## Filter basis

`window=arrival` filters items by **feed arrival** (`first_seen`, falling back
to `published`, then `last_seen`). This is the catch-up contract: the reader
sees what the pipeline admitted in the last 24 hours regardless of the
publisher's date. The API reads the admission ledger (`data/brief/*.json`) for
this path and filters on `admitted_at`/`first_seen`; it does not scan the run
snapshots. When no ledger exists yet, it falls back to the run pool.

`window=published` (the API default, used by calendar presets and explicit
ranges) filters items by **publish age** - the same date the card displays
(`published`, falling back to `first_seen`, then `last_seen`) - so a calendar
window like `Last 7d` always agrees with the date badge on each row.

The window bounds which pipeline runs the API scans to assemble the feed, but
run membership alone is not sufficient. For a calendar window, a highly-ranked
old story reappears in every hourly run and would otherwise survive while
badged "3d ago". `api/feed.js` therefore applies an item-level filter
(`filterItemsByPublishWindow`) after run assembly and label filtering, before
`limit`, so `total_items` and the "N stories" count reflect what the reader
sees. Items with no parseable date are kept (they cannot be proven out of
window).

## Completion contract

The feed API returns `total_items` and `has_more` after date and label filtering.
The Brief may show "You're all caught up" only when `has_more` is false. When a
range exceeds the requested `limit`, the UI states that it is showing a partial
result and asks the reader to narrow the range. The Brief's cap-overflow fold
is not a truncation: those items are already in `items` with
`beyond_cap: true`, and the count distinguishes the curated brief from the
expandable pool.
