---
name: ai-feed-digest-local
description: Run and iterate the AI SOTA feed pipeline locally (collect, health, digest, Telegram publish) with OpenClaw-host environment and keep development synced to GitHub via commit/push. Use when asked to run local end-to-end tests, iterate ranking/prompts/preferences, or ship changes while preserving remote repo history.
---

Run local pipeline from repository root using bundled scripts.

## Quick Commands

- Run full local pipeline (includes GitHub issue + Telegram publish):
  - `skills/ai-feed-digest-local/scripts/run_full.sh`
- Run dev pipeline without Telegram publish:
  - `skills/ai-feed-digest-local/scripts/run_dev.sh`
- Run fast Tier-1 pipeline (ingest + health + quick scoring, no LLM/publish):
  - `skills/ai-feed-digest-local/scripts/run_tier1_fast.sh`

## Workflow

1. Run `run_tier1_fast.sh` for fast freshness updates and lightweight sanity checks.
2. Run `run_dev.sh` while iterating on scoring/prompts/preferences.
3. Run `run_full.sh` for end-to-end verification.
4. Commit and push all relevant changes after successful local validation:
   - `git add ... && git commit -m "..." && git push`

## Notes

- `run_full.sh` auto-loads `.env` from repo root if present.
- Required for Telegram publish:
  - `TELEGRAM_BOT_TOKEN`
  - `TELEGRAM_CHAT_ID`
- Prefer local manual runs during development (no schedule required).
- Keep preferences prompt-driven via:
  - `config/user_preferences.yaml`
  - `config/prompts/label_system.txt`
  - `config/prompts/rerank_system.txt`

## Troubleshooting / Recovery

- If output shows `runtime_push_skipped=true reason=preexisting_dirty_worktree`, auto-push was intentionally skipped because there were uncommitted local changes before run start.
  - Recover by committing/stashing first, or intentionally reset to clean tree before a fresh e2e run.
- If output shows `FULL_RUN_SKIPPED: another run_full.sh execution is already in progress`, lock directory is active (`.run_full.lock`).
  - Verify no active `run_full.sh`; if none, remove stale lock and rerun.
- For a clean reproducible rerun:
  1. `git reset --hard HEAD && git clean -fd`
  2. `git status` must be clean
  3. rerun `skills/ai-feed-digest-local/scripts/run_full.sh`
- Success criteria for end-to-end completion:
  - `digest_items=...`
  - `latest_json_valid=true`
  - `runtime_commit_done=true` (or explicit reason if push intentionally disabled)
  - `updated_issue=#...`
  - `telegram_sent=true`
  - `FULL_RUN_OK`
