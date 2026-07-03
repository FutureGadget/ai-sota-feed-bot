import assert from 'node:assert/strict';
import test from 'node:test';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

import handler from '../api/feed.js';

// Regression test for a real production bug: a story ("Claude Fable 5 and
// Claude Mythos 5") first ranked on 2026-06-15, dropped out of the ranked
// window for weeks, then reappeared on 2026-07-02. Because the feed API used
// to bound which runs it scanned by the REQUEST's from/to window before
// computing first_seen, the item's first appearance *within that window*
// (2026-07-02) was mistaken for its true feed-arrival time — resurfacing a
// three-week-old, already-seen story as "New" in the UI. first_seen must
// always reflect the item's true earliest appearance across all history,
// independent of the requested display window.

function response() {
  return {
    statusCode: 200,
    body: null,
    status(code) {
      this.statusCode = code;
      return this;
    },
    json(body) {
      this.body = body;
      return this;
    },
  };
}

function writeRun(dir, name, runAt, items) {
  fs.writeFileSync(path.join(dir, name), JSON.stringify({ run_at: runAt, items }));
}

test('first_seen reflects the true earliest run, not just the requested from/to window', async (t) => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'feed-window-test-'));
  const runsDir = path.join(tmp, 'data', 'processed', 'runs');
  fs.mkdirSync(runsDir, { recursive: true });

  const item = {
    url: 'https://example.com/resurfaced-story',
    title: 'Resurfaced Story',
    type: 'news',
    source: 'example_source',
  };

  // First reaches the ranked window well before the requested display window.
  writeRun(runsDir, 'old-run.json', '2026-06-15T09:01:52.000Z', [
    { ...item, published: '2026-06-12T23:38:00.000Z' },
  ]);
  // Drops out, then reappears inside the requested display window with an
  // updated publish date (mirrors the real-world case: the source's own
  // published timestamp shifted after the story was already ranked once).
  writeRun(runsDir, 'new-run.json', '2026-07-02T22:03:57.000Z', [
    { ...item, published: '2026-06-30T16:00:00.000Z' },
  ]);

  const originalCwd = process.cwd();
  process.chdir(tmp);
  t.after(() => {
    process.chdir(originalCwd);
    fs.rmSync(tmp, { recursive: true, force: true });
  });

  const res = response();
  await handler(
    { query: { from: '2026-06-26T00:00:00.000Z', to: '2026-07-03T23:59:59.999Z' } },
    res,
  );

  assert.equal(res.statusCode, 200);
  const found = res.body.items.find((it) => it.url === item.url);
  assert.ok(found, 'expected the resurfaced item in the response');
  assert.equal(found.first_seen, '2026-06-15T09:01:52.000Z');
  assert.equal(found.last_seen, '2026-07-02T22:03:57.000Z');
});
