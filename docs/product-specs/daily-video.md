# Daily news video

Status: prototype (2026-10-17). Hand-made on request; not scheduled, not in CI,
not published anywhere.

## Contract

An agent (a Claude Code session) reads the day's curated recap
(`data/daily/<date>.json`) and writes a **storyboard**: a short, explanatory
motion-graphics video script picking the stories worth explaining. Scripts do
not generate the video. Templates cannot choose what to explain or how.

`video/player.html` + `player.js` + `player.css` is a deterministic motion
player (every frame is a pure function of time). `video/render.mjs` seeks it
frame by frame in headless Chromium (Playwright) and pipes frames to ffmpeg:

    node video/render.mjs <storyboard.json> <out.mp4> [--audio narration.wav] [--fps 24] [--scale 1]
    node video/render.mjs <storyboard.json> x.mp4 --frame <seconds> <out.png>   # still, for review

Needs `playwright` (resolvable by node, or set `PLAYWRIGHT_MODULE`), a Chromium
(`CHROMIUM_PATH` to override) and ffmpeg. A 110s video renders in about 2 minutes.

## Storyboard

`{date, scenes: [{type, seconds, narration, ...}]}`. Scene types:

| type | fields | use |
|---|---|---|
| `open` | kicker, heading, bullets[] | hook |
| `flow` | kicker, heading, rows[{label, nodes[{title, sub?, hot?}]}] | mechanisms, cause and effect |
| `versus` | kicker, heading, left/right {title, lines[], win?} | two approaches |
| `bars` | kicker, heading, items[{label, value, display, tag?, hot?}], callout? | magnitudes |
| `callout` | kicker, heading, sub | one statement |
| `stats` | kicker, heading, stats[{value, prefix, suffix, decimals, label}] | count-ups |
| `category` | kicker, heading, dek, total, stories[{title, summary, source, stat?}] | list of stories |
| `close` | kicker, heading, url | end card |

`narration` is shown as captions, split by sentence. Optional `lead` and
`speech` (seconds) sync captions to recorded audio. Only state facts present in
the recap summaries; derived arithmetic (a ratio) is fine, inventions are not.
Example: `video/examples/2026-10-16.storyboard.json`.

## Narration

Optional. Without `--audio` the video is silent with captions. Voice options
tried: a local offline Piper voice (`en_US-lessac-high`, no key needed), and
`gemini-3.8-flash-tts` on the Gemini API free tier (needs `GEMINI_API_KEY`).
Scene `seconds` must be at least lead + speech length + tail; concatenate
per-scene audio padded to each scene's `seconds`.

## Out of scope

Scheduling, CI, hosting (do not commit MP4s: Vercel bundles `data/`), Korean variant.
