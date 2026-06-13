# Decision Log

## 2026-06-13
- **Decision:** Fix "Catch me up" / "new since last visit" showing outdated articles by dropping `collected_at` from the item-recency fallback in `web/index.html`. Recency now resolves to `first_seen || published` (never `collected_at`), via a shared `itemArrivalMs(it)` helper used by both `isNewSinceLastVisit()` and the catch-up `fresh` filter.
- **Context / Problem:** A reader on the live site saw the "⚡ Catch me up" panel ("Since your last visit (Sat, Jun 13): 12 new stories") list articles published days earlier — e.g. "Access OpenAI models … Oracle" (published Jun 10) and "OpenAI to acquire Ona" (Jun 11). The newness test was `Date.parse(it.first_seen || it.collected_at || it.published)`. `collected_at` is the **pipeline build timestamp** — verified identical (`2026-06-13T22:01:07`) for *every* item in `data/processed/latest.json` and always ≈ now — so it is meaningless as a per-item recency signal. Whenever `first_seen` is absent the chain fell through to `collected_at` and flagged **every** item (any age) as new. `first_seen` is absent exactly on the feed API's no-history `mode: latest` path (`api/feed.js` maps base items with `first_seen: null`). The durable run-history path (`accumulateItems`) does populate `first_seen` (earliest run the item appeared in), which is why the live API currently returns correct Jun-11 values — but the `latest` fallback drops it, and that fallback was what the reader hit.
- **Rationale:** `published` is the article's real timestamp and is reliably present on every item (collector output, tier1, processed all carry it); it is already trusted elsewhere (freshness scoring, the tier1 24h fresh-blend gate). Falling back to `published` instead of `collected_at` makes the feature degrade gracefully in `mode: latest`: an article published before the last visit is no longer mislabeled "new." Empirically, replaying the live `/api/feed` payload with `first_seen` nulled (the bug case) and a Sat-Jun-13 last visit: the old chain flagged **37** "new" (including the Jun 10–11 items); the fixed chain flags **8** and excludes every outdated article. The history path (first_seen present) is unchanged (9 → 9).
- **Impact:** `web/index.html` only — a new `itemArrivalMs()` helper plus the two call sites (`isNewSinceLastVisit`, catch-up `fresh` filter). No API, pipeline, data, or config change. Effect: catch-up and the "N new since your last visit" count stop surfacing stale articles when the feed serves its latest-mode payload.
- **Rollback / Alternative:** Revert the `web/index.html` edit to restore the `|| it.collected_at ||` fallback. Considered-but-deferred alternative: backfill real `first_seen` into the API's `mode: latest` path from the durable story store (`data/stories/`, which keeps the true earliest first_seen per `sid`) so latest-mode has exact arrival times rather than the `published` proxy — a larger change (bundle the story shards into `feed.js`) not needed to resolve the reported symptom.

## 2026-06-14
- **Decision:** Revert the `disable_compression: true` PostHog config added earlier today (PR #106 / commit `46a3cd17`). Restore posthog-js default gzip behavior in `web/index.html`.
- **Context / Problem:** The earlier entry (below) attributed the `/e/` ingestion 503s to PostHog rejecting gzip-compressed bodies. A follow-up investigation showed that root cause was **wrong**. Re-debugging the live site with the `disable_compression` fix already deployed: capture POSTs to `/e/` had no `compression=gzip-js` param (so they were already uncompressed) yet **still returned 503 in the browser** — and the 503s vanished the instant uBlock Origin was disabled. Server-side `curl` probes (no browser, no extension) returned `200 {"status":"Ok"}` for **both** an uncompressed POST **and** a genuine `compression=gzip-js` gzip body, with a valid OPTIONS preflight (200, correct CORS for `www.llm-digest.com`). The probe event landed in the PostHog Activity feed. So PostHog never 503'd on gzip; the 503 is a **synthetic response injected by a content/tracking blocker** (uBlock Origin / EasyPrivacy filters block PostHog's `/e/`, `/i/v0/e/`, and `dead-clicks-autocapture.js` paths; the generically-named `array.js`/`config.js`/`surveys.js` loaders pass, which is what made the loss look partial).
- **Why the earlier diagnosis was wrong:** uBlock was active throughout the earlier session. The "uncompressed POST returns 200 / gzip POST 503s" comparison was a false signal — the manual uncompressed test request didn't match the blocklist the way posthog-js's request did, creating a spurious correlation with compression. The events that "started landing" after the flag were server-side test events, not recovered browser traffic.
- **Rationale:** `disable_compression: true` addressed a non-problem; gzip ingestion works fine. Reverting removes a config line added on a false premise and keeps the decision log accurate so a future PostHog-503 investigation isn't misdirected toward compression. The real lesson: **a tracking 503 that only reproduces in-browser and not via `curl` is almost always a client-side ad/tracking blocker, not a server/encoding bug.**
- **Impact:** `web/index.html` posthog init only (one config line + comment removed). No behavior change for real users — gzip ingestion already returned 200. No pipeline, data, or API change.
- **Follow-up (optional, not done):** If recovering blocker-using visitors matters, the proper fix is a PostHog **reverse proxy** — route events through a first-party path (e.g. `https://www.llm-digest.com/ingest/*` via a `vercel.json` rewrite) so requests aren't matched by tracker blocklists. Tracked as a possible future enhancement, not implemented here.

