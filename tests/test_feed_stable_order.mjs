import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import { GET } from '../api/feed.js';

// Phase 1 of the feed UX change: the served pool is append-only within its
// window. Ordering is keyed by the score a story had when it FIRST entered the
// feed, not by the latest run that re-selected it, and an editorial cap moves a
// story below the fold instead of deleting it.

async function invoke(query) {
  const url = new URL('https://example.test/api/feed');
  for (const [key, value] of Object.entries(query || {})) {
    if (value == null) continue;
    url.searchParams.set(key, value);
  }
  const res = await GET(new Request(url));
  return { statusCode: res.status, body: await res.json() };
}

function writeRun(dir, name, runAt, items) {
  fs.writeFileSync(path.join(dir, name), JSON.stringify({ run_at: runAt, items }));
}

function item(overrides) {
  return {
    id: overrides.id || overrides.url,
    url: overrides.url,
    title: overrides.title,
    source: overrides.source || 'example_source',
    type: 'news',
    llm_category: 'platform',
    published: overrides.published || '2026-10-24T00:00:00Z',
    summary_1line: '',
    ...overrides,
  };
}

function makeRunsDir(tmp) {
  const runsDir = path.join(tmp, 'data', 'processed', 'runs');
  fs.mkdirSync(runsDir, { recursive: true });
  fs.writeFileSync(path.join(tmp, 'data', 'processed', 'runs_index.json'), JSON.stringify([]));
  return runsDir;
}

test('order is stable across runs: first-seen score wins, not the latest rank', async (t) => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'feed-stable-order-'));
  const oldCwd = process.cwd();
  t.after(() => {
    process.chdir(oldCwd);
    fs.rmSync(tmp, { recursive: true, force: true });
  });
  const runsDir = makeRunsDir(tmp);

  writeRun(runsDir, 'old.json', '2026-10-24T08:00:00Z', [
    item({ id: 'a', url: 'https://example.com/a', title: 'A older high score', global_score: 5 }),
    item({ id: 'b', url: 'https://example.com/b', title: 'B older lower score', global_score: 4 }),
  ]);
  writeRun(runsDir, 'new.json', '2026-10-24T09:00:00Z', [
    item({ id: 'b', url: 'https://example.com/b', title: 'B now rank 1', global_score: 6 }),
    item({ id: 'c', url: 'https://example.com/c', title: 'C newly admitted', global_score: 5.5 }),
  ]);
  process.chdir(tmp);

  const res = await invoke({
    from: '2026-10-24T00:00:00Z',
    to: '2026-10-24T23:59:59.999Z',
    limit: '20',
  });
  assert.equal(res.statusCode, 200);
  assert.deepEqual(res.body.items.map((it) => it.id), ['c', 'a', 'b']);
  const b = res.body.items.find((it) => it.id === 'b');
  assert.equal(b.first_seen, '2026-10-24T08:00:00Z');
  assert.equal(b.last_seen, '2026-10-24T09:00:00Z');
});

test('a new story cannot evict an admitted one when the editorial cap binds', async (t) => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'feed-no-eviction-'));
  const oldCwd = process.cwd();
  t.after(() => {
    process.chdir(oldCwd);
    fs.rmSync(tmp, { recursive: true, force: true });
  });
  const runsDir = makeRunsDir(tmp);

  const older = Array.from({ length: 5 }, (_, i) =>
    item({
      id: `hn-old-${i}`,
      url: `https://news.ycombinator.com/item?id=old-${i}`,
      title: `Older HN story ${i}`,
      source: 'hackernews_ai',
      global_score: 5 - i,
    }),
  );
  writeRun(runsDir, 'old.json', '2026-10-24T08:00:00Z', older);
  writeRun(runsDir, 'new.json', '2026-10-24T09:00:00Z', [
    item({
      id: 'hn-new',
      url: 'https://news.ycombinator.com/item?id=new',
      title: 'New countdown',
      source: 'hackernews_ai',
      global_score: 6,
    }),
  ]);
  process.chdir(tmp);

  const res = await invoke({
    from: '2026-10-24T00:00:00Z',
    to: '2026-10-24T23:59:59.999Z',
    limit: '20',
    label: 'brief',
  });
  assert.equal(res.statusCode, 200);
  assert.equal(res.body.items.length, 6, 'all six admitted stories remain');
  assert.equal(res.body.total_items, 6);
  assert.equal(res.body.items.filter((it) => !it.beyond_cap).length, 4, 'the cap still mixes the top');
  assert.equal(res.body.items.filter((it) => it.beyond_cap).length, 2, 'the rest continue below');
  assert.ok(res.body.items.some((it) => it.id === 'hn-old-4'), 'the oldest admitted story is still present');
});

