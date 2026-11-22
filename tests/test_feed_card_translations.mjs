import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import { GET, sourceHash } from '../api/feed.js';

// Per-card translations: /api/feed?locale=ko (without localized_snapshot=latest)
// is the English response for the same params with each card overlaid from
// data/i18n/ko/feed/cards.json while the stored source_hash still matches.

async function invoke(query) {
  const url = new URL('https://example.test/api/feed');
  for (const [key, value] of Object.entries(query || {})) {
    if (value != null) url.searchParams.set(key, value);
  }
  const res = await GET(new Request(url));
  return { statusCode: res.status, body: await res.json() };
}

function writeJson(file, payload) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, JSON.stringify(payload));
}

const A = 'https://news.example.com/deepseek-pricing';
const B = 'https://www.bloomberg.com/deepseek-pricing';
const C = 'https://example.com/unrelated';
const TITLE = 'DeepSeek slashes api pricing for its reasoning model tier today';

// Two clustered cards (they collapse into A, which gains also_covered from
// coverage decoration) and one unrelated card C, in the run pool.
function fixture(t, { cards } = {}) {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'feed-card-i18n-'));
  const oldCwd = process.cwd();
  t.after(() => {
    process.chdir(oldCwd);
    fs.rmSync(tmp, { recursive: true, force: true });
  });
  const runAt = new Date().toISOString();
  const item = (id, url, extra) => ({
    id, url, source: 'google_news', type: 'news', published: runAt,
    summary_1line: `Summary ${id}`, why_it_matters: `Why ${id}`, ...extra,
  });
  writeJson(path.join(tmp, 'data', 'processed', 'runs_index.json'), [{ path: '2026/08/run.json' }]);
  writeJson(path.join(tmp, 'data', 'processed', 'runs', '2026', '08', 'run.json'), {
    run_at: runAt,
    items: [
      item('a', A, { title: TITLE }),
      item('b', B, { title: TITLE, source: 'bloomberg' }),
      item('c', C, { title: 'Unrelated launch' }),
    ],
  });
  process.chdir(tmp);
  const writeCards = (entries) => writeJson(
    path.join(tmp, 'data', 'i18n', 'ko', 'feed', 'cards.json'),
    { locale: 'ko', updated_at: runAt, cards: entries },
  );
  return { tmp, writeCards };
}

function entryFor(englishItem, overrides = {}) {
  return {
    source_hash: sourceHash(englishItem),
    model: 'm',
    translated_at: '2026-11-23T00:00:00Z',
    last_seen: '2026-11-23T00:00:00Z',
    title: `KO ${englishItem.id}`,
    summary_1line: `KO summary ${englishItem.id}`,
    why_it_matters: `KO why ${englishItem.id}`,
    also_covered: (englishItem.also_covered || []).map((e) => ({ url: e.url, title: `KO ${e.title}` })),
    ...overrides,
  };
}

const byId = (body, id) => body.items.find((it) => it.id === id);

test('a card whose stored hash matches is overlaid, including also_covered titles', async (t) => {
  const { writeCards } = fixture(t);
  const english = await invoke({ limit: '20' });
  const a = byId(english.body, 'a');
  assert.equal(a.also_covered.length, 1, 'the hash covers the decorated also_covered');
  writeCards({ [A]: entryFor(a) });

  const ko = await invoke({ locale: 'ko', limit: '20' });
  const koA = byId(ko.body, 'a');
  assert.equal(koA.title, 'KO a');
  assert.equal(koA.summary_1line, 'KO summary a');
  assert.equal(koA.why_it_matters, 'KO why a');
  assert.deepEqual(koA.i18n, { locale: 'ko', translated: true });
  assert.equal(koA.also_covered[0].title, `KO ${a.also_covered[0].title}`);
  assert.equal(koA.also_covered[0].source, a.also_covered[0].source, 'other also_covered fields survive');
  assert.equal(koA.url, a.url);
  assert.equal(koA.source, a.source);
});

test('a stale hash is ignored and the card stays English, marked untranslated', async (t) => {
  const { writeCards } = fixture(t);
  const english = await invoke({ limit: '20' });
  const c = byId(english.body, 'c');
  writeCards({ [C]: entryFor(c, { source_hash: 'f'.repeat(64) }) });

  const koC = byId((await invoke({ locale: 'ko', limit: '20' })).body, 'c');
  assert.equal(koC.title, 'Unrelated launch');
  assert.equal(koC.summary_1line, c.summary_1line);
  assert.deepEqual(koC.i18n, { locale: 'ko', translated: false });
});

test('an edited English card is no longer overlaid with its old translation', async (t) => {
  const { writeCards } = fixture(t);
  const c = byId((await invoke({ limit: '20' })).body, 'c');
  writeCards({ [C]: entryFor({ ...c, title: 'The earlier English title' }) });

  const koC = byId((await invoke({ locale: 'ko', limit: '20' })).body, 'c');
  assert.equal(koC.title, 'Unrelated launch');
  assert.equal(koC.i18n.translated, false);
});

