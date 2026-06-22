import assert from 'node:assert/strict';
import test from 'node:test';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

// The "new since your last visit" logic (the New badge, the meta-line count, and
// the "Catch me up" brief) lives as inline script in web/index.html. Rather than
// re-implement the predicate here, we extract the *actual shipped* source of the
// two helper functions and evaluate them, so the test pins real behavior.
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const HTML = fs.readFileSync(path.join(ROOT, 'web', 'index.html'), 'utf8');

// Pull a `function <name>(...) { ... }` block out of the HTML by brace matching.
function extractFunctionSource(html, name) {
  const head = new RegExp(`function\\s+${name}\\s*\\(`).exec(html);
  assert.ok(head, `could not find function ${name} in web/index.html`);
  const open = html.indexOf('{', head.index);
  assert.ok(open !== -1, `no opening brace for ${name}`);
  let depth = 0;
  for (let i = open; i < html.length; i++) {
    const c = html[i];
    if (c === '{') depth++;
    else if (c === '}') {
      depth--;
      if (depth === 0) return html.slice(head.index, i + 1);
    }
  }
  throw new Error(`unbalanced braces for ${name}`);
}

const itemArrivalSrc = extractFunctionSource(HTML, 'itemArrivalMs');
const isNewSrc = extractFunctionSource(HTML, 'isNewSinceLastVisit');

// Build the predicate against the extracted source, injecting a fixed
// `visitLastMs` (a module-level closure const in the page).
function buildIsNewSince(visitLastMs) {
  // eslint-disable-next-line no-new-func
  const factory = new Function(
    'visitLastMs',
    `${itemArrivalSrc}\n${isNewSrc}\nreturn isNewSinceLastVisit;`,
  );
  return factory(visitLastMs);
}

const DAY = 24 * 60 * 60 * 1000;
const NOW = Date.parse('2026-06-22T12:00:00Z');
const LAST_VISIT = NOW - DAY; // visited yesterday
const iso = (ms) => new Date(ms).toISOString();

test('flags an item that ENTERED THE FEED since last visit even if published earlier', () => {
  const isNew = buildIsNewSince(LAST_VISIT);
  // An arXiv paper / slow-RSS item: published 4 days ago, but first appeared in
  // the reader's feed today (after the last visit). This is exactly what
  // "newly added since last visit" should surface.
  const item = {
    title: 'AutoPass: Evidence-Guided LLM Agents',
    published: iso(NOW - 4 * DAY),
    first_seen: iso(NOW - 2 * 60 * 60 * 1000), // appeared 2h ago
  };
  assert.equal(isNew(item), true);
});

test('does NOT flag an item that has been in the feed since before last visit', () => {
  const isNew = buildIsNewSince(LAST_VISIT);
  const item = {
    title: 'old story still ranking',
    published: iso(NOW - 5 * DAY),
    first_seen: iso(NOW - 3 * DAY), // entered feed 3 days ago, before the visit
  };
  assert.equal(isNew(item), false);
});

test('falls back to published when first_seen is absent (no-history latest path)', () => {
  const isNew = buildIsNewSince(LAST_VISIT);
  const item = {
    title: 'fresh item, latest path',
    published: iso(NOW - 2 * 60 * 60 * 1000), // published 2h ago
    first_seen: null,
  };
  assert.equal(isNew(item), true);
});

test('never flags anything on the first visit (no baseline)', () => {
  const isNew = buildIsNewSince(0);
  const item = { title: 'whatever', published: iso(NOW), first_seen: iso(NOW) };
  assert.equal(isNew(item), false);
});

test('items with no usable date are not flagged new', () => {
  const isNew = buildIsNewSince(LAST_VISIT);
  assert.equal(isNew({ title: 'no dates', published: null, first_seen: null }), false);
});
