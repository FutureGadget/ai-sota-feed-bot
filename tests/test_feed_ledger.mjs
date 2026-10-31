import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import { GET } from '../api/feed.js';

// Phase 2: the default rolling 24h window is served from the admission ledger
// (data/brief/<day>.json), not from the accumulated run pool. The run pool is
// still the source for calendar ranges and the no-ledger fallback.

async function invoke(query) {
  const url = new URL('https://example.test/api/feed');
  for (const [key, value] of Object.entries(query || {})) {
    if (value == null) continue;
    url.searchParams.set(key, value);
  }
  const res = await GET(new Request(url));
  return { statusCode: res.status, body: await res.json() };
}

function writeJson(file, payload) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, JSON.stringify(payload));
}

function ledgerItem(overrides) {
  return {
    story_key: overrides.story_key || `story:${overrides.url}`,
    id: overrides.url,
    url: overrides.url,
    title: overrides.title,
    source: overrides.source || 'hackernews_ai',
    source_role: overrides.source_role || 'community',
    type: overrides.type || 'news',
    llm_category: overrides.llm_category || 'platform',
    v2_slot: overrides.v2_slot || 'community_signal',
    published: overrides.published || '2026-10-24T00:00:00Z',
    admitted_at: overrides.admitted_at || '2026-10-24T09:00:00Z',
    first_seen: overrides.first_seen || overrides.admitted_at || '2026-10-24T09:00:00Z',
    last_seen: overrides.last_seen || overrides.admitted_at || '2026-10-24T09:00:00Z',
    utility: overrides.utility ?? 1,
    score_at_first_seen: overrides.utility ?? 1,
    rank_at_first_seen: 1,
    summary_1line: overrides.summary_1line || '',
    why_it_matters: overrides.why_it_matters || '',
    also_covered: overrides.also_covered || [],
    ...overrides,
  };
}

test('arrival window serves the admission ledger, not the run pool', async (t) => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'feed-ledger-'));
  const oldCwd = process.cwd();
  t.after(() => {
    process.chdir(oldCwd);
    fs.rmSync(tmp, { recursive: true, force: true });
  });

  writeJson(path.join(tmp, 'data', 'brief', '2026-10-24.json'), {
    schema_version: 1,
    date: '2026-10-24',
    updated_at: '2026-10-24T10:00:00Z',
    items: {
      'story:https://example.com/admitted': ledgerItem({
        url: 'https://example.com/admitted',
        title: 'Admitted by the ledger',
        published: '2026-10-22T00:00:00Z',
        utility: 2,
      }),
      'story:https://example.com/also-admitted': ledgerItem({
        url: 'https://example.com/also-admitted',
        title: 'Second admitted story',
        source: 'simon_willison',
        source_role: 'practitioner',
        llm_category: 'platform',
        v2_slot: 'practitioner_analysis',
        utility: 1,
        admitted_at: '2026-10-24T09:30:00Z',
      }),
    },
  });
  writeJson(path.join(tmp, 'data', 'processed', 'runs_index.json'), [
    { run_at: '2026-10-24T09:00:00Z', path: '2026/10/run.json', item_count: 1 },
  ]);
  writeJson(path.join(tmp, 'data', 'processed', 'runs', '2026', '10', 'run.json'), {
    run_at: '2026-10-24T09:00:00Z',
    items: [
      {
        url: 'https://example.com/run-only',
        title: 'Run pool only, never admitted',
        source: 'openai_blog',
        type: 'news',
        llm_category: 'platform',
        published: '2026-10-24T08:00:00Z',
      },
    ],
  });
  process.chdir(tmp);

  const res = await invoke({
    from: '2026-10-24T00:00:00Z',
    to: '2026-10-24T12:00:00Z',
    window: 'arrival',
    label: 'brief',
    limit: '20',
  });
  assert.equal(res.statusCode, 200);
  assert.equal(res.body.filters.window, 'arrival');
  assert.equal(res.body.ledger.admitted, 2);
  assert.equal(res.body.items.length, 2);
  assert.deepEqual(
    res.body.items.map((item) => item.url),
    ['https://example.com/admitted', 'https://example.com/also-admitted'],
  );
  assert.ok(!res.body.items.some((item) => item.url === 'https://example.com/run-only'));
  // The admitted story was published before the arrival window; first_seen
  // (admission) is what keeps it in the 24h Brief.
  assert.equal(res.body.items[0].first_seen, '2026-10-24T09:00:00Z');
});

