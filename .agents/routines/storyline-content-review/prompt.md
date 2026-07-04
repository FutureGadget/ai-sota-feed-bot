# Review published storylines

Act as a rigorous content reviewer for
`https://www.llm-digest.com/storylines`.

Before acting, read:

1. `.agents/routines/COMMON.md`
2. `AGENTS.md`, especially **Product Positioning**
3. `.agents/skills/storyline-scout/SKILL.md`
4. `.agents/skills/storyline-editor/SKILL.md`
5. `docs/product-specs/storylines.md`

## Review

1. Open the live `/storylines` index and inspect every currently listed
   storyline.
2. Open each active storyline detail page and compare it with:

   - `data/storylines/<slug>.json`;
   - its durable narrative sidecar under
     `data/storylines/narratives/<slug>.json`;
   - the linked source articles and member timeline;
   - `data/storylines/scout/links.json` when the storyline was scout-surfaced.

3. Review for:

   - factual errors, unsupported claims, incorrect names, dates, amounts,
     status, chronology, or attribution;
   - summaries or timeline notes that misrepresent their cited article;
   - stale or contradictory `status`, `whats_new`, `tldr`,
     `take_for_builders`, beats, open questions, or day captions;
   - inflated or fabricated provenance, verification counts, or scout claims;
   - unrelated stories incorrectly joined into one thread, duplicate threads,
     or clear direct developments omitted from an existing confirmed link;
   - broken source links, placeholder text, malformed content, or obvious
     editorial mistakes;
   - claims that do not fit the platform- and agent-engineer audience lens.

4. Verify every suspected issue against the supplied articles and, when
   needed, authoritative primary sources.
5. Make a concise correction plan before editing. Apply only evidence-backed
   corrections; do not rewrite sound editorial choices for style alone.

## Apply and validate

Edit durable source-of-truth files only:

- narrative corrections:
  `data/storylines/narratives/<slug>.json`;
- confirmed membership corrections, only when clearly justified:
  `data/storylines/scout/links.json`.

Do not hand-edit generated `data/storylines/<slug>.json`,
`data/storylines/index.json`, or static storyline HTML.

After any correction, run both skills' validators (their SKILL.md validation
steps), then rebuild and re-render:

```bash
python pipeline/build_storylines.py
python pipeline/render_static_pages.py
```

Fix errors and repeat until both validators and the storyline build pass.
Inspect the regenerated index and affected detail pages to confirm each
correction appears correctly and no placeholder or layout-breaking content was
introduced.

If the review finds no supported issue, exit successfully without changing
files or creating an empty commit.

Otherwise, stage only:

```text
data/storylines/
web/storyline/
web/sitemap.xml
```

Create one data-only correction commit:

```text
storylines: correct reviewed content
```

Publish directly to `origin/main` using the shared rebase-and-retry contract in
`COMMON.md`. If a rebase conflicts only in generated storyline outputs, abort
the rebase, preserve the intended narrative or scout-sidecar corrections,
update to the latest `origin/main`, reapply those durable corrections, rebuild,
revalidate, recommit, and retry. If another change conflicts in an
agent-authored sidecar, stop and report it rather than guessing between
editorial versions. Never force-push.

Report the reviewed storyline slugs, issues found with supporting evidence,
durable corrections made, both validator results, final build result, commit
SHA or no-change result, and push result.
