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
    const pz = await personalizeItems(baseItems, { anonUserId, mode: process.env.PERSONALIZATION_MODE || 'shadow', debug: debugPersonalization, maxItems: limit });

    return res.status(200).json({
      mode: 'history',
      date: new Date().toISOString(),
      filters: { from, to, limit },
      runs: runSummaries,
      items: pz.items,
      personalization: pz.diagnostics,
    });
  } catch (e) {
    res.status(500).json({ error: 'feed_read_failed', detail: String(e) });
  }
}
