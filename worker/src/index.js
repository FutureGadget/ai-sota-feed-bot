// llm-digest.com site Worker: replaces the Vercel deployment.
//
// - Static pages/assets come from the bundled assets (public/ staged by
//   scripts/vercel_build.py); unmatched paths fall through here and get the
//   same rewrites vercel.json applied.
// - /api/* (plus /s and /rss.xml) run the exact handlers from ../api/*.js,
//   reading JSON data from R2 via the injected data source instead of disk.
// - GET API responses are cached at the edge (Vercel's s-maxage=300 parity).

import { installR2Source, preload, loadJson } from './r2-source.js';

import { GET as feedGET } from '../../api/feed.js';
import { GET as rssGET } from '../../api/rss.js';
import { GET as shareGET } from '../../api/share.js';
import { GET as dailyGET } from '../../api/daily.js';
import { GET as weeklyGET } from '../../api/weekly.js';
import { GET as storylinesGET } from '../../api/storylines.js';
import { GET as topicsGET } from '../../api/topics.js';
import { GET as foundationsGET } from '../../api/foundations.js';
import { GET as playbookGET } from '../../api/playbook.js';
import { GET as updatesGET } from '../../api/updates.js';
import { GET as clientConfigGET } from '../../api/client-config.js';
import { GET as subscribeGET, POST as subscribePOST } from '../../api/subscribe.js';

const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
const WEEK_RE = /^\d{4}-W\d{2}$/;
const SLUG_RE = /^[a-z0-9][a-z0-9-]{0,80}$/;
const LAB_SELECTOR_RE = /^[a-z0-9][a-z0-9-]{0,79}$/;

// Route -> data keys its handler may read. Everything a handler can touch must
// be preloaded; the R2 source is synchronous, so an unpreloaded key reads as a
// missing file.
async function preloadForApi(pathname, searchParams) {
  switch (pathname) {
    case '/api/feed': {
      const keys = [
        'processed/latest.json',
        'processed/runs_index.json',
        'processed/editorial.json',
        'feedback/source_adjustments.json',
        'served/pool.json',
        'served/brief_ledger.json',
      ];
      if (
        searchParams.get('locale') === 'ko'
        && searchParams.get('localized_snapshot') === 'latest'
      ) {
        keys.push('i18n/ko/feed/latest.json', 'i18n/ko/feed/status.json');
      }
      await preload(keys);
      return feedGET;
    }
    case '/api/rss':
      await preload(['served/rss_items.json', 'processed/editorial.json']);
      return rssGET;
    case '/api/share':
      await preload(['stories/index.json', 'served/share_index.json']);
      return shareGET;
    case '/api/daily': {
      const keys = ['daily/index.json'];
      const date = String(searchParams.get('date') || '').trim();
      keys.push(DATE_RE.test(date) ? `daily/${date}.json` : 'daily/latest.json');
      await preload(keys);
      return dailyGET;
    }
    case '/api/weekly': {
      const keys = ['weekly/index.json'];
      const week = String(searchParams.get('week') || '').trim();
      keys.push(WEEK_RE.test(week) ? `weekly/${week}.json` : 'weekly/latest.json');
      await preload(keys);
      return weeklyGET;
    }
    case '/api/storylines': {
      const slug = String(searchParams.get('slug') || '').trim();
      await preload([SLUG_RE.test(slug) ? `storylines/${slug}.json` : 'storylines/index.json']);
      return storylinesGET;
    }
    case '/api/topics':
      await preload(['wiki/index.json']);
      return topicsGET;
    case '/api/foundations':
      await preload(['foundations/index.json']);
      return foundationsGET;
    case '/api/playbook': {
      const locale = String(searchParams.get('locale') || '').trim();
      if (searchParams.has('lab')) {
        // Two-phase: the index names the records to validate by exact bytes.
        const index = await loadJson('playbook/lab/index.json');
        const raws = (Array.isArray(index) ? index : [])
          .slice(0, 4)
          .map((row) => `playbook/lab/${row?.slug}.json`)
          .filter((key) => LAB_SELECTOR_RE.test(key.split('/').pop().replace(/\.json$/, '')));
        await preload(['playbook/lab/index.json', ...raws], raws);
        return playbookGET;
      }
      const base = ['playbook/index.json', 'playbook/latest.json', 'playbook/source-index.json'];
      const date = String(searchParams.get('date') || '').trim();
      if (DATE_RE.test(date)) base.push(`playbook/${date}.json`);
      if (locale === 'ko') {
        base.push('i18n/ko/playbook/index.json', 'i18n/ko/playbook/latest.json');
        if (DATE_RE.test(date)) base.push(`i18n/ko/playbook/${date}.json`);
      }
      await preload(base);
      return playbookGET;
    }
    case '/api/updates':
      await preload(['served/updates.json']);
      return updatesGET;
    case '/api/client-config':
      return clientConfigGET;
    default:
      return null;
  }
}

