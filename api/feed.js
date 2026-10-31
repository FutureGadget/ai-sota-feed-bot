import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

import {
  collapseStoryClusters,
  orderWithEditorialCaps,
  readEditorial,
} from '../lib/editorial.js';

function readJsonSafe(p, fallback) {
  try {
    if (!fs.existsSync(p)) return fallback;
    return JSON.parse(fs.readFileSync(p, 'utf-8'));
  } catch {
    return fallback;
  }
}

function parseDateMaybe(v) {
  if (!v) return null;
  const d = new Date(v);
  return Number.isNaN(d.getTime()) ? null : d;
}

function toIso(v) {
  const d = parseDateMaybe(v);
  return d ? d.toISOString() : null;
}

function parseTimezoneAwareBound(v) {
  if (v == null || v === '') return { value: null, error: null };
  const raw = String(v).trim();
  if (!/(?:z|[+-]\d{2}:\d{2})$/i.test(raw)) {
    return { value: null, error: 'timezone_required' };
  }
  const value = toIso(raw);
  return value
    ? { value, error: null }
    : { value: null, error: 'invalid_timestamp' };
}

// URL-first identity: titles can be rewritten by pipeline enrichment between
// runs (e.g. release titles gaining a repo prefix), but the URL is stable.
function itemKey(it) {
  return String(it?.url || it?.title || '');
}

function normUrl(v) {
  const s = String(v || '').trim();
  return s.endsWith('/') && s.length > 1 ? s.slice(0, -1) : s;
}

function translationKey(it) {
  return normUrl(it?.url) || String(it?.id || it?.title || '').trim();
}

function cleanText(v) {
  return String(v || '').split(/\s+/).filter(Boolean).join(' ');
}

function sourceHash(it) {
  const alsoCovered = Array.isArray(it?.also_covered) ? it.also_covered : [];
  const payload = {
    also_covered: alsoCovered
      .map((entry) => ({
        title: cleanText(entry?.title),
        url: normUrl(entry?.url),
      }))
      .filter((entry) => entry.url || entry.title),
    summary_1line: cleanText(it?.summary_1line),
    title: cleanText(it?.title),
    why_it_matters: cleanText(it?.why_it_matters),
  };
  return crypto
    .createHash('sha256')
    .update(JSON.stringify(payload))
    .digest('hex');
}

function readLatest() {
  const p = path.join(process.cwd(), 'data', 'processed', 'latest.json');
  return readJsonSafe(p, []);
}

// Reader-driven source tuning (pipeline/auto_tune.py output). Exposed so the
// UI can show readers that their clicks/feedback actually move the ranking —
// the reciprocity that keeps the feedback loop fed.
function readReaderTuning() {
  const p = path.join(process.cwd(), 'data', 'feedback', 'source_adjustments.json');
  const data = readJsonSafe(p, null);
  const adj = data?.adjustments;
  if (!adj || typeof adj !== 'object') return null;

  const entries = Object.entries(adj)
    .map(([source, v]) => [String(source), Number(v)])
    .filter(([source, v]) => source && Number.isFinite(v) && v !== 0);
  if (!entries.length) return null;

  return {
    updated_at: data.generated_at || null,
    window_days: data.window_days ?? null,
    adjustments: Object.fromEntries(entries),
    boosted: entries.filter(([, v]) => v > 0).sort((a, b) => b[1] - a[1])
      .map(([source, adjustment]) => ({ source, adjustment })),
    downweighted: entries.filter(([, v]) => v < 0).sort((a, b) => a[1] - b[1])
      .map(([source, adjustment]) => ({ source, adjustment })),
  };
}

function readerTuningSummary(tuning) {
  if (!tuning) return null;
  return {
    updated_at: tuning.updated_at,
    window_days: tuning.window_days,
    boosted: tuning.boosted,
    downweighted: tuning.downweighted,
  };
}

function withReaderAdjustment(it, tuning) {
  const adj = tuning?.adjustments[String(it?.source || '')];
  return adj ? { ...it, reader_adjustment: adj } : it;
}

function readLocalizedFeed(locale) {
  const base = path.join(process.cwd(), 'data', 'i18n', String(locale || ''), 'feed');
  return {
    latest: readJsonSafe(path.join(base, 'latest.json'), null),
    status: readJsonSafe(path.join(base, 'status.json'), null),
  };
}

function localizedSnapshotIsCurrent(snapshot) {
  if (!snapshot || snapshot.is_complete !== true) return false;
  const expiresAt = parseDateMaybe(snapshot.expires_at);
  const sourceRunAt = parseDateMaybe(snapshot.source_run_at);
  const now = new Date();
  if (expiresAt) return expiresAt > now;
  if (!sourceRunAt) return false;
  return now.getTime() - sourceRunAt.getTime() <= 24 * 60 * 60 * 1000;
}