## 2026-06-14
- ⚠️ **Superseded by the entry above (root cause was wrong).** The 503s were caused by a client-side ad/tracking blocker, not gzip compression. Kept for historical record.
- **Decision:** Disable PostHog client-side request compression by adding `disable_compression: true` to the `posthog.init(...)` config in `web/index.html`.
- **Context / Problem:** Reader analytics stopped landing. Debugging the live site in Chrome showed every event-capture POST to `https://us.i.posthog.com/e/?...&compression=gzip-js` returning **HTTP 503**, with posthog-js retrying (retry_count=1..4) and all retries also 503. The rest of the integration was healthy: scripts loaded (200), the SDK initialized (valid token, correct `api_host`), and the `/flags/` endpoint returned 200. Billing was not the cause — Free plan, only ~1.5K/1M events used this cycle. Isolation tests pinned it to the request body encoding: a **plain (uncompressed) POST** to `/e/` returned `200 {"status":"Ok"}` and a **GET beacon** returned 200, while only the **gzip-js-compressed POST** 503'd. posthog-js v1.386.6 gzips capture bodies by default.
- **Rationale:** PostHog's ingestion endpoint for this project rejects gzip-compressed bodies with 503 but accepts uncompressed ones. Setting `disable_compression: true` makes posthog-js send uncompressed payloads. Validated live in-browser: setting the flag on the running instance made the capture POST return 200 immediately. Our event payloads are tiny, so the bandwidth cost of skipping gzip is negligible. This is the minimal, lowest-risk fix and keeps the analytics loop working regardless of whether the PostHog-side gzip issue is later resolved.
- **Impact:** `web/index.html` posthog init only (one config line + comment). No pipeline, data, or API change. Effect: reader analytics events (`page_view`, `click`, `item_save`, etc.) ingest successfully again.
- **Rollback / Alternative:** Remove the `disable_compression: true` line to restore default gzip behavior (only safe once PostHog stops 503ing compressed bodies). Alternative considered: opening a PostHog support ticket for the gzip 503 — worth doing in parallel, but the client-side flag is the immediate unblock.

## 2026-06-14
- **Decision:** Move the `feed-full-publish.yml` schedule off the top of the hour, from `cron: "0 * * * *"` to `cron: "37 * * * *"`.
- **Context / Problem:** The hourly feed pipeline was firing only ~6×/day instead of 24×. The Actions run list showed the signature of GitHub's best-effort scheduler under load: runs never landed at `:00` (drifting to :14/:23/:33/:44…) and whole hours were silently dropped. Job duration was not the cause — runs that fired completed in 1–4 min, and missing hours showed no run at all, so the loss was at the *dispatch* layer, before a runner is allocated. `:00` is the most congested cron minute on GitHub's shared infrastructure and the most likely to be deprioritized.
- **Rationale:** GitHub's own docs recommend scheduling away from the start of the hour to reduce delay. An odd minute (`:37`) dodges the congestion and recovers most missed runs with a one-line, zero-risk change. A true hourly guarantee would require an external trigger (e.g. a Vercel Cron calling `workflow_dispatch`), deferred as a follow-up since this site already runs on Vercel; the GitHub `schedule` stays as the baseline.
- **Impact:** `.github/workflows/feed-full-publish.yml` cron only. No script, pipeline, or data change. Expected effect: closer-to-hourly cadence; still best-effort, not guaranteed.
- **Rollback / Alternative:** Revert the cron line to `"0 * * * *"`. Alternative (for hard hourly): add an external Vercel-cron → GitHub `workflow_dispatch` ticker; rejected for now as more than the problem warrants.

## 2026-06-14
- **Decision:** Add a free external hourly ticker (cron-job.org) that calls the `feed-full-publish.yml` `workflow_dispatch` endpoint on a real `0 * * * *` tick, documented as a runbook. Keep the GitHub `schedule` (`37 * * * *`) as the baseline fallback.
- **Context / Problem:** The `:37` cron move (entry above) recovers most missed runs but GitHub `schedule` is best-effort by design and still drops hours. We wanted a *guaranteed* hourly trigger at no cost. Vercel Cron was evaluated and rejected: it is free only on the Hobby plan, which caps cron at **once per day** (hourly expressions fail at deploy) and has ±59 min precision; true hourly requires the $20/mo Pro plan.
- **Rationale:** cron-job.org is free, requires no infrastructure to deploy or maintain, and fires from its own scheduler — independent of GitHub's congested shared schedule queue. It authenticates with a GitHub fine-grained PAT scoped to *Actions: write on this repo only*. Running both triggers is safe: `run_full.sh` takes a lock dir, the workflow has a `concurrency` group (`cancel-in-progress: false`), and Tier-0 short-circuits on no-delta, so an overlapping `schedule` + `workflow_dispatch` run no-ops cleanly. A Cloudflare Worker cron was the considered alternative (also free) but rejected for v1 as more moving parts (code to deploy + secret management) than a no-infra hosted ticker.
- **Impact:** No code or workflow change — the trigger lives entirely outside the repo (cron-job.org account + a PAT held there). New runbook `docs/how-to/hourly-trigger-cron-job-org.md` (PAT scopes, exact request, verification, rotation, rollback). Docs: `AGENTS.md` automation table. The PAT is a secret held only in cron-job.org; nothing is committed.
- **Rollback / Alternative:** Delete the cron-job.org job and revoke the PAT — the workflow's own `schedule:` keeps it running best-effort, and there is no in-repo code to revert.

