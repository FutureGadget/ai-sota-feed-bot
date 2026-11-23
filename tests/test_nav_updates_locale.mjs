import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

import * as reader from '../web/editorial-state.js';
import { uiRuntime } from './ui_runtime.mjs';

// web/nav-updates.js draws the Editor's Desk (the feed strip and the updates
// panels) on every page. On a localized home page it asks /api/updates for that
// page's language, and it marks an item that kept its English text. These tests
// run the real script in a sandbox against each generated page's own dictionary.

const read = (path) => fs.readFileSync(new URL(path, import.meta.url), 'utf8');
// The sandbox cannot resolve the script's dynamic import; hand it the same module.
const SCRIPT = read('../web/nav-updates.js').replace(/import\('\/editorial-state\.js[^']*'\)/, 'Promise.resolve(globalThis.__reader)');

class Element {
  constructor(tag) { Object.assign(this, { tag, children: [], dataset: {}, className: '', textContent: '', attrs: {} }); }
  appendChild(child) { this.children.push(child); return child; }
  append(...kids) { this.children.push(...kids); }
  prepend(child) { this.children.unshift(child); }
  replaceChildren(...kids) { this.children = kids; }
  setAttribute(key, value) { this.attrs[key] = String(value); }
  querySelector() { return null; }
  querySelectorAll() { return []; }
  addEventListener() {}
  get classList() { return { add: () => {} }; }
  find(predicate, out = []) {
    if (predicate(this)) out.push(this);
    this.children.forEach((child) => child.find(predicate, out));
    return out;
  }
}

const item = (slug, extra = {}) => ({
  id: `storylines:${slug}`, section: 'storylines', section_label: 'Storylines', href: `/storyline/${slug}`,
  title: `Title ${slug}`, summary: `Summary ${slug}`, published_at: null, updated_at: '2026-11-22T00:00:00Z',
  date_precision: 'time', version: 'a'.repeat(24), kind: 'article', period: null, ...extra,
});

// Run the script as one page would: `dictionary` is that page's runtime source
// (or none), `catalog` what /api/updates returns. Resolves with the URLs the
// script fetched and the rows it drew into the feed strip.
async function runPage({ dictionary = '', catalog }) {
  const fetched = [];
  const anchor = new Element('div');
  const context = vm.createContext({
    URL, URLSearchParams, setTimeout, __reader: reader,
    fetch: (url) => { fetched.push(url); return Promise.resolve({ ok: true, json: async () => catalog }); },
    location: { pathname: '/', search: '' },
    matchMedia: () => ({ matches: false }),
    sessionStorage: { getItem: () => null, setItem() {} },
    localStorage: { getItem: () => null, setItem() {} },
    addEventListener() {},
    document: {
      readyState: 'complete', head: new Element('head'), documentElement: { dataset: {} },
      createElement: (tag) => new Element(tag),
      querySelector: (selector) => (selector.startsWith('link[') ? new Element('link') : null),
      querySelectorAll: () => [],
      getElementById: (id) => (id === 'freshUpdates' ? anchor : null),
      addEventListener() {},
    },
  });
  vm.runInContext(dictionary || 'globalThis.window = globalThis;', context);
  vm.runInContext(SCRIPT, context);
  await context.llmDigestUpdates.promise;
  await new Promise((resolve) => setTimeout(resolve, 0));
  const rows = anchor.find((el) => el.tag === 'li');
  return { fetched, rows };
}

const catalog = (...items) => ({ catalog_version: 1, now: '2026-11-23T00:00:00Z', items });
const korean = uiRuntime(read('../web/ko/index.html'));
const english = uiRuntime(read('../web/index.html'));
const titleOf = (row) => row.find((el) => el.className === 'editorial-title')[0];
const summaryOf = (row) => row.find((el) => el.className === 'editorial-summary')[0];

test('the Korean home page asks /api/updates for Korean', async () => {
  const { fetched } = await runPage({ dictionary: korean, catalog: catalog(item('a')) });
  assert.deepEqual(fetched, ['/api/updates?locale=ko']);
});

test('the English home page and a page with no dictionary ask for the plain catalog', async () => {
  for (const dictionary of [english, '']) {
    const { fetched } = await runPage({ dictionary, catalog: catalog(item('a')) });
    assert.deepEqual(fetched, ['/api/updates']);
  }
});

test('an item the translator skipped is marked as English on the Korean page', async () => {
  const { rows } = await runPage({
    dictionary: korean,
    catalog: catalog(item('kept', { i18n: { locale: 'ko', translated: false } })),
  });
  assert.equal(rows.length, 1);
  assert.equal(titleOf(rows[0]).lang, 'en');
  assert.equal(summaryOf(rows[0]).lang, 'en');
  const tags = rows[0].find((el) => el.tag === 'span' && el.textContent === '영문');
  assert.equal(tags.length, 1);
  assert.equal(tags[0].title, '아직 번역되지 않아 영문으로 표시됩니다');
});

test('a translated item, or one with no language data, carries no mark', async () => {
  for (const [dictionary, extra] of [
    [korean, { i18n: { locale: 'ko', translated: true } }],
    [english, {}],
  ]) {
    const { rows } = await runPage({ dictionary, catalog: catalog(item('a', extra)) });
    assert.equal(rows.length, 1);
    assert.equal(titleOf(rows[0]).lang, undefined);
    assert.equal(summaryOf(rows[0]).lang, undefined);
    assert.equal(rows[0].find((el) => el.textContent === '영문' || el.textContent === 'English').length, 0);
  }
});

test('on the Korean page a desk link opens the Korean page when the item has one', async () => {
  const { rows } = await runPage({
    dictionary: korean,
    catalog: catalog(
      item('ko', { localized_href: '/ko/storyline/ko', i18n: { locale: 'ko', translated: true } }),
      item('en', { i18n: { locale: 'ko', translated: false } }),
      item('bad', { localized_href: '/ko/storyline/elsewhere' }),
    ),
  });
  const hrefs = Object.fromEntries(rows.map((row) => [titleOf(row).textContent, titleOf(row).href]));
  assert.deepEqual(hrefs, {
    'Title ko': '/ko/storyline/ko',
    'Title en': '/storyline/en',
    'Title bad': '/storyline/bad',
  });
});
