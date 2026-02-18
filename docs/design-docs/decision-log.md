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

## 2026-02-18
- **Decision:** Introduce Tier-1 fast data lane as Phase-1 migration step (without changing Tier-0 publish flow yet).
- **Context / Problem:** Full runs are too slow/costly for higher freshness cadence; we need faster updates without LLM/publish overhead.
- **Rationale:** Separate cheap, frequent ingest+quick-score artifacts from slower decorated Tier-0 processing.
- **Impact:** Added `pipeline/build_tier1.py` and `run_tier1_fast.sh` to produce `data/tier1/latest.json` plus run snapshots/index.
- **Rollback / Alternative:** Keep single-lane pipeline and adjust cron frequency only.

## 2026-02-18
- **Decision:** Schedule Tier-1 fast lane every 30 minutes and blend Tier-1 fresh items into `/api/feed` ahead of deep-ranked items.
- **Context / Problem:** Needed quicker UX freshness between 3x/day Tier-0 publish runs.
- **Rationale:** Frequent cheap updates improve perceived freshness while preserving slower high-quality curation path.
- **Impact:** Added cron job `AI Feed Tier1 Fast 30m`; `/api/feed` now returns `tier1_blend` diagnostics and prepends fresh Tier-1 non-duplicate items.
- **Rollback / Alternative:** Disable Tier-1 cron and call `/api/feed?blend_tier1=0`.

## 2026-02-18
- **Decision:** Make Tier-0 digest pipeline consume Tier-1 as default input (`TIER0_INPUT=tier1`).
- **Context / Problem:** Tier-0 still depended directly on raw ingest artifacts, limiting separation between fast and decorated lanes.
- **Rationale:** Tier-1 should be ingestion source-of-truth; Tier-0 should focus on decoration/reranking/publishing.
- **Impact:** `build_digest.py` now loads Tier-1 by default with automatic raw fallback and logs selected input mode.
- **Rollback / Alternative:** Set `TIER0_INPUT=raw`.

## 2026-02-18
- **Decision:** Surface Tier-1 freshness explicitly in UI with metadata note and per-item badge.
- **Context / Problem:** Users need visible confirmation that feed freshness improved before deep ranking finishes.
- **Rationale:** Explicit UX cues reduce confusion and make two-tier data model understandable.
- **Impact:** Header now shows fresh count when Tier-1 blend adds items; blended items show `⚡ Fresh (awaiting deep rank)` badge.
- **Rollback / Alternative:** Hide tier hints and rely on silent ordering only.

## 2026-02-18
- **Decision:** Add source crawl cooldown for frequent Tier-1 runs, with explicit bypass for full/dev runs.
- **Context / Problem:** 30-minute ingest cadence risks over-crawling sources and wasting quota while data is unchanged.
- **Rationale:** Respect source cadence and reduce unnecessary fetches/cost without sacrificing full-run quality.
- **Impact:** `collect.py` now supports per-source/global poll interval (`poll_interval_minutes` / `COLLECT_DEFAULT_POLL_MINUTES`) and emits `skipped_cooldown`; `run_tier1_fast.sh` uses default 30m cooldown, `run_full.sh` and `run_dev.sh` bypass via `COLLECT_BYPASS_COOLDOWN=1`.
- **Rollback / Alternative:** Set cooldown minutes to 0 or always bypass cooldown.

## 2026-02-18
- **Decision:** Tone down Tier-1 fresh dominance with insertion and quality guardrails.
- **Context / Problem:** Fresh lane was overly dominant when prepended at top with high cap.
- **Rationale:** Keep freshness visible without destabilizing overall quality ranking.
- **Impact:** Tier-1 blend now defaults to cap=4, inserts after top-3, enforces minimum quick score, and limits one fresh item per source.
- **Rollback / Alternative:** Disable blend (`blend_tier1=0`) or restore previous prepend behavior.

