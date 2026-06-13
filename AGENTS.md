# AGENTS.md

## Repo Mission
Build and operate an AI Platform Engineer-focused news intelligence bot (collect → rank → digest → publish).

## Product Positioning (decided 2026-06-13)
The target audience is **AI platform engineers** — and only them. Danu (the
owner) is one himself and built llm-digest.com from his own need, so "would the
owner read this every morning and save time" is the primary quality bar.

We deliberately do NOT compete with SNS/X (freshness), Google News (algorithmic
personalization), or HN/GeekNews (community). The position is built on the jobs
those products are structurally bad at:

1. **Finishable** — a ranked, deduped daily brief that *ends* ("read 12 items,
   you're caught up"), vs. infinite engagement-optimized feeds.
2. **Transparent / anti-hype** — one shared deterministic ranking for everyone,
   🫧 hype flagging, source reliability tracking, and visible reader-tuning
   (Reader-boosted badges). Explicitly not a personalized filter bubble; pinned
   topics are a lens, not a bubble.
3. **Memory** — storylines ("what happened next with X"), daily/weekly recaps
   ("what did I miss this week"), and durable `/story/<sid>` permalinks. This
   continuity layer is the structural moat: timelines and community threads
   forget; we don't.

Tagline shape: "The finishable AI feed for platform engineers — 10 minutes a
day, with memory."

Implications for any change in this repo:
- Site copy, source selection, and ranking tuning (`config/profile.yaml`)
  optimize for the platform-engineer lens and the catch-up job — never for
  breadth, engagement, or generic AI news. Niche drift erases the advantage.
- Storylines and recap pages are the shareable growth artifacts (shared *into*
  HN/Slack/Reddit); invest there before feed features.
- Distribution targets places platform engineers already are; we don't build
  community features.

## Working Rules
- Keep changes small and shippable.
- Prefer deterministic ranking logic before LLM layers.
- Never commit secrets or tokens.
- Add/update docs with every meaningful feature change.
- If you add a new feature or a new document category, update docs index/links in the same PR.
- Follow git hygiene: commit code/config/docs separately from generated runtime data.

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
  - `docs/deploy/` — deployment guides and runtime hosting notes
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

## Project Memory Rule (Working Directory Scope)
- While working in this repository, treat this `AGENTS.md` as mandatory context before making changes.
- Keep a running decision log in `docs/design-docs/decision-log.md` for architecture/ranking/publishing choices.
- For each non-trivial change, write a short ADR-style entry: date, decision, rationale, impact, rollback plan.

## Engineering Guardrails
- Keep workflows idempotent and observable.
- Fail gracefully when optional integrations are missing (e.g., Telegram secrets).
- Prefer config-driven behavior (`config/*.yaml`) over hardcoding.

## Release Rhythm
- `main` always runnable.
- Daily digest workflow must remain green.
- New features should include a validation path (local run or workflow run).

## Deployment (Vercel)
- The site (`web/` pages + `api/` serverless functions, e.g. `/weekly` and
  `/api/weekly`) is auto-deployed to Vercel. Config lives in `vercel.json`.
- Every PR gets an automatic **Vercel preview deployment** — push to a branch /
  open a PR and the changes are viewable on the preview URL Vercel posts on the
  PR. Use the preview to eyeball UI changes (like the `/weekly` page) before merge.
- Merging to `main` triggers the production deploy.
