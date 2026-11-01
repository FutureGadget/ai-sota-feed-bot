// Build-time precompute for the Cloudflare Worker deployment.
//
// The Worker serves the API from R2 objects instead of bundled files, and a
// single request cannot afford to walk hundreds of run snapshots (Workers cap
// subrequests per request and CPU milliseconds). This script runs in the
// deploy workflow on the repo checkout — where the full committed data/ tree
// is available — and collapses the expensive reads into a handful of
// precomputed JSON artifacts under data/served/, which scripts/r2_sync.py
// then publishes to the R2 bucket.
//
// Every artifact is produced by the SAME functions the API handlers use, so
// the Worker and Vercel/Node paths cannot drift:
//   served/pool.json         feed.js readRuns + accumulateItems + clusterCoverage
//   served/brief_ledger.json feed.js readBriefLedger
//   served/rss_items.json    rss.js getRecentItems
//   served/share_index.json  share.js candidateItemLists (first match wins)
//   served/updates.json      updates.js GET body (minus volatile `now`)

import fs from 'node:fs';
import path from 'node:path';

import { readRuns, accumulateItems, clusterCoverage, readBriefLedger } from '../api/feed.js';
import { getRecentItems } from '../api/rss.js';
import { candidateItemLists } from '../api/share.js';
import { GET as updatesGET } from '../api/updates.js';

const OUT_DIR = path.join(process.cwd(), 'data', 'served');
fs.mkdirSync(OUT_DIR, { recursive: true });

function write(name, value) {
  const file = path.join(OUT_DIR, name);
  fs.writeFileSync(file, JSON.stringify(value));
  const kb = (fs.statSync(file).size / 1024).toFixed(1);
  console.log(`served/${name}: ${kb} KB`);
}

// --- feed run pool -------------------------------------------------------
const runs = readRuns();
const baseItems = accumulateItems(runs);
const coverageByItem = clusterCoverage(baseItems);
write('pool.json', {
  version: 1,
  generated_at: new Date().toISOString(),
  runs: runs.map((r) => ({ run_at: r?.run_at || null, item_count: (r?.items || []).length })),
  baseItems,
  coverage: [...coverageByItem],
});

// --- brief ledger ---------------------------------------------------------
const ledger = readBriefLedger();
write('brief_ledger.json', {
  version: 1,
  items: ledger?.items || [],
  files: ledger?.files || [],
  updated_at: ledger?.updated_at || null,
});

// --- rss 7-day pool -------------------------------------------------------
write('rss_items.json', getRecentItems());

// --- share URL index ------------------------------------------------------
const normUrl = (v) => {
  const s = String(v || '').trim();
  return s.endsWith('/') && s.length > 1 ? s.slice(0, -1) : s;
};
const shareIndex = {};
for (const items of candidateItemLists()) {
  for (const it of items) {
    const key = normUrl(it?.url);
    if (!key || shareIndex[key]) continue;
    shareIndex[key] = {
      title: it.title,
      summary_1line: it.summary_1line,
      why_it_matters: it.why_it_matters,
      source: it.source,
    };
  }
}
write('share_index.json', shareIndex);

// --- updates catalog ------------------------------------------------------
const res = await updatesGET(new Request('http://localhost/api/updates'));
if (!res.ok) throw new Error(`updates GET failed: ${res.status}`);
const body = await res.json();
delete body.now;
write('updates.json', body);

console.log('served data built OK');
