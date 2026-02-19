import fs from 'node:fs';
import path from 'node:path';

function esc(s = '') {
  return String(s)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&apos;');
}

function readJsonSafe(p, fallback = []) {
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
  return Number.isFinite(d.getTime()) ? d : null;
}

function loadRunsIndex() {
  const p = path.join(process.cwd(), 'data', 'processed', 'runs_index.json');
  return readJsonSafe(p, []);
}

function loadTier1Recent({ lookbackMs, maxRuns = 12 } = {}) {
  const base = path.join(process.cwd(), 'data', 'tier1');
  const indexPath = path.join(base, 'runs_index.json');
  const index = readJsonSafe(indexPath, []);
  const now = Date.now();

  const selected = (Array.isArray(index) ? index : [])
    .filter((row) => {
      const d = parseDateMaybe(row?.run_at);
      return !!d && (now - d.getTime()) <= lookbackMs;
    })
    .sort((a, b) => String(b?.run_at || '').localeCompare(String(a?.run_at || '')))
    .slice(0, maxRuns);

  const byKey = new Map();
  for (const row of selected) {
    const rel = row?.path || row?.file;
    if (!rel) continue;
    const run = readJsonSafe(path.join(base, 'runs', rel), null);
    if (!run || !Array.isArray(run.items)) continue;
    for (const it of run.items) {
      const key = it.url || it.title || '';
      if (!key || byKey.has(key)) continue;
      byKey.set(key, { ...it, tier_hint: 'tier1_fresh' });
    }
  }
  return [...byKey.values()];
}

function getRecentItems() {
  const now = Date.now();
  const windowMs = 7 * 24 * 60 * 60 * 1000;
  const fromMs = now - windowMs;

  // 1. Collect processed items from recent runs
  const runsIndex = loadRunsIndex();
  const byUrl = new Map();

  for (const row of runsIndex) {
    const runDate = parseDateMaybe(row?.run_at);
    if (!runDate || runDate.getTime() < fromMs) continue;

    const rel = row?.path || row?.file;
    if (!rel) continue;
    const runFile = path.join(process.cwd(), 'data', 'processed', 'runs', rel);
    const data = readJsonSafe(runFile, null);
    if (!data || !Array.isArray(data.items || data)) continue;
    const items = Array.isArray(data.items) ? data.items : data;

    for (const it of items) {
      const key = (it.url || '').trim();
      if (!key || byUrl.has(key)) continue;
      byUrl.set(key, {
        ...it,
        first_seen: it.collected_at || it.published || row.run_at || null,
        last_seen: row.run_at || it.collected_at || it.published || null,
      });
    }
  }

  // Also include latest.json as fallback
  const latest = readJsonSafe(path.join(process.cwd(), 'data', 'processed', 'latest.json'), []);
  for (const it of latest) {
    const key = (it.url || '').trim();
    if (!key || byUrl.has(key)) continue;
    byUrl.set(key, it);
  }

  // 2. Blend tier1 fresh items (24h lookback for fresh blend)
  const tier1Items = loadTier1Recent({ lookbackMs: 24 * 60 * 60 * 1000, maxRuns: 12 });
  const prioritySources = new Set(['openai_blog', 'anthropic_newsroom', 'anthropic_engineering', 'anthropic_research', 'claude_blog']);

  const tier1Fresh = tier1Items
    .filter((it) => {
      const key = (it.url || '').trim();
      if (!key || byUrl.has(key)) return false;
      const score = Number(it.tier1_quick_score ?? it.score ?? 0);
      return score >= 2.6;
    })
    .sort((a, b) => {
      const ap = prioritySources.has(a.source) ? 1 : 0;
      const bp = prioritySources.has(b.source) ? 1 : 0;
      if (ap !== bp) return bp - ap;
      return (b.tier1_quick_score ?? 0) - (a.tier1_quick_score ?? 0);
    })
    .slice(0, 4);

  for (const it of tier1Fresh) {
    const key = (it.url || '').trim();
    byUrl.set(key, it);
  }

  // 3. Sort by score descending
  return [...byUrl.values()].sort((a, b) => {
    const sa = Number(a.v2_final_score ?? a.score ?? a.tier1_quick_score ?? 0);
    const sb = Number(b.v2_final_score ?? b.score ?? b.tier1_quick_score ?? 0);
    return sb - sa;
  });
}

export default function handler(req, res) {
  try {
    const items = getRecentItems();
    const now = new Date().toUTCString();
    const site = 'https://ai-sota-feed-bot.vercel.app';

    const xmlItems = items.map((it) => {
      const image = String(it.image_url || '').trim();
      const enclosure = image ? `\n  <enclosure url="${esc(image)}" type="image/jpeg"/>` : '';
      const pubDate = parseDateMaybe(it.published || it.first_seen || it.collected_at);
      const pubDateStr = pubDate ? `\n  <pubDate>${pubDate.toUTCString()}</pubDate>` : '';
      const source = it.source ? `\n  <category>${esc(it.source)}</category>` : '';

      return `\n<item>\n  <title>${esc(it.title || 'Untitled')}</title>\n  <link>${esc(it.url || site)}</link>\n  <guid>${esc(it.url || `${site}/#${it.id || it.title || ''}`)}</guid>\n  <description>${esc(it.summary_1line || it.why_it_matters || '')}</description>${pubDateStr}${source}${enclosure}\n</item>`;
    }).join('');

    const xml = `<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0">\n<channel>\n  <title>AI Feed</title>\n  <link>${site}</link>\n  <description>AI platform engineering feed — rolling 7-day window</description>\n  <lastBuildDate>${now}</lastBuildDate>${xmlItems}\n</channel>\n</rss>`;

    res.setHeader('Content-Type', 'application/rss+xml; charset=utf-8');
    res.setHeader('Cache-Control', 's-maxage=300, stale-while-revalidate=600');
    res.status(200).send(xml);
  } catch (e) {
    res.status(500).json({ error: 'rss_build_failed', detail: String(e) });
  }
}
