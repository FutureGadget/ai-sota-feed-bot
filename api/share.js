import fs from 'node:fs';
import path from 'node:path';

// Share permalink endpoint (served at /s?u=<encoded source url>).
//
// The feed's share button used to share the source article URL directly, so
// every share sent readers to the source site. This endpoint makes shares
// land on llm-digest.com instead: crawlers/unfurlers get item-specific Open
// Graph tags (title + why-it-matters), humans get redirected to the live
// feed with the story highlighted (/?item=<url>&utm_source=share).
//
// The item is looked up by URL in the same data the feed serves. If it has
// aged out of retention, the page degrades to a generic site card and still
// redirects to the feed — never to an unvalidated external URL.

const SITE_BASE_URL = process.env.SITE_BASE_URL || 'https://www.llm-digest.com';
const SITE_NAME = 'LLM Digest';
const MAX_RUNS_SCANNED = 60;

function readJsonSafe(p, fallback) {
  try {
    if (!fs.existsSync(p)) return fallback;
    return JSON.parse(fs.readFileSync(p, 'utf-8'));
  } catch {
    return fallback;
  }
}

function esc(v) {
  return String(v ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function normUrl(v) {
  const s = String(v || '').trim();
  return s.endsWith('/') && s.length > 1 ? s.slice(0, -1) : s;
}

function parseTargetUrl(raw) {
  try {
    const u = new URL(String(raw || ''));
    if (u.protocol === 'http:' || u.protocol === 'https:') return u.href;
  } catch {}
  return null;
}

function* candidateItemLists() {
  const cwd = process.cwd();
  yield readJsonSafe(path.join(cwd, 'data', 'processed', 'latest.json'), []);
  yield readJsonSafe(path.join(cwd, 'data', 'tier1', 'latest.json'), []);

  for (const [dir, indexName] of [
    ['processed', 'runs_index.json'],
    ['tier1', 'runs_index.json'],
  ]) {
    const base = path.join(cwd, 'data', dir);
    const index = readJsonSafe(path.join(base, indexName), []);
    const rows = (Array.isArray(index) ? index : [])
      .sort((a, b) => String(b?.run_at || '').localeCompare(String(a?.run_at || '')))
      .slice(0, MAX_RUNS_SCANNED);
    for (const row of rows) {
      const rel = row?.path || row?.file;
      if (!rel) continue;
      const run = readJsonSafe(path.join(base, 'runs', rel), null);
      const items = Array.isArray(run?.items) ? run.items : Array.isArray(run) ? run : [];
      if (items.length) yield items;
    }
  }
}

function findItemByUrl(targetUrl) {
  const target = normUrl(targetUrl);
  if (!target) return null;
  for (const items of candidateItemLists()) {
    for (const it of items) {
      if (it && normUrl(it.url) === target) return it;
    }
  }
  return null;
}

function sharePage({ title, description, canonical, redirect, sourceUrl, sourceName }) {
  const sourceLink = sourceUrl
    ? `<p class="muted">Original story: <a href="${esc(sourceUrl)}" rel="noopener">${esc(sourceName || sourceUrl)}</a></p>`
    : '';
  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>${esc(title)} | ${esc(SITE_NAME)}</title>
  <meta name="description" content="${esc(description)}" />
  <meta name="robots" content="noindex" />
  <link rel="canonical" href="${esc(canonical)}" />
  <meta property="og:type" content="article" />
  <meta property="og:site_name" content="${esc(SITE_NAME)}" />
  <meta property="og:title" content="${esc(title)}" />
  <meta property="og:description" content="${esc(description)}" />
  <meta property="og:url" content="${esc(canonical)}" />
  <meta name="twitter:card" content="summary" />
  <meta name="twitter:title" content="${esc(title)}" />
  <meta name="twitter:description" content="${esc(description)}" />
  <style>
    body { font-family: system-ui, sans-serif; max-width: 640px; margin: 3rem auto; padding: 0 1rem; line-height: 1.5; }
    .muted { color: #6b7280; font-size: 0.92rem; }
    a { color: #2563eb; }
  </style>
  <script>window.location.replace(${JSON.stringify(redirect)});</script>
</head>
<body>
  <h1>${esc(title)}</h1>
  ${description ? `<p>${esc(description)}</p>` : ''}
  <p><a href="${esc(redirect)}">Continue to ${esc(SITE_NAME)} →</a></p>
  ${sourceLink}
</body>
</html>
`;
}

export default async function handler(req, res) {
  try {
    const targetUrl = parseTargetUrl(req.query?.u);
    res.setHeader('Content-Type', 'text/html; charset=utf-8');

    if (!targetUrl) {
      res.status(200).send(
        sharePage({
          title: `${SITE_NAME} — AI news feed for platform engineers`,
          description: 'A low-hype AI news feed: model releases, research, and tooling — ranked for what changed and why it matters.',
          canonical: `${SITE_BASE_URL}/`,
          redirect: '/?utm_source=share&utm_medium=social',
        })
      );
      return;
    }

    const item = findItemByUrl(targetUrl);
    const canonical = `${SITE_BASE_URL}/s?u=${encodeURIComponent(targetUrl)}`;
    const redirect = `/?item=${encodeURIComponent(targetUrl)}&utm_source=share&utm_medium=social`;

    if (!item) {
      // Aged out of feed retention: generic card, still land on our feed.
      res.status(200).send(
        sharePage({
          title: `${SITE_NAME} — AI news feed for platform engineers`,
          description: 'This story is no longer in the live feed, but the latest AI news is one tap away.',
          canonical,
          redirect,
        })
      );
      return;
    }

    res.status(200).send(
      sharePage({
        title: String(item.title || 'AI news'),
        description: String(item.summary_1line || item.why_it_matters || '').slice(0, 250),
        canonical,
        redirect,
        sourceUrl: targetUrl,
        sourceName: String(item.source || ''),
      })
    );
  } catch (e) {
    res.status(500).json({ error: 'share_failed', detail: String(e) });
  }
}
