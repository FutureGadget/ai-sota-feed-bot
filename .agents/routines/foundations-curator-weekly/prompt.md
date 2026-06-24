# Weekly Agent Builder Foundations curation

Maintain the Agent Builder Foundations pages backing `/foundations` and
`/foundations/<slug>`.

Before acting, read these contracts completely:

1. `.agents/routines/COMMON.md`
2. `AGENTS.md`, especially **Product Positioning**
3. `.agents/skills/foundations-curator/SKILL.md`
4. `config/foundations_schema.md`

The schema is authoritative if it disagrees with the skill.

## Run the routine

1. Build a fourteen-day input bundle:

   ```bash
   python .agents/skills/foundations-curator/scripts/build_foundations_input.py --days 14
   ```

   Read `data/foundations/input/latest.json` as source material.

2. Decide whether there is a substantial evidence-backed update:

   - Create a new concept only when there is enough durable evidence.
   - Update an existing concept when new evidence changes the mechanism,
     application guidance, or failure-mode treatment.
   - Do not publish thin stubs, generic beginner lessons, or prompt-tip lists.

3. Edit only `data/foundations/concepts/*.md` for content synthesis:

   - Preserve the builder-question shape.
   - Keep explanation careful and source-grounded.
   - Keep application guidance opinionated.
   - Label evidence tiers explicitly.
   - Refresh `updated` and `covers_evidence`.

4. Validate and rebuild:

   ```bash
   python pipeline/build_foundations.py --check
   python pipeline/build_foundations.py
   python pipeline/render_static_pages.py
   ```

   Fix all schema, reference, and render errors.

## Output boundaries

You may edit:

```text
data/foundations/
web/foundations.html
web/foundations/
web/sitemap.xml
```

You may read `data/stories/`, `data/storylines/`, `data/wiki/`, and
`data/playbook/` as evidence or cross-link material. Do not edit those directories
unless a separate requested task explicitly requires it.

If there is nothing substantial to publish, exit successfully without changing
files or creating an empty commit.

Otherwise, stage only the files above and commit with:

```text
foundations: update <slugs touched>
```

Publish directly to `main` using the shared rebase-and-retry contract in
`COMMON.md`. Do not open a pull request or publish to a feature branch.

Report concepts created or updated, evidence tiers added, validation result,
commit status, and push status.
