// Regression test for the RSS feed ordering.
//
// Bug: /api/rss sorted purely by score, so an agent / RSS reader consuming the
// site got days-old high-score items at the top and perceived the feed as
// "outdated" even though the data was current. RSS must be reverse-chronological
// and capped.
//
// Run from the repo root (the handler reads data via process.cwd()):
//   node tests/test_rss_recency.mjs

import assert from 'node:assert';
import rss from '../api/rss.js';

function mockRes() {
  return {
    _status: 200,
    _headers: {},
    _body: null,
    status(c) { this._status = c; return this; },
    setHeader(k, v) { this._headers[k] = v; },
    send(s) { this._body = s; return this; },
    json(o) { this._body = o; return this; },
  };
}

function parseItems(xml) {
  return [...xml.matchAll(/<item>([\s\S]*?)<\/item>/g)].map((m) => {
    const block = m[1];
    const pub = block.match(/<pubDate>([\s\S]*?)<\/pubDate>/);
    return { pubDate: pub ? new Date(pub[1]).getTime() : null };
  });
}

const res = mockRes();
await rss({ query: {} }, res);

assert.strictEqual(res._status, 200, 'RSS handler should return 200');
const xml = String(res._body || '');
assert.ok(xml.startsWith('<?xml'), 'response should be RSS XML');

const items = parseItems(xml);
assert.ok(items.length > 0, 'feed should contain items');

// 1. Capped to a focused recency view.
assert.ok(items.length <= 50, `feed should be capped at 50 items, got ${items.length}`);

// 2. Reverse-chronological: every consecutive pair with dates is non-increasing.
let prev = Infinity;
let datedSeen = 0;
let missingSeen = false;
for (const it of items) {
  if (it.pubDate == null) { missingSeen = true; continue; }
  datedSeen += 1;
  assert.ok(it.pubDate <= prev, 'items must be ordered newest-first by pubDate');
  // dated items must all come before any undated item
  assert.ok(!missingSeen, 'undated items must sort to the end, not interleave');
  prev = it.pubDate;
}
assert.ok(datedSeen > 0, 'expected at least some dated items');

console.log(`ok: RSS recency order (items=${items.length}, dated=${datedSeen})`);
