# Daily video routine: setup and operations

Routine: `.agents/routines/daily-video/` (ships `enabled: false`). Skill:
`.agents/skills/daily-video/`. Spec: `docs/product-specs/daily-video.md`.

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

Free tier: 10 Gemini TTS requests per day for `gemini-3.8-flash-tts`, one per
scene, at most 8 scenes.

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

## Failure behavior
- Upload fails: nothing under `data/` or `web/` changes; the routine reports.
- Voice fails or quota is spent: the routine stops and reports; no silent video.
- Uploaded but the commit fails: rerun the routine; `video_target.py` still
  finds the recap without `video`. The earlier upload stays on YouTube and can
  be deleted in YouTube Studio.
- The upload scope cannot rename or delete videos. Fix titles in YouTube Studio.
