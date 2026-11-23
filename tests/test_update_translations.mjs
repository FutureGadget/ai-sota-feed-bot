import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import { GET } from '../api/updates.js';
import { updateHash } from '../lib/update-translations.js';

// /api/updates?locale=ko is the English catalog with each Editor's Desk item
// overlaid from data/i18n/ko/updates/titles.json while the stored source_hash
// still matches. LOCALIZED_FEED_ENABLED=0 switches the overlay off.

function writeJson(file, payload) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, JSON.stringify(payload));
}

const item = (id, title, summary, extra = {}) => ({
  id, section: 'storylines', section_label: 'Storylines', href: `/storyline/${id.split(':')[1]}`,
  title, summary, published_at: null, updated_at: '2026-11-22T00:00:00Z', date_precision: 'time',
  version: 'a'.repeat(24), kind: 'article', period: null, ...extra,
});

const STEERING = item('storylines:activation-steering', 'Activation Steering', 'A Nov 19 paper argues RL post-training is steering.');
const DEEPSEEK = item('storylines:deepseek-open-sources', 'DeepSeek Open-Sources', 'Zhang Bo open-sourced a personal agent.');
const BARE = item('map:agent-cost', 'Agent token costs run away', '');

function fixture(t, entries, links) {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'updates-i18n-'));
  const oldCwd = process.cwd();
  t.after(() => {
    process.chdir(oldCwd);
    fs.rmSync(tmp, { recursive: true, force: true });
  });
  writeJson(path.join(tmp, 'data', 'served', 'updates.json'), {
    catalog_version: 1, items: [STEERING, DEEPSEEK, BARE], daily: null,
  });
  if (entries) {
    writeJson(path.join(tmp, 'data', 'i18n', 'ko', 'updates', 'titles.json'), { locale: 'ko', updated_at: 'x', items: entries, ...(links ? { links } : {}) });
  }
  process.chdir(tmp);
}

async function invoke(query = '') {
  const res = await GET(new Request(`https://example.test/api/updates${query}`));
  return { status: res.status, body: await res.json() };
}

const entry = (english, overrides = {}) => ({
  source_hash: updateHash(english), origin: 'translation', model: 'm', translated_at: '2026-11-23T00:00:00Z',
  title: `KO ${english.title}`, summary: `KO ${english.summary}`, ...overrides,
});
const byId = (body, id) => body.items.find((i) => i.id === id);

test('an item whose stored hash matches shows the Korean title and summary, with identity untouched', async (t) => {
  fixture(t, { [STEERING.id]: entry(STEERING) });
  const { body } = await invoke('?locale=ko');
  const got = byId(body, STEERING.id);
  assert.equal(got.title, 'KO Activation Steering');
  assert.equal(got.summary, 'KO A Nov 19 paper argues RL post-training is steering.');
  assert.deepEqual(got.i18n, { locale: 'ko', translated: true });
  for (const key of ['id', 'href', 'version', 'updated_at', 'section']) assert.equal(got[key], STEERING[key]);
});

test('a stale or missing entry leaves the item in English, marked untranslated', async (t) => {
  fixture(t, {
    [STEERING.id]: entry({ ...STEERING, title: 'Activation Steering (old title)' }),
    // DEEPSEEK has no entry at all.
  });
  const { body } = await invoke('?locale=ko');
  for (const source of [STEERING, DEEPSEEK]) {
    const got = byId(body, source.id);
    assert.equal(got.title, source.title);
    assert.equal(got.summary, source.summary);
    assert.deepEqual(got.i18n, { locale: 'ko', translated: false });
  }
});

test('a summary change makes the entry stale even when the title is unchanged', async (t) => {
  fixture(t, { [STEERING.id]: entry({ ...STEERING, summary: 'An older summary.' }) });
  const { body } = await invoke('?locale=ko');
  assert.equal(byId(body, STEERING.id).i18n.translated, false);
  assert.equal(byId(body, STEERING.id).title, 'Activation Steering');
});

test('an item with no English summary stays without one', async (t) => {
  fixture(t, { [BARE.id]: entry(BARE, { summary: '' }) });
  const got = byId((await invoke('?locale=ko')).body, BARE.id);
  assert.equal(got.title, 'KO Agent token costs run away');
  assert.equal(got.summary, '');
});

test('an item with a Korean page gets localized_href, translated or not, and its href stays the identity', async (t) => {
  fixture(t, { [STEERING.id]: entry(STEERING) }, {
    [STEERING.id]: '/ko/storyline/activation-steering',
    [DEEPSEEK.id]: '/ko/storyline/deepseek-open-sources',
  });
  const { body } = await invoke('?locale=ko');
  const steering = byId(body, STEERING.id);
  assert.equal(steering.localized_href, '/ko/storyline/activation-steering');
  assert.equal(steering.href, STEERING.href);
  assert.equal(steering.i18n.translated, true);
  const deepseek = byId(body, DEEPSEEK.id);
  assert.equal(deepseek.localized_href, '/ko/storyline/deepseek-open-sources');
  assert.equal(deepseek.i18n.translated, false);
  assert.equal('localized_href' in byId(body, BARE.id), false);
});

test('a stored link that is not the locale form of the item href is ignored', async (t) => {
  fixture(t, {}, {
    [STEERING.id]: 'https://evil.example/ko/storyline/activation-steering',
    [DEEPSEEK.id]: '/ko/storyline/something-else',
    [BARE.id]: '/en/topic/agent-cost',
  });
  const { body } = await invoke('?locale=ko');
  for (const source of [STEERING, DEEPSEEK, BARE]) assert.equal('localized_href' in byId(body, source.id), false, source.id);
});

test('the English catalog never carries localized_href', async (t) => {
  fixture(t, {}, { [STEERING.id]: '/ko/storyline/activation-steering' });
  assert.equal('localized_href' in byId((await invoke('')).body, STEERING.id), false);
});

test('the default locale, no locale and an unknown locale get the English catalog and no i18n field', async (t) => {
  fixture(t, { [STEERING.id]: entry(STEERING) });
  for (const query of ['', '?locale=en', '?locale=xx']) {
    const { status, body } = await invoke(query);
    assert.equal(status, 200);
    const got = byId(body, STEERING.id);
    assert.equal(got.title, 'Activation Steering');
    assert.equal('i18n' in got, false, query);
  }
});

test('LOCALIZED_FEED_ENABLED=0 returns the plain English catalog', async (t) => {
  fixture(t, { [STEERING.id]: entry(STEERING) });
  for (const flag of ['0', 'false', 'off']) {
    process.env.LOCALIZED_FEED_ENABLED = flag;
    t.after(() => { delete process.env.LOCALIZED_FEED_ENABLED; });
    const got = byId((await invoke('?locale=ko')).body, STEERING.id);
    assert.equal(got.title, 'Activation Steering');
    assert.equal('i18n' in got, false, flag);
  }
});

test('a localized request with no store file still serves the catalog in English', async (t) => {
  fixture(t);
  const { status, body } = await invoke('?locale=ko');
  assert.equal(status, 200);
  assert.deepEqual(body.items.map((i) => i.i18n.translated), [false, false, false]);
});

test('the Worker preloads the titles store for a localized locale only', () => {
  const worker = fs.readFileSync(new URL('../worker/src/index.js', import.meta.url), 'utf8');
  assert.match(worker, /case '\/api\/updates':[\s\S]*?isLocalized\(locale\)\) keys\.push\(`i18n\/\$\{locale\}\/updates\/titles\.json`\)/);
});