test('the front-page band caps one source at three without dropping the fourth story', async (t) => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'feed-top-band-'));
  const oldCwd = process.cwd();
  t.after(() => {
    process.chdir(oldCwd);
    fs.rmSync(tmp, { recursive: true, force: true });
  });
  const runsDir = makeRunsDir(tmp);

  const hn = Array.from({ length: 4 }, (_, i) =>
    item({
      id: `hn-${i}`,
      url: `https://news.ycombinator.com/item?id=top-${i}`,
      title: `HN top story ${i}`,
      source: 'hackernews_ai',
      global_score: 5 - i,
    }),
  );
  writeRun(runsDir, 'run.json', '2026-10-24T08:00:00Z', [
    ...hn,
    item({ id: 'p1', url: 'https://example.com/p1', title: 'Practitioner story', source: 'simon_willison', global_score: 1.5 }),
    item({ id: 'f1', url: 'https://example.com/f1', title: 'First-party story', source: 'openai_blog', global_score: 1.4 }),
  ]);
  process.chdir(tmp);

  const res = await invoke({
    from: '2026-10-24T00:00:00Z',
    to: '2026-10-24T23:59:59.999Z',
    limit: '20',
    label: 'brief',
  });
  assert.equal(res.statusCode, 200);
  assert.equal(res.body.items.length, 6, 'the fourth HN story stays in the body');
  const topFive = res.body.items.slice(0, 5);
  assert.equal(topFive.filter((it) => it.source === 'hackernews_ai').length, 3);
  assert.equal(topFive.filter((it) => it.source === 'simon_willison').length, 1);
  assert.equal(topFive.filter((it) => it.source === 'openai_blog').length, 1);
});

test('arrival window includes a story published earlier but admitted inside 24h', async (t) => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'feed-arrival-window-'));
  const oldCwd = process.cwd();
  t.after(() => {
    process.chdir(oldCwd);
    fs.rmSync(tmp, { recursive: true, force: true });
  });
  const runsDir = makeRunsDir(tmp);

  writeRun(runsDir, 'run.json', '2026-10-24T09:00:00Z', [
    item({
      id: 'slow',
      url: 'https://example.com/slow',
      title: 'Slow RSS post published two days ago',
      published: '2026-10-22T09:00:00Z',
    }),
    item({
      id: 'fresh',
      url: 'https://example.com/fresh',
      title: 'Fresh post published today',
      published: '2026-10-24T08:00:00Z',
    }),
  ]);
  process.chdir(tmp);

  const arrival = await invoke({
    from: '2026-10-24T00:00:00Z',
    to: '2026-10-24T23:59:59.999Z',
    window: 'arrival',
    limit: '20',
  });
  assert.equal(arrival.statusCode, 200);
  assert.deepEqual(arrival.body.items.map((it) => it.id).sort(), ['fresh', 'slow']);

  const published = await invoke({
    from: '2026-10-24T00:00:00Z',
    to: '2026-10-24T23:59:59.999Z',
    limit: '20',
  });
  assert.equal(published.statusCode, 200);
  assert.deepEqual(published.body.items.map((it) => it.id), ['fresh']);
});
