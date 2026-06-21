# Feed Date Ranges

Homepage date presets and explicit date ranges are calendar-day filters in the
reader's local timezone.

## Request contract

- The browser converts local start/end boundaries to ISO timestamps with `Z`.
- `from` is local midnight at the start of the first included day.
- `to` is the final millisecond before the next local midnight and is inclusive.
- Presets include exactly the displayed number of local calendar dates:
  `Today` is one date; `Last 3d` is today plus the previous two dates.
- The feed API rejects timezone-naive `from` or `to` values with HTTP 400.

Constructing both local midnights before converting to UTC keeps ranges correct
across daylight-saving transitions.

## Filter basis: publish age, not run time

The `from`/`to` window filters items by **publish age** — the same date the
card displays (`published`, falling back to `first_seen`, then `last_seen`) —
so a window like `Today` always agrees with the date badge on each row.

The window still bounds which pipeline runs the API scans to assemble the feed,
but run membership alone is not sufficient: a highly-ranked story reappears in
every hourly run and would otherwise survive a `Today` window while badged
"3d ago". `api/feed.js` therefore applies an item-level publish-window filter
(`filterItemsByPublishWindow`) after run assembly and label filtering, before
`limit`, so `total_items` and the "N stories" count reflect what the reader
sees. Items with no parseable date are kept (they cannot be proven out of
window).

## Completion contract

The feed API returns `total_items` and `has_more` after date and label filtering.
The Brief may show "You're all caught up" only when `has_more` is false. When a
range exceeds the requested `limit`, the UI states that it is showing a partial
result and asks the reader to narrow the range.
