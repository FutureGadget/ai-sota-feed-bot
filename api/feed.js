import fs from 'node:fs';
import path from 'node:path';

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
  const runs = [];

  if (Array.isArray(index) && index.length > 0) {
    for (const row of index) {
      const file = row?.file;
      if (!file) continue;
      const run = readJsonSafe(path.join(runsDir, file), null);
      if (run && Array.isArray(run.items)) runs.push(run);
    }
  } else if (fs.existsSync(runsDir)) {
    const files = fs.readdirSync(runsDir).filter((f) => f.endsWith('.json')).sort().reverse();
    for (const file of files) {
      const run = readJsonSafe(path.join(runsDir, file), null);
      if (run && Array.isArray(run.items)) runs.push(run);
    }
  }

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

  for (const run of runs) {
    const runAt = run?.run_at || null;
    for (const it of run.items || []) {
      const key = `${it.url || ''}::${it.title || ''}`;
      const prev = byKey.get(key);

      if (!prev) {
        byKey.set(key, {
          ...it,
          first_seen: runAt,
          last_seen: runAt,
          seen_count: 1,
        });
      } else {
        prev.seen_count += 1;
        if (runAt && (!prev.first_seen || runAt < prev.first_seen)) prev.first_seen = runAt;
        if (runAt && (!prev.last_seen || runAt > prev.last_seen)) {
          prev.last_seen = runAt;
          prev.why_it_matters = it.why_it_matters || prev.why_it_matters;
          prev.score = it.score ?? prev.score;
          prev.v2_final_score = it.v2_final_score ?? prev.v2_final_score;
          prev.type = it.type || prev.type;
          prev.source = it.source || prev.source;
          prev.maturity = it.maturity || prev.maturity;
        }
      }
    }
  }

  return [...byKey.values()].sort((a, b) => String(b.last_seen || '').localeCompare(String(a.last_seen || '')));
}

export default function handler(req, res) {
  try {
    const from = toIso(req.query?.from);
    const to = toIso(req.query?.to);
    const limit = Math.max(1, Math.min(500, Number.parseInt(String(req.query?.limit || '200'), 10) || 200));

    const runs = readRuns();

    // Backward-compatible latest view when no historical runs are available.
    if (!runs.length) {
      const items = readLatest().slice(0, limit).map((it) => ({ ...it, first_seen: null, last_seen: null, seen_count: 1 }));
      return res.status(200).json({
        mode: 'latest',
        date: new Date().toISOString(),
        filters: { from, to, limit },
        runs: [],
        items,
      });
    }

    const filteredRuns = filterRunsByDate(runs, from, to);
    const runSummaries = filteredRuns.map((r) => ({
      run_at: r.run_at,
      item_count: r.item_count ?? (r.items || []).length,
    }));

    const items = accumulateItems(filteredRuns).slice(0, limit);

    return res.status(200).json({
      mode: 'history',
      date: new Date().toISOString(),
      filters: { from, to, limit },
      runs: runSummaries,
      items,
    });
  } catch (e) {
    res.status(500).json({ error: 'feed_read_failed', detail: String(e) });
  }
}
