# Weekly explainer video

A 150-180 s narrated video that explains how the week's stories connect, shown
on the weekly recap page and linked from the weekly email. It follows the daily
explainer (`daily-video.md`) and reuses its pipeline.

## Reader behavior
- `/weekly` and `/weekly/<week>` show a "Prefer to watch?" block after the
  intro and the focus widget, before the category list. The text recap stays
  first. The block is `<section id="video">`, so `/weekly/<week>#video` scrolls
  straight to it.
- The block is a YouTube thumbnail with a play button. Nothing loads from
  YouTube until the reader presses play, which swaps in a
  `youtube-nocookie.com` iframe.
- A recap without `video` renders exactly as before.
- The weekly email shows "Watch the weekly explainer" under the title when the
  recap has a valid `video`. It links to
  `/weekly/<week>?utm_source=email&rid=<token>#video`. The email never embeds
  the video, and emails without a video are unchanged.

## Data contract
`data/weekly/<week>.json` may contain `video: {youtube_id, title?, duration_s?}`.
`youtube_id` must be 11 characters of `A-Za-z0-9_-`; `validate_recap` rejects
anything else and the renderers ignore an invalid id. Only the id is stored. The
video file is never committed. The weekly index entries do not carry `video`.

## Production
Phase 2 of `.agents/routines/weekly-recap/` (skill `.agents/skills/weekly-video/`,
shared steps in `.agents/skills/video-common/`) runs Saturday right after the
recap is pushed (06:00 KST start). It uploads first and attaches `video` only after
the upload succeeds. A weekly video uses 9-12 scenes. Voice requests spread
across the Gemini TTS fallback chain, so one video may carry two voices. Setup
and failure handling: `docs/how-to/daily-video-routine.md`.

## Content rules
Same as the daily video: only facts in the recap summaries; no invented numbers,
causes or quotes; no number is drawn unless the recap gives one; generic
diagrams are labeled illustrative.
