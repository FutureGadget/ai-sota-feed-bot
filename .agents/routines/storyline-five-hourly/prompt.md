# End-to-end storyline publishing

Publish current storylines for llm-digest.com directly to `main`.

Before acting, read these contracts completely:

1. `.agents/routines/COMMON.md`
2. `AGENTS.md`, especially **Product Positioning**
3. `.agents/skills/storyline-scout/SKILL.md`
4. `.agents/skills/storyline-editor/SKILL.md`
5. `.agents/skills/writing-style/SKILL.md`

Do not create a branch or pull request.

## Run the routine

The two skills own the domain steps. Follow each skill's routine in order,
exactly as written, with one override: **skip each skill's own commit/push
step** — this routine makes a single combined commit below.

1. Run the **storyline-scout** skill: build candidates, judge them, merge the
   links file, validate, and apply through the floor.
2. Run the **storyline-editor** skill: build the input, create or refresh
   every narrative marked new or stale (using the skill's inline vs per-slug
   fan-out rule), validate, and overlay. One more override: where the skill
   says to stop when nothing needs a narrative, skip the remaining editor
   steps and continue to final verification instead — scout link changes may
   still need publishing.

## Final verification

Before committing:

- Run both skills' validators again.
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
