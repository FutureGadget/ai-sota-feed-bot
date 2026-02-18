# Decision Log

Purpose: preserve key project decisions so we can recover context quickly after resets/new sessions.

## Entry Template
- **Date (KST):** YYYY-MM-DD
- **Decision:**
- **Context / Problem:**
- **Rationale:**
- **Impact:**
- **Rollback / Alternative:**

---

## 2026-02-17
- **Decision:** Parse `claude_blog` publish dates from article pages instead of relying on sitemap `lastmod`.
- **Context / Problem:** Claude sitemap blog entries often have missing `lastmod`; old posts were being stamped with `now`, causing incorrect freshness and top ranking.
- **Rationale:** Page metadata (`datePublished` / article publish tags) reflects true publication date.
- **Impact:** Recency scoring is now aligned with actual post date; older posts no longer jump to top because of missing sitemap metadata.
- **Rollback / Alternative:** Revert to sitemap-only dates (not recommended) or keep page parsing disabled via source config.

## 2026-02-17
- **Decision:** Keep runtime safety guard that skips auto-push when worktree is dirty (`preexisting_dirty_worktree`).
- **Context / Problem:** Mixed local code edits + generated data can create noisy/unsafe commits.
- **Rationale:** Preserve commit hygiene and prevent accidental blending of manual changes with runtime artifacts.
- **Impact:** Some runs finish without pushing unless repo is clean first.
- **Rollback / Alternative:** Remove guard (higher risk), or enforce pre-run clean check.

## 2026-02-18
- **Decision:** Introduce Turso as persistent event store for no-login personalization telemetry on Vercel.
- **Context / Problem:** Vercel serverless filesystem is ephemeral, so local SQLite cannot reliably persist click/impression events.
- **Rationale:** Turso provides SQLite-compatible SQL with persistent remote storage and minimal ops overhead.
- **Impact:** Added `/api/events` write endpoint with idempotent `event_id` dedupe and schema auto-bootstrap (`feed_events` table + indexes).
- **Rollback / Alternative:** Move to Vercel Postgres/Neon and port schema/query layer.

## 2026-02-18
- **Decision:** Add anonymous client-side telemetry (`impression` + `click`) from `web/index.html` using localStorage/sessionStorage IDs.
- **Context / Problem:** Personalization requires interaction signals but product intentionally avoids login to preserve UX.
- **Rationale:** Anonymous stable device ID (`anon_user_id`) + per-tab session ID enables usable behavioral signals without user friction.
- **Impact:** Feed render now posts batched impressions; item link clicks emit click events to `/api/events`.
- **Rollback / Alternative:** Disable client tracking calls and keep static ranking only.
