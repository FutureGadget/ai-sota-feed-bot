# Daily explainer video

A 90-120 s narrated video that explains how 4-6 of the day's stories work, shown
on the daily recap page.

## Reader behavior
- `/daily` and `/daily/<date>` show a "Prefer to watch?" block after the "In 30
  seconds" intro and before the category list. The text brief stays first.
- The block shows the YouTube thumbnail with a play button. Nothing loads from
  YouTube until the reader presses play, which swaps in a `youtube-nocookie.com`
  iframe.
- The block is a `<section id="video">`, so `/daily/<date>#video` scrolls straight to it.
- A recap without `video` renders exactly as before.

## Data contract
`data/daily/<date>.json` may contain `video: {youtube_id, title?, duration_s?}`.
`youtube_id` must be 11 characters of `A-Za-z0-9_-`; `validate_recap` rejects
anything else and the renderers ignore an invalid id. Only the id is stored. The
video file is never committed.

## Production
Phase 2 of `.agents/routines/daily-recap/` (skill `.agents/skills/daily-video/`)
runs right after the recap is pushed, in the same run. It uploads first and attaches `video` only after the
upload succeeds. Setup and failure handling:
`docs/how-to/daily-video-routine.md`.

## Weekly
The weekly recap has the same block and contract; see `weekly-video.md`.
Both kinds share the pipeline in `.agents/skills/video-common/`.

## Content rules
Only facts in the recap summaries; no invented numbers, causes or quotes; no
number is drawn unless the recap gives one; generic diagrams are labeled
illustrative.

## Email
When the recap has a valid `video`, the daily email shows a "Watch the 2-minute
explainer" link under the "In 30 seconds" box. It points to
`/daily/<date>?utm_source=email&rid=<token>#video`: the page opens at the video
block and plays on click. The email never embeds the video. Recaps without a
video produce the same email as before.

## Craft rules
Hook-first opening (no title card), one lead story, before / change / so-what
per story scene, visible magnitude for every number the recap gives, varied
layouts, and a closing takeaway. Owned by `.agents/skills/video-common/SKILL.md`.
