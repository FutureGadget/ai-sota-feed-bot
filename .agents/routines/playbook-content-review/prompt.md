# Review the published Agent Builder's Playbook

Act as a rigorous content reviewer for
`https://www.llm-digest.com/playbook`.

Before acting, read these contracts completely:

1. `.agents/routines/COMMON.md`
2. `AGENTS.md`, especially **Product Positioning**
3. `.agents/skills/playbook/SKILL.md`
4. `docs/product-specs/playbook.md`

## Review

1. Open the live `/playbook` page and identify the latest edition date.
2. Inspect every card in the latest edition. Also use the archive selector to
   check other currently exposed editions for obvious broken or malformed
   content.
3. Compare reviewed cards with their source edition under
   `data/playbook/<date>.json`, the input bundle when available, and each linked
   source or wiki topic.
4. Review for:

   - factual errors, unsupported claims, incorrect names, dates, amounts,
     metrics, or attribution;
   - a `problem` that the source does not establish;
   - an `apply` instruction that is vague, impractical, unsafe, or not actually
     supported by the source;
   - a `result` that violates the skill's evidence.kind rules (presents
     inference as measurement, or overpromises);
   - an incorrect `evidence.kind`, `source_sid`, `kind`, `area`, effort, or
     topic link;
   - broken, mismatched, fabricated, normalized, or redirected source URLs;
   - duplicate cards, or cards that fail the skill's curation lens and
     audience bar;
   - placeholder text, malformed content, or obvious editorial mistakes.

5. Verify suspected issues against the linked source and, when needed,
   authoritative primary sources.
6. Make a concise correction plan before editing. Apply only evidence-backed
   corrections; do not rewrite sound cards merely for style.

## Apply and validate

Edit the dated source edition JSON under `data/playbook/<date>.json`, following
the skill's editorial guidance (stable IDs, verbatim source URLs, `card_count`,
and which files are generated rather than hand-edited). If a card cannot
support a concrete, honest `problem → apply → result`, remove it.

After any correction, validate and rebuild:

```bash
python .agents/skills/playbook/scripts/build_playbook_index.py
```

Fix errors and repeat until every edition validates. Reopen the live-shaped
local Playbook page or inspect its API data to confirm the corrected edition
renders coherently and contains no placeholder content.

If the review finds no supported issue, exit successfully without changing
files or creating an empty commit.

Otherwise, stage only:

```text
data/playbook/
```

Create one data-only correction commit:

```text
playbook: correct reviewed content
```

Publish directly to `origin/main` using the shared rebase-and-retry contract in
`COMMON.md`. If a rebase conflicts only in generated Playbook indexes, abort
the conflict, preserve the intended dated-edition correction, update to the
latest `origin/main`, reapply the correction, rebuild, revalidate, recommit,
and retry. If another change conflicts in the same dated edition, stop and
report it rather than overwriting another editor's work. Never force-push.

Report the reviewed editions and cards, issues found with supporting evidence,
corrections or removals made, validation result, final card counts, commit SHA
or no-change result, and push result.
