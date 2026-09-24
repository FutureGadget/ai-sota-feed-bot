import assert from 'node:assert/strict';
import { createHmac } from 'node:crypto';
import test from 'node:test';

import { GET, POST } from '../api/subscribe.js';
import { addFollow, parseFollows, unfollowToken } from '../lib/follow.js';

// The signing spec both sides implement (tests/test_publish_follows.py
// checks the Python signer against the same formula).
const TOKEN_VECTOR = createHmac('sha256', 'test-key').update('unfollow:c-123:gemini-3-8').digest('hex').slice(0, 32);

function mockProvider(routes) {
  const calls = [];
  const fetchImpl = async (url, options = {}) => {
    const path = new URL(url).pathname;
    const method = options.method || 'GET';
    const body = options.body ? JSON.parse(options.body) : undefined;
    calls.push({ method, path, body });
    for (const [key, handler] of Object.entries(routes)) {
      const [m, p] = key.split(' ');
      if (m === method && (p === path || (p.endsWith('*') && path.startsWith(p.slice(0, -1))))) {
        const [status, json] = handler(body, path);
        return new Response(JSON.stringify(json ?? {}), { status });
      }
    }
    return new Response('{}', { status: 200 });
  };
  return { calls, fetchImpl };
}

async function withEnv(fetchImpl, fn) {
  const prevKey = process.env.EMAIL_API_KEY;
  const prevSeg = process.env.EMAIL_SEGMENT_ID_FOLLOWERS;
  const prevFetch = global.fetch;
  process.env.EMAIL_API_KEY = 'test-key';
  delete process.env.EMAIL_SEGMENT_ID_FOLLOWERS;
  global.fetch = fetchImpl;
  try {
    return await fn();
  } finally {
    global.fetch = prevFetch;
    if (prevKey === undefined) delete process.env.EMAIL_API_KEY; else process.env.EMAIL_API_KEY = prevKey;
    if (prevSeg !== undefined) process.env.EMAIL_SEGMENT_ID_FOLLOWERS = prevSeg;
  }
}

const baseRoutes = {
  'GET /contact-properties': () => [200, { data: [{ key: 'followed_storylines' }, { key: 'reader_id' }] }],
  'GET /segments': () => [200, { data: [{ id: 'seg-f', name: 'Storyline followers' }] }],
};

function followRequest(body) {
  return new Request('https://example.com/api/subscribe', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action: 'follow', ...body }),
  });
}

test('follow list parsing dedupes, drops junk and caps length', () => {
  assert.deepEqual(parseFollows('a, b,,a,Bad Slug,c'), ['a', 'b', 'c']);
  assert.deepEqual(addFollow('a,b', 'a'), ['b', 'a']);
  const many = Array.from({ length: 30 }, (_, i) => `s${i}`).join(',');
  assert.equal(addFollow(many, 'new').length, 25);
  assert.equal(addFollow(many, 'new').at(-1), 'new');
});

test('unfollow token follows the shared signing spec', () => {
  assert.equal(unfollowToken('test-key', 'c-123', 'gemini-3-8'), TOKEN_VECTOR);
});

test('new follower is created in the followers segment only', async () => {
  const { calls, fetchImpl } = mockProvider({
    ...baseRoutes,
    'GET /contacts/reader%40example.com': () => [404, {}],
    'POST /contacts': () => [201, { id: 'c-new' }],
  });
  const res = await withEnv(fetchImpl, () => POST(followRequest({
    email: 'Reader@Example.com', slug: 'gemini-3-8', reader_id: 'anon_0b3c9a3e-5d1f-4c1e-9a55-2f1f0c7d9e11',
  })));
  assert.equal(res.status, 200);
  const created = calls.find((c) => c.method === 'POST' && c.path === '/contacts');
  assert.deepEqual(created.body.segments, [{ id: 'seg-f' }]);
  assert.equal(created.body.properties.followed_storylines, 'gemini-3-8');
  assert.equal(created.body.properties.reader_id, 'anon_0b3c9a3e-5d1f-4c1e-9a55-2f1f0c7d9e11');
  assert.equal(created.body.topics, undefined);
  assert.ok(calls.some((c) => c.method === 'POST' && c.path === '/contacts/c-new/segments/seg-f'));
});