test('only translated cards flip the flag; the rest of the response is the English one', async (t) => {
  const { writeCards } = fixture(t);
  const english = (await invoke({ limit: '20' })).body;
  writeCards({ [C]: entryFor(byId(english, 'c')) });

  const ko = (await invoke({ locale: 'ko', limit: '20' })).body;
  assert.deepEqual(
    ko.items.map((it) => [it.id, it.i18n.translated]).sort(),
    [['a', false], ['c', true]],
  );
  const { items: _en, date: _d, ...enRest } = english;
  const { items: _ko, date: _d2, ...koRest } = ko;
  assert.deepEqual(koRest, enRest);
  assert.deepEqual(ko.items.map((it) => it.id), english.items.map((it) => it.id));
});

test('without a cards file every card is English and untranslated', async (t) => {
  fixture(t);
  const ko = (await invoke({ locale: 'ko', limit: '20' })).body;
  assert.equal(ko.items.length, 2);
  assert.ok(ko.items.every((it) => it.i18n.translated === false && it.i18n.locale === 'ko'));
});

test('the default locale and unknown locales get no overlay and no i18n field', async (t) => {
  const { writeCards } = fixture(t);
  const c = byId((await invoke({ limit: '20' })).body, 'c');
  writeCards({ [C]: entryFor(c) });

  for (const query of [{}, { locale: 'en' }, { locale: 'fr' }]) {
    const body = (await invoke({ ...query, limit: '20' })).body;
    assert.equal(byId(body, 'c').title, 'Unrelated launch');
    assert.ok(body.items.every((it) => !('i18n' in it)), JSON.stringify(query));
  }
});

test('localized_snapshot=latest keeps the snapshot path and adds no per-card fields', async (t) => {
  const { writeCards, tmp } = fixture(t);
  const c = byId((await invoke({ limit: '20' })).body, 'c');
  writeCards({ [C]: entryFor(c) });
  writeJson(path.join(tmp, 'data', 'i18n', 'ko', 'feed', 'latest.json'), {
    locale: 'ko', surface: 'feed', is_complete: true,
    source_run_at: new Date().toISOString(),
    expires_at: new Date(Date.now() + 3600000).toISOString(),
    items: [{ translation_key: C, source_hash: sourceHash(c), title: '스냅샷 C' }],
  });

  const res = await invoke({ locale: 'ko', localized_snapshot: 'latest', label: 'brief', limit: '20' });
  assert.equal(res.body.mode, 'localized_snapshot');
  assert.ok(res.body.items.every((it) => !('i18n' in it)));
  fs.rmSync(path.join(tmp, 'data', 'i18n', 'ko', 'feed', 'cards.json'));
  const again = await invoke({ locale: 'ko', localized_snapshot: 'latest', label: 'brief', limit: '20' });
  assert.deepEqual(again.body.items, res.body.items, 'cards.json does not change the snapshot response');
});

test('the arrival-window ledger path, the English home default, is overlaid too', async (t) => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'feed-card-i18n-ledger-'));
  const oldCwd = process.cwd();
  t.after(() => {
    process.chdir(oldCwd);
    fs.rmSync(tmp, { recursive: true, force: true });
  });
  const url = 'https://example.com/admitted';
  writeJson(path.join(tmp, 'data', 'brief', '2026-10-24.json'), {
    schema_version: 1, date: '2026-10-24', updated_at: '2026-10-24T10:00:00Z',
    items: {
      [`story:${url}`]: {
        story_key: `story:${url}`, id: url, url, title: 'Admitted by the ledger',
        source: 'hackernews_ai', source_role: 'community', type: 'news', llm_category: 'platform',
        v2_slot: 'community_signal', published: '2026-10-24T00:00:00Z',
        admitted_at: '2026-10-24T09:00:00Z', first_seen: '2026-10-24T09:00:00Z',
        last_seen: '2026-10-24T09:00:00Z', utility: 1, score_at_first_seen: 1, rank_at_first_seen: 1,
        summary_1line: 'Ledger summary', why_it_matters: 'Ledger why', also_covered: [],
      },
    },
  });
  writeJson(path.join(tmp, 'data', 'processed', 'runs_index.json'), []);
  process.chdir(tmp);
  const params = { from: '2026-10-24T00:00:00Z', to: '2026-10-24T12:00:00Z', window: 'arrival', label: 'brief', limit: '200' };

  const english = (await invoke(params)).body;
  assert.equal(english.mode, 'history');
  assert.ok(english.ledger, 'served from the ledger');
  writeJson(path.join(tmp, 'data', 'i18n', 'ko', 'feed', 'cards.json'), {
    locale: 'ko', updated_at: '', cards: { [url]: entryFor({ ...english.items[0] }) },
  });

  const ko = (await invoke({ ...params, locale: 'ko' })).body;
  assert.equal(ko.items[0].title, `KO ${english.items[0].id}`);
  assert.deepEqual(ko.items[0].i18n, { locale: 'ko', translated: true });
});
