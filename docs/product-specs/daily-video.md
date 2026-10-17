# Daily news video

Status: prototype (2026-10-17). Not scheduled, not published anywhere yet.

## Contract

`pipeline/build_daily_video.py` renders the curated daily recap
(`data/daily/<date>.json`, default `latest.json`) as a 1920x1080 MP4 of about
90 seconds: opening scene (title + intro), headlines, one scene per recap
category (top 3 story titles + "+N more"), and a closing call to
`llm-digest.com/daily`. Scenes are deterministic; there is no LLM step.

Slides reuse the broadsheet palette and Playfair fonts from
`pipeline/og_cards.py`. Output (not committed, `build/` is gitignored):
`build/daily-video/<date>/{<date>.mp4,<date>.vtt,script.json,slide-NN.png}`.

## Narration

Optional. With `GEMINI_API_KEY` set, each scene's narration goes to
`gemini-3.8-flash-tts` (Interactions API, voice `Kore`, override with
`GEMINI_TTS_MODEL` / `GEMINI_TTS_VOICE`) on the Gemini API free tier. One request
per scene, paced `GEMINI_TTS_PACE_SECONDS` (default 6s) apart. Scene length
follows the audio.

Failure policy (fail soft): no key, `--no-tts`, or a failed request makes the
affected scenes silent, timed from word count (2.6 words/s, 4s minimum). A
400/401/403/404/429 stops further TTS calls for the run. The video always
builds; the log line `tts_done ok=N failed=M silent=K` says how many scenes
are voiced.

The free tier publishes no fixed quota (limits show in AI Studio) and may use
requests to improve Google products; input is public recap text. Paid pricing
is about $16.20 per 1M audio tokens through 2026-12-31, doubling 2027-01-01.
A day's narration is roughly 2-3k tokens.

## Out of scope (open decisions)

Scheduling after the daily recap routine, hosting (do not commit MP4s: Vercel
bundles `data/`; use release assets or external video hosting), a spend
ledger like `translation_guard.py` if moved to the paid tier, Korean variant.

Run: `python3 pipeline/build_daily_video.py [--date YYYY-MM-DD] [--no-tts]`.
Needs ffmpeg, Pillow and the vendored fonts; otherwise it exits with
`video_build_skipped`.
