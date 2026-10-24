import fs from 'node:fs';
import path from 'node:path';

import {
  applyEditorialCaps,
  collapseStoryClusters,
  readEditorial,
} from '../lib/editorial.js';

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

  // 2. Order reverse-chronologically. RSS / agent consumers treat feed order as
  //    recency; sorting by score buried fresh items under days-old high-score
  //    ones, so an agent pulling the feed saw "outdated" results even though the
  //    underlying data was current. Score is only a tiebreaker now.
  const bestDate = (it) =>
    parseDateMaybe(it.published) ||
    parseDateMaybe(it.first_seen) ||
    parseDateMaybe(it.collected_at) ||
    parseDateMaybe(it.last_seen);

  return [...byUrl.values()].sort((a, b) => {
    const da = bestDate(a)?.getTime() ?? 0;
    const db = bestDate(b)?.getTime() ?? 0;
    if (db !== da) return db - da;
    const sa = Number(a.v2_final_score ?? a.score ?? 0);
    const sb = Number(b.v2_final_score ?? b.score ?? 0);
    return sb - sa;
  });
}

// An RSS feed is a recency surface, not the full archive. Cap the item count so
// agents get a focused "what's new" view instead of a 7-day score dump.
const RSS_MAX_ITEMS = 50;

export function GET(request) {
  try {
    const editorial = readEditorial();
    const items = collapseStoryClusters(applyEditorialCaps(getRecentItems(), editorial), editorial)
      .slice(0, RSS_MAX_ITEMS);
    const now = new Date().toUTCString();
    const site = process.env.SITE_BASE_URL || 'https://www.llm-digest.com';

    const xmlItems = items.map((it) => {
      const image = String(it.image_url || '').trim();
      const enclosure = image ? `\n  <enclosure url="${esc(image)}" type="image/jpeg"/>` : '';
      const pubDate = parseDateMaybe(it.published || it.first_seen || it.collected_at);
      const pubDateStr = pubDate ? `\n  <pubDate>${pubDate.toUTCString()}</pubDate>` : '';
      const source = it.source ? `\n  <category>${esc(it.source)}</category>` : '';

      return `\n<item>\n  <title>${esc(it.title || 'Untitled')}</title>\n  <link>${esc(it.url || site)}</link>\n  <guid>${esc(it.url || `${site}/#${it.id || it.title || ''}`)}</guid>\n  <description>${esc(it.summary_1line || it.why_it_matters || '')}</description>${pubDateStr}${source}${enclosure}\n</item>`;
    }).join('');

    const xml = `<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n<channel>\n  <title>LLM Digest</title>\n  <link>${site}</link>\n  <atom:link href="${site}/rss.xml" rel="self" type="application/rss+xml"/>\n  <description>AI platform &amp; agent engineering feed — rolling 7-day window</description>\n  <lastBuildDate>${now}</lastBuildDate>\n  <ttl>30</ttl>${xmlItems}\n</channel>\n</rss>`;

    return new Response(xml, {
      status: 200,
      headers: {
        'Content-Type': 'application/rss+xml; charset=utf-8',
        'Cache-Control': 's-maxage=300, stale-while-revalidate=600',
      }
    });
  } catch (e) {
    return Response.json({ error: 'rss_build_failed', detail: String(e) }, { status: 500 });
  }
}