test('existing contact keeps its follows and gains the new one', async () => {
  const { calls, fetchImpl } = mockProvider({
    ...baseRoutes,
    'GET /contacts/reader%40example.com': () => [200, {
      id: 'c-1', properties: { followed_storylines: { value: 'gpt-6-astra', type: 'string' } },
    }],
  });
  const res = await withEnv(fetchImpl, () => POST(followRequest({ email: 'reader@example.com', slug: 'gemini-3-8' })));
  assert.equal(res.status, 200);
  const patch = calls.find((c) => c.method === 'PATCH');
  assert.equal(patch.path, '/contacts/c-1');
  assert.deepEqual(patch.body, { properties: { followed_storylines: 'gpt-6-astra,gemini-3-8' } });
  assert.ok(!calls.some((c) => c.method === 'POST' && c.path === '/contacts'));
});

test('rejects bad input before calling the provider', async () => {
  for (const body of [{ email: 'nope', slug: 'a' }, { email: 'a@b.co', slug: '../etc' }]) {
    const { calls, fetchImpl } = mockProvider({});
    const res = await withEnv(fetchImpl, () => POST(followRequest(body)));
    assert.equal(res.status, 400);
    assert.equal(calls.length, 0);
  }
});

test('honeypot gets a neutral success without touching the provider', async () => {
  const { calls, fetchImpl } = mockProvider({});
  const res = await withEnv(fetchImpl, () => POST(followRequest({ email: 'a@b.co', slug: 'a', hp: 'x' })));
  assert.equal(res.status, 200);
  assert.equal(calls.length, 0);
});

test('signed unfollow removes one story and keeps the rest', async () => {
  const { calls, fetchImpl } = mockProvider({
    ...baseRoutes,
    'GET /contacts/c-123': () => [200, { id: 'c-123', properties: { followed_storylines: 'gemini-3-8,gpt-6-astra' } }],
  });
  const url = `https://example.com/api/subscribe?c=c-123&s=gemini-3-8&t=${TOKEN_VECTOR}`;
  const res = await withEnv(fetchImpl, () => GET(new Request(url)));
  assert.equal(res.status, 200);
  const patch = calls.find((c) => c.method === 'PATCH');
  assert.deepEqual(patch.body, { properties: { followed_storylines: 'gpt-6-astra' } });
  assert.ok(!calls.some((c) => c.method === 'DELETE'));
});

test('unfollow all empties the list and leaves the followers segment (one-click POST)', async () => {
  const { calls, fetchImpl } = mockProvider({
    ...baseRoutes,
    'GET /contacts/c-123': () => [200, { id: 'c-123', properties: { followed_storylines: 'gemini-3-8' } }],
  });
  const token = unfollowToken('test-key', 'c-123', '*');
  const url = `https://example.com/api/subscribe?c=c-123&s=*&t=${token}`;
  const res = await withEnv(fetchImpl, () => POST(new Request(url, { method: 'POST', body: 'List-Unsubscribe=One-Click' })));
  assert.equal(res.status, 200);
  assert.deepEqual(calls.find((c) => c.method === 'PATCH').body, { properties: { followed_storylines: '' } });
  assert.ok(calls.some((c) => c.method === 'DELETE' && c.path === '/contacts/c-123/segments/seg-f'));
});

test('forged or mismatched unfollow tokens are refused', async () => {
  for (const url of [
    'https://example.com/api/subscribe?c=c-123&s=gemini-3-8&t=deadbeef',
    `https://example.com/api/subscribe?c=c-999&s=gemini-3-8&t=${TOKEN_VECTOR}`,
    `https://example.com/api/subscribe?c=c-123&s=*&t=${TOKEN_VECTOR}`,
  ]) {
    const { calls, fetchImpl } = mockProvider({});
    const res = await withEnv(fetchImpl, () => GET(new Request(url)));
    assert.equal(res.status, 400);
    assert.equal(calls.length, 0);
  }
});
