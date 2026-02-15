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
