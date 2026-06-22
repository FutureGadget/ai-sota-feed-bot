# Daily knowledge-wiki maintenance

Maintain the agent-engineering knowledge wiki backing `/map` and
`/topic/<slug>`.

Before acting, read these contracts completely:

1. `.agents/routines/COMMON.md`
2. `AGENTS.md`, especially **Product Positioning**
3. `.agents/skills/wiki-curator/SKILL.md`
4. `config/wiki_schema.md`

The schema is authoritative if it disagrees with the skill.

## Run the routine

1. Build a seven-day ingest bundle:

   ```bash
   python .agents/skills/wiki-curator/scripts/build_wiki_input.py --days 7
   ```

   Read `data/wiki/input/latest.json` as the routine's source material.

2. Ingest genuinely new, on-brand stories into
   `data/wiki/{obstacles,solutions}/*.md`:

   - Update **State of the art** in place as compounding synthesis, not a
     changelog.
   - Refresh **What's new**, obstacle-to-solution edges, real `evidence` story
     SIDs, `related_storylines`, `covers_evidence`, and `updated`.
   - Create a new obstacle or solution page only when the evidence supports a
     substantial agent-engineering topic.
   - Declare an obstacle↔solution edge from one side, conventionally the
     obstacle's `solutions`; the compiler symmetrizes it.

3. Lint and fix the existing graph. Check for:

   - orphan nodes;
   - unsynthesized or thin stubs;
   - stale nodes whose evidence moved beyond `covers_evidence`;
   - dangling or unresolved edges, evidence, and storyline references;
   - contradictions between pages.

4. Append one concise line to `data/wiki/log.md` and update
   `data/wiki/index.md` when changes are made.

5. Compile and validate:

   ```bash
   python pipeline/build_wiki.py --check
   python pipeline/build_wiki.py
   ```

   Fix all schema or reference errors and repeat until the command reports
   `WIKI_BUILD_OK`.

6. Optionally regenerate static pages for inspection:

   ```bash
   python pipeline/render_static_pages.py
   ```

## Output boundaries

- You may edit `data/wiki/` and, when regenerated, `web/map.html`,
  `web/topic/`, and `web/sitemap.xml`.
- Read `data/raw/`, `data/stories/`, and `data/storylines/` as evidence; never
  edit them.
- Never hand-edit `data/wiki/index.json`; it is compiler output.
- Keep storylines episodic and the wiki semantic. Reference storylines as
  evidence; do not reproduce their clustering in the wiki.
- Never invent sources. Every evidence SID and storyline slug must resolve.
- Keep the work narrowly focused on engineering and operating agent systems.

If there is nothing genuinely new and no lint issue, exit successfully without
changing files or creating an empty commit.

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
