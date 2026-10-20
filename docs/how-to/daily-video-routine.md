# Daily and weekly explainer video: setup and operations

Routines: the video is Phase 2 of `.agents/routines/daily-recap/` and
`.agents/routines/weekly-recap/` (06:00 KST; Phase 1 publishes the recap, Phase
2 makes the video, one commit each). Skills: `.agents/skills/daily-video/` and
`.agents/skills/weekly-video/`, which share the steps and scripts in
`.agents/skills/video-common/`. Specs: `docs/product-specs/daily-video.md` and
`docs/product-specs/weekly-video.md`. The recap routines' cloud environment
must carry the setup below: Phase 2 skips itself with
`video skipped: environment not configured` when the `YOUTUBE_*` variables are
absent, so the recap keeps publishing until the environment is ready. The
separate `daily-video` and `weekly-video` routines were retired; delete or
disable their scheduler jobs.

## Cloud environment

Use an Anthropic-hosted cloud environment.

### Gemini TTS: network secret
The agent proxy attaches the key to requests for the host, so `gemini_tts.py`
sends no credentials.

| Host | Credential |
|---|---|
| `generativelanguage.googleapis.com` | Gemini API key: custom header `x-goog-api-key`, no prefix (not `Authorization: Bearer`) |

Network secrets cannot be edited: delete and re-add to change one. A secret
listed as **Not sent** is not being applied; read the note under it.

### YouTube: environment variables
No network-secret type refreshes a Google user OAuth token (client credentials
and JWT bearer are rejected by Google for YouTube, e.g. `unsupported_grant_type`),
so `youtube_upload.py` reads credentials from the environment and mints a fresh
access token on every run. Do not add a network secret for `www.googleapis.com`
or `oauth2.googleapis.com`: it would be applied to the upload requests and fail.

| Variable | Value |
|---|---|
| `YOUTUBE_CLIENT_ID` | OAuth client id |
| `YOUTUBE_CLIENT_SECRET` | OAuth client secret |
| `YOUTUBE_REFRESH_TOKEN` | refresh token, scope `youtube.upload`, granted by the account that owns the target channel (pick the channel at the consent screen) |
| `YOUTUBE_ACCESS_TOKEN` | optional; used only when the three above are absent; expires after one hour |

Environment variables are readable by the agent and by anyone using the
environment: use a dedicated environment and a Google project used for nothing
else. The token can only upload videos.

Free tier: 3 requests per minute and 10 per day for each Gemini TTS model, one
request per scene. Daily videos use at most 8 scenes and weekly videos at most
12 (`--max-scenes`). `gemini_tts.py` falls back in quality order when a model's
daily quota is spent, which pools the four quotas (40 requests a day): `gemini-3.8-flash-tts`,
`gemini-3.1-flash-tts-preview`, `gemini-3.8-flash-lite-tts`,
`gemini-2.5-flash-preview-tts` (2.5 returns raw PCM; the script wraps it as WAV).

### Network access
Allow `generativelanguage.googleapis.com` (secret hosts bypass the allowlist),
`oauth2.googleapis.com` and `www.googleapis.com`, plus whichever host serves the Chromium download
(`npx playwright-core install chromium-headless-shell`), or use a setup script
that installs `ffmpeg`, `fonts-liberation` and a Chromium.

### OAuth app notes
Create the OAuth client in a Google Cloud project with **YouTube Data API v3**
enabled and the channel owner as a test user. Move the app to **In production**:
refresh tokens of apps left in "Testing" expire after 7 days.

## Local test
Export the four `YOUTUBE_*` variables in your shell to run `youtube_upload.py`
locally. `gemini_tts.py` sends no credentials, so a plain local run is rejected
by Google: add the key yourself, for example a temporary local patch that sends
`~/.gemini-api-key` as `x-goog-api-key`. Never commit that patch. Test the
upload with `--privacy private` first.

## Saturday overlap
The weekly recap and the daily recap both start Saturday 06:00 KST, each then
runs its video phase (about 40 minutes for weekly), and the weekly email goes
out 08:00 KST. If a video finishes late, that email goes out without the video
link. The two video phases draw on the same TTS quotas (about 8 + up to 12
requests against 40 a day) and the same 3 requests per minute per model. Each
handles a per-minute 429 by waiting, and a per-day 429 by moving to the next
model, so overlap slows a run but does not fail it. Expect the weekly video to
be voiced by a second model.

## Failure behavior
- Video failures never affect the recap: it is committed and pushed before the
  video phase starts, and a video failure is reported as a partial success.
- Upload fails: nothing under `data/` or `web/` changes; the routine reports.
- Voice fails or quota is spent: the routine stops and reports; no silent video.
- Uploaded but the commit fails: the next recap routine run retries it; `video_target.py` still
  finds the recap without `video`. The earlier upload stays on YouTube and can
  be deleted in YouTube Studio.
- The upload scope cannot rename or delete videos. Fix titles in YouTube Studio.