Purpose: preserve key project decisions so we can recover context quickly after resets/new sessions.

## Entry Template
- **Date (KST):** YYYY-MM-DD
- **Decision:**
- **Context / Problem:**
- **Rationale:**
- **Impact:**
- **Rollback / Alternative:**

---

## 2026-06-13
- **Decision:** Raise `google_cloud_blog` `source_bias` from `-0.18` to `-0.12`, giving it a modest edge over `nvidia_blog` (-0.18) and `aws_ml_blog` (-0.20) within the `vendor_general_updates` slot.
- **Context / Problem:** Owner wanted Google Cloud ranked a bit higher than the other cloud vendors because it publishes standards/spec articles (Open Knowledge Format, MCP/A2UI integration, GKE Inference Gateway), which are more platform-engineer-relevant than typical vendor marketing.
- **Rationale:** Keep Google Cloud in the vendor slot (still capped/soft-penalized as a vendor) but let it tend to win the single vendor spot over AWS/NVIDIA when their items compete. Applied in both `config/ranking.yaml` and `config/presets/balanced.yaml`.
- **Impact:** When the vendor slot fills, Google Cloud's standards-oriented posts are favored over AWS/NVIDIA marketing. Slot cap (1 item) and `soft_penalize` unchanged, so the brief stays finishable.
- **Rollback / Alternative:** Restore `google_cloud_blog: -0.18` in both files.

## 2026-06-13
- **Decision:** Add `google_deepmind_blog` source (`deepmind.google/blog/rss.xml`) to the **`frontier_official`** slot, treating Google as a frontier lab on par with OpenAI/Anthropic — not as a promotional vendor.
- **Context / Problem:** The only Google feeds we collected (`google_ai_blog`, `google_cloud_blog`) both sit in the penalized `vendor_general_updates` slot (whole slot capped at 1 item, `base_bias -0.22`, `source_bias -0.18`, `soft_penalize`). That meant genuine frontier launches (Gemini 3.5, Gemma 4) were capped/penalized like marketing. But `blog.google/technology/ai` is mostly consumer PR (Google Search/Finance, state investments), so it is *not* a good frontier source — promoting it would inject marketing into the top of the brief.
- **Rationale:** The clean frontier-lab Google signal lives on the **DeepMind blog** (100 entries: Gemma 4 12B, DiffusionGemma, Gemini 3.5 Live Translate, multi-agent safety research). Wired as a frontier peer: added to `frontier_official` in both `config/ranking.yaml` and `config/presets/balanced.yaml`, with `source_bias 0.10` (matching `openai_blog`) and **no** `soft_penalize`. The slot's `max_per_source` cap (4 canonical / 2 preset) keeps DeepMind's higher post volume from flooding the slot. Existing `google_ai_blog`/`google_cloud_blog` stay in the vendor slot unchanged.
- **Impact:** Google frontier launches now compete in the top-priority slot (no vendor cap), so Gemini/Gemma news can reach the brief instead of losing the single vendor slot. Verified the feed is well-formed RSS (100 items, all with title/link/pubDate) reachable via the standard `type: rss` collector path.
- **Rollback / Alternative:** Remove the `google_deepmind_blog` entries from `sources.yaml`, `ranking.yaml`, and `presets/balanced.yaml`. Alternative considered and rejected: promoting `google_ai_blog` into `frontier_official` (too much consumer-marketing noise).

## 2026-06-13
- **Decision:** Add `google_cloud_blog` source, scoped to the Google Cloud **AI & ML category** RSS feed (`cloudblog.withgoogle.com/products/ai-machine-learning/rss/`), not the general Google Cloud blog.
- **Context / Problem:** Owner requested adding the Google Cloud blog after the "Open Knowledge Format" announcement (2026-06-12); the full blog mixes heavy database/infra/marketing content that dilutes the platform-engineer lens.
- **Rationale:** The category feed keeps AI/ML-relevant items (OKF, GKE Inference Gateway, Confidential AI) while filtering out non-AI noise. Wired like the other cloud-vendor blogs: in the `vendor_general_updates` slot, with a `-0.18` `source_bias` (on par with `nvidia_blog`) and `soft_penalize` in `user_preferences.yaml`, since vendor posts skew promotional.
- **Impact:** New AI items from Google Cloud now enter ranking; capped at 1/slot via `vendor_general_updates` so it can't crowd the brief.
- **Rollback / Alternative:** Remove the four config entries (`sources.yaml`, `ranking.yaml`, `presets/balanced.yaml`, `user_preferences.yaml`), or switch the URL to the full-blog feed if broader coverage is later wanted.

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

## 2026-02-18
- **Decision:** Add label-queryable feed API and web label selector for agent/human exploration.
- **Context / Problem:** Needed better feed queryability without forcing users/agents to parse full payloads manually.
- **Rationale:** Label-based filtering is simple, explainable, and useful across both API consumers and UI users.
- **Impact:** `/api/feed` now supports `label` query filters (multi-select via repeated params or CSV), returns `available_labels` counts, and enriches items with derived `labels`; web UI now exposes multi-select label filter and renders label badges.
- **Rollback / Alternative:** Remove label filter path and rely on date/range-only filtering.

