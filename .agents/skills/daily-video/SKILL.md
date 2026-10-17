---
name: daily-video
description: Make and publish the 90-120 s narrated explainer video for the newest daily recap of ai-sota-feed-bot. Builds a deterministic HTML animation from data/daily/<date>.json, voices it with Gemini TTS, renders an MP4, uploads it to YouTube, and records the video id on the recap so /daily shows it. Use this when running the daily video routine.
---

You make one explainer video per daily recap. Viewers must understand how 4-6
of the day's stories work, not just hear headlines. The video file is never
committed: only its YouTube id goes into the recap JSON.

All scripts live in `scripts/` next to this file. Work in
`build/daily-video/<date>/` (gitignored). Do not edit `pipeline/`, other
`data/` files, or `.github/`.

## 1. Pick the target

```bash
python .agents/skills/daily-video/scripts/video_target.py
```

Stop when it prints `"due": false`. Otherwise use its `date`.

## 2. Storyboard

Source: `data/daily/<date>.json` only.

- Pick 4-6 stories whose summaries explain a mechanism, comparison or
  magnitude. Skip stories that are only an announcement.
- Use only facts in the recap summaries. Derived arithmetic is fine. Never
  invent numbers, causes or quotes. If no number is given, do not draw one.
  Label any diagram that is a generic illustration as illustrative.
- 6-8 scenes, at most 8 (TTS free-tier limit). One title scene, then story
  scenes, then a recap scene that names `llm-digest.com`.
- Narration: 1-3 short sentences per scene, numbers and acronyms spelled out,
  calm and specific. Write `narration.json`: `[{"id":"s1","text":"..."}]`.
- Look: light broadsheet. Paper `#f4efe4`, ink `#15120f`, one red `#c4271c`,
  Georgia serif headlines, kinetic headlines, staggered reveals, smooth
  easing, wipe transitions, flow diagrams, side-by-side comparisons, animated
  bars and count-ups, on-screen captions.

## 3. Voice

```bash
python .agents/skills/daily-video/scripts/gemini_tts.py narration.json clips --voice Kore
python .agents/skills/daily-video/scripts/assemble.py timing narration.json clips
```

- One request per scene. Clips already saved are skipped.
- Each model allows 3 requests per minute and 10 per day. The script tries
  `gemini-3.8-flash-tts`, `gemini-3.1-flash-tts-preview`,
  `gemini-3.8-flash-lite-tts`, then `gemini-2.5-flash-preview-tts`, moving to
  the next on a per-day 429. Do not pass `--model` unless pinning one. Report
  which model voiced each clip.
- Stop and report only when every model is out of quota.
- Do not add a style or instruction prefix to the text: it is spoken aloud.
- Gemini authentication is handled outside the skill: send requests without
  credentials and never look for or create keys. If a script fails with an
  authentication or quota error, stop and report it. Do not publish a silent
  video.
- Heed any `WARNING` from `assemble.py timing`: regenerate nothing blindly,
  each model allows 10 requests per day. Report it instead.

## 4. Animation

Start from `reference/example-animation.html` (copy to `index.html`) and
`reference/capture.cjs`. Replace every scene function and the chrome text with
this day's content. Keep the contract: `render(t)` is a pure function of time,
scene boundaries come from `timing.json` injected as `window.__TIMING__`, and
the captions come from the narration text.

Setup if missing: `ffmpeg`, then `npm i playwright-core` and a Chromium
(`npx playwright-core install chromium-headless-shell`, or set `PW_CHROMIUM`
to an installed browser). Check that a serif font renders.

```bash
node capture.cjs stills 0.45,0.9     # one still per scene into stills/
```

Read the stills. Fix overflow and orphan words by shortening text. Check the
last frame of every scene.

## 5. Render

```bash
node capture.cjs frames
python .agents/skills/daily-video/scripts/assemble.py encode frames explainer-<date>.mp4
```

Check duration is 90-120 s and the file plays (`ffprobe`).

## 6. Publish

```bash
python .agents/skills/daily-video/scripts/youtube_upload.py explainer-<date>.mp4 \
  --title "LLM Digest Daily Explainer - <Mon D, YYYY>" \
  --description "<intro sentence>. Full recap: https://www.llm-digest.com/daily/<date>" \
  --privacy unlisted
python .agents/skills/daily-video/scripts/attach_video.py --date <date> \
  --youtube-id <id> --title "LLM Digest Daily Explainer: <Mon D, YYYY>" --duration-s <seconds>
```

- Run `attach_video.py` only after the upload succeeds. On upload failure,
  change nothing under `data/` or `web/` and report the error.
- `youtube_upload.py` reads its credentials from the environment itself. Never
  print or log them. If the upload fails with an authentication error, stop and
  report it.
- Stage only `data/daily/ web/daily/ web/sitemap.xml web/robots.txt`. Never
  stage anything under `build/`. Commit message: `daily video: <date>`.

## Report

Target date, stories chosen, TTS requests used, video duration, YouTube URL,
validation result, and any claim you were unsure about.
