# Daily video routine: setup and operations

Routine: `.agents/routines/daily-video/` (ships `enabled: false`). Skill:
`.agents/skills/daily-video/`. Spec: `docs/product-specs/daily-video.md`.

## Cloud environment

Use an Anthropic-hosted cloud environment. The routine and skill never handle
credentials: the Anthropic agent proxy attaches them to requests for the hosts
below, after the request leaves the VM. Claude Code does not inject environment
variables for these, so scripts send plain requests.

### Network secrets
| Host | Credential |
|---|---|
| `generativelanguage.googleapis.com` | Gemini API key: custom header `x-goog-api-key`, no prefix (not `Authorization: Bearer`) |
| `www.googleapis.com` | YouTube OAuth 2.0 authorization with scope `https://www.googleapis.com/auth/youtube.upload` (the narrowest scope that allows `videos.insert`) |

Network secrets cannot be edited: delete and re-add to change one. A secret
listed as **Not sent** is not being applied; read the note under it.

Free tier: 10 Gemini TTS requests per day for `gemini-3.8-flash-tts`, one per
scene, at most 8 scenes.

### Network access
Allow `generativelanguage.googleapis.com` and `www.googleapis.com` (secret
hosts bypass the allowlist), plus whichever host serves the Chromium download
(`npx playwright-core install chromium-headless-shell`), or use a setup script
that installs `ffmpeg`, `fonts-liberation` and a Chromium.

### OAuth app notes
Create the OAuth client in a Google Cloud project with **YouTube Data API v3**
enabled and the channel owner as a test user. Move the app to **In production**:
refresh tokens of apps left in "Testing" expire after 7 days.

## Local test
The scripts send no credentials, so a plain local run is rejected by Google. To
test the pipeline off the cloud, add the authorization yourself, for example a
temporary local patch that reads `~/.gemini-api-key` (sent as `x-goog-api-key`)
and exchanges `~/.youtube-client-secret.json` + `~/.youtube-refresh-token`
(mode 600, scope `youtube.upload`) for an access token. Never commit that
patch. Test the upload with `--privacy private` first.

## Failure behavior
- Upload fails: nothing under `data/` or `web/` changes; the routine reports.
- Voice fails or quota is spent: the routine stops and reports; no silent video.
- Uploaded but the commit fails: rerun the routine; `video_target.py` still
  finds the recap without `video`. The earlier upload stays on YouTube and can
  be deleted in YouTube Studio.
- The upload scope cannot rename or delete videos. Fix titles in YouTube Studio.
