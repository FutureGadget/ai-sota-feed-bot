# X watch

Save today's posts from the watched practitioner X accounts so the next feed
run collects them.

Before acting, read these contracts completely:

1. `.agents/routines/COMMON.md`
2. `.agents/skills/x-watch/SKILL.md`

## Run the routine

The x-watch skill owns the domain steps. Follow it in order, exactly as
written.

- If the skill reports `X_WATCH_BROWSER_UNAVAILABLE`, stop without changing
  files and report it.
- If `merge` adds no posts, exit successfully without a commit.

## Commit and publish

Stage only `data/browsed/x/` and commit:

```text
browsed: x posts <UTC date>
```

Publish directly to `main` using the shared rebase-and-retry contract in
`COMMON.md`.

Report accounts visited, accounts skipped and why, posts added per account,
the `check` result, commit SHA or no-op reason, and push status.
