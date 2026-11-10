import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

// web/watchlist.js is a browser script; without a document it only publishes
// its pure helpers on globalThis.
await import('../web/watchlist.js');
const { matchEntities, normalize, unseenItems } = globalThis.llmDigestWatch;

const read = (path) => JSON.parse(readFileSync(new URL(path, import.meta.url), 'utf8'));
const { entities } = read('../web/watch-data.json');
const { cases } = read('./fixtures/watch_match_cases.json');

test('browser matcher agrees with pipeline/watch.py on the shared cases', () => {
  for (const c of cases) {
    assert.deepEqual(matchEntities(c.title, c.source, entities), c.expect, c.title);
  }
});

test('normalize keeps inner dots and drops sentence dots', () => {
  assert.equal(normalize('Z.ai ships GLM-5.5.'), ' z.ai ships glm 5.5 ');
});

test('published entities carry what the browser needs', () => {
  assert.ok(entities.length >= 10);
  for (const e of entities) {
    assert.match(e.slug, /^[a-z0-9][a-z0-9-]{0,99}$/);
    assert.ok(e.label && ['tool', 'model', 'topic'].includes(e.kind));
    for (const item of e.items) {
      assert.match(item.sid, /^[0-9a-f]{16}$/);
      assert.equal(item.url, undefined);
    }
  }
});

test('unseen items are those after the seen mark, capped at a week', () => {
  const now = Date.parse('2026-11-10T12:00:00Z');
  const entity = { items: [
    { sid: 'a', first_seen: '2026-11-10T06:00:00+00:00' },
    { sid: 'b', first_seen: '2026-11-08T00:00:00+00:00' },
    { sid: 'c', first_seen: '2026-11-01T00:00:00+00:00' },
  ] };
  assert.deepEqual(unseenItems(entity, '2026-11-09T00:00:00Z', now).map((i) => i.sid), ['a']);
  // A reader away for a month sees the last week, not the whole backlog.
  assert.deepEqual(unseenItems(entity, '2026-10-01T00:00:00Z', now).map((i) => i.sid), ['a', 'b']);
  assert.deepEqual(unseenItems(entity, '', now).map((i) => i.sid), ['a', 'b']);
});
