import assert from 'node:assert/strict';
import test from 'node:test';

import { GET } from '../api/foundations.js';

async function invoke(query = {}) {
  const url = new URL('https://example.com/api/foundations');
  for (const [key, value] of Object.entries(query)) {
    url.searchParams.set(key, String(value));
  }
  const response = await GET(new Request(url));
  return { statusCode: response.status, body: await response.json() };
}

test('serves the foundations index', async () => {
  const res = await invoke();
  assert.equal(res.statusCode, 200);
  assert.ok(res.body.concepts);
  assert.ok(res.body.concepts['prompt-reliability']);
});

test('serves one foundation concept by slug', async () => {
  const res = await invoke({ slug: 'prompt-reliability' });
  assert.equal(res.statusCode, 200);
  assert.equal(res.body.slug, 'prompt-reliability');
});

test('rejects invalid concept slugs', async () => {
  const res = await invoke({ slug: '../secret' });
  assert.equal(res.statusCode, 400);
  assert.equal(res.body.error, 'invalid_slug');
});
