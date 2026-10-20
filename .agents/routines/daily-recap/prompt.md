# Daily recap and explainer video

Publish the curated recap for the next unpublished UTC calendar day, then make
and publish its explainer video. Two phases, two commits: the recap reaches
`main` before the video starts.

Before acting, read these contracts completely:

1. `.agents/routines/COMMON.md`
2. `AGENTS.md`, especially **Product Positioning**
3. `.agents/skills/daily-summary/SKILL.md`
4. `.agents/skills/daily-video/SKILL.md`
5. `.agents/skills/video-common/SKILL.md`
6. `.agents/skills/writing-style/SKILL.md`

## Phase 1: recap

The daily-summary skill owns the domain steps: build the input bundle, check
the day isn't already published, write the recap, and validate + rebuild the
index. Follow it in order, exactly as written, with these overrides:

- If the input-bundle step reports `due: false`, there is no new recap. Skip
  the rest of Phase 1 and go to **Phase 2**.
- If it reports `empty: true`, the target date had no genuine articles. Do
  not write a recap - the script already recorded the date in
  `data/daily/state.json`. Skip the skill's remaining editorial steps, commit
  the state change below, and end the routine without Phase 2.
- If the dedup step finds the recap already published, skip the rest of
  Phase 1 and go to **Phase 2**.
- Skip the skill's own commit/push step - commit and publish below instead.

Confirm the changed files contain no placeholder or sample content.

### Commit and publish the recap

- If a recap was written, stage:

  ```text
  data/daily/
  web/daily/
  web/sitemap.xml
  web/robots.txt
  ```

  and commit:

  ```text
  daily recap: <date>
  ```

- If no recap was written but `data/daily/state.json` changed (the
  no-genuine-articles case), stage only:

  ```text
  data/daily/
  ```

  and commit:

  ```text
  daily recap: skip <date> (no genuine articles)
  ```

- If neither changed, create no commit.

Publish directly to `origin/main` using the shared rebase-and-retry contract
in `COMMON.md`, and use its pull-request fallback if direct publication stays
impossible. Phase 2 starts only after the recap is on `origin/main`. If the
recap cannot be published, stop and report the blocker; do not start Phase 2.

## Phase 2: explainer video

Make and publish the explainer video for the newest daily recap that has none.
A Phase 2 failure never undoes or blocks the published recap: report it as a
partial success.

First check that YouTube credentials exist, without printing any value:

```bash
{ [ -n "$YOUTUBE_CLIENT_ID" ] && [ -n "$YOUTUBE_CLIENT_SECRET" ] && [ -n "$YOUTUBE_REFRESH_TOKEN" ]; } || [ -n "$YOUTUBE_ACCESS_TOKEN" ] \
  && echo youtube_env=configured || echo youtube_env=missing
```

If it prints `youtube_env=missing`, skip Phase 2 and report
`video skipped: environment not configured`.

Otherwise the daily-video skill, with the shared video-common steps, owns the
domain steps. Follow them in order, exactly as written, with these overrides:

- If the target step reports `due: false`, skip Phase 2. Nothing to publish.
- Never commit, push, or open a pull request containing the video, frames,
  audio, or anything under `build/`. The video lives only on YouTube.
- If the upload fails, change nothing under `data/` or `web/`, create no
  commit, and report the error.
- If voice generation fails for any reason, stop and report. Do not publish a
  silent or partial video.

### Commit and publish the video

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
use the pull-request fallback in `COMMON.md`. Never force-push or bypass
failed validation.

## Report

Report both phases.

- Recap: target date, input article count, published article and category
  counts, validation result, commit SHA or no-op reason, publication result.
- Video: target date, stories chosen, TTS requests used and the model that
  voiced each clip, video duration, YouTube URL, validation result, commit SHA
  or skip/no-op reason, publication result, and any claim you were unsure
  about.
