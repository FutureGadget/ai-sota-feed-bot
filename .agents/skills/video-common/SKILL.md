---
name: video-common
description: Shared pipeline for the ai-sota-feed-bot explainer videos (daily-video and weekly-video). Owns the scripts and reference animation for target picking, Gemini TTS with model fallback, timing, HTML-to-MP4 rendering, YouTube upload, and attaching the video id to a recap. Not run on its own; the kind-specific skills point here.
---

This is the shared contract for `daily-video` and `weekly-video`. The kind
skill sets the values below; this file owns every step that is the same.

| Value | daily | weekly |
|---|---|---|
| `<kind>` | `daily` | `weekly` |
| `<key>` | `YYYY-MM-DD` | `YYYY-Www` |
| Source | `data/daily/<key>.json` | `data/weekly/<key>.json` |
| Work dir | `build/daily-video/<key>/` | `build/weekly-video/<key>/` |

Scripts live in `scripts/` next to this file; the reference animation is in
`reference/`. Work in the work dir (gitignored). Do not edit `pipeline/`, other
`data/` files, or `.github/`. The video file is never committed: only its
YouTube id goes into the recap JSON.

## 1. Pick the target

```bash
python .agents/skills/video-common/scripts/video_target.py --kind <kind>
```

Stop when it prints `"due": false`. Otherwise use its `id` as `<key>`.

## 2. Storyboard rules

- Use only facts in the recap summaries. Derived arithmetic is fine. Never
  invent numbers, causes or quotes. If no number is given, do not draw one.
  Label any diagram that is a generic illustration as illustrative.
- Pick stories whose summaries explain a mechanism, comparison or magnitude.
  Skip stories that are only an announcement.
- Pick one lead story (the sharpest number, tradeoff or surprise) and give it
  about 40 percent of the runtime. Supporting stories each teach a different
  mechanism: a price, a tradeoff, a workflow.
- Scene 1 is a hook of 8 s at most, not a title card. Open on the most
  surprising fact as a big animated number, or a one-line question. Narration
  starts within 1 s. No "here is what happened" opener. The brand is a small
  corner mark.
- Every story scene runs three beats: before (the old situation, drawn
  simply), the change (one animated transformation that shows the mechanism),
  then so-what (one red-highlighted consequence phrased as "so you can ..." or
  "watch out if ...").
- Make magnitude visible. Count up every number the recap gives and pair it
  with a comparison bar or a derived ratio, with the arithmetic on screen.
  No number in the recap means no number on screen: use before/after
  structure instead.
- Vary the layout. No two adjacent scenes share one. Rotate big-number
  count-up, before/after split, flow diagram with a highlighted failing step,
  ranked bars, layer stack, timeline. One red packet or cursor travels through
  every scene as a through-line.
- Pacing: a visual change at least every 3 s, a wipe or cut on each scene
  boundary, a 0.4 s pause before each so-what. The first and last 5 s are the
  most dynamic. One hero moment: the lead story's mechanism animates end to
  end for 6-8 s with no competing text.
- The last scene gives one takeaway sentence for the viewer, then at most
  three one-line bullets, then `llm-digest.com`. The narration ends on the
  takeaway, not the URL.
- Narration: spoken, conversational, second person, 1-3 short sentences per
  scene. Open each story with a concrete image or a question, not "<Company>
  announced". Numbers and acronyms spelled out. Never read a list aloud. Write
  `narration.json`: `[{"id":"s1","text":"..."}]`.
- Look: light broadsheet. Paper `#f4efe4`, ink `#15120f`, one red `#c4271c`,
  Georgia serif headlines, kinetic headlines, staggered reveals, smooth
  easing, wipe transitions, flow diagrams, side-by-side comparisons, animated
  bars and count-ups, on-screen captions.
- Keep notes and diagrams above y=590 (captions use the bottom 130 px).
  Captions are at most 2 lines of 42 characters; `caption()` in the reference
  splits sentences into such chunks.
- Draw each so-what with `sowhat()` from the reference at y=520. Keep
  diagrams and notes above y=490 so the band and captions never overlap them.
  Keep dashed routes and labels clear of the band.
- Reject the storyboard if: scene 1 is a title card; two adjacent scenes share
  a layout; a story scene has no so-what; a number has no comparison; the lead
  story runs under 25 s of a daily video.

## 3. Voice

```bash
python .agents/skills/video-common/scripts/gemini_tts.py narration.json clips --voice Kore
python .agents/skills/video-common/scripts/assemble.py timing narration.json clips
```

- One request per scene. Clips already saved are skipped, so a rerun resumes.
- Each model allows 3 requests per minute and 10 per day. The script tries
  `gemini-3.8-flash-tts`, `gemini-3.1-flash-tts-preview`,
  `gemini-3.8-flash-lite-tts`, then `gemini-2.5-flash-preview-tts`, moving to
  the next on a per-day 429. This pools the four daily quotas, so a run may
  use more than 10 scenes. Do not pass `--model` unless pinning one. Report
  which model voiced each clip.
- Stop and report only when every model is out of quota.
- Do not add a style or instruction prefix to the text: it is spoken aloud.
- Gemini authentication is handled outside the skill: send requests without
  credentials and never look for or create keys. If a script fails with an
  authentication error, stop and report it. Do not publish a silent video.
- Heed any `WARNING` from `assemble.py timing`: regenerate nothing blindly,
  every request spends quota. Report it instead.

## 4. Animation

Start from `reference/example-animation.html` (copy to `index.html`) and
`reference/capture.cjs`. Replace every scene function and the chrome text with
this recap's content. Keep the contract: `render(t)` is a pure function of
time, scene boundaries come from `timing.json` injected as `window.__TIMING__`,
and the captions come from the narration text.

Setup if missing: `ffmpeg`, then `npm i playwright-core` (run it inside the
work dir) and a Chromium (`npx playwright-core install chromium-headless-shell`,
or set `PW_CHROMIUM` to an installed browser). Check that a serif font renders.

```bash
node capture.cjs stills 0.45,0.9     # one still per scene into stills/
```

Read the stills. Fix overflow and orphan words by shortening text. Check the
last frame of every scene.

## 5. Render

```bash
node capture.cjs frames
python .agents/skills/video-common/scripts/assemble.py encode frames explainer-<key>.mp4
```

Check the duration against the kind's range and that the file plays
(`ffprobe`).

## 6. Publish

```bash
python .agents/skills/video-common/scripts/youtube_upload.py explainer-<key>.mp4 \
  --title "<kind title>" --description "<intro sentence>. Full recap: <page url>" \
  --privacy unlisted
python .agents/skills/video-common/scripts/attach_video.py --kind <kind> --id <key> \
  --youtube-id <id> --title "<kind title>" --duration-s <seconds>
```

- Run `attach_video.py` only after the upload succeeds. On upload failure,
  change nothing under `data/` or `web/` and report the error.
- `youtube_upload.py` reads its credentials from the environment itself. Never
  print or log them. If the upload fails with an authentication error, stop and
  report it.
- `attach_video.py` rebuilds pages beyond the ones to stage. Stage only the
  paths the routine names, and restore any other file it changed with
  `git checkout -- <path>`. Never stage anything under `build/`.

## Report

Target key, stories chosen, TTS requests used (and which model voiced each
clip), video duration, YouTube URL, validation result, and any claim you were
unsure about.
