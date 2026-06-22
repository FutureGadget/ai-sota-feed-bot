# Git Hygiene for AI Feed Bot

Goal: reduce rebase/merge conflicts while keeping reproducible history.

## Commit strategy
Use two commit types instead of one mixed commit:

1. **Code/config/docs commit**
   - `pipeline/`, `collectors/`, `publish/`, `config/`, `docs/`, `scripts/`, workflows
2. **Runtime data commit** (optional)
   - `data/raw`, `data/processed`, `data/digest`, `data/health`, `data/diagnostics`, `data/llm/labels*.json`

This keeps feature history clean and makes conflict resolution much easier.

## Recommended flow

```bash
# 1) Commit code/config/docs first
./scripts/git_commit_code.sh "feat: ..."

# 2) Run pipeline/tests
./skills/ai-feed-digest-local/scripts/run_full.sh

# 3) Commit runtime artifacts separately (if needed)
./scripts/git_commit_runtime.sh "chore(data): refresh digest artifacts"
```

## Conflict-prone files
Most frequent conflicts are rolling files:
- `data/digest/latest.md`
- `data/digest/latest_v2.md`
- `data/processed/latest.json`
- `data/processed/latest_v2.json`
- `data/health/*.json`
- `data/health/ingest_runs.jsonl`

When rebasing with conflicts, prefer **keeping local generated artifacts** after rerun.

## Rules
- Never mix large runtime-data changes into logic commits.
- Re-run pipeline after rebases that touched runtime data.
- Keep commit messages explicit (`feat|fix|refactor` for code, `chore(data)` for artifacts).

## Commit identity (agent routines)
Agent routines (`daily-summary`, `weekly-summary`, `storyline-editor`,
`storyline-scout`, `wiki-curator`, `playbook`) run **outside** GitHub Actions, so a bare
`git commit` inherits whatever `user.name`/`user.email` the machine happens to
have configured. That is how a stray commit once landed on `main` signed
`wiki-curator <plumlike8@gmail.com>` instead of the canonical bot identity.

Canonical agent identity: **`Claude <noreply@anthropic.com>`**.

Pin it explicitly on every routine commit so the signature can't depend on
ambient config (this sets both author and committer):

```bash
git -c user.name="Claude" -c user.email="noreply@anthropic.com" \
  commit -m "<routine message>"
```

GitHub Actions data/code commits keep their own `github-actions[bot]` identity —
this rule is only for the agent routines listed above.

The canonical shared checkout, staging, commit, rebase/retry, and push behavior
for externally scheduled routines is `.agents/routines/COMMON.md`. A push race
may be retried after fetching and rebasing. A real rebase conflict must be
aborted and reported; routines never force-push shared `main`.
