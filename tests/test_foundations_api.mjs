import assert from 'node:assert/strict';
import test from 'node:test';

import handler from '../api/foundations.js';

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

test('serves the foundations index', async () => {
  const res = response();
  await handler({ query: {} }, res);
  assert.equal(res.statusCode, 200);
  assert.ok(res.body.concepts);
  assert.ok(res.body.concepts['prompt-reliability']);
});

test('serves one foundation concept by slug', async () => {
  const res = response();
  await handler({ query: { slug: 'prompt-reliability' } }, res);
  assert.equal(res.statusCode, 200);
  assert.equal(res.body.slug, 'prompt-reliability');
});

test('rejects invalid concept slugs', async () => {
  const res = response();
  await handler({ query: { slug: '../secret' } }, res);
  assert.equal(res.statusCode, 400);
  assert.equal(res.body.error, 'invalid_slug');
});