## 2026-02-18
- **Decision:** Expand retention policy for recap readiness (weekly/monthly/yearly) with tiered compaction.
- **Context / Problem:** Previous 3/7 high-resolution window was too short to support recap generation without losing temporal detail.
- **Rationale:** Keep enough recent high-res data for analysis, then downsample long-tail history to bound repository growth.
- **Impact:** Defaults changed to `TIER1_RUN_RETENTION_DAYS=14`, `PROCESSED_RUN_RETENTION_DAYS=45`; prune now compacts older history to daily snapshots, and snapshots older than `WEEKLY_ARCHIVE_AFTER_DAYS=365` to weekly snapshots.
- **Rollback / Alternative:** Revert retention defaults and prune logic to prior daily-only compaction.

## 2026-02-18
- **Decision:** Add optional PostHog dual-tracking on web client while keeping Turso telemetry as source-of-truth.
- **Context / Problem:** Needed page-view/dashboard visibility without replacing existing recommendation feedback pipeline.
- **Rationale:** Parallel tracking enables fast dashboard rollout with low migration risk.
- **Impact:** Added `/api/client-config` for public PostHog runtime config and web events (`page_view`, `feed_view`, `impression_batch`, `click`) behind env toggle.
- **Rollback / Alternative:** Disable via `POSTHOG_ENABLED=0` and continue Turso-only telemetry.

## 2026-06-11
- **Decision:** Ship one-tap reader feedback on feed cards, transported via PostHog and synced back into `data/feedback/events.jsonl`.
- **Context / Problem:** The feedback-loop spec and `data/feedback/events.jsonl` existed, but the only input path was a CLI nobody runs; ranking had zero human signal.
- **Rationale:** Reuse the already-deployed PostHog client as the event transport instead of adding a database or a git-writing endpoint — a daily workflow pulls `item_feedback` events into the repo, matching the existing git-as-database pattern. Feedback compounds: it feeds the v1.3 auto-tuning plan.
- **Impact:** Feed cards show `👍 Useful / 👎 Not relevant / 🫧 Hype` (choice persisted in localStorage, retractable); new `pipeline/feedback.py` (`add` / `summary` / `sync-posthog`); new `.github/workflows/feedback-sync.yml` daily sync that no-ops without PostHog credentials.
- **Rollback / Alternative:** Remove the feedback row from `web/index.html` and disable the sync workflow; events already in `events.jsonl` remain usable.

## 2026-06-11
- **Decision:** Surface trending signals already computed by the feed API as card badges: `🔥 N sources` (cross-source coverage) and `📈 Climbing` (rank improvement).
- **Context / Problem:** `also_covered`, `seen_count`, and `rank_at_last_seen` existed in the API payload but nothing told readers "is this actually important?" at a glance; the API also lacked a previous-rank baseline to derive a trend from.
- **Rationale:** Zero new pipeline work — `accumulateItems` already walks runs newest-first, so the second sighting of an item yields the previous rank (`rank_prev_seen`). Badges keep positive signals only (no "falling" noise) with a ≥2-position climb threshold to avoid jitter.
- **Impact:** `api/feed.js` adds `rank_prev_seen` per item; `web/index.html` renders the two badges in the card meta row with tooltips.
- **Rollback / Alternative:** Remove the badge markup from `cardHtml`; `rank_prev_seen` is additive and harmless to leave in the API.

## 2026-06-11
- **Decision:** Add pinned "my topics" — readers can save the current label selection as a localStorage default that auto-applies when the URL carries no `label` params.
- **Context / Problem:** Label chips existed but reset every visit; returning readers re-built the same filter each time.
- **Rationale:** Defaults belong client-side (no accounts); explicit URL labels must keep winning so shared links render identically for everyone.
- **Impact:** `web/index.html` adds a pin toggle in the chips row (`📌 Pin as default` / `📌 Pinned ✓`), a one-tap `📌 My topics` re-apply chip when filters are cleared, and a `labels_pin` PostHog event (pin/unpin/apply).
- **Rollback / Alternative:** Remove the pin buttons and the pinned-fallback branch in `readFiltersFromUrl`; stored localStorage keys are inert.

## 2026-06-11
- **Decision:** Implement v1.3 source-weight auto-tuning as an additive learned layer (`source_tune`) blending explicit reader feedback with click-through rate.
- **Context / Problem:** Feedback collection shipped but nothing consumed it; explicit taps alone are too low-volume to tune from on day one.
- **Rationale:** Keep hand-tuned `source_bias` (config, committed) separate from learned adjustments (`data/feedback/source_adjustments.json`, runtime artifact) — rollback is deleting a file. CTR blend solves cold start: clicks come from PostHog, but the web client only reports batched impression counts, so exposure is computed locally from `data/processed/runs` snapshots with DCG-style 1/log2(rank+1) weighting. Guardrails: min sample sizes, empirical-Bayes CTR smoothing, hard cap ±0.15 (below hand-tuned bias magnitudes), rolling-window decay, and a ranking-side staleness cutoff (`max_age_days`).
- **Impact:** New `pipeline/auto_tune.py` (`report`/`apply`/`sync-ctr`); `pipeline/ranking.py` stage C adds `source_tune` to slot scores; `config/ranking.yaml` gains an `auto_tune:` section; feedback-sync workflow now also syncs CTR and applies tuning daily; ops daily summary reports top deltas.
- **Rollback / Alternative:** Set `auto_tune.enabled: false` in `config/ranking.yaml` (or delete the adjustments artifact); tuner and data remain inert.