// Budget-governor passthrough (translation-budget-governor plan, Phase 5):
// status.json may now carry `status: "budget_paused"`, `reason`,
// `resumes_at`, `mode` (governor ladder step), and `budget` (ledger
// snapshot). These are optional, pure passthroughs — present when the
// pipeline's governor has written them, absent otherwise (older status.json,
// or governor never engaged).
//
// Note: status.json's `mode` field names the governor step (normal/conserve/
// economy/paused). It is intentionally NOT written to the response's
// top-level `mode` key, which is an established, tested API contract field
// meaning the response shape (`"localized_snapshot"`, per
// docs/product-specs/localized-live-feed.md). The governor step is exposed
// as `governor_mode` instead so both fields coexist without collision.
function localizedStatusBody(body, locale, snapshot, statusPayload) {
  const current = localizedSnapshotIsCurrent(snapshot);
  const status = current ? 'current' : String(statusPayload?.status || 'missing');
  const result = {
    ...body,
    locale,
    mode: 'localized_snapshot',
    status,
    is_current: current,
    is_complete: current,
    source_run_at: snapshot?.source_run_at || statusPayload?.source_run_at || null,
    translated_at: snapshot?.translated_at || statusPayload?.translated_at || null,
    expires_at: snapshot?.expires_at || statusPayload?.expires_at || null,
  };
  if (statusPayload?.reason != null) result.reason = statusPayload.reason;
  if (statusPayload?.resumes_at != null) result.resumes_at = statusPayload.resumes_at;
  if (statusPayload?.mode != null) result.governor_mode = statusPayload.mode;
  if (statusPayload?.budget != null) result.budget = statusPayload.budget;
  return result;
}

// Frozen-snapshot render: when the Korean snapshot is no longer current
// (budget pause or ordinary staleness), serve the last complete snapshot's
// own items as clearly-dated Korean content instead of live English items,
// so the paused /ko/ page still shows articles. Requires snapshots carrying
// target_keys + per-item source_meta (build_localized_feed.py); older
// artifacts return null and keep the previous behavior.
function frozenLocalizedItems(snapshot) {
  const keys = Array.isArray(snapshot?.target_keys) ? snapshot.target_keys : [];
  if (!keys.length) return null;
  const byKey = new Map();
  for (const row of Array.isArray(snapshot?.items) ? snapshot.items : []) {
    const key = normUrl(row?.translation_key || row?.key);
    if (key) byKey.set(key, row);
  }
  const items = [];
  for (const rawKey of keys) {
    const row = byKey.get(normUrl(rawKey));
    if (!row || !row.source_meta) continue;
    items.push({
      id: row.id || null,
      url: row.source_meta.url || row.translation_key || null,
      source: row.source_meta.source || null,
      published: row.source_meta.published || null,
      type: row.source_meta.type || null,
      title: row.title || '',
      summary_1line: row.summary_1line || '',
      why_it_matters: row.why_it_matters || '',
      also_covered: Array.isArray(row.also_covered) ? row.also_covered : [],
    });
  }
  return items.length ? items : null;
}

function overlayLocalizedFeed(body, locale) {
  const { latest, status } = readLocalizedFeed(locale);
  const withStatus = localizedStatusBody(body, locale, latest, status);
  if (!withStatus.is_current) {
    const frozen = frozenLocalizedItems(latest);
    if (frozen) return { ...withStatus, items: frozen, frozen_snapshot: true };
    return withStatus;
  }
  if (!Array.isArray(body?.items)) return withStatus;

  const translations = new Map();
  for (const row of Array.isArray(latest?.items) ? latest.items : []) {
    const key = normUrl(row?.translation_key || row?.key);
    if (key) translations.set(key, row);
  }

  const missing = body.items
    .filter((item) => {
      const key = translationKey(item);
      if (!key || !translations.has(key)) return true;
      const translated = translations.get(key);
      const expectedHash = sourceHash(item);
      return String(translated?.source_hash || '') !== expectedHash;
    })
    .map((item) => translationKey(item));
  if (missing.length) {
    // The live English feed has moved past the snapshot (new/changed items
    // not yet translated — e.g. mid-hour, a failed batch, or a budget pause
    // blocking catch-up). Serve the last complete snapshot as frozen dated
    // content instead of an empty list. During a budget pause, keep the
    // paused status so the shell explains *why* catch-up is not happening.
    const frozen = frozenLocalizedItems(latest);
    const incompleteStatus =
      status?.status === 'budget_paused' ? 'budget_paused' : 'incomplete';
    return {
      ...withStatus,
      status: incompleteStatus,
      is_current: false,
      is_complete: false,
      localized_missing_count: missing.length,
      items: frozen || [],
      ...(frozen ? { frozen_snapshot: true } : {}),
    };
  }

  return {
    ...withStatus,
    items: body.items.map((item) => {
      const translated = translations.get(translationKey(item));
      if (!translated) return item;
      return {
        ...item,
        id: item.id,
        title: translated.title || item.title,
        summary_1line: translated.summary_1line || item.summary_1line,
        why_it_matters: translated.why_it_matters || item.why_it_matters,
      };
    }),
  };
}

