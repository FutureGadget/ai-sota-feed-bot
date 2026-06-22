# Weekly recap publishing

Publish the current ISO week's curated AI recap for `/weekly`.

Before acting, read these contracts completely:

1. `.agents/routines/COMMON.md`
2. `AGENTS.md`, especially **Product Positioning**
3. `.agents/skills/weekly-summary/SKILL.md`

## Run the routine

1. Build the news-only input bundle for the ISO week containing the current
   date:

   ```bash
   python .agents/skills/weekly-summary/scripts/build_weekly_input.py --types news
   ```

2. Read the command result and `data/weekly/input/latest.json`. Use the bundle's
   `week` value as the canonical ISO week ID.

   - If `already_published` is true or `data/weekly/<week>.json` already exists,
     stop successfully. Report that the week is already published and do not
     overwrite it.
   - If the bundle contains no genuine articles, stop successfully without
     publishing. Do not fabricate content.

3. Otherwise, read the complete bundle and write
   `data/weekly/<week>.json` according to the weekly-summary skill:

   - Set `week` to the exact bundle value and preserve its `start` and `end`.
   - Curate the strongest items; skip duplicates and low-signal posts.
   - Skip items whose only supplied URL is an ugly redirect or tracking URL.
     Never rewrite, clean, invent, normalize, or shorten a URL; every included
     URL must be copied verbatim from the bundle.
   - Organize the edition into 4–6 meaningful thematic categories derived from
     the week's actual shifts, not the input category labels.
   - Write a two- or three-paragraph narrative introduction connecting the
     dominant shifts and durable engineering implication.
   - Write 3–6 standalone highlights, a focused 1–2 sentence summary for each
     category, and one tight `what it is + why it matters` line per article.

4. Validate, rebuild the index, and regenerate static weekly outputs:

   ```bash
   python .agents/skills/weekly-summary/scripts/build_weekly_index.py
   ```

   Fix all errors and repeat until every recap validates.

5. Confirm the changed files contain no placeholder or sample content.

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

