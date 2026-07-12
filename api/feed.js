import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

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

function localizedStatusBody(body, locale, snapshot, statusPayload) {
  const current = localizedSnapshotIsCurrent(snapshot);
  const status = current ? 'current' : String(statusPayload?.status || 'missing');
  return {
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
}

function overlayLocalizedFeed(body, locale) {
  const { latest, status } = readLocalizedFeed(locale);
  const withStatus = localizedStatusBody(body, locale, latest, status);
  if (!withStatus.is_current || !Array.isArray(body?.items)) return withStatus;

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
    return {
      ...withStatus,
      status: 'incomplete',
      is_current: false,
      is_complete: false,
      localized_missing_count: missing.length,
      items: [],
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

function readTier1Latest() {
  const p = path.join(process.cwd(), 'data', 'tier1', 'latest.json');
  return readJsonSafe(p, []);
}

function readTier1Recent({ lookbackHours = 24, maxRuns = 12 } = {}) {
  const base = path.join(process.cwd(), 'data', 'tier1');
  const runsDir = path.join(base, 'runs');
  const indexPath = path.join(base, 'runs_index.json');
  const index = readJsonSafe(indexPath, []);

  const now = Date.now();
  const lookbackMs = Math.max(1, Number(lookbackHours || 24)) * 60 * 60 * 1000;
  const selected = (Array.isArray(index) ? index : [])
    .filter((row) => {
      const d = parseDateMaybe(row?.run_at);
      return !!d && (now - d.getTime()) <= lookbackMs;
    })
    .sort((a, b) => String(b?.run_at || '').localeCompare(String(a?.run_at || '')))
    .slice(0, Math.max(1, Number(maxRuns || 12)));

  const byKey = new Map();
  for (const row of selected) {
    const rel = row?.path || row?.file;
    if (!rel) continue;
    const run = readJsonSafe(path.join(runsDir, rel), null);
    if (!run || !Array.isArray(run.items)) continue;

    for (const it of run.items) {
      const key = itemKey(it);
      if (!key || byKey.has(key)) continue;
      byKey.set(key, { ...it, run_at: run?.run_at || null });
    }
  }

  if (byKey.size > 0) return [...byKey.values()];
  return readTier1Latest();
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
// published days ago survive a "Today" window. Filter the assembled items by
// the SAME date the card displays (published, then first_seen, then last_seen)
// so the timeframe reflects publish age and never contradicts the date badge.
// Items with no usable date are kept — we can't prove they're out of window.
function filterItemsByPublishWindow(items, fromIso, toIso) {
  const from = parseDateMaybe(fromIso);
  const to = parseDateMaybe(toIso);
  if (!from && !to) return items;

  return items.filter((it) => {
    const d = parseDateMaybe(it?.published || it?.first_seen || it?.last_seen);
    if (!d) return true;
    if (from && d < from) return false;
    if (to && d > to) return false;
    return true;
  });
}

function mergeTier1Fresh(baseItems, tier1Items, deepRunAtIso, opts = {}) {
  const {
    freshCap = 4,
    insertAfter = 3,
    minQuickScore = 2.6,
    maxPerSource = 1,
    prioritySources = ['openai_blog', 'anthropic_newsroom', 'anthropic_engineering', 'anthropic_research', 'claude_blog'],
    priorityMin = 1,
  } = opts;

  if (!Array.isArray(tier1Items) || !tier1Items.length || !deepRunAtIso) {
    return { items: baseItems, added: 0 };
  }

  const deepRunAt = parseDateMaybe(deepRunAtIso);
  if (!deepRunAt) return { items: baseItems, added: 0 };

  const byKey = new Set(baseItems.map((it) => itemKey(it)));
  const sourceCounts = new Map();

  const maxFreshAgeMs = 24 * 60 * 60 * 1000; // items older than 24h by publish date are not "fresh"
  const nowMs = Date.now();

  const fresh = tier1Items
    .filter((it) => {
      const collected = parseDateMaybe(it?.collected_at);
      const published = parseDateMaybe(it?.published);
      const d = collected || published;
      const quick = Number(it?.tier1_quick_score || 0);
      if (!d || d <= deepRunAt || quick < minQuickScore) return false;
      // Reject items with old publish dates — they aren't truly fresh
      if (published && (nowMs - published.getTime()) > maxFreshAgeMs) return false;
      // Skip routine version releases (e.g. "v2.1.39", "vllm 0.105.0") — low
      // signal for the fresh lane. Titles may carry a repo-name prefix added
      // by pipeline enrichment, so match on the release-tag URL + a version
      // pattern rather than the title starting with a version.
      const title = String(it?.title || '');
      const isReleaseTag = /\/releases\/tag\//i.test(String(it?.url || ''));
      if (/^\d+\.\d+\.\d+/.test(title) || /^v\d+\.\d+/.test(title)) return false;
      if (isReleaseTag && /(?:^|\s)v?\d+\.\d+/.test(title)) return false;
      return true;
    })
    .sort((a, b) => Number(b?.tier1_quick_score || 0) - Number(a?.tier1_quick_score || 0));

  const toFreshItem = (it) => ({
    ...it,
    first_seen: it.collected_at || it.published || null,
    last_seen: it.collected_at || it.published || null,
    seen_count: 1,
    last_seen_run_order: -1,
    rank_at_last_seen: null,
    rank_prev_seen: null,
    score_at_last_seen: Number(it.tier1_quick_score ?? it.score ?? 0),
    tier_hint: 'tier1_fresh',
  });

  const picked = [];
  const prioritySet = new Set((Array.isArray(prioritySources) ? prioritySources : []).map((s) => String(s || '').trim()).filter(Boolean));

  // Pass 1: keep a small guaranteed lane for priority sources.
  for (const it of fresh) {
    if (picked.length >= Math.max(0, freshCap)) break;
    if (picked.length >= Math.max(0, priorityMin)) break;

    const src = String(it?.source || 'unknown');
    if (!prioritySet.has(src)) continue;

    const k = itemKey(it);
    if (!k || byKey.has(k)) continue;
    const cur = Number(sourceCounts.get(src) || 0);
    if (cur >= Math.max(1, maxPerSource)) continue;

    byKey.add(k);
    sourceCounts.set(src, cur + 1);
    picked.push(toFreshItem(it));
  }

  // Pass 2: normal best-score fill.
  for (const it of fresh) {
    if (picked.length >= Math.max(0, freshCap)) break;
    const k = itemKey(it);
    if (!k || byKey.has(k)) continue;

    const src = String(it?.source || 'unknown');
    const cur = Number(sourceCounts.get(src) || 0);
    if (cur >= Math.max(1, maxPerSource)) continue;

    byKey.add(k);
    sourceCounts.set(src, cur + 1);
    picked.push(toFreshItem(it));
  }

  const at = Math.max(0, Math.min(baseItems.length, Number(insertAfter || 0)));
  const merged = [...baseItems.slice(0, at), ...picked, ...baseItems.slice(at)];
  return { items: merged, added: picked.length };
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
  return cat === 'release' || type === 'release';
}

function applyLabelFilter(items, selectedLabels) {
  if (!selectedLabels?.length) return items;
  const selected = new Set(selectedLabels);
  // "brief" is a synthetic lens, not a real item label: the finishable default
  // view = everything except release notes (which live under the Releases tab).
  // It OR-combines with any real labels also selected.
  const briefMode = selected.has('brief');
  return items.filter((it) => {
    if (briefMode && !isReleaseItem(it)) return true;
    return labelsFromItem(it).some((l) => selected.has(l));
  });
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
          rank_at_last_seen: rank,
          rank_prev_seen: null,
          score_at_last_seen: Number(it.v2_final_score ?? it.score ?? 0),
          run_id: it.run_id || it.ingest_batch_id || runAt,
        });
      } else {
        prev.seen_count += 1;
        if (runAt && (!prev.first_seen || runAt < prev.first_seen)) prev.first_seen = runAt;

        const isNewer = runAt && (!prev.last_seen || runAt > prev.last_seen);
        // Runs iterate newest-first, so the second sighting is the
        // chronologically previous run — its rank gives the trend baseline.
        if (!isNewer && prev.rank_prev_seen == null) prev.rank_prev_seen = rank;
        if (isNewer) {
          prev.last_seen = runAt;
          prev.last_seen_run_order = runIdx;
          prev.rank_prev_seen = prev.rank_at_last_seen;
          prev.rank_at_last_seen = rank;
          prev.score_at_last_seen = Number(it.v2_final_score ?? it.score ?? prev.score_at_last_seen ?? 0);
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
    const ro = Number(a.last_seen_run_order ?? 9999) - Number(b.last_seen_run_order ?? 9999);
    if (ro !== 0) return ro; // newer run first

    const ra = Number(a.rank_at_last_seen ?? 9999);
    const rb = Number(b.rank_at_last_seen ?? 9999);
    if (ra !== rb) return ra - rb; // within run, preserve ranking order

    return Number(b.score_at_last_seen ?? 0) - Number(a.score_at_last_seen ?? 0);
  });
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
    const limit = Math.max(1, Math.min(500, Number.parseInt(String(url.searchParams.get('limit') || '200'), 10) || 200));
    const selectedLabels = parseLabelFilters(url.searchParams);
    const blendTier1 = String(url.searchParams.get('blend_tier1') ?? '1') !== '0';
    const tier1FreshCap = Math.max(0, Math.min(20, Number.parseInt(String(url.searchParams.get('tier1_fresh_cap') || process.env.TIER1_FRESH_CAP || '4'), 10) || 4));
    const tier1InsertAfter = Math.max(0, Math.min(20, Number.parseInt(String(url.searchParams.get('tier1_insert_after') || process.env.TIER1_INSERT_AFTER || '3'), 10) || 3));
    const tier1MinQuickScore = Number.parseFloat(String(url.searchParams.get('tier1_min_quick_score') || process.env.TIER1_MIN_QUICK_SCORE || '2.6')) || 2.6;
    const tier1MaxPerSource = Math.max(1, Math.min(3, Number.parseInt(String(url.searchParams.get('tier1_max_per_source') || process.env.TIER1_MAX_PER_SOURCE || '1'), 10) || 1));
    const tier1PriorityMin = Math.max(0, Math.min(4, Number.parseInt(String(url.searchParams.get('tier1_priority_min') || process.env.TIER1_PRIORITY_MIN || '1'), 10) || 1));
    const tier1PrioritySources = String(url.searchParams.get('tier1_priority_sources') || process.env.TIER1_PRIORITY_SOURCES || 'openai_blog,anthropic_newsroom,anthropic_engineering,anthropic_research,claude_blog')
      .split(',')
      .map((s) => String(s || '').trim())
      .filter(Boolean);

    const runs = readRuns();
    const readerTuning = readReaderTuning();

    // Backward-compatible latest view when no historical runs are available.
    if (!runs.length) {
      const allItems = readLatest().map((it) =>
        withReaderAdjustment({ ...it, first_seen: null, last_seen: null, seen_count: 1, labels: labelsFromItem(it) }, readerTuning));
      const availableLabels = summarizeLabels(allItems);
      const filteredBase = applyLabelFilter(allItems, selectedLabels);
      const totalItems = filteredBase.length;
      const body = {
        mode: 'latest',
        date: new Date().toISOString(),
        filters: { from, to, limit, labels: selectedLabels },
        runs: [],
        items: filteredBase.slice(0, limit),
        total_items: totalItems,
        has_more: totalItems > limit,
        available_labels: availableLabels,
        reader_tuning: readerTuningSummary(readerTuning),
      };
      const { body: localizedBody, cacheControl } = maybeLocalized(body, url.searchParams);
      const headers = {};
      if (cacheControl) headers['Cache-Control'] = cacheControl;
      return Response.json(localizedBody, { status: 200, headers });
    }

    const filteredRuns = filterRunsByDate(runs, from, to);
    const runSummaries = filteredRuns.map((r) => ({
      run_at: r.run_at,
      item_count: r.item_count ?? (r.items || []).length,
    }));

    // Accumulate over the FULL run history, not just the requested from/to
    // window. first_seen/last_seen/seen_count must reflect an item's true
    // feed-arrival time; bounding the scan by the request window makes an
    // item that drops out of the ranked window and later re-enters look
    // freshly "new" again (its earliest occurrence inside the window becomes
    // its computed first_seen), resurfacing old/already-seen stories in the
    // "New" badge and "Catch me up" brief. filterItemsByPublishWindow below
    // still applies the requested window to what's actually displayed.
    const baseItems = accumulateItems(runs);
    const deepRunAt = filteredRuns?.[0]?.run_at || null;
    const tier1LookbackHours = Math.max(1, Math.min(168, Number.parseInt(String(url.searchParams.get('tier1_lookback_hours') || process.env.TIER1_BLEND_LOOKBACK_HOURS || '24'), 10) || 24));
    const tier1MaxRuns = Math.max(1, Math.min(48, Number.parseInt(String(url.searchParams.get('tier1_max_runs') || process.env.TIER1_BLEND_MAX_RUNS || '12'), 10) || 12));
    const tier1Latest = blendTier1 ? readTier1Recent({ lookbackHours: tier1LookbackHours, maxRuns: tier1MaxRuns }) : [];
    const merged = blendTier1
      ? mergeTier1Fresh(baseItems, tier1Latest, deepRunAt, {
          freshCap: tier1FreshCap,
          insertAfter: tier1InsertAfter,
          minQuickScore: tier1MinQuickScore,
          maxPerSource: tier1MaxPerSource,
          prioritySources: tier1PrioritySources,
          priorityMin: tier1PriorityMin,
        })
      : { items: baseItems, added: 0 };

    const mergedWithLabels = merged.items.map((it) =>
      withReaderAdjustment({ ...it, labels: labelsFromItem(it) }, readerTuning));
    const availableLabels = summarizeLabels(mergedWithLabels);
    const labelFiltered = applyLabelFilter(mergedWithLabels, selectedLabels);
    const filteredMerged = filterItemsByPublishWindow(labelFiltered, from, to);
    const totalItems = filteredMerged.length;

    const body = {
      mode: 'history',
      date: new Date().toISOString(),
      filters: { from, to, limit, labels: selectedLabels },
      runs: runSummaries,
      items: filteredMerged.slice(0, limit),
      total_items: totalItems,
      has_more: totalItems > limit,
      available_labels: availableLabels,
      reader_tuning: readerTuningSummary(readerTuning),
      tier1_blend: {
        enabled: blendTier1,
        fresh_added: merged.added,
        deep_run_at: deepRunAt,
        config: {
          fresh_cap: tier1FreshCap,
          insert_after: tier1InsertAfter,
          min_quick_score: tier1MinQuickScore,
          max_per_source: tier1MaxPerSource,
          priority_min: tier1PriorityMin,
          priority_sources: tier1PrioritySources,
          lookback_hours: tier1LookbackHours,
          max_runs: tier1MaxRuns,
        },
      },
    };
    const { body: localizedBody, cacheControl } = maybeLocalized(body, url.searchParams);
    const headers = {};
    if (cacheControl) headers['Cache-Control'] = cacheControl;
    return Response.json(localizedBody, { status: 200, headers });
  } catch (e) {
    return Response.json({ error: 'feed_read_failed', detail: String(e) }, { status: 500 });
  }
}
