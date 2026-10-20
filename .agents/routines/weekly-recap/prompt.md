# Weekly recap and explainer video

Publish the current ISO week's curated AI recap for `/weekly`, then make and
publish its explainer video. Two phases, two commits: the recap reaches `main`
before the video starts.

Before acting, read these contracts completely:

1. `.agents/routines/COMMON.md`
2. `AGENTS.md`, especially **Product Positioning**
3. `.agents/skills/weekly-summary/SKILL.md`
4. `.agents/skills/weekly-video/SKILL.md`
5. `.agents/skills/video-common/SKILL.md`
6. `.agents/skills/writing-style/SKILL.md`

## Phase 1: recap

The weekly-summary skill owns the domain steps. Follow its routine in order,
exactly as written, with these overrides:

1. Build the input bundle news-only: pass `--types news` instead of the
   skill's default type list.
2. Organize the edition into 4-6 thematic categories rather than the skill's
   3-6.
3. Skip the skill's own commit/push step - commit and publish as described
   below.

If the skill's dedup check reports the week already published, skip the rest
of Phase 1 and go to **Phase 2**. If the bundle contains no genuine articles,
end the routine without a recap and without Phase 2. Do not fabricate content
and do not overwrite an existing edition.

Confirm the changed files contain no placeholder or sample content.

### Commit and publish the recap

If a recap was written, stage only:

```text
data/weekly/
web/weekly/
web/sitemap.xml
web/robots.txt
```

Create one data-only commit:

```text
weekly recap: <week>
```

Publish directly to `origin/main` using the shared rebase-and-retry contract in
`COMMON.md`, and use its pull-request fallback if direct publication stays
impossible. Phase 2 starts only after the recap is on `origin/main`. If the
recap cannot be published, stop and report the blocker; do not start Phase 2.

## Phase 2: explainer video

Make and publish the explainer video for the newest weekly recap that has
none. A Phase 2 failure never undoes or blocks the published recap: report it
as a partial success.

First check that YouTube credentials exist, without printing any value:

```bash
{ [ -n "$YOUTUBE_CLIENT_ID" ] && [ -n "$YOUTUBE_CLIENT_SECRET" ] && [ -n "$YOUTUBE_REFRESH_TOKEN" ]; } || [ -n "$YOUTUBE_ACCESS_TOKEN" ] \
  && echo youtube_env=configured || echo youtube_env=missing
```

If it prints `youtube_env=missing`, skip Phase 2 and report
`video skipped: environment not configured`.

Otherwise the weekly-video skill, with the shared video-common steps, owns the
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
data/weekly/
web/weekly/
web/sitemap.xml
web/robots.txt
```

and commit:

```text
weekly video: <week>
```

Publish directly to `origin/main` using the shared rebase-and-retry contract
in `COMMON.md`. If direct publication remains impossible after those retries,
use the pull-request fallback in `COMMON.md`. Never force-push or bypass
failed validation.

## Report

Report both phases.

- Recap: ISO week ID, selected category names, included article count,
  validation result, commit SHA or no-op reason, publication result.
- Video: target week, stories chosen, TTS requests used and the model that
  voiced each clip, video duration, YouTube URL, validation result, commit SHA
  or skip/no-op reason, publication result, and any claim you were unsure
  about.
