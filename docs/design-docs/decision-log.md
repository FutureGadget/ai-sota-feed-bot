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

## 2026-02-18
- **Decision:** Deduplicate impressions by run scope in event ID generation.
- **Context / Problem:** Re-renders were emitting repeated impressions for the same user/item/run and inflating counts.
- **Rationale:** For feed ranking signals, one impression per user-item-run is usually the right granularity.
- **Impact:** Impression `event_id` now ignores per-render timestamp and keys on `anon_user_id + item_id + run_id` (day fallback if run_id absent).
- **Rollback / Alternative:** Keep timestamp-sensitive IDs and handle dedupe only in analytics query layer.

## 2026-02-18
- **Decision:** Add feed API personalization layer with source-first + topic-second boost in shadow mode by default.
- **Context / Problem:** Need click-based personalization without changing offline digest generation immediately.
- **Rationale:** Applying personalization in `/api/feed` allows fast iteration, safe rollback, and per-user behavior without affecting publishing pipeline.
- **Impact:** `/api/feed` now accepts `X-Anon-User-Id` (or `anon_user_id`) and returns personalization diagnostics; order changes only when `PERSONALIZATION_MODE=active`.
- **Rollback / Alternative:** Set `PERSONALIZATION_MODE=off` and feed reverts to baseline ranking.

## 2026-02-18
- **Decision:** Standardize a reusable personalization QA skill and use low-threshold active mode for test cycles.
- **Context / Problem:** Repeated manual env toggling and verification was error-prone and slow.
- **Rationale:** A dedicated skill/script makes future boost testing fast and consistent.
- **Impact:** Added `skills/personalization-boost-testing/` with a smoke script that sets envs, deploys, verifies debug feed output, and checks Turso event totals.
- **Rollback / Alternative:** Keep manual ad-hoc testing commands only.
