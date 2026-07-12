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

const DATA = path.join(process.cwd(), 'data');

// Pick the index entry with the largest value of `field` (lexical compare works
// for ISO dates / YYYY-MM-DD), so we never depend on the index sort order.
function newestBy(entries, field) {
  let best = null;
  for (const e of Array.isArray(entries) ? entries : []) {
    const v = e && typeof e[field] === 'string' ? e[field] : '';
    if (v && (!best || v > best[field])) best = e;
  }
  return best;
}

function latestDaily() {
  const idx = readJsonSafe(path.join(DATA, 'daily', 'index.json'), []);
  const top = newestBy(idx, 'date');
  if (!top) return null;
  return { date: top.date || null, generated_at: top.generated_at || null };
}

function latestWeekly() {
  const idx = readJsonSafe(path.join(DATA, 'weekly', 'index.json'), []);
  const top = newestBy(idx, 'end');
  if (!top) return null;
  return { week: top.week || null, end: top.end || null, generated_at: top.generated_at || null };
}

function latestStorylines() {
  const idx = readJsonSafe(path.join(DATA, 'storylines', 'index.json'), null);
  if (!idx || !Array.isArray(idx.storylines)) return null;
  // `last_updated` is content-based (latest item in any thread) and only moves
  // when a thread actually gets new material — unlike `generated_at`, which the
  // 5-hourly rebuild bumps every run. Read-history dots key off this.
  let latest = null;
  for (const s of idx.storylines) {
    const t = s && s.last_updated ? Date.parse(s.last_updated) : NaN;
    if (Number.isFinite(t) && (latest === null || t > latest)) latest = t;
  }
  return {
    generated_at: idx.generated_at || null,
    last_updated: latest !== null ? new Date(latest).toISOString() : null,
  };
}

function latestPlaybook() {
  // Editions are dated like the daily recap; `date` is the period and
  // `generated_at` the content signal the read-history dot keys off.
  const idx = readJsonSafe(path.join(DATA, 'playbook', 'index.json'), []);
  const top = newestBy(idx, 'date');
  if (!top) return null;
  return { date: top.date || null, generated_at: top.generated_at || null };
}

function latestMap() {
  const idx = readJsonSafe(path.join(DATA, 'wiki', 'index.json'), null);
  if (!idx || !idx.nodes || typeof idx.nodes !== 'object') return null;
  // Per-node `updated` (YYYY-MM-DD) reflects real page edits and survives
  // rebuilds; `index.generated_at` changes on every compile, so we ignore it.
  let updated = '';
  for (const n of Object.values(idx.nodes)) {
    const u = n && typeof n.updated === 'string' ? n.updated : '';
    if (u && u > updated) updated = u;
  }
  return { updated: updated || null };
}

function latestFoundations() {
  const idx = readJsonSafe(path.join(DATA, 'foundations', 'index.json'), null);
  if (!idx || !idx.concepts || typeof idx.concepts !== 'object') return null;
  // Per-concept `updated` (YYYY-MM-DD) reflects real page edits and survives
  // rebuilds; `index.generated_at` changes on every compile, so we ignore it.
  let updated = '';
  for (const c of Object.values(idx.concepts)) {
    const u = c && typeof c.updated === 'string' ? c.updated : '';
    if (u && u > updated) updated = u;
  }
  return { updated: updated || null };
}

// GET /api/updates -> lightweight freshness signals powering the nav "new
// updates" dots and the feed's "New for you" strip. Daily/weekly/playbook
// carry period fields so the client can apply a time-aware staleness gate;
// storylines/map/foundations expose content-based timestamps for pure
// read-history comparison.
export function GET(request) {
  try {
    return Response.json({
      now: new Date().toISOString(),
      daily: latestDaily(),
      weekly: latestWeekly(),
      storylines: latestStorylines(),
      playbook: latestPlaybook(),
      map: latestMap(),
      foundations: latestFoundations(),
    });
  } catch (e) {
    return Response.json({ error: 'updates_read_failed', detail: String(e) }, { status: 500 });
  }
}
