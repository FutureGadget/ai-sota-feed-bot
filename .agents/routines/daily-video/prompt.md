# Daily explainer video

Make and publish the explainer video for the newest daily recap that has none.

Before acting, read these contracts completely:

1. `.agents/routines/COMMON.md`
2. `AGENTS.md`, especially **Product Positioning**
3. `.agents/skills/daily-video/SKILL.md`
4. `.agents/skills/video-common/SKILL.md`
5. `.agents/skills/writing-style/SKILL.md`

## Run the routine

The daily-video skill, with the shared video-common steps, owns the domain
steps. Follow them in order, exactly as
written, with these overrides:

- If the target step reports `due: false`, stop. Nothing to publish.
- Never commit, push, or open a pull request containing the video, frames,
  audio, or anything under `build/`. The video lives only on YouTube.
- If the upload fails, change nothing under `data/` or `web/`, create no
  commit, and report the error.
- If voice generation fails for any reason, stop and report. Do not publish a
  silent or partial video.

## Commit and publish

After a successful upload and `attach_video.py`, stage:

```text
data/daily/
web/daily/
web/sitemap.xml
web/robots.txt
```

and commit:

```text
daily video: <date>
```

Publish directly to `origin/main` using the shared rebase-and-retry contract
in `COMMON.md`. If direct publication remains impossible after those retries,
use the pull-request fallback in `COMMON.md`.

Report the target date, stories chosen, TTS requests used and the model that
voiced each clip, video duration,
YouTube URL, validation result, commit SHA or no-op reason, final publication
result, and any claim you were unsure about.
