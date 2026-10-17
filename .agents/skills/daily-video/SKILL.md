---
name: daily-video
description: Make and publish the 90-120 s narrated explainer video for the newest daily recap of ai-sota-feed-bot. Builds a deterministic HTML animation from data/daily/<date>.json, voices it with Gemini TTS, renders an MP4, uploads it to YouTube, and records the video id on the recap so /daily shows it. Use this when running the daily video routine.
---

You make one explainer video per daily recap. Viewers must understand how 4-6
of the day's stories work, not just hear headlines.

Follow `.agents/skills/video-common/SKILL.md` for every step, with
`<kind>` = `daily` and `<key>` = the recap date. These values apply:

- Source: `data/daily/<date>.json` only. Work dir: `build/daily-video/<date>/`.
- Stories: pick 4-6.
- Scenes: 6-8, at most 8. Pass no `--max-scenes`.
- Duration: 90-120 s.
- YouTube title: `LLM Digest Daily Explainer - <Mon D, YYYY>`. Attach title:
  `LLM Digest Daily Explainer: <Mon D, YYYY>`.
- Page url in the description: `https://www.llm-digest.com/daily/<date>`.
- Stage only `data/daily/ web/daily/ web/sitemap.xml web/robots.txt`. Commit
  message: `daily video: <date>`.
