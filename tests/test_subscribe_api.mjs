import assert from 'node:assert/strict';
import test from 'node:test';

import { POST } from '../api/subscribe.js';

async function invoke(body, fetchImpl) {
  const previousKey = process.env.EMAIL_API_KEY;
  const previousFetch = global.fetch;
  process.env.EMAIL_API_KEY = 'test-key';
  global.fetch = fetchImpl;
  try {
    const response = await POST(new Request('https://example.com/api/subscribe', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }));
    return { statusCode: response.status, body: await response.json() };
  } finally {
    global.fetch = previousFetch;
    if (previousKey === undefined) delete process.env.EMAIL_API_KEY;
    else process.env.EMAIL_API_KEY = previousKey;
  }
}

test('rejects invalid email before calling the provider', async () => {
  let called = false;
  const res = await invoke({ email: 'not-an-email' }, async () => {
    called = true;
    return new Response();
  });
  assert.equal(res.statusCode, 400);
  assert.equal(res.body.error, 'invalid_email');
  assert.equal(called, false);
});

test('accepts a successful provider response', async () => {
  const res = await invoke({ email: 'reader@example.com' }, async () =>
    new Response('{}', { status: 201 }),
  );
  assert.equal(res.statusCode, 200);
  assert.deepEqual(res.body, { ok: true });
});

test('treats duplicate contacts as idempotent success', async () => {
  for (const status of [409, 422]) {
    const res = await invoke({ email: 'reader@example.com' }, async () =>
      new Response('{}', { status }),
    );
    assert.equal(res.statusCode, 200);
    assert.deepEqual(res.body, { ok: true });
  }
});

test('reports provider failure without exposing credentials', async () => {
  const res = await invoke({ email: 'reader@example.com' }, async () =>
    new Response('provider rejected request', { status: 403 }),
  );
  assert.equal(res.statusCode, 502);
  assert.equal(res.body.error, 'provider_error');
  assert.equal(res.body.status, 403);
});

test('reports provider network failure', async () => {
  const res = await invoke({ email: 'reader@example.com' }, async () => {
    throw new Error('offline');
  });
  assert.equal(res.statusCode, 502);
  assert.equal(res.body.error, 'provider_unreachable');
});

async function invokeCapturing(body, responses) {
  const calls = [];
  const res = await invoke(body, async (_url, options) => {
    calls.push(JSON.parse(options.body));
    return responses.shift();
  });
  return { res, calls };
}

test('stores the signup browser anonymous id as the contact reader_id', async () => {
  const readerId = 'anon_0b3c9a3e-5d1f-4c1e-9a55-2f1f0c7d9e11';
  const { res, calls } = await invokeCapturing(
    { email: 'reader@example.com', reader_id: readerId },
    [new Response('{}', { status: 201 })],
  );
  assert.equal(res.statusCode, 200);
  assert.equal(calls.length, 1);
  assert.deepEqual(calls[0].properties, { reader_id: readerId });
});

test('mints a fresh reader_id when the supplied one is malformed', async () => {
  const { calls } = await invokeCapturing(
    { email: 'reader@example.com', reader_id: 'alice@example.com' },
    [new Response('{}', { status: 201 })],
  );
  assert.match(calls[0].properties.reader_id, /^anon_[0-9a-f-]{36}$/);
  assert.notEqual(calls[0].properties.reader_id, 'alice@example.com');
});

test('retries without properties when the provider rejects them', async () => {
  const { res, calls } = await invokeCapturing(
    { email: 'reader@example.com' },
    [new Response('{"message":"unknown property"}', { status: 422 }), new Response('{}', { status: 201 })],
  );
  assert.equal(res.statusCode, 200);
  assert.equal(calls.length, 2);
  assert.ok(calls[0].properties);
  assert.equal(calls[1].properties, undefined);
  assert.equal(calls[1].email, 'reader@example.com');
});
