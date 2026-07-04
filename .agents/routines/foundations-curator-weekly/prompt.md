# Weekly Agent Builder Foundations curation

Maintain the Agent Builder Foundations pages backing `/foundations` and
`/foundations/<slug>`.

Before acting, read these contracts completely:

1. `.agents/routines/COMMON.md`
2. `AGENTS.md`, especially **Product Positioning**
3. `.agents/skills/foundations-curator/SKILL.md`
4. `config/foundations_schema.md`
5. `.agents/skills/writing-style/SKILL.md`

## Run the routine

The skill owns the domain steps. Run the **foundations-curator** skill's
routine in order, exactly as written, with no overrides.

## Output boundaries

You may edit:

```text
data/foundations/
web/foundations.html
web/foundations/
web/sitemap.xml
```

You may read `data/stories/`, `data/storylines/`, `data/wiki/`, and
`data/playbook/` as evidence or cross-link material. Do not edit those
directories unless a separate requested task explicitly requires it.

If there is nothing substantial to publish, exit successfully without
changing files or creating an empty commit.

Otherwise, stage only the files above and commit with:

```text
foundations: update <slugs touched>
```

Publish directly to `main` using the shared rebase-and-retry contract in
`COMMON.md`. Do not open a pull request or publish to a feature branch.

Report concepts created or updated, evidence tiers added, validation result,
commit status, and push status.
