# Daily recap publishing

Publish the curated recap for the next unpublished UTC calendar day.

Before acting, read these contracts completely:

1. `.agents/routines/COMMON.md`
2. `AGENTS.md`, especially **Product Positioning**
3. `.agents/skills/daily-summary/SKILL.md`

## Run the routine

1. Build the input bundle:

   ```bash
   python .agents/skills/daily-summary/scripts/build_daily_input.py
   ```

   - If the result's `due` is false, stop — nothing changed, nothing to
     publish yet.
   - If the result's `empty` is true, the target date had no genuine
     articles. Do not write a recap; the script already recorded this date in
     `data/daily/state.json`. Skip to **Commit and publish** below.

2. Otherwise, read `data/daily/input/latest.json` and use its `date` as the
   canonical edition date. If `data/daily/<date>.json` already exists, stop
   successfully and report that the date is already published.

3. Write `data/daily/<date>.json` according to the daily-summary skill:

   - synthesize a concise two- or three-paragraph introduction;
   - write 3–6 standalone **In 30 seconds** highlights;
   - organize the strongest articles into 3–6 meaningful thematic categories;
   - curate rather than dumping every input item;
   - copy every article URL verbatim from the bundle—never invent, normalize,
     shorten, or guess links.

4. Validate, rebuild the index, and regenerate the static recap outputs:

   ```bash
   python .agents/skills/daily-summary/scripts/build_daily_index.py
   ```

   Fix all errors and repeat until every recap validates.

5. Confirm the changed files contain no placeholder or sample content.

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
