---
name: weekly-video
description: Make and publish the 150-180 s narrated explainer video for the newest weekly recap of ai-sota-feed-bot. Builds a deterministic HTML animation from data/weekly/<week>.json, voices it with Gemini TTS across the model fallback chain, renders an MP4, uploads it to YouTube, and records the video id on the recap so /weekly shows it. Use this when running the weekly video routine.
---

You make one explainer video per weekly recap. Viewers must understand how
the week's patterns connect, not just see a longer list of headlines.

Follow `.agents/skills/video-common/SKILL.md` for every step, with
`<kind>` = `weekly` and `<key>` = the ISO week (for example `2026-W42`). These
values apply:

- Source: `data/weekly/<week>.json` only. Work dir: `build/weekly-video/<week>/`.
- Stories: pick 5-8 across at least 3 categories. Prefer stories that show a
  pattern across days (the same problem from two sources, a before and after,
  a number that moved) over single announcements.
- Scenes: 9-12, at most 12. The default `--max-scenes 12` applies. Open with
  the week's through-line in the title scene, end with a recap scene that
  names `llm-digest.com`.
- Duration: 150-180 s. A scene runs about 16 s, so 9-11 scenes fit.
- Voice: the run needs up to 12 requests, more than one model's 10 per day.
  The fallback chain covers it; expect two models to voice one video and
  report both.
- YouTube title: `LLM Digest Weekly Explainer - <Mon D>-<Mon D, YYYY>` from the
  recap `start` and `end`. Attach title: the same with `:` before the dates.
- Page url in the description: `https://www.llm-digest.com/weekly/<week>`.
- Stage only `data/weekly/ web/weekly/ web/sitemap.xml web/robots.txt`. Commit
  message: `weekly video: <week>`.