test('calendar ranges still use the run pool and published dates', async (t) => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'feed-ledger-calendar-'));
  const oldCwd = process.cwd();
  t.after(() => {
    process.chdir(oldCwd);
    fs.rmSync(tmp, { recursive: true, force: true });
  });

  writeJson(path.join(tmp, 'data', 'brief', '2026-10-24.json'), {
    schema_version: 1,
    date: '2026-10-24',
    updated_at: '2026-10-24T10:00:00Z',
    items: {
      'story:https://example.com/admitted': ledgerItem({
        url: 'https://example.com/admitted',
        title: 'Admitted by the ledger',
      }),
    },
  });
  writeJson(path.join(tmp, 'data', 'processed', 'runs_index.json'), [
    { run_at: '2026-10-24T09:00:00Z', path: '2026/10/run.json', item_count: 1 },
  ]);
  writeJson(path.join(tmp, 'data', 'processed', 'runs', '2026', '10', 'run.json'), {
    run_at: '2026-10-24T09:00:00Z',
    items: [
      {
        url: 'https://example.com/run-only',
        title: 'Run pool calendar story',
        source: 'openai_blog',
        type: 'news',
        llm_category: 'platform',
        published: '2026-10-24T08:00:00Z',
        global_score: 3,
      },
    ],
  });
  process.chdir(tmp);

  const res = await invoke({
    from: '2026-10-24T00:00:00Z',
    to: '2026-10-24T23:59:59.999Z',
    limit: '20',
    label: 'brief',
  });
  assert.equal(res.statusCode, 200);
  assert.equal(res.body.filters.window, 'published');
  assert.equal(res.body.ledger, undefined);
  assert.deepEqual(res.body.items.map((item) => item.url), ['https://example.com/run-only']);
});

test('a story re-admitted after 24h keeps its latest admission, not the old one', async (t) => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'feed-ledger-readmit-'));
  const oldCwd = process.cwd();
  t.after(() => {
    process.chdir(oldCwd);
    fs.rmSync(tmp, { recursive: true, force: true });
  });

  writeJson(path.join(tmp, 'data', 'brief', '2026-10-23.json'), {
    schema_version: 1,
    date: '2026-10-23',
    updated_at: '2026-10-23T09:00:00Z',
    items: {
      'story:https://example.com/long-runner': ledgerItem({
        url: 'https://example.com/long-runner',
        title: 'Long-running story',
        admitted_at: '2026-10-23T09:00:00Z',
        utility: 1,
      }),
    },
  });
  writeJson(path.join(tmp, 'data', 'brief', '2026-10-24.json'), {
    schema_version: 1,
    date: '2026-10-24',
    updated_at: '2026-10-24T09:00:00Z',
    items: {
      'story:https://example.com/long-runner': ledgerItem({
        url: 'https://example.com/long-runner',
        title: 'Long-running story',
        admitted_at: '2026-10-24T09:00:00Z',
        utility: 2,
      }),
    },
  });
  process.chdir(tmp);

  const res = await invoke({
    from: '2026-10-23T12:00:00Z',
    to: '2026-10-24T12:00:00Z',
    window: 'arrival',
    label: 'brief',
    limit: '20',
  });
  assert.equal(res.statusCode, 200);
  assert.equal(res.body.items.length, 1);
  assert.equal(res.body.items[0].admitted_at, '2026-10-24T09:00:00Z');
  assert.equal(res.body.items[0].first_seen, '2026-10-24T09:00:00Z');
});

