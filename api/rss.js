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

function readLatest() {
  const p = path.join(process.cwd(), 'data', 'processed', 'latest.json');
  if (!fs.existsSync(p)) return [];
  return JSON.parse(fs.readFileSync(p, 'utf-8'));
}

export default function handler(req, res) {
  try {
    const items = readLatest();
    const now = new Date().toUTCString();
    const site = process.env.VERCEL_URL ? `https://${process.env.VERCEL_URL}` : 'https://example.com';
    const xmlItems = items.map((it) => {
      const image = String(it.image_url || '').trim();
      const enclosure = image ? `\n  <enclosure url="${esc(image)}" type="image/jpeg"/>` : '';
      return `\n<item>\n  <title>${esc(it.title || 'Untitled')}</title>\n  <link>${esc(it.url || site)}</link>\n  <guid>${esc(it.url || `${site}/#${it.id || it.title || ''}`)}</guid>\n  <description>${esc(it.summary_1line || it.why_it_matters || '')}</description>${enclosure}\n</item>`;
    }).join('');

    const xml = `<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0">\n<channel>\n  <title>AI Feed</title>\n  <link>${site}</link>\n  <description>AI platform engineering feed</description>\n  <lastBuildDate>${now}</lastBuildDate>${xmlItems}\n</channel>\n</rss>`;

    res.setHeader('Content-Type', 'application/rss+xml; charset=utf-8');
    res.status(200).send(xml);
  } catch (e) {
    res.status(500).json({ error: 'rss_build_failed', detail: String(e) });
  }
}
