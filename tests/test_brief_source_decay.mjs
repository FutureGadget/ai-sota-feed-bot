import assert from 'node:assert/strict';
import test from 'node:test';

import { orderWithEditorialCaps, spreadRepeatedSources } from '../lib/editorial.js';

const CFG = { decay: 0.7, floor: 0.3 };
const card = (source, utility, url = `${source}-${utility}`) => ({ source, utility, url, title: url });
const sources = (items) => items.map((it) => it.source).join(',');

test('distinct sources keep their utility order', () => {
  const items = [card('a', 3), card('b', 2), card('c', 1)];
  assert.deepEqual(spreadRepeatedSources(items, CFG), items);
});

test('a block from one source is spread among close-scoring cards', () => {
  const items = [card('hn', 1.0, 'h1'), card('hn', 0.99, 'h2'), card('hn', 0.98, 'h3'), card('blog', 0.9), card('paper', 0.85)];
  assert.equal(sources(spreadRepeatedSources(items, CFG)), 'hn,blog,paper,hn,hn');
});

test('a much stronger repeat still outranks a weak card', () => {
  const items = [card('hn', 1.0, 'h1'), card('hn', 0.95, 'h2'), card('blog', 0.2)];
  assert.equal(sources(spreadRepeatedSources(items, CFG)), 'hn,hn,blog');
});

test('no config or decay 1 leaves the order alone', () => {
  const items = [card('hn', 1, 'h1'), card('hn', 0.9, 'h2'), card('blog', 0.8)];
  assert.deepEqual(spreadRepeatedSources(items, null), items);
  assert.deepEqual(spreadRepeatedSources(items, { decay: 1, floor: 0 }), items);
});

test('rank stands in for utility when a card has none', () => {
  const ranked = [card('hn', undefined, 'h1'), card('hn', undefined, 'h2'), card('blog', undefined), card('hn', undefined, 'h3')];
  const scored = ranked.map((it, i) => ({ ...it, utility: ranked.length - i }));
  assert.deepEqual(
    spreadRepeatedSources(ranked, CFG).map((it) => it.url),
    spreadRepeatedSources(scored, CFG).map((it) => it.url)
  );
});

test('non-positive utility keeps a repeat below a close rival', () => {
  const items = [card('hn', 0, 'h1'), card('hn', -0.1, 'h2'), card('blog', -0.11)];
  assert.equal(sources(spreadRepeatedSources(items, CFG)), 'hn,blog,hn');
});

test('over-cap cards stay below every cap-compliant card', () => {
  const editorial = {
    caps: { community: 2, default: 3 },
    role_totals: { community: 2 },
    source_roles: { hn: 'community' },
    source_decay: CFG,
  };
  const items = [card('hn', 1, 'h1'), card('hn', 0.99, 'h2'), card('hn', 0.98, 'h3'), card('blog', 0.8)];
  const ordered = orderWithEditorialCaps(items, editorial);
  assert.deepEqual(ordered.map((it) => it.url), ['h1', 'blog-0.8', 'h2', 'h3']);
  assert.equal(ordered[3].beyond_cap, true);
});
