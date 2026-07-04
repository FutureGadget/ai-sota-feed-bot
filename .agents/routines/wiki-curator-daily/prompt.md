# Daily knowledge-wiki maintenance

Maintain the agent-engineering knowledge wiki backing `/map` and
`/topic/<slug>`.

Before acting, read these contracts completely:

1. `.agents/routines/COMMON.md`
2. `AGENTS.md`, especially **Product Positioning**
3. `.agents/skills/wiki-curator/SKILL.md`
4. `config/wiki_schema.md`
5. `.agents/skills/writing-style/SKILL.md`

The schema is authoritative if it disagrees with the skill.

## Run the routine

The wiki-curator skill owns the domain steps. Run it in order, exactly as
written: build the ingest bundle, ingest genuinely new on-brand stories into
`data/wiki/{obstacles,solutions}/*.md`, then lint the full existing graph. One
override: skip the skill's own commit/push step — this routine's own commit
and publish steps below replace it.

You may edit `data/wiki/` and, when regenerated, `web/map.html`,
`web/topic/`, and `web/sitemap.xml`. Read `data/raw/`, `data/stories/`, and
`data/storylines/` only as evidence.

## Final verification

```bash
python pipeline/build_wiki.py --check
python pipeline/build_wiki.py
```

Fix all schema or reference errors and repeat until the command reports
`WIKI_BUILD_OK`. Optionally run `python pipeline/render_static_pages.py` to
inspect the result locally.

If there is nothing genuinely new and no lint issue, exit successfully
without changing files or creating an empty commit.

Otherwise, stage only:

```text
data/wiki/
web/map.html
web/topic/
web/sitemap.xml
```

Keep the commit data-only and use:

```text
wiki: <slugs touched>
```

Publish directly to `main` using the shared rebase-and-retry contract in
`COMMON.md`. Do not open a pull request or publish to a feature branch.

Report the nodes created or updated, lint issues fixed, validation result,
commit status, and push status.
