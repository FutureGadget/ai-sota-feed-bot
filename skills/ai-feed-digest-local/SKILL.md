---
name: ai-feed-digest-local
description: Run and iterate the AI SOTA feed pipeline locally (collect, health, digest, Telegram publish) with OpenClaw-host environment and keep development synced to GitHub via commit/push. Use when asked to run local end-to-end tests, iterate ranking/prompts/preferences, or ship changes while preserving remote repo history.
---

Run local pipeline from repository root using bundled scripts.

## Quick Commands

- Run full local pipeline (includes Telegram publish if secrets/env exist):
  - `skills/ai-feed-digest-local/scripts/run_full.sh`
- Run dev pipeline without Telegram publish:
  - `skills/ai-feed-digest-local/scripts/run_dev.sh`

## Workflow

1. Run `run_dev.sh` while iterating on scoring/prompts/preferences.
2. Run `run_full.sh` for end-to-end verification.
3. Commit and push all relevant changes after successful local validation:
   - `git add ... && git commit -m "..." && git push`

## Notes

- Prefer local manual runs during development (no schedule required).
- Keep preferences prompt-driven via:
  - `config/user_preferences.yaml`
  - `config/prompts/label_system.txt`
  - `config/prompts/rerank_system.txt`