## 2026-06-13
- **Decision:** Lock product positioning to AI platform engineers only, positioned on the jobs incumbent feeds are structurally bad at: finishable daily brief, transparent/anti-hype shared ranking, and memory (storylines, recaps, durable story permalinks). Recorded as a "Product Positioning" section in `AGENTS.md`, with `CLAUDE.md` symlinked to it so coding agents always load it.
- **Context / Problem:** Compared against HN/X/Google News/GeekNews, the site loses on freshness, personalization, and community; broadening the target audience was considered and rejected.
- **Rationale:** Founder-market fit — the owner is an AI platform engineer building from his own need, so founder taste is the quality bar; niche depth compounds (default choice for a narrow audience) while generic AI news re-enters competition with everyone. The perceived weaknesses invert into the position: finishability vs. infinite feeds, transparency vs. filter bubbles, continuity vs. amnesiac timelines.
- **Impact:** `AGENTS.md` gains the positioning section and its implications (copy/source/ranking tuning optimize for the platform-engineer catch-up job; storylines/recaps are the growth artifacts; no community features). New `CLAUDE.md` → `AGENTS.md` symlink.
- **Rollback / Alternative:** Remove the section and symlink; alternative considered was multi-persona positioning via per-audience lens pages (`/for/<persona>`), deferred unless an adjacent practitioner segment is deliberately added later.

## 2026-06-13
- **Decision:** Rewrite `AGENTS.md` as an explicit context cache and refresh the architecture docs it references (`ARCHITECTURE.md`, `docs/ranking-v2-flow.md`, `docs/status/current-system-state.md`, `docs/generated/db-schema.md`, README GitHub Actions section) to match the deployed system.
- **Context / Problem:** The docs lagged the code: they referenced `config/ranking_v2.yaml` / `pipeline/ranking_v2.py` (now `config/ranking.yaml` + presets / `pipeline/ranking.py`), claimed no feedback loop (PostHog → `feedback.py`/`auto_tune.py` runs daily), omitted the two-tier pipeline, story store/storylines/static rendering, `api/` functions, and described `hourly-ingest`/`daily-digest` as the schedulers when `feed-full-publish` (hourly → `run_full.sh`) is the production driver. Agents were re-deriving this every session.
- **Rationale:** AGENTS.md is the caching layer for agent context; a stale cache is worse than none because it sends agents down dead paths (e.g. editing a config file that no longer exists).
- **Impact:** AGENTS.md now carries the system flow, automation table, config/data/web-surface maps, and a Gotchas section (LLM disabled, generated `web/` dirs, `vercel.json` includeFiles coupling, run_full.sh lock/dirty-worktree/no-delta behaviors). `db-schema.md` now documents the real file-based data layout instead of a placeholder.
- **Rollback / Alternative:** Docs-only change; revert the commit. Alternative was incremental patching, rejected because the structure index itself was the stale part.

## 2026-06-13
- **Decision:** Make storyline threading deterministically sound before adding any NLP: collapse re-syndicated copies of a story into one "node" before clustering, and merge candidate threads that share a strong anchor token (not just heavy member overlap). Both in `pipeline/build_storylines.py`.
- **Context / Problem:** Two visible quality failures. (1) Under-merging: "Claude Fable" and "Fable Mythos" rendered as two separate threads for the same Fable 5 launch, because the old merge step only joined clusters sharing >=60% of items. (2) Duplicate aggregation: the same headline re-syndicated across sources — and the same Google-News article resurfacing under different redirect URLs (different sids) — was counted as multiple items/days, manufacturing junk multi-source "storylines" (e.g. "Social Sciences", which was one article counted three times). The output was a mechanical timeline, not a thread a reader could follow.
- **Rationale:** Storylines are a trust surface in a deterministic-ranking product, so precision and a non-inflated source-of-truth matter more than recall. Dedup signature = significant title tokens (`title_tokens`, grammar/hype noise stripped); a smaller signature also folds into a larger one when the only extra tokens are broad company/topic words (`WEAK`), catching "Coding Agents Social Sciences" ≈ "... social sciences - Anthropic". Thread-merge by shared strong anchor token is safe because strong tokens are rare (df-capped) and exclude broad company words, so the bridge is specific (e.g. `fable`) and cannot chain unrelated stories via a generic word like `claude`. Genuine narrative synthesis ("where is this going") is deferred to a future Claude Code agent routine rather than an inline LLM call, keeping the LLM-disabled stance intact.
- **Impact:** `build_storylines.py` now dedups into nodes (`dedup_nodes`) before `cluster`, which thread-merges candidates via union-find. Timeline cards carry a `sources` list when a story ran in multiple places; `web/storyline.html` renders those as multiple source badges on one card instead of duplicate cards. On the current store this took the page from 4 storylines (1 junk, 1 split) to 2 coherent threads — the Fable thread is now 6 items / 5 days from launch → impressions → analysis → access/suspension news. JSON schema is additive (existing fields unchanged; `member_sids`/`member_urls` now flatten across deduped members).
- **Rollback / Alternative:** Revert the `build_storylines.py` + `storyline.html` change; the next pipeline run regenerates `data/storylines/`. Alternatives considered: keep clustering on raw records and only dedup at render time (rejected — leaves inflated item/day/source counts that still manufacture threads); fuzzy title similarity instead of signature equality (rejected for now — harder to reason about, exact significant-token signatures are deterministic and explainable).

