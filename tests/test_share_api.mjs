import assert from 'node:assert/strict';
import test from 'node:test';

import handler from '../api/share.js';

function response() {
  return {
    statusCode: 200,
    body: null,
    headers: {},
    ended: false,
    setHeader(name, value) {
      this.headers[name] = value;
      return this;
    },
    status(code) {
      this.statusCode = code;
      return this;
    },
    send(body) {
      this.body = body;
      return this;
    },
    json(body) {
      this.body = body;
      return this;
    },
    end() {
      this.ended = true;
      return this;
    },
  };
}

async function invoke(query) {
  const res = response();
  await handler({ query }, res);
  return res;
}

test('story share redirects preserve a supported target language', async () => {
  const res = await invoke({
    u: 'https://openai.com/index/introducing-chatgpt-futures-class-of-2026',
    lang: 'ko',
  });

  assert.equal(res.statusCode, 302);
  assert.equal(
    res.headers.Location,
    '/story/0001057cafdd5edc?utm_source=share&utm_medium=social&lang=ko',
  );
});

test('story share redirects ignore unsupported target languages', async () => {
  const res = await invoke({
    u: 'https://openai.com/index/introducing-chatgpt-futures-class-of-2026',
    lang: 'fr',
  });

  assert.equal(res.statusCode, 302);
  assert.equal(
    res.headers.Location,
    '/story/0001057cafdd5edc?utm_source=share&utm_medium=social',
  );
});
