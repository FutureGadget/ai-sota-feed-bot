# Daily video routine: setup and operations

Routine: `.agents/routines/daily-video/` (ships `enabled: false`). Skill:
`.agents/skills/daily-video/`. Spec: `docs/product-specs/daily-video.md`.

## Cloud environment

Create (or reuse) an Anthropic-hosted cloud environment for the routine.

### Environment variables (YouTube upload)
| Variable | Value |
|---|---|
| `YOUTUBE_CLIENT_ID` | OAuth client id (Desktop client) |
| `YOUTUBE_CLIENT_SECRET` | OAuth client secret |
| `YOUTUBE_REFRESH_TOKEN` | refresh token with scope `youtube.upload` |

YouTube only accepts OAuth access tokens, which expire after one hour, so a
network secret (a fixed header value) cannot hold the credential. Environment
variables are readable by the agent and by anyone who uses the environment:
use a dedicated environment for this routine, and a Google project used for
nothing else.

### Gemini TTS key
Either a network secret (preferred) or the `GEMINI_API_KEY` variable:
- Network secret: allowed website `generativelanguage.googleapis.com`, custom
  header `x-goog-api-key`, no prefix. The scripts then send no key.
- Or set `GEMINI_API_KEY`; `gemini_tts.py` sends it as `x-goog-api-key`.

Free tier: 10 requests per day for `gemini-3.8-flash-tts`, one per scene, at
most 8 scenes.

### Network access
Allow these hosts beyond the default package registries:
`generativelanguage.googleapis.com`, `oauth2.googleapis.com`,
`www.googleapis.com`, and whichever host serves the Chromium download
(`npx playwright-core install chromium-headless-shell`), or use a setup script
that installs `ffmpeg`, `fonts-liberation` and a Chromium.

## Getting the OAuth refresh token (once)
1. Google Cloud project: enable **YouTube Data API v3**.
2. Google Auth Platform: External consent screen, add the channel owner as a
   test user, then move the app to **In production**. Apps left in "Testing"
   get refresh tokens that expire after 7 days.
3. Create an OAuth client of type **Desktop**.
4. Run the consent flow (a loopback redirect to `127.0.0.1` with scope
   `https://www.googleapis.com/auth/youtube.upload`, `access_type=offline`,
   `prompt=consent`) and store the returned refresh token.

## Local test
Put the client JSON at `~/.youtube-client-secret.json` and the refresh token
at `~/.youtube-refresh-token` (mode 600); `youtube_upload.py` uses them when the
environment variables are absent. Test with `--privacy private` first.

## Failure behavior
- Upload fails: nothing under `data/` or `web/` changes; the routine reports.
- Voice fails or quota is spent: the routine stops and reports; no silent video.
- Uploaded but the commit fails: rerun the routine; `video_target.py` still
  finds the recap without `video`. The earlier upload stays on YouTube and can
  be deleted in YouTube Studio.
- The upload scope cannot rename or delete videos. Fix titles in YouTube Studio.