// vercel.json rewrites, in the same order. Only reached when no asset matched
// the request path (Vercel likewise checks the filesystem first).
const STATIC_REWRITES = [
  [/^\/$/, '/web/index.html'],
  [/^\/ko\/?$/, '/web/ko/index.html'],
  [/^\/weekly\/?$/, '/web/weekly/index.html'],
  [/^\/weekly\/(\d{4}-W\d{2})$/, (m) => `/web/weekly/${m[1]}.html`],
  [/^\/weekly\/[^/]+$/, '/web/weekly.html'],
  [/^\/ko\/weekly\/(\d{4}-W\d{2})$/, (m) => `/web/ko/weekly/${m[1]}.html`],
  [/^\/daily\/?$/, '/web/daily/index.html'],
  [/^\/daily\/(\d{4}-\d{2}-\d{2})$/, (m) => `/web/daily/${m[1]}.html`],
  [/^\/daily\/[^/]+$/, '/web/daily.html'],
  [/^\/ko\/daily\/(\d{4}-\d{2}-\d{2})$/, (m) => `/web/ko/daily/${m[1]}.html`],
  [/^\/updates\/?$/, '/web/updates.html'],
  [/^\/voices\/?$/, '/web/voices.html'],
  [/^\/subscribe\/?$/, '/web/subscribe.html'],
  [/^\/storylines\/?$/, '/web/storyline.html'],
  [/^\/storyline\/([a-z0-9-]+)$/, (m) => `/web/storyline/${m[1]}.html`],
  [/^\/ko\/storyline\/([a-z0-9-]+)$/, (m) => `/web/ko/storyline/${m[1]}.html`],
  [/^\/playbook\/?$/, '/web/playbook.html'],
  [/^\/playbook\/lab\/([a-z0-9-]+)$/, '/web/playbook-lab.html'],
  [/^\/playbook\/(\d{4}-\d{2}-\d{2})$/, '/web/playbook.html'],
  [/^\/playbook\/[^/]+$/, '/web/playbook.html'],
  [/^\/ko\/playbook\/?$/, '/web/ko/playbook.html'],
  [/^\/ko\/playbook\/(\d{4}-\d{2}-\d{2})$/, '/web/ko/playbook.html'],
  [/^\/ko\/playbook\/[^/]+$/, '/web/ko/playbook.html'],
  [/^\/map\/?$/, '/web/map.html'],
  [/^\/topic\/([a-z0-9-]+)$/, (m) => `/web/topic/${m[1]}.html`],
  [/^\/ko\/topic\/([a-z0-9-]+)$/, (m) => `/web/ko/topic/${m[1]}.html`],
  [/^\/foundations\/?$/, '/web/foundations.html'],
  [/^\/foundations\/([a-z0-9-]+)$/, (m) => `/web/foundations/${m[1]}.html`],
  [/^\/ko\/foundations\/([a-z0-9-]+)$/, (m) => `/web/ko/foundations/${m[1]}.html`],
  [/^\/models\/?$/, '/web/models.html'],
  [/^\/models\/compare\/?$/, '/web/models-compare.html'],
  [/^\/models\/([a-z0-9-]+)$/, (m) => `/web/models/${m[1]}.html`],
  [/^\/skills\/?$/, '/web/skills/index.html'],
  [/^\/skills\/([a-z0-9-]+)$/, (m) => `/web/skills/${m[1]}.html`],
  [/^\/story\/([0-9a-f]{16})$/, (m) => `/web/story/${m[1]}.html`],
  [/^\/ko\/story\/([0-9a-f]{16})$/, (m) => `/web/ko/story/${m[1]}.html`],
  [/^\/sitemap\.xml$/, '/web/sitemap.xml'],
  [/^\/robots\.txt$/, '/web/robots.txt'],
  [/^\/llms\.txt$/, '/web/llms.txt'],
  [/^\/llm-guide\.txt$/, '/web/llm-guide.txt'],
];

