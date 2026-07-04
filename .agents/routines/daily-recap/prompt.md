# Daily recap publishing

Publish the curated recap for the next unpublished UTC calendar day.

Before acting, read these contracts completely:

1. `.agents/routines/COMMON.md`
2. `AGENTS.md`, especially **Product Positioning**
3. `.agents/skills/daily-summary/SKILL.md`
4. `.agents/skills/writing-style/SKILL.md`

## Run the routine

The daily-summary skill owns the domain steps: build the input bundle, check
the day isn't already published, write the recap, and validate + rebuild the
index. Follow it in order, exactly as written, with these overrides:

- If the input-bundle step reports `due: false`, stop — nothing changed,
  nothing to publish yet.
- If it reports `empty: true`, the target date had no genuine articles. Do
  not write a recap — the script already recorded the date in
  `data/daily/state.json`. Skip the skill's remaining editorial steps and go
  straight to **Commit and publish** below.
- Skip the skill's own commit/push step — this routine commits and publishes
  below instead.

## Final verification

Confirm the changed files contain no placeholder or sample content.

## Commit and publish

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

- If neither changed, exit without creating a commit.

Publish directly to `origin/main` using the shared rebase-and-retry contract in
`COMMON.md`.

If direct publication remains impossible after those retries, and repository
pull-request tooling is available, create a temporary branch containing only
this commit, open a pull request to `main`, and merge it without requesting
further input. Do not leave the routine complete with an unmerged pull request.
Never force-push or bypass failed validation. If the fallback cannot be
completed, report the blocker and the unmerged branch or pull request.

Report the target date, input article count, published article and category
counts, validation result, commit SHA or no-op reason, and final publication
result.
