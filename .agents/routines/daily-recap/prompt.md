# Daily recap publishing

Publish the curated recap for yesterday in UTC.

Before acting, read these contracts completely:

1. `.agents/routines/COMMON.md`
2. `AGENTS.md`, especially **Product Positioning**
3. `.agents/skills/daily-summary/SKILL.md`

## Run the routine

1. Determine yesterday's UTC calendar date as `YYYY-MM-DD`. Use UTC explicitly;
   do not derive the date from the machine's local timezone.
2. Build the input bundle for that date:

   ```bash
   python .agents/skills/daily-summary/scripts/build_daily_input.py --date <YYYY-MM-DD>
   ```

3. Read `data/daily/input/latest.json` and use its `date` as the canonical
   edition date.

   - If `data/daily/<date>.json` already exists, stop successfully. Report that
     the date is already published and make no other changes.
   - If the bundle contains no genuine articles, stop successfully without
     publishing. Do not fabricate content.

4. Otherwise, write `data/daily/<date>.json` according to the daily-summary
   skill:

   - synthesize a concise two- or three-paragraph introduction;
   - write 3–6 standalone **In 30 seconds** highlights;
   - organize the strongest articles into 3–6 meaningful thematic categories;
   - curate rather than dumping every input item;
   - copy every article URL verbatim from the bundle—never invent, normalize,
     shorten, or guess links.

5. Validate, rebuild the index, and regenerate the static recap outputs:

   ```bash
   python .agents/skills/daily-summary/scripts/build_daily_index.py
   ```

   Fix all errors and repeat until every recap validates.

6. Confirm the changed files contain no placeholder or sample content.

If nothing was published, exit without creating an empty commit.

Otherwise, stage only:

```text
data/daily/
web/daily/
web/sitemap.xml
web/robots.txt
```

Create one data-only commit:

```text
daily recap: <date>
```

Publish directly to `origin/main` using the shared rebase-and-retry contract in
`COMMON.md`.

If direct publication remains impossible after those retries, and repository
pull-request tooling is available, create a temporary branch containing only
this commit, open a pull request to `main`, and merge it without requesting
further input. Do not leave the routine complete with an unmerged pull request.
Never force-push or bypass failed validation. If the fallback cannot be
completed, report the blocker and the unmerged branch or pull request.

Report the UTC recap date, input article count, published article and category
counts, validation result, commit SHA or no-op reason, and final publication
result.