function maybeLocalized(body, searchParams) {
  const locale = String(searchParams.get('locale') || '').trim().toLowerCase();
  const localizedSnapshot = String(searchParams.get('localized_snapshot') || '').trim().toLowerCase();
  if (locale !== 'ko' || localizedSnapshot !== 'latest') return { body, cacheControl: null };

  const cacheControl = 's-maxage=300, stale-while-revalidate=300';
  if (['0', 'false', 'no', 'off'].includes(String(process.env.LOCALIZED_FEED_ENABLED || '1').trim().toLowerCase())) {
    return {
      body: {
        ...body,
        locale,
        mode: 'localized_snapshot',
        status: 'disabled',
        is_current: false,
        is_complete: false,
        items: [],
      },
      cacheControl
    };
  }
  return {
    body: overlayLocalizedFeed(body, locale),
    cacheControl
  };
}

function readRuns() {
  const base = path.join(process.cwd(), 'data', 'processed');
  const runsDir = path.join(base, 'runs');
  const indexPath = path.join(base, 'runs_index.json');

  const index = readJsonSafe(indexPath, []);
  const runsByFile = new Map();

  if (Array.isArray(index) && index.length > 0) {
    for (const row of index) {
      const relPath = row?.path || row?.file;
      if (!relPath) continue;
      const run = readJsonSafe(path.join(runsDir, relPath), null);
      if (run && Array.isArray(run.items)) runsByFile.set(relPath, run);
    }
  }

  // Always backfill from runs dir recursively in case index was truncated.
  if (fs.existsSync(runsDir)) {
    const stack = [''];
    const relFiles = [];
    while (stack.length) {
      const rel = stack.pop();
      const abs = path.join(runsDir, rel);
      for (const ent of fs.readdirSync(abs, { withFileTypes: true })) {
        const childRel = rel ? path.join(rel, ent.name) : ent.name;
        if (ent.isDirectory()) stack.push(childRel);
        else if (ent.isFile() && childRel.endsWith('.json')) relFiles.push(childRel);
      }
    }

    relFiles.sort().reverse();
    for (const relPath of relFiles) {
      if (runsByFile.has(relPath)) continue;
      const run = readJsonSafe(path.join(runsDir, relPath), null);
      if (run && Array.isArray(run.items)) runsByFile.set(relPath, run);
    }
  }

  const runs = [...runsByFile.values()];
  return runs.sort((a, b) => String(b.run_at || '').localeCompare(String(a.run_at || '')));
}

function filterRunsByDate(runs, fromIso, toIso) {
  const from = parseDateMaybe(fromIso);
  const to = parseDateMaybe(toIso);

  return runs.filter((r) => {
    const d = parseDateMaybe(r?.run_at);
    if (!d) return false;
    if (from && d < from) return false;
    if (to && d > to) return false;
    return true;
  });
}

// The run window above bounds which snapshots we scan, but a highly-ranked
// item lingers across many runs, so run-based filtering alone lets a story
// published days ago survive a "Past 24h" window. `window=arrival` filters by
// when the story entered the feed (first_seen), which is what the 24-hour
// catch-up promise means: a slow RSS post or arXiv paper published yesterday
// but admitted today is still part of today's feed. The default `published`
// mode keeps calendar date browsing (and the date badge) honest. Items with no
// usable date are kept - we can't prove they're out of window.
function filterItemsByPublishWindow(items, fromIso, toIso, windowMode = 'published') {
  const from = parseDateMaybe(fromIso);
  const to = parseDateMaybe(toIso);
  if (!from && !to) return items;
  const arrival = String(windowMode || '').toLowerCase() === 'arrival';

  return items.filter((it) => {
    const d = arrival
      ? parseDateMaybe(it?.first_seen || it?.published || it?.last_seen)
      : parseDateMaybe(it?.published || it?.first_seen || it?.last_seen);
    if (!d) return true;
    if (from && d < from) return false;
    if (to && d > to) return false;
    return true;
  });
}

function labelsFromItem(it) {
  const labels = new Set();

  const add = (v) => {
    const s = String(v || '').trim().toLowerCase();
    if (!s) return;
    labels.add(s);
  };

  add(it?.llm_category);
  add(it?.v2_slot);
  add(it?.type);
  // Papers and research-lane items belong to the Research lens even when the
  // legacy labeler wrote a coarse `platform` category.
  const typeLabel = String(it?.type || '').trim().toLowerCase();
  const slotLabel = String(it?.v2_slot || '').trim().toLowerCase();
  if (typeLabel === 'paper' || typeLabel === 'research' || slotLabel === 'research_watch') {
    add('research');
  }
  if (isReleaseItem(it)) add('release');

  return [...labels];
}

function parseLabelFilters(searchParams) {
  const vals = [];
  for (const key of ['label', 'labels']) {
    for (const val of searchParams.getAll(key)) {
      if (val) vals.push(...val.split(','));
    }
  }
  return [...new Set(vals.map((s) => String(s || '').trim().toLowerCase()).filter(Boolean))];
}

