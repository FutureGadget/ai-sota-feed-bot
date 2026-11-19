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

test('a Korean signup joins the Korean segment when it is configured', async () => {
  const saved = { en: process.env.EMAIL_SEGMENT_ID, ko: process.env.EMAIL_SEGMENT_ID_KO };
  process.env.EMAIL_SEGMENT_ID = 'seg-en';
  process.env.EMAIL_SEGMENT_ID_KO = 'seg-ko';
  try {
    const ko = await invokeCapturing({ email: 'reader@example.com', locale: 'ko' }, [new Response('{}', { status: 201 })]);
    assert.deepEqual(ko.calls[0].segments, [{ id: 'seg-ko' }]);
    const en = await invokeCapturing({ email: 'reader@example.com' }, [new Response('{}', { status: 201 })]);
    assert.deepEqual(en.calls[0].segments, [{ id: 'seg-en' }]);
    delete process.env.EMAIL_SEGMENT_ID_KO;
    const fallback = await invokeCapturing({ email: 'reader@example.com', locale: 'ko' }, [new Response('{}', { status: 201 })]);
    assert.deepEqual(fallback.calls[0].segments, [{ id: 'seg-en' }]);
  } finally {
    for (const [key, value] of [['EMAIL_SEGMENT_ID', saved.en], ['EMAIL_SEGMENT_ID_KO', saved.ko]]) {
      if (value === undefined) delete process.env[key];
      else process.env[key] = value;
    }
  }
});

async function withSegments(fn) {
  const saved = { en: process.env.EMAIL_SEGMENT_ID, ko: process.env.EMAIL_SEGMENT_ID_KO };
  process.env.EMAIL_SEGMENT_ID = 'seg-en';
  process.env.EMAIL_SEGMENT_ID_KO = 'seg-ko';
  try {
    await fn();
  } finally {
    for (const [key, value] of [['EMAIL_SEGMENT_ID', saved.en], ['EMAIL_SEGMENT_ID_KO', saved.ko]]) {
      if (value === undefined) delete process.env[key];
      else process.env[key] = value;
    }
  }
}

function recordingFetch(responses) {
  const calls = [];
  const impl = async (url, init) => {
    calls.push({ url: String(url), method: init?.method || 'GET' });
    return responses.shift() || new Response('{}', { status: 200 });
  };
  return { calls, impl };
}

test('an existing subscriber who picks Korean moves to the Korean edition', async () => {
  await withSegments(async () => {
    const { calls, impl } = recordingFetch([
      new Response('{}', { status: 409 }),
      new Response('{}', { status: 200 }),
      new Response('{}', { status: 200 }),
    ]);
    const res = await invoke({ email: 'Reader@Example.com', locale: 'ko' }, impl);
    assert.equal(res.statusCode, 200);
    assert.deepEqual(res.body, { ok: true });
    assert.deepEqual(calls.slice(1), [
      { url: 'https://api.resend.com/contacts/reader%40example.com/segments/seg-ko', method: 'POST' },
      { url: 'https://api.resend.com/contacts/reader%40example.com/segments/seg-en', method: 'DELETE' },
    ]);
  });
});

test('an existing Korean subscriber who picks English moves back', async () => {
  await withSegments(async () => {
    const { calls, impl } = recordingFetch([
      new Response('{}', { status: 409 }),
      new Response('{}', { status: 422 }),
      new Response('{}', { status: 404 }),
    ]);
    const res = await invoke({ email: 'reader@example.com', locale: 'en' }, impl);
    assert.equal(res.statusCode, 200);
    assert.deepEqual(calls.slice(1).map((c) => [c.method, c.url.split('/segments/')[1]]), [
      ['POST', 'seg-en'],
      ['DELETE', 'seg-ko'],
    ]);
  });
});

test('a failed join keeps the reader in their current edition', async () => {
  await withSegments(async () => {
    const { calls, impl } = recordingFetch([
      new Response('{}', { status: 409 }),
      new Response('{}', { status: 500 }),
    ]);
    const res = await invoke({ email: 'reader@example.com', locale: 'ko' }, impl);
    assert.equal(res.statusCode, 502);
    assert.equal(res.body.error, 'provider_error');
    assert.equal(calls.length, 2, 'never leaves the old segment when the join failed');
  });
});

