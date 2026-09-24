import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = fs.readFileSync(new URL('../web/posthog-client.js', import.meta.url), 'utf8');
const READER_ID = 'anon_0b3c9a3e-5d1f-4c1e-9a55-2f1f0c7d9e11';

function load(href, { stored = {}, storageThrows = false } = {}) {
  const replaced = [];
  const storage = {
    getItem(key) {
      if (storageThrows) throw new Error('blocked');
      return Object.hasOwn(stored, key) ? stored[key] : null;
    },
    setItem(key, value) {
      if (storageThrows) throw new Error('blocked');
      stored[key] = String(value);
    },
  };
  const window = {
    location: new URL(href),
    history: { state: null, replaceState: (_state, _title, url) => replaced.push(url) },
    crypto: { randomUUID: () => '11111111-2222-4333-8444-555555555555' },
    addEventListener() {},
  };
  const context = vm.createContext({
    URL,
    window,
    localStorage: storage,
    // init() bails on localhost; stub fetch so it resolves to "disabled".
    fetch: async () => ({ ok: false }),
    console: { debug() {} },
  });
  vm.runInContext(source, context);
  return { api: window.aiFeedPostHog, replaced, stored };
}

test('adopts a valid rid as the reader id and strips it from the URL', () => {
  const { api, replaced, stored } = load(
    `https://www.llm-digest.com/story/abc?utm_source=email&rid=${READER_ID}#top`,
    { stored: { ai_feed_anon_user_id: 'anon_old' } },
  );
  assert.deepEqual(replaced, ['/story/abc?utm_source=email#top']);
  assert.equal(stored.ai_feed_anon_user_id, READER_ID);
  assert.equal(api.getAnonUserId(), READER_ID);
});

test('strips but ignores the fallback sentinel and malformed ids', () => {
  for (const rid of ['none', 'alice@example.com', '{{{contact.reader_id|none}}}']) {
    const { api, replaced } = load(
      `https://www.llm-digest.com/?utm_source=email&rid=${encodeURIComponent(rid)}`,
      { stored: { ai_feed_anon_user_id: 'anon_existing' } },
    );
    assert.deepEqual(replaced, ['/?utm_source=email']);
    assert.equal(api.getAnonUserId(), 'anon_existing');
  }
});

test('keeps the adopted id for the page when storage is blocked', () => {
  const { api } = load(`https://www.llm-digest.com/?rid=${READER_ID}`, { storageThrows: true });
  assert.equal(api.getAnonUserId(), READER_ID);
  assert.equal(api.getAnonUserId(), READER_ID);
});

test('leaves URLs without rid untouched', () => {
  const { replaced } = load('https://www.llm-digest.com/daily?utm_source=email');
  assert.deepEqual(replaced, []);
});