## 2026-06-13
- **Decision:** Add a `storyline-editor` agent routine that writes editorial narratives for storylines (TL;DR arc, what's-new, why-it-matters, per-item editor notes), realizing the "genuine narrative synthesis deferred to a future Claude Code agent routine" note from the storyline-threading ADR above. The narrative is a durable **sidecar** (`data/storylines/narratives/<slug>.json`) that the hourly `build_storylines.py` deterministically overlays onto the served files; the LLM never enters the pipeline loop.
- **Context / Problem:** The storyline surface was 100% mechanical — it could thread six Fable articles across five days but never told the reader what *happened* (launch → impressions → controversial terms → access change → suspension). Per-item text was a truncated raw blurb; `why_it_matters` was a deterministic keyword echo. The daily/weekly recap routines already proved the "agent-as-employee, committing-is-publishing, LLM-outside-the-pipeline" pattern; storylines were the highest-value surface still missing it.
- **Rationale:** `build_storylines.py` regenerates `<slug>.json` + `index.json` every hour, so an agent writing into them would be clobbered. A separate sidecar that the pipeline only *reads and overlays* keeps a single served file (no API change for data), survives reclustering, and keeps the deterministic/LLM-disabled stance — the overlay is a plain JSON read + dict merge. Each sidecar carries a `covers_last_updated` + `covers_member_sids` snapshot so the overlay (and the routine's input bundler) can detect when a thread moved on and flag/refresh the narrative; the page shows a stale narrative rather than hiding it. The skill mirrors `daily-summary`/`weekly-summary` (input bundler → agent writes → validate → build → commit) and documents an optional `ultracode` Workflow fan-out (one schema-validated agent per storyline) for when many threads need narrating at once.
- **Impact:** New `.agents/skills/storyline-editor/` (SKILL.md + `build_storyline_input.py`, `validate_narratives.py`, `seed_storyline_sample.py`, `run_storyline.sh`, `storyline_common.py`). `pipeline/build_storylines.py` gains `apply_narrative()` (overlay `editorial` block + per-item `editor_note` onto detail, `{tldr, stale}` teaser onto index). `web/storyline.html` renders the TL;DR/what's-new/why box, editor notes as the lead per-item line, a list-card teaser, and a stale notice. `vercel.json` excludes `data/storylines/{input,narratives}/**` (the API serves only the overlaid `<slug>.json`). Docs: `db-schema.md`, `AGENTS.md`. JSON schema is additive — pages without a narrative render exactly as before.
- **Rollback / Alternative:** Revert `apply_narrative()` (the overlay is the only pipeline coupling) and the `storyline.html` render block; sidecars become inert and the next run regenerates clean `data/storylines/`. Alternatives considered: merge the narrative at API read-time in `api/storylines.js` (rejected — splits logic across JS and needs the sidecar bundled; build-time overlay keeps one source-of-truth file); write narrative directly into `<slug>.json` (rejected — clobbered hourly).

## 2026-06-13
- **Decision:** Add a `storyline-scout` agent routine as a *recall* layer on top of the precision-first deterministic clustering, without letting an LLM decide what becomes a storyline. The scout proposes thread links the anchor-pair rule structurally misses (same story under different vocabulary; emerging near-miss threads); confirmed links are written to a durable sidecar (`data/storylines/scout/links.json`) that `build_storylines.py` applies as synthetic candidates **through the same MIN_ITEMS/MIN_DAYS/MIN_SOURCES floor** — the deterministic gate. Selection that reaches readers always passes that floor, never raw LLM output.
- **Context / Problem:** `build_storylines.py` clusters on shared *rare anchor tokens*, which is deliberately precision-first and therefore misses real threads: a launch covered as "OpenAI's new flagship" and "GPT-5 is here" shares no rare anchor, so the two never join; and a genuinely developing story sitting one item/day/source under the floor never surfaces. We wanted agents to do more of the intelligent work, but replacing the clustering with LLM judgment would break three things: stable membership (slugs carry over by member overlap so follows survive recluster jitter — LLM re-clustering thrashes membership and silently breaks follows), the "one shared deterministic ranking for everyone, not a filter bubble" product belief (a storyline is a trust surface), and the cheap must-stay-green hourly heartbeat (an LLM pass over a 21-day window every hour is real tokens + a new failure mode).
- **Rationale:** Keep deterministic clustering as the spine; add the agent only where LLM judgment beats token-matching (semantic links across vocabulary, near-miss promotion, labeling). The integration mirrors the `storyline-editor` narrative sidecar: a script does the cheap, exact, reproducible prep (`pipeline/scout_candidates.py` enumerates near-miss anchors and broad-token co-mention buckets into a tight bundle — the token-efficiency lever), Haiku subagents do only the judgment on that pre-filtered set ("are these the same story/thread?", high-precision, default-to-no), and the deterministic builder applies confirmed links through the existing floor. A scout link is inert unless its nodes clear the floor, and it joins any candidate it shares a node with (extends an existing thread rather than spawning a duplicate). Threads that used a scout link carry a `via_scout` flag for transparency (anti-hype: show how it was found). Pure-Haiku-without-script was rejected — it pays tokens to read the whole store and badly re-derive cheap deterministic facts (dates/sources/dedup).
- **Impact:** New `pipeline/scout_candidates.py` (deterministic candidate generator → `data/storylines/scout/candidates.json`). `pipeline/build_storylines.py` `cluster()` injects scout links from `scout/links.json` as floor-gated synthetic candidates and sets `via_scout`. New `.agents/skills/storyline-scout/` (SKILL.md + `scout_common.py`, `validate_links.py`, `seed_scout_sample.py`, `run_scout.sh`; documents a Haiku `ultracode` Workflow fan-out with adversarial verification). `web/storyline.html` renders a "🔍 surfaced by scout" badge. `vercel.json` excludes `data/storylines/scout/**`. Docs: `AGENTS.md`, `db-schema.md`. Behavior is unchanged when no links file exists (regression-safe).
- **Rollback / Alternative:** Delete `data/storylines/scout/links.json` (or revert the `cluster()` injection) — the next run regenerates clean threads with zero scout influence. Alternatives considered: let the agent emit storylines directly (rejected — bypasses the floor, destabilizes slugs/follows); apply links at the dedup/node level (rejected for v1 — collapses multi-day arcs into one node; thread-level links keep the timeline intact); fuzzy/embedding similarity in the deterministic layer (rejected — non-explainable on a trust surface; the agent is the judgment layer, gated by the floor).

## 2026-06-13
- **Decision:** Remove `build_storylines.py` from the hourly GitHub Actions feed pipeline and make the external Claude Code storyline routine the sole owner of storyline generation and publishing, scheduled every 5 hours.
- **Context / Problem:** After adding scout and editor agent routines, the hourly `run_full.sh` still rebuilt storyline output mechanically. That split ownership could overwrite or prematurely re-cluster the same served artifacts between agent runs, and made it unclear which automation was authoritative.
- **Rationale:** Keep responsibilities explicit: GitHub Actions continuously collects/ranks news and syncs the durable `data/stories/` input; the Claude Code routine performs the complete storyline transaction (deterministic build, semantic scout, editorial refresh, validation, rebuild, commit, push). A 5-hour cadence is sufficient for the memory/catch-up surface and avoids two automations writing the same files.
- **Impact:** `run_full.sh` no longer invokes `pipeline/build_storylines.py`; no GitHub Actions workflow generates `data/storylines/`. Hourly story-store sync remains, so each Claude routine run sees current source material. Operational docs now identify the Claude routine as the storyline publisher.
- **Rollback / Alternative:** Re-add `python pipeline/build_storylines.py` after `story_store.py sync` in `run_full.sh` to restore hourly mechanical refresh. The alternative of keeping both writers was rejected because ownership and conflict behavior would remain ambiguous.

## 2026-06-13
- **Decision:** Cap `data/tier1/runs/` retention at a **3-day hard delete** (no daily/weekly archive tail), down from "14d high-res + 1/day for a year". Added an optional `max_age_days` hard cutoff to `pipeline/prune_runtime_data.py` and wired `--tier1-max-age-days` (default 3) in `run_full.sh`. Processed snapshots keep their 45d + archive tail unchanged.
- **Context / Problem:** `api/feed.js` and `api/rss.js` bundle `tier1/runs/**` into their Vercel serverless functions (`vercel.json` `includeFiles`). tier1 snapshots are heavy (~1.3–1.7 MB each, ~8/day) and the old retention kept ~14 days high-res then 1/day for a full year — so the dir had grown to ~122 MB and was on track to rebuild the 250 MB function-size failure already fixed once in commit `1fe029de`. A live deploy failure would freeze the site, because each hourly data commit *is* the deploy that ships fresh feed data (no DB).
- **Rationale:** Verified against the consuming code that nothing reads tier1 snapshots older than ~24h: `feed.js readTier1Recent` and `rss.js loadTier1Recent` both use a 24h lookback for the "fresh-blend" overlay, and `mergeTier1Fresh` hard-rejects items older than 24h by publish date (`maxFreshAgeMs`), so even the tunable `tier1_lookback_hours` ceiling (168h) cannot surface older items. RSS's 7-day window is built from `processed/runs` (small files), not tier1. `share.js` resolves share URLs via the durable `stories/index.json` first and only scans the *newest* runs as a fallback, so trimming old tier1 runs is invisible to it. 3 days = the 24h read window plus a generous buffer. The durable memory layer (`stories/`, `storylines/`, `daily/`, `weekly/`) reads none of tier1/runs, so storyline/permalink/recap durability is unaffected. Corrects an earlier mistaken assumption that tier1 needed ≥7 days for RSS.
- **Impact:** Dry run on the current store: tier1 runs 96 → 21 files (75 deleted, ~97 MB freed); bundled tier1 drops ~122 MB → ~31 MB, taking the `feed.js` data bundle from ~158 MB → ~67 MB and restoring comfortable headroom under the 250 MB limit. Zero customer-facing behavior change (feed, fresh-blend, RSS 7-day window, date-range browsing, storylines, permalinks, recaps all identical). Only loss: high-resolution tier1 audit/replay beyond 3 days — an ops artifact no surface reads. Docs: `AGENTS.md`, `docs/generated/db-schema.md`.
- **Known residual:** `feed.js` still clamps `tier1_lookback_hours` to 168h / `tier1_max_runs` to 48 — vestigial ceilings retention can no longer honor, but harmless because `mergeTier1Fresh` filters to 24h publish age. Left as-is to keep the change minimal; could be lowered to ~72h/24 for contract honesty in a separate cleanup.
- **Rollback / Alternative:** Set `TIER1_RUN_MAX_AGE_DAYS=0` (disables the cap) and `TIER1_RUN_RETENTION_DAYS` back to 14 in `run_full.sh`; next run restores the prior retention shape. Deleted snapshots are not recoverable, but nothing reads them. Alternatives considered: drop `tier1/runs/**` from `vercel.json` `includeFiles` entirely and serve only `tier1/latest.json` (rejected — fresh-blend dedupes across the last few runs, so it needs recent run history, just not 100+ MB of it); move served blobs to object storage (rejected as over-engineering for the current size — retention cap is sufficient).

## 2026-06-13
- **Decision:** Give `google_cloud_blog` its own ranking slot (`cloud_platform_updates`, split out of `vendor_general_updates`) and raise `candidate_pool_cap` 120 → 140. Also ship an `add-source` skill so future source additions are validated end-to-end against the exposure gates.
- **Context / Problem:** A genuinely on-mission Google Cloud post ("Introducing the Open Knowledge Format" — an open standard, exactly the platform-engineer signal the feed targets) never reached the feed. Investigation found two compounding causes, not the one first assumed. (1) The post died at the **global `candidate_pool_cap`**, ranking 126th of 215 freshness-survivors when only 120 enter the candidate pool. The prefilter ranks by `freshness + reliability` where the freshness decay is **slot-scaled** (`freshness_hours/3`): frontier_official's 240h window decays ~2.5× slower than vendor/cloud's 96h window, so 64h-old OpenAI posts (score 1.449) crowded out the 27h-old OKF post (1.429). (2) Even had it entered the pool, `google_cloud_blog` was lumped with `google_ai_blog`/`aws_ml_blog`/`nvidia_blog` in `vendor_general_updates`, a "vendor noise, allow 1" slot — so a substantive spec post competed for a single seat against an NVIDIA benchmark PR piece and lost on the keyword-heuristic score. The config's own `source_bias` comment already flagged google_cloud as a standards/spec exception, contradicting its placement in the noise bucket.
- **Rationale:** The slot split removes the contradiction: `cloud_platform_updates` (sources: `[google_cloud_blog]`, min_items 0, max_items 1, base_bias −0.10 vs vendor's −0.22) lets platform-engineering posts (OKF, MCP/A2UI, inference-gateway) earn a seat on merit instead of fighting marketing for one slot; min_items 0 keeps it honest (the source also posts marketing, so nothing is guaranteed). The pool-cap bump to 140 is the minimal value that lets a fresh short-window post clear the global pool (validated: feed 21 → 23, OKF in via `cloud_platform_updates`, NVIDIA still in `vendor_general_updates`). With the LLM disabled the pool only bounds cheap heuristic scoring, so widening it is low-risk; the deeper slot-scaled-decay asymmetry is left documented rather than re-worked, to keep the change small. The recurring lesson — adding/placing a source touches collection, slot mapping, pool cap, slot caps, merge, and top-band before it reaches readers — is captured as a reusable skill (`add-source`) with a `validate_source.py` that reports, for any source, collected? → passed prefilter (or drop reason)? → slot? → in final feed?.
- **Impact:** `config/ranking.yaml` + `config/presets/balanced.yaml`: new `cloud_platform_updates` slot, `google_cloud_blog` removed from `vendor_general_updates`, `base_bias.cloud_platform_updates: -0.10`, `candidate_pool_cap: 140`. New skill `.agents/skills/add-source/` (SKILL.md + `scripts/validate_source.py`), symlinked into `.claude/skills/`. Docs: `docs/ranking-v2-flow.md` (slot list + exposure-gates section), `AGENTS.md` (structure index). No code change to `pipeline/ranking.py`; behavior is config-driven.
- **Rollback / Alternative:** Revert the two config files (re-add `google_cloud_blog` to `vendor_general_updates`, drop the new slot + base_bias, set `candidate_pool_cap: 120`); next run regenerates the feed under the old shape. Alternatives considered: (a) bump `vendor_general_updates.max_items` to 2 — rejected, doesn't reliably surface OKF (it can still lose to google_ai/aws on score) and doesn't address the pool-cap drop; (b) add a keyword classifier routing spec posts to a different slot — rejected, adds logic rather than simplifying; (c) make the prefilter freshness decay uniform/global instead of slot-scaled — the principled fix for the crowd-out asymmetry, but high blast radius (reshuffles the pool for every run), deferred and documented instead.
