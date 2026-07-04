# End-to-end storyline publishing

Publish current storylines for llm-digest.com directly to `main`.

Before acting, read these contracts completely:

1. `.agents/routines/COMMON.md`
2. `AGENTS.md`, especially **Product Positioning**
3. `.agents/skills/storyline-scout/SKILL.md`
4. `.agents/skills/storyline-editor/SKILL.md`
5. `.agents/skills/writing-style/SKILL.md`

Do not create a branch or pull request.

## Run the scout

Follow the storyline-scout skill in order:

1. Rebuild storylines and generate scout candidates:

   ```bash
   python pipeline/build_storylines.py
   python pipeline/scout_candidates.py
   ```

2. Read `data/storylines/scout/candidates.json`. Conservatively confirm only
   clear same-story links or direct developments of one story. Preserve
   existing valid links and stable link IDs. When uncertain, do not link.
3. Merge confirmed judgments into
   `data/storylines/scout/links.json`, preserving valid existing entries.
4. Validate links and apply them through the deterministic floor:

   ```bash
   python .agents/skills/storyline-scout/scripts/validate_links.py --check
   python pipeline/build_storylines.py
   ```

   Fix errors and repeat until validation passes.

## Run the editor

Follow the storyline-editor skill in order:

1. Build the editor input:

   ```bash
   python .agents/skills/storyline-editor/scripts/build_storyline_input.py
   ```

2. Read the builder's printed summary. If `needs_narrative_count` is 0, skip to
   the final verification. If it is 4 or fewer, read
   `data/storylines/input/latest.json` and write each narrative inline. If it
   is more than 4, do not read `latest.json`: read
   `data/storylines/input/manifest.json` and dispatch one subagent per
   storyline, following the skill's per-slug fan-out — each subagent reads only
   its own `data/storylines/input/by-slug/<slug>.json` and writes
   `data/storylines/narratives/<slug>.json`.
3. Create or refresh every narrative marked new or stale. Write for AI platform
   and agent engineers. Include the required TL;DR, latest consequential
   change, engineering impact, builder action, beats, and concise per-item
   notes described by the skill. On a refresh, carry the prior narrative's arc
   and open questions forward as the skill directs. Use only facts supported by
   the supplied articles and keep provenance claims truthful.
4. Validate narratives and rebuild the served storyline artifacts:

   ```bash
   python .agents/skills/storyline-editor/scripts/validate_narratives.py --check
   python pipeline/build_storylines.py
   ```

   Fix errors and repeat until validation passes.

## Final verification

Before committing:

- Run both validators again.
- Run `python pipeline/build_storylines.py` successfully.
- Confirm every changed JSON file parses.
- Confirm no placeholder, seed, sample, or test content was introduced.
- Confirm only intended files under `data/storylines/` changed.

If nothing meaningful changed, exit successfully without creating an empty
commit.

Otherwise, stage only `data/storylines/` and create one data-only commit:

```text
storylines: update scout links and narratives
```

Publish directly to `origin/main`. This routine overrides the shared retry
limit: retry a push race at most three times.

If rebasing conflicts only in deterministic generated storyline outputs:

1. Abort the conflicted rebase rather than resolving generated JSON by hand.
2. Preserve the intended agent-authored changes to
   `data/storylines/scout/links.json` and
   `data/storylines/narratives/*.json`.
3. Update to the latest `origin/main`.
4. Reapply those agent-authored sidecar changes.
5. Rebuild all deterministic storyline outputs and rerun both validators.
6. Recreate the single data-only commit and retry the push.

If a conflict affects agent-authored sidecars or cannot be resolved by that
rebuild procedure, stop and report it. Never force-push or guess between two
editorial versions.

The routine is complete only after the commit reaches `origin/main`, or after
confirming there was no meaningful change.

Report:

- commit SHA, if created;
- scout links added, updated, preserved, or removed;
- narratives created or refreshed;
- affected storyline slugs;
- both validator results and final build result;
- push result or no-change result.