## 2026-02-18
- **Decision:** Split batch identity from deep-run identity in telemetry context (`ingest_batch_id` first).
- **Context / Problem:** Frequent Tier-1 runs make a single deep `run_id` insufficient for precise behavior analysis.
- **Rationale:** Per-item ingest batch identity preserves event lineage under high-frequency ingestion.
- **Impact:** Collector writes `ingest_batch_id`; feed API carries per-item `run_id`; web impression/click telemetry uses item-level batch/run context.
- **Rollback / Alternative:** Keep deep-run-only IDs and infer batch lineage heuristically.

## 2026-02-18
- **Decision:** Add Tier-0 incremental delta diagnostics with optional no-delta short-circuit.
- **Context / Problem:** Tier-0 still runs full heavy path even when Tier-1 introduces little or no new data.
- **Rationale:** Measure delta size every run and enable safe skip behavior behind explicit flag.
- **Impact:** `build_digest.py` now logs previous processed run time and `delta_items`; optional `TIER0_INCREMENTAL_SKIP_NO_DELTA=1` can skip no-delta rebuilds.
- **Rollback / Alternative:** Set `TIER0_INCREMENTAL=0` and always run full Tier-0.

## 2026-02-18
- **Decision:** Enable no-delta skip behavior by default for scheduled full runs.
- **Context / Problem:** Running publish pipeline with unchanged Tier-0 data wastes compute and causes redundant publishes.
- **Rationale:** If Tier-0 has no delta, skip publish actions safely and keep schedule for eventual deltas.
- **Impact:** `run_full.sh` now defaults `TIER0_INCREMENTAL=1` and `TIER0_INCREMENTAL_SKIP_NO_DELTA=1`; when no delta is detected it exits with `FULL_RUN_NO_DELTA_SKIP=true` before issue/telegram publish.
- **Rollback / Alternative:** Set `TIER0_INCREMENTAL_SKIP_NO_DELTA=0` when invoking `run_full.sh`.

## 2026-02-18
- **Decision:** Make full runs respect crawl cooldown by default, with explicit force-bypass switch.
- **Context / Problem:** Full runs were still always fetching all sources before discovering no Tier-0 delta.
- **Rationale:** Respecting cooldown lowers crawl pressure and compute while preserving an explicit emergency refresh path.
- **Impact:** `run_full.sh` now uses `FULL_RUN_BYPASS_COOLDOWN` (default `0`); set `FULL_RUN_BYPASS_COOLDOWN=1` for forced full fetch.
- **Rollback / Alternative:** Revert to unconditional collector bypass in full runs.

## 2026-02-18
- **Decision:** Force full-run pipeline to produce Tier-1 first and feed Tier-0 from Tier-1 explicitly.
- **Context / Problem:** Full runs occasionally fell back to raw input when Tier-1 artifact was absent locally, weakening lane separation.
- **Rationale:** A deterministic lane order (`collect -> tier1 -> tier0`) guarantees consistent source-of-truth and simpler ops reasoning.
- **Impact:** `run_full.sh` now runs `build_tier1.py`, checks `data/tier1/latest.json`, and invokes `build_digest.py` with `TIER0_INPUT=tier1`.
- **Rollback / Alternative:** Remove forced Tier-1 pre-step and rely on Tier-0 raw fallback.

## 2026-02-18
- **Decision:** Add retention/compaction policy for runtime run snapshots and enforce it in full runs.
- **Context / Problem:** Increased run frequency grows `data/processed/runs/*` and `data/tier1/runs/*` rapidly, bloating repo history.
- **Rationale:** Keep recent high-resolution history while compacting older runs to one snapshot per day.
- **Impact:** Added `pipeline/prune_runtime_data.py`; `run_full.sh` now prunes processed/tier1 run snapshots before runtime commit using configurable retention windows.
- **Rollback / Alternative:** Disable prune step and retain all run snapshots.

## 2026-02-18
- **Decision:** Add daily ops summary utility + reusable skill for ongoing validation.
- **Context / Problem:** Needed quick visibility into run cadence, cooldown effects, and lane health without manual log digging.
- **Rationale:** A structured summary improves day-to-day operations and helps tune skip/cooldown behavior safely.
- **Impact:** Added `pipeline/ops_daily_summary.py` and `skills/ops-daily-summary/` with a one-command runbook.
- **Rollback / Alternative:** Continue ad-hoc checks from raw files and cron transcripts.
