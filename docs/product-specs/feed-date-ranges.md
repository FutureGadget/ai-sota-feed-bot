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

## Completion contract

The feed API returns `total_items` and `has_more` after date and label filtering.
The Brief may show "You're all caught up" only when `has_more` is false. When a
range exceeds the requested `limit`, the UI states that it is showing a partial
result and asks the reader to narrow the range.