const LAB_PATH_RE = /^\/(?:web\/)?lab-artifacts\//;
const DEFAULT_API_CACHE = 's-maxage=300, stale-while-revalidate=3600';

function isApiPath(pathname) {
  return pathname.startsWith('/api/') || pathname === '/s' || pathname === '/rss.xml';
}

async function handleApi(request, env, ctx) {
  const url = new URL(request.url);
  const pathname = url.pathname === '/s'
    ? '/api/share'
    : url.pathname === '/rss.xml'
      ? '/api/rss'
      : url.pathname;

  // Edge-cache GETs so bot traffic doesn't burn Worker requests.
  const cacheable = request.method === 'GET';
  if (cacheable) {
    const cached = await caches.default.match(request);
    if (cached) return cached;
  }

  let response;
  if (pathname === '/api/subscribe') {
    response = request.method === 'POST'
      ? await subscribePOST(request)
      : await subscribeGET(request);
  } else {
    const handler = await preloadForApi(pathname, url.searchParams);
    if (!handler) return null;
    response = await handler(request);
  }

  // vercel.json applied s-maxage=300 to /api/*; keep it, honoring handlers
  // that set their own (localized feed, RSS, no-store pages).
  const headers = new Headers(response.headers);
  if (!headers.has('Cache-Control')) headers.set('Cache-Control', DEFAULT_API_CACHE);
  response = new Response(response.body, { status: response.status, headers });

  // Skip explicitly non-cacheable responses (unfollow pages are no-store).
  if (cacheable && response.ok && !/no-store|private/.test(headers.get('Cache-Control') || '')) {
    ctx.waitUntil(caches.default.put(request, response.clone()));
  }
  return response;
}

export default {
  async fetch(request, env, ctx) {
    installR2Source(env);
    // Handlers read config via process.env (Node style). Workers only exposes
    // plain-text vars there - secrets live solely on the env binding - so
    // bridge every string binding (vars AND secrets) into process.env.
    for (const [key, value] of Object.entries(env)) {
      if (typeof value === 'string') {
        process.env[key] = value;
      }
    }
    const url = new URL(request.url);


    // vercel.json: llm-digest.com -> www.llm-digest.com (permanent).
    if (url.hostname === 'llm-digest.com') {
      return Response.redirect(`https://www.llm-digest.com${url.pathname}${url.search}`, 308);
    }

    try {
      if (isApiPath(url.pathname)) {
        const response = await handleApi(request, env, ctx);
        if (response) {
          if (request.method === 'HEAD') {
            return new Response(null, { status: response.status, headers: response.headers });
          }
          return response;
        }
      }

      // lab-artifacts arrive here via run_worker_first: serve the asset with
      // the CSP sandbox headers vercel.json attached.
      if (LAB_PATH_RE.test(url.pathname)) {
        const asset = await env.ASSETS.fetch(request);
        const headers = new Headers(asset.headers);
        headers.set('Content-Security-Policy', "sandbox; default-src 'none'");
        headers.set('X-Content-Type-Options', 'nosniff');
        return new Response(asset.body, { status: asset.status, headers });
      }

      // Page rewrites for paths with no matching asset.
      for (const [pattern, target] of STATIC_REWRITES) {
        const match = url.pathname.match(pattern);
        if (!match) continue;
        const rewritten = typeof target === 'function' ? target(match) : target;
        const assetUrl = new URL(rewritten, url.origin);
        assetUrl.search = url.search;
        return await env.ASSETS.fetch(new Request(assetUrl, request));
      }

      // No asset, no rewrite: same 404 Vercel would give.
      return new Response('Not Found', { status: 404 });
    } catch (e) {
      console.error('worker error', e);
      return Response.json({ error: 'worker_error', detail: String(e).slice(0, 200) }, { status: 500 });
    }
  },
};
