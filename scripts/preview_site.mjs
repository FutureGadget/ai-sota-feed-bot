#!/usr/bin/env node
// Local preview server for the Cloudflare-deployed site.
//
// Stands in for `wrangler dev` without R2: static files come from `web/` and the
// real `api/*.js` handlers run against the committed `data/` tree
// (`lib/data-source.js` reads from disk when no custom source is installed).
// The Worker replaced both the Vercel previews and `next dev`-style tooling, so
// this is the fastest way to review a UI change with live data.
//
// Routing mirrors the Worker closely enough for review: `/api/*`, `/s`, and
// `/rss.xml` dispatch to a handler; every other path resolves to a file in
// `web/` (`/skills` -> `web/skills/index.html`, `/skills/x` -> `web/skills/x.html`).
//
// Usage:
//   node scripts/preview_site.mjs [--port 4173]
//
// Prerequisites: `node scripts/build_served_data.mjs` once (the feed reads
// data/served/*.json; without it the handler falls back to the run pool).

import fs from 'node:fs';
import http from 'node:http';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { GET as feedGET } from '../api/feed.js';
import { GET as rssGET } from '../api/rss.js';
import { GET as shareGET } from '../api/share.js';
import { GET as dailyGET } from '../api/daily.js';
import { GET as weeklyGET } from '../api/weekly.js';
import { GET as storylinesGET } from '../api/storylines.js';
import { GET as topicsGET } from '../api/topics.js';
import { GET as foundationsGET } from '../api/foundations.js';
import { GET as playbookGET } from '../api/playbook.js';
import { GET as updatesGET } from '../api/updates.js';
import { GET as clientConfigGET } from '../api/client-config.js';
import { GET as subscribeGET, POST as subscribePOST } from '../api/subscribe.js';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const WEB = path.join(ROOT, 'web');

const API = {
  '/api/feed': feedGET,
  '/api/rss': rssGET,
  '/api/share': shareGET,
  '/api/daily': dailyGET,
  '/api/weekly': weeklyGET,
  '/api/storylines': storylinesGET,
  '/api/topics': topicsGET,
  '/api/foundations': foundationsGET,
  '/api/playbook': playbookGET,
  '/api/updates': updatesGET,
  '/api/client-config': clientConfigGET,
  '/api/subscribe': subscribeGET,
};

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.xml': 'application/xml; charset=utf-8',
  '.txt': 'text/plain; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.webp': 'image/webp',
  '.ico': 'image/x-icon',
  '.woff2': 'font/woff2',
  '.woff': 'font/woff',
};

function resolveStatic(pathname) {
  let clean;
  try {
    clean = decodeURIComponent(pathname);
  } catch {
    return null;
  }
  const rel = clean.replace(/^\/+/, '');
  const candidates = rel
    ? [rel, `${rel}.html`, path.posix.join(rel, 'index.html')]
    : ['index.html'];
  for (const candidate of candidates) {
    const file = path.resolve(WEB, candidate);
    // Path traversal guard: keep everything inside web/.
    if (file !== WEB && !file.startsWith(WEB + path.sep)) continue;
    if (fs.existsSync(file) && fs.statSync(file).isFile()) return file;
  }
  return null;
}

async function serveApi(request, pathname, origin) {
  // Handlers are Web-standard `Request` consumers; Node gives us an
  // IncomingMessage with a path-only `url`, so adapt it here.
  const isBodyless = request.method === 'GET' || request.method === 'HEAD';
  const fetchRequest = new Request(new URL(request.url, origin), {
    method: request.method,
    headers: request.headers,
    body: isBodyless ? undefined : request,
    duplex: isBodyless ? undefined : 'half',
  });
  const isSubscribe = pathname === '/api/subscribe';
  if (isSubscribe && request.method === 'POST') return subscribePOST(fetchRequest);
  if (isSubscribe) return subscribeGET(fetchRequest);
  const handler = pathname === '/s' ? shareGET : pathname === '/rss.xml' ? rssGET : API[pathname];
  if (!handler) return null;
  return handler(fetchRequest);
}

const server = http.createServer(async (request, response) => {
  const url = new URL(request.url, 'http://localhost');
  const isApi = url.pathname.startsWith('/api/') || url.pathname === '/s' || url.pathname === '/rss.xml';

  if (isApi) {
    let result = null;
    try {
      result = await serveApi(request, url.pathname, `http://localhost:${port}`);
    } catch (error) {
      console.error('api error', url.pathname, error);
      response.writeHead(500, { 'content-type': 'application/json' });
      response.end(JSON.stringify({ error: 'preview_api_failed', detail: String(error).slice(0, 200) }));
      return;
    }
    if (!result) {
      response.writeHead(404, { 'content-type': 'text/plain' });
      response.end(`No preview route for ${url.pathname}`);
      return;
    }
    const body = Buffer.from(await result.arrayBuffer());
    const headers = Object.fromEntries(result.headers.entries());
    response.writeHead(result.status, { ...headers, 'cache-control': 'no-store' });
    response.end(body);
    return;
  }

  const file = resolveStatic(url.pathname);
  if (!file) {
    response.writeHead(404, { 'content-type': 'text/plain' });
    response.end(
      `404 ${url.pathname}\n\nRendered pages live in web/. Run:\n  python3 pipeline/render_static_pages.py\n`,
    );
    return;
  }
  const body = fs.readFileSync(file);
  response.writeHead(200, {
    'content-type': MIME[path.extname(file).toLowerCase()] || 'application/octet-stream',
    'cache-control': 'no-store',
    'content-length': body.length,
  });
  response.end(body);
});

function parsePort(argv) {
  const index = argv.indexOf('--port');
  const value = index >= 0 ? Number(argv[index + 1]) : 4173;
  return Number.isFinite(value) && value > 0 ? value : 4173;
}

const port = parsePort(process.argv.slice(2));
server.listen(port, () => {
  if (!fs.existsSync(path.join(ROOT, 'data', 'served', 'pool.json'))) {
    console.warn('warning: data/served/pool.json is missing; run `node scripts/build_served_data.mjs`');
  }
  console.log(`preview: http://localhost:${port}`);
  console.log(`  board   http://localhost:${port}/skills`);
  console.log(`  feed    http://localhost:${port}/`);
  console.log(`  family  http://localhost:${port}/skills/garrytan-gstack`);
});