test('an arrival range older than the ledger falls back to the run pool', async (t) => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'feed-ledger-range-'));
  const oldCwd = process.cwd();
  t.after(() => {
    process.chdir(oldCwd);
    fs.rmSync(tmp, { recursive: true, force: true });
  });

  writeJson(path.join(tmp, 'data', 'brief', '2026-10-24.json'), {
    schema_version: 1,
    date: '2026-10-24',
    updated_at: '2026-10-24T09:00:00Z',
    items: {
      'story:https://example.com/admitted': ledgerItem({
        url: 'https://example.com/admitted',
        title: 'Admitted by the ledger',
      }),
    },
  });
  writeJson(path.join(tmp, 'data', 'processed', 'runs_index.json'), [
    { run_at: '2026-10-24T09:00:00Z', path: '2026/10/run.json', item_count: 1 },
  ]);
  writeJson(path.join(tmp, 'data', 'processed', 'runs', '2026', '10', 'run.json'), {
    run_at: '2026-10-24T09:00:00Z',
    items: [
      {
        url: 'https://example.com/run-only',
        title: 'Run pool older range',
        source: 'openai_blog',
        type: 'news',
        llm_category: 'platform',
        published: '2026-10-24T08:00:00Z',
        global_score: 3,
      },
    ],
  });
  process.chdir(tmp);

  const res = await invoke({
    from: '2026-10-20T00:00:00Z',
    to: '2026-10-24T12:00:00Z',
    window: 'arrival',
    label: 'brief',
    limit: '20',
  });
  assert.equal(res.statusCode, 200);
  assert.equal(res.body.ledger, undefined);
  assert.deepEqual(res.body.items.map((item) => item.url), ['https://example.com/run-only']);
});

test('an interior missing ledger day falls back to the run pool', async (t) => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'feed-ledger-gap-'));
  const oldCwd = process.cwd();
  t.after(() => {
    process.chdir(oldCwd);
    fs.rmSync(tmp, { recursive: true, force: true });
  });

  for (const day of ['2026-10-23', '2026-10-25']) {
    writeJson(path.join(tmp, 'data', 'brief', `${day}.json`), {
      schema_version: 1,
      date: day,
      updated_at: `${day}T09:00:00Z`,
      items: {
        [`story:https://example.com/${day}`]: ledgerItem({
          url: `https://example.com/${day}`,
          title: `Ledger ${day}`,
          admitted_at: `${day}T09:00:00Z`,
        }),
      },
    });
  }
  writeJson(path.join(tmp, 'data', 'processed', 'runs_index.json'), [
    { run_at: '2026-10-25T09:00:00Z', path: '2026/10/run.json', item_count: 1 },
  ]);
  writeJson(path.join(tmp, 'data', 'processed', 'runs', '2026', '10', 'run.json'), {
    run_at: '2026-10-25T09:00:00Z',
    items: [
      {
        url: 'https://example.com/run-gap',
        title: 'Run pool gap fallback',
        source: 'openai_blog',
        type: 'news',
        llm_category: 'platform',
        published: '2026-10-25T08:00:00Z',
        global_score: 3,
      },
    ],
  });
  process.chdir(tmp);

  const res = await invoke({
    from: '2026-10-24T00:00:00Z',
    to: '2026-10-25T12:00:00Z',
    window: 'arrival',
    label: 'brief',
    limit: '20',
  });
  assert.equal(res.statusCode, 200);
  assert.equal(res.body.ledger, undefined);
  assert.deepEqual(res.body.items.map((item) => item.url), ['https://example.com/run-gap']);
});

test('the run pool is the fallback when no ledger exists yet', async (t) => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'feed-ledger-fallback-'));
  const oldCwd = process.cwd();
  t.after(() => {
    process.chdir(oldCwd);
    fs.rmSync(tmp, { recursive: true, force: true });
  });

  writeJson(path.join(tmp, 'data', 'processed', 'runs_index.json'), [
    { run_at: '2026-10-24T09:00:00Z', path: '2026/10/run.json', item_count: 1 },
  ]);
  writeJson(path.join(tmp, 'data', 'processed', 'runs', '2026', '10', 'run.json'), {
    run_at: '2026-10-24T09:00:00Z',
    items: [
      {
        url: 'https://example.com/run-only',
        title: 'Run pool fallback story',
        source: 'openai_blog',
        type: 'news',
        llm_category: 'platform',
        published: '2026-10-24T08:00:00Z',
        global_score: 3,
      },
    ],
  });
  process.chdir(tmp);

  const res = await invoke({
    from: '2026-10-23T12:00:00Z',
    to: '2026-10-24T12:00:00Z',
    window: 'arrival',
    label: 'brief',
    limit: '20',
  });
  assert.equal(res.statusCode, 200);
  assert.deepEqual(res.body.items.map((item) => item.url), ['https://example.com/run-only']);
  assert.equal(res.body.ledger, undefined);
});
