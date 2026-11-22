import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import { GET } from '../api/feed.js';

async function invoke(query) {
  const url = new URL('https://example.test/api/feed');
  for (const [key, value] of Object.entries(query || {})) {
    if (value == null) continue;
    url.searchParams.set(key, value);
  }
  const res = await GET(new Request(url));
  const body = await res.json();
  return {
    statusCode: res.status,
    body,
    headers: Object.fromEntries(res.headers.entries()),
  };
}

test('rejects timezone-naive date bounds', async () => {
  const res = await invoke({ from: '2026-06-20T00:00:00' });
  assert.equal(res.statusCode, 400);
  assert.equal(res.body.error, 'timezone_required');
  assert.equal(res.body.field, 'from');
});

test('accepts timezone-aware date bounds', async () => {
  const res = await invoke({
    from: '2026-06-20T00:00:00-07:00',
    to: '2026-06-20T23:59:59.999-07:00',
    limit: '1',
  });
  assert.equal(res.statusCode, 200);
  assert.match(res.body.filters.from, /Z$/);
  assert.match(res.body.filters.to, /Z$/);
});

test('latest mode applies date bounds consistently to items, totals, and label counts', async () => {
  const oldCwd = process.cwd();
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'feed-latest-window-'));
  try {
    fs.mkdirSync(path.join(tmp, 'data', 'processed'), { recursive: true });
    fs.writeFileSync(
      path.join(tmp, 'data', 'processed', 'latest.json'),
      JSON.stringify([
        {
          id: 'old',
          url: 'https://example.com/old',
          title: 'Old story outside the requested window',
          source: 'example_source',
          type: 'news',
          llm_category: 'platform',
          published: '2026-08-01T12:00:00Z',
        },
        {
          id: 'current',
          url: 'https://example.com/current',
          title: 'Current story inside the requested window',
          source: 'example_source',
          type: 'news',
          llm_category: 'platform',
          published: '2026-08-24T12:00:00Z',
        },
      ]),
    );
    fs.writeFileSync(path.join(tmp, 'data', 'processed', 'runs_index.json'), JSON.stringify([]));
    process.chdir(tmp);

    const res = await invoke({
      from: '2026-08-24T00:00:00Z',
      to: '2026-08-24T23:59:59.999Z',
      label: 'brief',
      limit: '20',
    });

    assert.equal(res.statusCode, 200);
    assert.equal(res.body.mode, 'latest');
    assert.deepEqual(res.body.items.map((item) => item.id), ['current']);
    assert.equal(res.body.total_items, 1);
    assert.equal(res.body.has_more, false);
    assert.deepEqual(res.body.label_counts, {
      brief: 1,
      platform: 1,
      research: 0,
      release: 0,
      news: 1,
    });
  } finally {
    process.chdir(oldCwd);
    fs.rmSync(tmp, { recursive: true, force: true });
  }
});

test('reports when the selected feed is truncated', async () => {
  const res = await invoke({ limit: '1', label: 'brief' });
  assert.equal(res.statusCode, 200);
  assert.equal(res.body.items.length, 1);
  assert.ok(res.body.total_items > res.body.items.length);
  assert.equal(res.body.has_more, true);
});
