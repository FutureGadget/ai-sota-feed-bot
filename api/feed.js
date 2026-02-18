import fs from 'node:fs';
import path from 'node:path';
import { personalizeItems } from '../lib/personalization.js';

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

function readLatest() {
  const p = path.join(process.cwd(), 'data', 'processed', 'latest.json');
  return readJsonSafe(p, []);
}

function readTier1Latest() {
  const p = path.join(process.cwd(), 'data', 'tier1', 'latest.json');
  return readJsonSafe(p, []);
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

function mergeTier1Fresh(baseItems, tier1Items, deepRunAtIso, opts = {}) {
  const {
    freshCap = 4,
    insertAfter = 3,
    minQuickScore = 2.6,
    maxPerSource = 1,
  } = opts;

  if (!Array.isArray(tier1Items) || !tier1Items.length || !deepRunAtIso) {
    return { items: baseItems, added: 0 };
  }

  const deepRunAt = parseDateMaybe(deepRunAtIso);
  if (!deepRunAt) return { items: baseItems, added: 0 };

  const byKey = new Set(baseItems.map((it) => `${it.url || ''}::${it.title || ''}`));
  const sourceCounts = new Map();

  const fresh = tier1Items
    .filter((it) => {
      const collected = parseDateMaybe(it?.collected_at);
      const published = parseDateMaybe(it?.published);
      const d = collected || published;
      const quick = Number(it?.tier1_quick_score || 0);
      return !!d && d > deepRunAt && quick >= minQuickScore;
    })
    .sort((a, b) => Number(b?.tier1_quick_score || 0) - Number(a?.tier1_quick_score || 0));

  const picked = [];
  for (const it of fresh) {
    if (picked.length >= Math.max(0, freshCap)) break;
    const k = `${it.url || ''}::${it.title || ''}`;
    if (!k || byKey.has(k)) continue;

    const src = String(it?.source || 'unknown');
    const cur = Number(sourceCounts.get(src) || 0);
    if (cur >= Math.max(1, maxPerSource)) continue;

    byKey.add(k);
    sourceCounts.set(src, cur + 1);
    picked.push({
      ...it,
      first_seen: it.collected_at || it.published || null,
      last_seen: it.collected_at || it.published || null,
      seen_count: 1,
      last_seen_run_order: -1,
      rank_at_last_seen: null,
      score_at_last_seen: Number(it.tier1_quick_score ?? it.score ?? 0),
      tier_hint: 'tier1_fresh',
    });
  }

  const at = Math.max(0, Math.min(baseItems.length, Number(insertAfter || 0)));
  const merged = [...baseItems.slice(0, at), ...picked, ...baseItems.slice(at)];
  return { items: merged, added: picked.length };
}

function accumulateItems(runs) {
  const byKey = new Map();

  runs.forEach((run, runIdx) => {
    const runAt = run?.run_at || null;
    (run.items || []).forEach((it, idx) => {
      const key = `${it.url || ''}::${it.title || ''}`;
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
          score_at_last_seen: Number(it.v2_final_score ?? it.score ?? 0),
          run_id: it.run_id || it.ingest_batch_id || runAt,
        });
      } else {
        prev.seen_count += 1;
        if (runAt && (!prev.first_seen || runAt < prev.first_seen)) prev.first_seen = runAt;

        const isNewer = runAt && (!prev.last_seen || runAt > prev.last_seen);
        if (isNewer) {
          prev.last_seen = runAt;
          prev.last_seen_run_order = runIdx;
          prev.rank_at_last_seen = rank;
          prev.score_at_last_seen = Number(it.v2_final_score ?? it.score ?? prev.score_at_last_seen ?? 0);
          prev.why_it_matters = it.why_it_matters || prev.why_it_matters;
          prev.summary_1line = it.summary_1line || prev.summary_1line;
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

export default async function handler(req, res) {
  try {
    const from = toIso(req.query?.from);
    const to = toIso(req.query?.to);
    const limit = Math.max(1, Math.min(500, Number.parseInt(String(req.query?.limit || '200'), 10) || 200));
    const anonUserId = String(req.headers['x-anon-user-id'] || req.query?.anon_user_id || '').trim();
    const debugPersonalization = String(req.query?.debug_personalization || '') === '1';
    const blendTier1 = String(req.query?.blend_tier1 ?? '1') !== '0';
    const tier1FreshCap = Math.max(0, Math.min(20, Number.parseInt(String(req.query?.tier1_fresh_cap || process.env.TIER1_FRESH_CAP || '4'), 10) || 4));
    const tier1InsertAfter = Math.max(0, Math.min(20, Number.parseInt(String(req.query?.tier1_insert_after || process.env.TIER1_INSERT_AFTER || '3'), 10) || 3));
    const tier1MinQuickScore = Number.parseFloat(String(req.query?.tier1_min_quick_score || process.env.TIER1_MIN_QUICK_SCORE || '2.6')) || 2.6;
    const tier1MaxPerSource = Math.max(1, Math.min(3, Number.parseInt(String(req.query?.tier1_max_per_source || process.env.TIER1_MAX_PER_SOURCE || '1'), 10) || 1));

    const runs = readRuns();

    // Backward-compatible latest view when no historical runs are available.
    if (!runs.length) {
      const baseItems = readLatest().map((it) => ({ ...it, first_seen: null, last_seen: null, seen_count: 1 }));
      const pz = await personalizeItems(baseItems, { anonUserId, mode: process.env.PERSONALIZATION_MODE || 'shadow', debug: debugPersonalization, maxItems: limit });
      return res.status(200).json({
        mode: 'latest',
        date: new Date().toISOString(),
        filters: { from, to, limit },
        runs: [],
        items: pz.items,
        personalization: pz.diagnostics,
      });
    }

    const filteredRuns = filterRunsByDate(runs, from, to);
    const runSummaries = filteredRuns.map((r) => ({
      run_at: r.run_at,
      item_count: r.item_count ?? (r.items || []).length,
    }));

    const baseItems = accumulateItems(filteredRuns);
    const deepRunAt = filteredRuns?.[0]?.run_at || null;
    const tier1Latest = blendTier1 ? readTier1Latest() : [];
    const merged = blendTier1
      ? mergeTier1Fresh(baseItems, tier1Latest, deepRunAt, {
          freshCap: tier1FreshCap,
          insertAfter: tier1InsertAfter,
          minQuickScore: tier1MinQuickScore,
          maxPerSource: tier1MaxPerSource,
        })
      : { items: baseItems, added: 0 };

    const pz = await personalizeItems(merged.items, { anonUserId, mode: process.env.PERSONALIZATION_MODE || 'shadow', debug: debugPersonalization, maxItems: limit });

    return res.status(200).json({
      mode: 'history',
      date: new Date().toISOString(),
      filters: { from, to, limit },
      runs: runSummaries,
      items: pz.items,
      personalization: pz.diagnostics,
      tier1_blend: {
        enabled: blendTier1,
        fresh_added: merged.added,
        deep_run_at: deepRunAt,
        config: {
          fresh_cap: tier1FreshCap,
          insert_after: tier1InsertAfter,
          min_quick_score: tier1MinQuickScore,
          max_per_source: tier1MaxPerSource,
        },
      },
    });
  } catch (e) {
    res.status(500).json({ error: 'feed_read_failed', detail: String(e) });
  }
}
