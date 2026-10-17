# Daily explainer video

A 90-120 s narrated video that explains how 4-6 of the day's stories work, shown
on the daily recap page.

## Reader behavior
- `/daily` and `/daily/<date>` show a "Prefer to watch?" block after the "In 30
  seconds" intro and before the category list. The text brief stays first.
- The block shows the YouTube thumbnail with a play button. Nothing loads from
  YouTube until the reader presses play, which swaps in a `youtube-nocookie.com`
  iframe.
- A recap without `video` renders exactly as before.

## Data contract
`data/daily/<date>.json` may contain `video: {youtube_id, title?, duration_s?}`.
`youtube_id` must be 11 characters of `A-Za-z0-9_-`; `validate_recap` rejects
anything else and the renderers ignore an invalid id. Only the id is stored. The
video file is never committed.

## Production
`.agents/routines/daily-video/` (skill `.agents/skills/daily-video/`) runs after
the daily recap routine. It uploads first and attaches `video` only after the
upload succeeds. Setup and failure handling:
`docs/how-to/daily-video-routine.md`.

## Content rules
Only facts in the recap summaries; no invented numbers, causes or quotes; no
number is drawn unless the recap gives one; generic diagrams are labeled
illustrative.
