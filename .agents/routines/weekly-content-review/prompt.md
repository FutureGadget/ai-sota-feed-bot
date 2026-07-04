# Improve the published weekly recap

Act as a rigorous newsletter editor for the latest recap at
`https://www.llm-digest.com/weekly`.

Before acting, read these contracts completely:

1. `.agents/routines/COMMON.md`
2. `AGENTS.md`, especially **Product Positioning**
3. `.agents/skills/weekly-summary/SKILL.md`

## Review

1. Open the live `/weekly` page and identify the exact ISO week currently
   served.
2. Read the complete corresponding `data/weekly/<week>.json`, its input bundle
   when available, and its rendered page under `web/weekly/`.
3. Evaluate whether an AI platform or agent engineer can understand the week's
   important shifts quickly. Review:

   - whether the introduction identifies a real dominant shift, connects the
     secondary patterns, and ends with a useful durable implication;
   - whether the highlights are standalone, concrete, non-repetitive, and
     scannable;
   - whether categories represent meaningful weekly shifts rather than storage
     buckets, overlap, or vague labels;
   - whether category summaries make claims supported by their listed
     articles;
   - whether article takeaways clearly state `what it is + why it matters`;
   - whether low-signal, duplicate, or weakly related articles dilute the
     finishable recap;
   - whether factual claims, names, dates, amounts, attribution, and source
     links are correct;
   - whether wording is unnecessarily dense, repetitive, generic, or
     promotional.

4. Verify factual changes against the linked source and, when needed,
   authoritative primary sources.
5. Make a concise improvement plan before editing.

## Apply and validate

Edit the weekly recap source JSON, not generated HTML. You may improve:

- the intro and highlights;
- category names, grouping, order, and summaries;
- article selection and order;
- concise article summaries.

Preserve the edition's ISO week, date range, schema, and source provenance.
Copy URLs verbatim from the input bundle or existing validated recap,
following the weekly-summary skill's URL standard. Do not add unsupported
facts or turn the recap into generic AI news.

After any improvement, rebuild and validate per the skill's
validate-and-rebuild step. Fix errors and repeat until every recap
validates. Inspect the regenerated
weekly page to confirm the result is more readable and introduced no
placeholder or layout-breaking content.

If the review finds no material improvement worth publishing, exit
successfully without changing files or creating an empty commit.

Otherwise, stage only:

```text
data/weekly/
web/weekly/
web/sitemap.xml
web/robots.txt
```

Create one data-only editorial commit:

```text
weekly recap: improve <week>
```

Publish directly to `origin/main` using the shared rebase-and-retry contract in
`COMMON.md`. If a rebase conflicts in generated weekly files, abort the
conflicted rebase, update to the latest `origin/main`, reapply the editorial
changes to the source recap JSON, rebuild, revalidate, recommit, and retry. If
the source recap itself has conflicting editorial changes, stop and report the
conflict rather than overwriting another agent's work. Never force-push.

Report the reviewed ISO week, diagnosed readability problems, improvements
made, final categories and article count, validation result, commit SHA or
no-change result, and push result.