test('a new subscriber is not moved between editions', async () => {
  await withSegments(async () => {
    const { calls, impl } = recordingFetch([new Response('{}', { status: 201 })]);
    const res = await invoke({ email: 'reader@example.com', locale: 'ko' }, impl);
    assert.equal(res.statusCode, 200);
    assert.equal(calls.length, 1);
  });
});

test('without a Korean segment a duplicate signup makes no segment calls', async () => {
  const saved = process.env.EMAIL_SEGMENT_ID_KO;
  delete process.env.EMAIL_SEGMENT_ID_KO;
  try {
    const { calls, impl } = recordingFetch([new Response('{}', { status: 409 })]);
    const res = await invoke({ email: 'reader@example.com', locale: 'ko' }, impl);
    assert.equal(res.statusCode, 200);
    assert.equal(calls.length, 1);
  } finally {
    if (saved !== undefined) process.env.EMAIL_SEGMENT_ID_KO = saved;
  }
});

async function withFrom(fn, extra = {}) {
  const saved = { from: process.env.EMAIL_FROM, reply: process.env.EMAIL_REPLY_TO };
  process.env.EMAIL_FROM = 'LLM Digest <digest@example.com>';
  if (extra.replyTo) process.env.EMAIL_REPLY_TO = extra.replyTo;
  else delete process.env.EMAIL_REPLY_TO;
  try {
    await fn();
  } finally {
    for (const [key, value] of [['EMAIL_FROM', saved.from], ['EMAIL_REPLY_TO', saved.reply]]) {
      if (value === undefined) delete process.env[key];
      else process.env[key] = value;
    }
  }
}

function capturingFetch(responses) {
  const calls = [];
  const impl = async (url, init) => {
    calls.push({ url: String(url), method: init?.method || 'GET', body: init?.body ? JSON.parse(init.body) : null });
    return responses.shift() || new Response('{}', { status: 200 });
  };
  return { calls, impl };
}

test('a new subscriber gets one welcome email in their language', async () => {
  await withFrom(async () => {
    const { calls, impl } = capturingFetch([new Response('{}', { status: 201 }), new Response('{}', { status: 200 })]);
    const res = await invoke({ email: 'reader@example.com', locale: 'ko' }, impl);
    assert.equal(res.statusCode, 200);
    assert.equal(calls.length, 2);
    assert.equal(calls[1].url, 'https://api.resend.com/emails');
    assert.deepEqual(calls[1].body.to, ['reader@example.com']);
    assert.equal(calls[1].body.from, 'LLM Digest <digest@example.com>');
    assert.match(calls[1].body.subject, /구독을 환영합니다/);
    assert.match(calls[1].body.html, /\/ko\/daily\?utm_source=email/);
    assert.match(calls[1].body.html, /digest@example\.com을 연락처에 추가/);
    assert.equal(calls[1].body.reply_to, undefined);
  });
});

test('a weekly-only welcome points at the weekly recap and carries Reply-To when set', async () => {
  await withFrom(async () => {
    const { calls, impl } = capturingFetch([new Response('{}', { status: 201 }), new Response('{}', { status: 200 })]);
    await invoke({ email: 'reader@example.com', weekly_only: true }, impl);
    assert.match(calls[1].body.subject, /Welcome to LLM Digest/);
    assert.match(calls[1].body.text, /weekly recap arrives every Saturday/);
    assert.match(calls[1].body.html, /\/weekly\?utm_source=email/);
    assert.equal(calls[1].body.reply_to, 'owner@example.com');
    assert.match(calls[1].body.text, /replies reach a person/);
  }, { replyTo: 'owner@example.com' });
});

test('an existing subscriber gets no welcome email', async () => {
  await withFrom(async () => {
    const { calls, impl } = capturingFetch([new Response('{}', { status: 409 })]);
    const res = await invoke({ email: 'reader@example.com' }, impl);
    assert.equal(res.statusCode, 200);
    assert.equal(calls.filter((c) => c.url.endsWith('/emails')).length, 0);
  });
});

test('a failed welcome email never fails the signup', async () => {
  await withFrom(async () => {
    const { impl } = capturingFetch([new Response('{}', { status: 201 }), new Response('boom', { status: 500 })]);
    const res = await invoke({ email: 'reader@example.com' }, impl);
    assert.equal(res.statusCode, 200);
    assert.deepEqual(res.body, { ok: true });
  });
});
