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
    prioritySources = ['openai_blog', 'anthropic_newsroom', 'anthropic_engineering', 'anthropic_research', 'claude_blog'],
    priorityMin = 1,
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

  const toFreshItem = (it) => ({
    ...it,
    first_seen: it.collected_at || it.published || null,
    last_seen: it.collected_at || it.published || null,
    seen_count: 1,
    last_seen_run_order: -1,
    rank_at_last_seen: null,
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

    const k = `${it.url || ''}::${it.title || ''}`;
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
    const k = `${it.url || ''}::${it.title || ''}`;
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

function parseLabelFilters(query) {
  const raw = query?.label ?? query?.labels ?? '';
  const arr = Array.isArray(raw) ? raw : String(raw).split(',');
  return [...new Set(arr.map((s) => String(s || '').trim().toLowerCase()).filter(Boolean))];
}

function applyLabelFilter(items, selectedLabels) {
  if (!selectedLabels?.length) return items;
  const selected = new Set(selectedLabels);
  return items.filter((it) => labelsFromItem(it).some((l) => selected.has(l)));
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
    const selectedLabels = parseLabelFilters(req.query);
    const anonUserId = String(req.headers['x-anon-user-id'] || req.query?.anon_user_id || '').trim();
    const debugPersonalization = String(req.query?.debug_personalization || '') === '1';
    const blendTier1 = String(req.query?.blend_tier1 ?? '1') !== '0';
    const tier1FreshCap = Math.max(0, Math.min(20, Number.parseInt(String(req.query?.tier1_fresh_cap || process.env.TIER1_FRESH_CAP || '4'), 10) || 4));
    const tier1InsertAfter = Math.max(0, Math.min(20, Number.parseInt(String(req.query?.tier1_insert_after || process.env.TIER1_INSERT_AFTER || '3'), 10) || 3));
    const tier1MinQuickScore = Number.parseFloat(String(req.query?.tier1_min_quick_score || process.env.TIER1_MIN_QUICK_SCORE || '2.6')) || 2.6;
    const tier1MaxPerSource = Math.max(1, Math.min(3, Number.parseInt(String(req.query?.tier1_max_per_source || process.env.TIER1_MAX_PER_SOURCE || '1'), 10) || 1));
    const tier1PriorityMin = Math.max(0, Math.min(4, Number.parseInt(String(req.query?.tier1_priority_min || process.env.TIER1_PRIORITY_MIN || '1'), 10) || 1));
    const tier1PrioritySources = String(req.query?.tier1_priority_sources || process.env.TIER1_PRIORITY_SOURCES || 'openai_blog,anthropic_newsroom,anthropic_engineering,anthropic_research,claude_blog')
      .split(',')
      .map((s) => String(s || '').trim())
      .filter(Boolean);

    const runs = readRuns();

    // Backward-compatible latest view when no historical runs are available.
    if (!runs.length) {
      const allItems = readLatest().map((it) => ({ ...it, first_seen: null, last_seen: null, seen_count: 1, labels: labelsFromItem(it) }));
      const availableLabels = summarizeLabels(allItems);
      const filteredBase = applyLabelFilter(allItems, selectedLabels);
      const pz = await personalizeItems(filteredBase, { anonUserId, mode: process.env.PERSONALIZATION_MODE || 'shadow', debug: debugPersonalization, maxItems: limit });
      return res.status(200).json({
        mode: 'latest',
        date: new Date().toISOString(),
        filters: { from, to, limit, labels: selectedLabels },
        runs: [],
        items: pz.items,
        available_labels: availableLabels,
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
          prioritySources: tier1PrioritySources,
          priorityMin: tier1PriorityMin,
        })
      : { items: baseItems, added: 0 };

    const mergedWithLabels = merged.items.map((it) => ({ ...it, labels: labelsFromItem(it) }));
    const availableLabels = summarizeLabels(mergedWithLabels);
    const filteredMerged = applyLabelFilter(mergedWithLabels, selectedLabels);

    const pz = await personalizeItems(filteredMerged, { anonUserId, mode: process.env.PERSONALIZATION_MODE || 'shadow', debug: debugPersonalization, maxItems: limit });

    return res.status(200).json({
      mode: 'history',
      date: new Date().toISOString(),
      filters: { from, to, limit, labels: selectedLabels },
      runs: runSummaries,
      items: pz.items,
      available_labels: availableLabels,
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
          priority_min: tier1PriorityMin,
          priority_sources: tier1PrioritySources,
        },
      },
    });
  } catch (e) {
    res.status(500).json({ error: 'feed_read_failed', detail: String(e) });
  }
}