function isReleaseItem(it) {
  const cat = String(it?.llm_category || '').trim().toLowerCase();
  const type = String(it?.type || '').trim().toLowerCase();
  const summaryPrefix = String(it?.summary_1line || it?.summary || '')
    .slice(0, 2048)
    .replace(/<[^>]*>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .toLowerCase();
  return cat === 'release' || type === 'release' || /^release(?: notes)?:\s/.test(summaryPrefix);
}

// The Brief is release-free. pipeline/release_policy.py still tiers releases
// (major/minor) and ranking boosts major ones so they rank above bare bumps
// inside the Releases lane; that tier does not make an item Brief-eligible.
function isBriefExcludedReleaseItem(it) {
  return isReleaseItem(it);
}

function applyLabelFilter(items, selectedLabels) {
  if (!selectedLabels?.length) return items;
  const selected = new Set(selectedLabels);
  // "brief" is a synthetic lens, not a real item label: the finishable default
  // view = everything except release notes (which live under Releases). Every
  // release item is excluded here; the release tier only orders the Releases
  // lane. It OR-combines with any real labels also selected.
  const briefMode = selected.has('brief');
  return items.filter((it) => {
    if (briefMode && !isBriefExcludedReleaseItem(it)) return true;
    return labelsFromItem(it).some((l) => selected.has(l));
  });
}

// The stable score can put four cards from one source in the five-story front
// page. Keep the pipeline's mix without touching the body: only the top band
// is rebalanced, and only from the cap-compliant prefix, so an over-cap story
// never jumps the fold.
const BRIEF_TOP_BAND = 5;
const BRIEF_MAX_PER_SOURCE = 3;

function balanceTopBand(items, primaryCount, topN = BRIEF_TOP_BAND, maxPerSource = BRIEF_MAX_PER_SOURCE) {
  const list = Array.isArray(items) ? items : [];
  const primary = list.slice(0, Math.max(0, primaryCount));
  const overflow = list.slice(Math.max(0, primaryCount));
  if (primary.length <= maxPerSource) return list;

  const head = primary.slice(0, topN);
  const tail = primary.slice(topN);
  const counts = new Map();
  const out = [];

  for (const item of head) {
    const source = String(item?.source || 'unknown');
    const count = Number(counts.get(source) || 0);
    if (count < maxPerSource || !tail.length) {
      out.push(item);
      counts.set(source, count + 1);
      continue;
    }
    const idx = tail.findIndex((cand) =>
      Number(counts.get(String(cand?.source || 'unknown')) || 0) < maxPerSource);
    if (idx === -1) {
      out.push(item);
      counts.set(source, count + 1);
      continue;
    }
    const replacement = tail[idx];
    tail[idx] = item; // displaced card keeps the promoted card's tail slot
    out.push(replacement);
    const replacementSource = String(replacement?.source || 'unknown');
    counts.set(replacementSource, Number(counts.get(replacementSource) || 0) + 1);
  }

  return out.concat(tail, overflow);
}

function summarizeLabels(items, max = 30) {
  const counts = new Map();
  for (const it of items) {
    for (const l of labelsFromItem(it)) {
      counts.set(l, Number(counts.get(l) || 0) + 1);
    }
  }
  return [...counts.entries()]
    .sort((a, b) => (b[1] - a[1]) || a[0].localeCompare(b[0]))
    .slice(0, Math.max(1, max))
    .map(([label, count]) => ({ label, count }));
}

function itemScore(it) {
  const value = Number(
    it?.global_score ??
      it?.v2_final_score ??
      it?.final_score ??
      it?.score_at_first_seen ??
      it?.utility ??
      it?.score ??
      0
  );
  return Number.isFinite(value) ? value : 0;
}

// The served pool is append-only within its window. Ordering is keyed by the
// score the story had when it FIRST entered the feed, not by the latest run
// that happened to re-select it. A story that the ranker drops on a later
// edition keeps its seat and its position; a new story enters by its own
// first-seen score. This is what stops a refresh from removing or reshuffling
// cards a reader is already looking at.
function accumulateItems(runs) {
  const byKey = new Map();

  runs.forEach((run, runIdx) => {
    const runAt = run?.run_at || null;
    (run.items || []).forEach((it, idx) => {
      const key = itemKey(it);
      const rank = idx + 1; // preserve per-run ranking order from digest output
      const prev = byKey.get(key);

      if (!prev) {
        byKey.set(key, {
          ...it,
          first_seen: runAt,
          last_seen: runAt,
          seen_count: 1,
          last_seen_run_order: runIdx,
          rank_at_first_seen: rank,
          rank_at_last_seen: rank,
          rank_prev_seen: null,
          score_at_first_seen: itemScore(it),
          score_at_last_seen: itemScore(it),
          run_id: it.run_id || it.ingest_batch_id || runAt,
        });
      } else {
        prev.seen_count += 1;
        if (runAt && (!prev.first_seen || runAt < prev.first_seen)) {
          prev.first_seen = runAt;
          prev.rank_at_first_seen = rank;
          prev.score_at_first_seen = itemScore(it);
        }

        const isNewer = runAt && (!prev.last_seen || runAt > prev.last_seen);
        // Runs iterate newest-first, so the second sighting is the
        // chronologically previous run - its rank gives the trend baseline.
        if (!isNewer && prev.rank_prev_seen == null) prev.rank_prev_seen = rank;
        if (isNewer) {
          prev.last_seen = runAt;
          prev.last_seen_run_order = runIdx;
          prev.rank_prev_seen = prev.rank_at_last_seen;
          prev.rank_at_last_seen = rank;
          prev.score_at_last_seen = itemScore(it);
          prev.why_it_matters = it.why_it_matters || prev.why_it_matters;
          prev.summary_1line = it.summary_1line || prev.summary_1line;
          prev.also_covered = it.also_covered || prev.also_covered;
          prev.score = it.score ?? prev.score;
          prev.v2_final_score = it.v2_final_score ?? prev.v2_final_score;
          prev.type = it.type || prev.type;
          prev.source = it.source || prev.source;
          prev.maturity = it.maturity || prev.maturity;
          prev.run_id = it.run_id || it.ingest_batch_id || runAt || prev.run_id;
        }
      }
    });
  });

  return [...byKey.values()].sort((a, b) => {
    const sa = Number(a.score_at_first_seen ?? 0);
    const sb = Number(b.score_at_first_seen ?? 0);
    if (sb !== sa) return sb - sa; // stable quality order at admission

    const fa = String(a.first_seen || '');
    const fb = String(b.first_seen || '');
    if (fa !== fb) return fa.localeCompare(fb); // older admission first on ties

    const ra = Number(a.rank_at_first_seen ?? 9999);
    const rb = Number(b.rank_at_first_seen ?? 9999);
    if (ra !== rb) return ra - rb;

    return String(a.url || '').localeCompare(String(b.url || ''));
  });
}

function coverageScore(it) {
  return itemScore(it);
}

// Normalized-title clustering over the accumulated run pool: distinct outlets
// that ran (near-)identical headlines are one story, so each member can list
// the others as "also covered". Pure + side-effect-free: returns a Map keyed
// by itemKey(it) -> candidate entries[] ({source, url, title<=160}), sorted by
// score desc. Groups only when the shared normalized title is >= 30 chars
// (keeps generic headlines like "openai launches new model" from merging),
// 2..8 members, and >= 2 distinct sources; arXiv papers never cross-link to
// other arXiv listings. Never mutates the input items.
export function clusterCoverage(poolItems) {
  const groups = new Map();
  for (const it of Array.isArray(poolItems) ? poolItems : []) {
    const key = itemKey(it);
    const norm = String(it?.title || '')
      .toLowerCase()
      .replace(/^(?:show\s+)?hn:\s*/, '')
      .replace(/[^a-z0-9]+/g, ' ')
      .trim();
    if (!key || !norm || norm.length < 30) continue;
    const members = groups.get(norm) || [];
    members.push(it);
    groups.set(norm, members);
  }

  const coverage = new Map();
  for (const members of groups.values()) {
    if (members.length < 2 || members.length > 8) continue;
    if (new Set(members.map((m) => String(m?.source || ''))).size < 2) continue;
    for (const it of members) {
      const src = String(it?.source || '');
      const entries = members
        .filter((other) => other !== it && String(other?.source || '') !== src)
        .filter((other) => !(src.startsWith('arxiv_') && String(other?.source || '').startsWith('arxiv_')))
        .sort((a, b) => coverageScore(b) - coverageScore(a))
        .map((other) => ({
          source: String(other?.source || ''),
          url: String(other?.url || ''),
          title: String(other?.title || '').slice(0, 160),
        }));
      if (entries.length) coverage.set(itemKey(it), entries);
    }
  }
  return coverage;
}

function coverageUrlKey(v) {
  const s = String(v || '').trim().toLowerCase().split('?')[0];
  return s.endsWith('/') && s.length > 1 ? s.slice(0, -1) : s;
}

// Merge pipeline-provided also_covered with clustered candidates into a fresh
// array (max 4): deduped on (source, normalized url sans query/trailing slash),
// entries pointing at the item itself dropped either way.
function mergeAlsoCovered(item, clusterEntries) {
  const selfSource = String(item?.source || '');
  const selfUrl = coverageUrlKey(item?.url);
  const seen = new Set();
  const merged = [];
  for (const entry of [
    ...(Array.isArray(item?.also_covered) ? item.also_covered : []),
    ...(Array.isArray(clusterEntries) ? clusterEntries : []),
  ]) {
    const source = String(entry?.source || '');
    const urlKey = coverageUrlKey(entry?.url);
    if (!source || source === selfSource) continue;
    if (urlKey && urlKey === selfUrl) continue;
    const dedupe = `${source}|${urlKey}`;
    if (seen.has(dedupe)) continue;
    seen.add(dedupe);
    merged.push({ source, url: String(entry?.url || ''), title: String(entry?.title || '').slice(0, 160) });
    if (merged.length >= 4) break;
  }
  return merged;
}

// data/processed/runs is bundled at deploy time (vercel.json includeFiles)
// and never rewritten at function runtime - parse + accumulate once per
// process instead of re-walking ~34MB of run snapshots on every request.
// Keyed by cwd because readRuns() resolves data/ relative to it (tests chdir
// into fixture dirs; in production the cwd never changes within a process).
const runsPoolCaches = new Map();

function readRunsPool() {
  const cwd = process.cwd();
  let pool = runsPoolCaches.get(cwd);
  if (!pool) {
    const runs = readRuns();
    const baseItems = accumulateItems(runs);
    // Side-map built once per pool: itemKey -> clustered "also covered"
    // candidates. Keyed by itemKey (the accumulateItems dedupe identity), not
    // object identity, so per-request {...it} response copies can still look
    // their entries up without threading pooled object references around.
    pool = { runs, baseItems, coverageByItem: clusterCoverage(baseItems) };
    runsPoolCaches.set(cwd, pool);
  }
  return pool;
}

// The admitted Brief ledger is the serving source for the default 24h window.
// It is small (a few files), so a process cache keyed by file signatures keeps
// repeated requests cheap without reading the 500-run snapshot pool.
const briefLedgerCaches = new Map();

function readBriefLedger() {
  const cwd = process.cwd();
  const dir = path.join(cwd, 'data', 'brief');
  if (!fs.existsSync(dir)) return null;

  let files = [];
  try {
    files = fs.readdirSync(dir).filter((name) => /^\d{4}-\d{2}-\d{2}\.json$/.test(name)).sort();
  } catch {
    return null;
  }
  if (!files.length) return null;

  let signature = files.join('|');
  try {
    signature = files
      .map((name) => {
        const stat = fs.statSync(path.join(dir, name));
        return `${name}:${stat.mtimeMs}:${stat.size}`;
      })
      .join('|');
  } catch {}
  const cached = briefLedgerCaches.get(cwd);
  if (cached && cached.signature === signature) return cached;

  const byStory = new Map();
  let updatedAt = null;
  for (const name of files) {
    const data = readJsonSafe(path.join(dir, name), null);
    if (!data || !data.items) continue;
    if (data.updated_at && (!updatedAt || String(data.updated_at) > updatedAt)) {
      updatedAt = String(data.updated_at);
    }
    const rows = Array.isArray(data.items) ? data.items : Object.values(data.items);
    for (const row of rows) {
      if (!row || typeof row !== 'object') continue;
      const key = String(row.story_key || row.url || row.title || '');
      if (!key) continue;
      const prev = byStory.get(key);
      if (!prev) {
        byStory.set(key, { ...row });
        continue;
      }
      // Defensive merge: a story admitted near UTC midnight can appear in two
      // files. Keep the latest admission (the writer only re-admits after the
      // previous one has aged out of the 24h window), the latest sighting, and
      // the union of coverage, never a duplicate card.
      const prevAt = parseDateMaybe(prev.admitted_at || prev.first_seen);
      const rowAt = parseDateMaybe(row.admitted_at || row.first_seen);
      if (rowAt && (!prevAt || rowAt > prevAt)) {
        prev.admitted_at = row.admitted_at;
        prev.first_seen = row.first_seen || row.admitted_at;
        prev.score_at_first_seen = row.score_at_first_seen ?? prev.score_at_first_seen;
        prev.rank_at_first_seen = row.rank_at_first_seen ?? prev.rank_at_first_seen;
        prev.utility = row.utility ?? prev.utility;
      }
      const prevLast = parseDateMaybe(prev.last_seen);
      const rowLast = parseDateMaybe(row.last_seen);
      if (rowLast && (!prevLast || rowLast > prevLast)) prev.last_seen = row.last_seen;
      const coverage = [...(Array.isArray(prev.also_covered) ? prev.also_covered : []), ...(Array.isArray(row.also_covered) ? row.also_covered : [])];
      const mergedCoverage = mergeAlsoCovered(prev, coverage);
      if (mergedCoverage.length) prev.also_covered = mergedCoverage;
    }
  }

  const items = [...byStory.values()].sort((a, b) => {
    const ua = Number(a.utility ?? 0);
    const ub = Number(b.utility ?? 0);
    if (ub !== ua) return ub - ua;
    const fa = String(a.admitted_at || a.first_seen || '');
    const fb = String(b.admitted_at || b.first_seen || '');
    if (fa !== fb) return fa.localeCompare(fb);
    return String(a.url || '').localeCompare(String(b.url || ''));
  });
  const result = { items, files, updated_at: updatedAt, signature };
  briefLedgerCaches.set(cwd, result);
  return result;
}

// The ledger is a short retention window. A historical `window=arrival`
// request that starts before the retained files must fall back to the run
// pool (which has the longer first_seen history) instead of returning a
// partial range.
function ledgerCoversWindow(ledger, from, to) {
  if (!ledger || !Array.isArray(ledger.files) || !ledger.files.length) return false;
  const dates = ledger.files
    .map((name) => String(name).replace(/\.json$/, ''))
    .filter(Boolean)
    .sort();
  if (!dates.length) return false;
  const start = dates[0];
  const end = dates[dates.length - 1];
  const dateSet = new Set(dates);
  const fromDate = from ? String(from).slice(0, 10) : start;
  const toDate = to ? String(to).slice(0, 10) : end;
  if (fromDate < start || fromDate > end) return false;
  if (toDate < start || toDate > end) return false;
  if (fromDate > toDate) return false;
  // Every day in the requested span must exist. A missing day (failed write,
  // pruned file) would otherwise serve a partial arrival window silently.
  const last = new Date(`${toDate}T00:00:00Z`);
  for (let day = new Date(`${fromDate}T00:00:00Z`); day <= last; day.setUTCDate(day.getUTCDate() + 1)) {
    if (!dateSet.has(day.toISOString().slice(0, 10))) return false;
  }
  return true;
}

// The ledger branch only needs run timestamps for the "updated X ago" note,
// not the 500 run snapshots themselves.
function readRunIndexSummaries() {
  const index = readJsonSafe(path.join(process.cwd(), 'data', 'processed', 'runs_index.json'), []);
  if (!Array.isArray(index)) return [];
  return index
    .filter((row) => row && row.run_at)
    .map((row) => ({ run_at: row.run_at, item_count: row.item_count ?? 0 }))
    .sort((a, b) => String(b.run_at).localeCompare(String(a.run_at)));
}

// Shared window assembly for the ledger, the run pool, and the no-history
// latest fallback. Keeping one path means the label lens, cap ordering, and
// top-band balance cannot drift between serving sources.
function assembleServedPool(items, { from, to, windowMode, selectedLabels, editorial, readerTuning, limit }) {
  const windowItems = filterItemsByPublishWindow(items, from, to, windowMode);
  const editorialItems = editorial
    ? orderWithEditorialCaps(collapseStoryClusters(windowItems, editorial), editorial)
    : windowItems;
  const mergedWithLabels = editorialItems.map((it) =>
    withReaderAdjustment({ ...it, labels: labelsFromItem(it) }, readerTuning)
  );
  const availableLabels = summarizeLabels(mergedWithLabels);
  const winPool = mergedWithLabels;
  const filtered = applyLabelFilter(mergedWithLabels, selectedLabels);
  const totalItems = filtered.length;
  const firstOverflow = filtered.findIndex((it) => it.beyond_cap);
  const ordered = selectedLabels.includes('brief')
    ? balanceTopBand(filtered, firstOverflow === -1 ? filtered.length : firstOverflow)
    : filtered;
  return {
    items: ordered.slice(0, limit),
    totalItems,
    availableLabels,
    winPool,
    editorialItems,
  };
}

export async function GET(request) {
  try {
    const url = new URL(request.url);
    const fromBound = parseTimezoneAwareBound(url.searchParams.get('from'));
    const toBound = parseTimezoneAwareBound(url.searchParams.get('to'));
    if (fromBound.error || toBound.error) {
      const field = fromBound.error ? 'from' : 'to';
      return Response.json(
        {
          error: fromBound.error || toBound.error,
          field,
          message: `${field} must be a valid ISO timestamp with Z or an explicit UTC offset`,
        },
        { status: 400 }
      );
    }
    const from = fromBound.value;
    const to = toBound.value;
    const requestedWindow = String(url.searchParams.get('window') || 'published').trim().toLowerCase();
    const windowMode = requestedWindow === 'arrival' ? 'arrival' : 'published';
    const limit = Math.max(1, Math.min(500, Number.parseInt(String(url.searchParams.get('limit') || '200'), 10) || 200));
    const selectedLabels = parseLabelFilters(url.searchParams);
    const readerTuning = readReaderTuning();
    const localizedRequested =
      String(url.searchParams.get('locale') || '').trim().toLowerCase() === 'ko'
      && String(url.searchParams.get('localized_snapshot') || '').trim().toLowerCase() === 'latest';
    const effectiveWindow = localizedRequested ? 'published' : windowMode;
    const editorial = localizedRequested ? null : readEditorial();

    // Default 24h path: serve the admission ledger, not the accumulated run
    // pool. The ledger already contains every admitted story (including the
    // keeps that never won an edition), so the run snapshots are only needed
    // for the "updated X ago" timestamps.
    const ledger = effectiveWindow === 'arrival' ? readBriefLedger() : null;
    const usableLedger = ledgerCoversWindow(ledger, from, to) ? ledger : null;
    if (usableLedger) {
      const runSummaries = filterRunsByDate(readRunIndexSummaries(), from, to).map((r) => ({
        run_at: r.run_at,
        item_count: r.item_count ?? 0,
      }));
      const assembled = assembleServedPool(usableLedger.items, {
        from,
        to,
        windowMode: 'arrival',
        selectedLabels,
        editorial,
        readerTuning,
        limit,
      });
      const body = {
        mode: 'history',
        date: new Date().toISOString(),
        filters: { from, to, limit, labels: selectedLabels, window: 'arrival' },
        runs: runSummaries,
        items: assembled.items,
        total_items: assembled.totalItems,
        has_more: assembled.totalItems > limit,
        available_labels: assembled.availableLabels,
        reader_tuning: readerTuningSummary(readerTuning),
        ledger: {
          files: usableLedger.files.length,
          updated_at: usableLedger.updated_at,
          admitted: usableLedger.items.length,
        },
      };
      body.label_counts = Object.fromEntries(['brief', 'platform', 'research', 'release', 'news'].map((s) => [s, applyLabelFilter(assembled.winPool, [s]).length]));
      // The ledger branch is never the localized path (localized requests are
      // forced to `published`), so decorate coverage and return the body
      // directly. The global Vercel API cache header still applies.
      const ledgerCoverage = clusterCoverage(assembled.editorialItems);
      for (const it of body.items) {
        const mergedCoverage = mergeAlsoCovered(it, ledgerCoverage.get(itemKey(it)));
        if (mergedCoverage.length) it.also_covered = mergedCoverage;
      }
      return Response.json(body, { status: 200 });
    }

    const { runs, baseItems, coverageByItem } = readRunsPool();

    // Backward-compatible latest view when no historical runs are available.
    if (!runs.length) {
      const assembled = assembleServedPool(
        readLatest().map((it) => ({ ...it, first_seen: null, last_seen: null, seen_count: 1 })),
        { from, to, windowMode: effectiveWindow, selectedLabels, editorial, readerTuning, limit }
      );
      const body = {
        mode: 'latest',
        date: new Date().toISOString(),
        filters: { from, to, limit, labels: selectedLabels, window: effectiveWindow },
        runs: [],
        items: assembled.items,
        total_items: assembled.totalItems,
        has_more: assembled.totalItems > limit,
        available_labels: assembled.availableLabels,
        reader_tuning: readerTuningSummary(readerTuning),
      };
      body.label_counts = Object.fromEntries(['brief', 'platform', 'research', 'release', 'news'].map((s) => [s, applyLabelFilter(assembled.winPool, [s]).length]));
      const { body: localizedBody, cacheControl } = maybeLocalized(body, url.searchParams);
      // No runs -> the pool-built side map is empty; cluster this fallback's
      // own (small) item list directly. English path only, same reason as the
      // main handler below: ko snapshot hashes pin pooled also_covered.
      if (localizedBody.mode !== 'localized_snapshot' && Array.isArray(localizedBody.items)) {
        const latestCoverage = clusterCoverage(assembled.editorialItems);
        for (const it of localizedBody.items) {
          const mergedCoverage = mergeAlsoCovered(it, latestCoverage.get(itemKey(it)));
          if (mergedCoverage.length) it.also_covered = mergedCoverage;
        }
      }
      const headers = {};
      if (cacheControl) headers['Cache-Control'] = cacheControl;
      return Response.json(localizedBody, { status: 200, headers });
    }

    const filteredRuns = filterRunsByDate(runs, from, to);
    const runSummaries = filteredRuns.map((r) => ({
      run_at: r.run_at,
      item_count: r.item_count ?? (r.items || []).length,
    }));

    // Calendar ranges read the accumulated run pool. first_seen/last_seen/
    // seen_count must reflect an item's true feed-arrival time; bounding the
    // scan by the request window makes an item that drops out and later
    // re-enters look freshly "new" again. The shared assembly below applies
    // the requested window, the editorial mix, and the top-band balance.
    const assembled = assembleServedPool(baseItems, {
      from,
      to,
      windowMode: effectiveWindow,
      selectedLabels,
      editorial,
      readerTuning,
      limit,
    });

    const body = {
      mode: 'history',
      date: new Date().toISOString(),
      filters: { from, to, limit, labels: selectedLabels, window: effectiveWindow },
      runs: runSummaries,
      items: assembled.items,
      total_items: assembled.totalItems,
      has_more: assembled.totalItems > limit,
      available_labels: assembled.availableLabels,
      reader_tuning: readerTuningSummary(readerTuning),
    };
    body.label_counts = Object.fromEntries(['brief', 'platform', 'research', 'release', 'news'].map((s) => [s, applyLabelFilter(assembled.winPool, [s]).length]));
    const { body: localizedBody, cacheControl } = maybeLocalized(body, url.searchParams);
    // Coverage decoration runs AFTER the localized overlay and only on the
    // English path: the ko snapshot's source_hash pins the pipeline's own
    // also_covered entries, so pooled items must reach that hash untouched.
    // The items here are per-request {...it} copies (labels step above), so
    // assigning a fresh also_covered never touches the cached pool.
    if (localizedBody.mode !== 'localized_snapshot' && Array.isArray(localizedBody.items)) {
      for (const it of localizedBody.items) {
        const mergedCoverage = mergeAlsoCovered(it, coverageByItem.get(itemKey(it)));
        if (mergedCoverage.length) it.also_covered = mergedCoverage;
      }
    }
    const headers = {};
    if (cacheControl) headers['Cache-Control'] = cacheControl;
    return Response.json(localizedBody, { status: 200, headers });
  } catch (e) {
    return Response.json({ error: 'feed_read_failed', detail: String(e) }, { status: 500 });
  }
}
