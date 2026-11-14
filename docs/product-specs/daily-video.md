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
`.agents/routines/daily-video/` (skill `.agents/skills/daily-video/`) runs after
the daily recap routine. It uploads first and attaches `video` only after the
upload succeeds. Setup and failure handling:
`docs/how-to/daily-video-routine.md`.

## Weekly
The weekly recap has the same block and contract; see `weekly-video.md`.
Both kinds share the pipeline in `.agents/skills/video-common/`.

## Content rules
Only facts in the recap summaries; no invented numbers, causes or quotes; no
number is drawn unless the recap gives one; generic diagrams are labeled
illustrative.

## Coverage
The video is the audio edition of the recap, not a separate edit. Scene 1 states
the recap `intro`'s central claim and the last scene gives its takeaway. Every
highlight and every category appears in a scene; at most 2 highlights and 1
category may be cut, each with a reason. The lead story is a highlight. The
storyboard maps highlights and categories to scenes in `coverage.json`, and
`.agents/skills/video-common/scripts/check_coverage.py` must pass before voicing.

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
