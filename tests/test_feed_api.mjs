import assert from 'node:assert/strict';
import test from 'node:test';

import handler from '../api/feed.js';

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

async function invoke(query) {
  const res = response();
  await handler({ query }, res);
  return res;
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

test('reports when the selected feed is truncated', async () => {
  const res = await invoke({ limit: '1', label: 'brief' });
  assert.equal(res.statusCode, 200);
  assert.equal(res.body.items.length, 1);
  assert.ok(res.body.total_items > res.body.items.length);
  assert.equal(res.body.has_more, true);
});
