# AGENTS.md

## Repo Mission
Build and operate an AI Platform Engineer-focused news intelligence bot (collect → rank → digest → publish).

## Working Rules
- Keep changes small and shippable.
- Prefer deterministic ranking logic before LLM layers.
- Never commit secrets or tokens.
- Add/update docs with every meaningful feature change.
- If you add a new feature or a new document category, update docs index/links in the same PR.

## Repository Structure Index
- `collectors/` — ingestion jobs (RSS/sitemap/arXiv, normalization entry points)
- `pipeline/` — ranking, labeling, health/alerts, digest build
- `publish/` — output channels (GitHub Issue, Telegram)
- `config/` — runtime knobs (`sources.yaml`, `profile.yaml`, `llm.yaml`, `ranking_v2.yaml`, prompts)
- `scripts/` — local utilities and comparison/debug scripts
- `skills/` — local run helpers (e.g., full/dev scripts)
- `data/` — generated runtime artifacts (raw, processed, digest, health, llm cache, diagnostics)
- `docs/` — living documentation
  - `docs/status/` — current operational snapshots
  - `docs/how-to/` — operational playbooks and debugging guides
  - `docs/product-specs/` — behavior specs
  - `docs/design-docs/` — design rationale/decisions
  - `docs/exec-plans/` — execution plans and tracking
  - `docs/generated/` — derived references (e.g., schema)
  - root docs (`docs/*.md`) — architecture/flow/quality/reliability summaries

## Documentation Contract
When implementing a feature:
1. Update architecture/flow docs if system flow/components changed (`docs/ranking-v2-flow.md` and related docs).
2. Update at least one of:
   - `docs/product-specs/*` for product behavior
   - `docs/design-docs/*` for design decisions
   - `docs/exec-plans/*` for execution tracking
   - `docs/status/*` for current operating state changes
3. If data model changes, update `docs/generated/db-schema.md`.
4. If you add a new documentation category (new subdirectory under `docs/`), add it to the Repository Structure Index in this file and link it from README where relevant.

## Engineering Guardrails
- Keep workflows idempotent and observable.
- Fail gracefully when optional integrations are missing (e.g., Telegram secrets).
- Prefer config-driven behavior (`config/*.yaml`) over hardcoding.

## Release Rhythm
- `main` always runnable.
- Daily digest workflow must remain green.
- New features should include a validation path (local run or workflow run).
