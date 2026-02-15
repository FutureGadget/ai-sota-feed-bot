# AGENTS.md

## Repo Mission
Build and operate an AI Platform Engineer-focused news intelligence bot (collect → rank → digest → publish).

## Working Rules
- Keep changes small and shippable.
- Prefer deterministic ranking logic before LLM layers.
- Never commit secrets or tokens.
- Add/update docs with every meaningful feature change.

## Documentation Contract
When implementing a feature:
1. Update `ARCHITECTURE.md` if system flow/components changed.
2. Update one of:
   - `docs/product-specs/*` for product behavior
   - `docs/design-docs/*` for design decisions
   - `docs/exec-plans/*` for execution tracking
3. If data model changes, update `docs/generated/db-schema.md`.

## Engineering Guardrails
- Keep workflows idempotent and observable.
- Fail gracefully when optional integrations are missing (e.g., Telegram secrets).
- Prefer config-driven behavior (`config/*.yaml`) over hardcoding.

## Release Rhythm
- `main` always runnable.
- Daily digest workflow must remain green.
- New features should include a validation path (local run or workflow run).
