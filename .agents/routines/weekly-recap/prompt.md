# Weekly recap publishing

Publish the current ISO week's curated AI recap for `/weekly`.

Before acting, read these contracts completely:

1. `.agents/routines/COMMON.md`
2. `AGENTS.md`, especially **Product Positioning**
3. `.agents/skills/weekly-summary/SKILL.md`
4. `.agents/skills/writing-style/SKILL.md`

## Run the routine

The weekly-summary skill owns the domain steps. Follow its routine in order,
exactly as written, with these overrides:

1. Build the input bundle news-only: pass `--types news` instead of the
   skill's default type list.
2. Organize the edition into 4–6 thematic categories rather than the skill's
   3–6.
3. Skip the skill's own commit/push step — commit and publish as described
   below.

Stop successfully without publishing when the skill's dedup check reports the
week already published, or when the bundle contains no genuine articles. Do
not fabricate content and do not overwrite an existing edition.

## Final verification

Confirm the changed files contain no placeholder or sample content.

If nothing was published, exit without creating an empty commit.

Otherwise, stage only:

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
`COMMON.md`.

If direct publication remains impossible after those retries, and repository
pull-request tooling is available, create a temporary branch containing only
this commit, open a pull request to `main`, and merge it without requesting
further input. Do not leave the routine complete with an unmerged pull request.
Never force-push or bypass failed validation. If the fallback cannot be
completed, report the blocker and the unmerged branch or pull request.

Report the ISO week ID, selected category names, included article count,
validation result, commit SHA or no-op reason, and final publication result.
