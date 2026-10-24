import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import { GET } from '../api/feed.js';

async function invoke(query) {
  const url = new URL('https://example.test/api/feed');
  for (const [key, value] of Object.entries(query || {})) {
    if (value == null) continue;
    url.searchParams.set(key, value);
  }
  const res = await GET(new Request(url));
  return { statusCode: res.status, body: await res.json() };
}

function writeLatest(tmp, items) {
  fs.mkdirSync(path.join(tmp, 'data', 'processed'), { recursive: true });
  fs.writeFileSync(path.join(tmp, 'data', 'processed', 'latest.json'), JSON.stringify(items));
  fs.writeFileSync(path.join(tmp, 'data', 'processed', 'runs_index.json'), JSON.stringify([]));
}

function item(overrides) {
  return {
    id: overrides.id || overrides.url,
    url: overrides.url,
    title: overrides.title,
    source: overrides.source,
    type: 'news',
    llm_category: 'platform',
    published: overrides.published || '2026-10-24T00:00:00Z',
    summary_1line: overrides.summary_1line || '',
    ...overrides,
  };
}

test('latest feed caps a search query to one card', async (t) => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'feed-editorial-search-'));
  const oldCwd = process.cwd();
  t.after(() => {
    process.chdir(oldCwd);
    fs.rmSync(tmp, { recursive: true, force: true });
  });
  writeLatest(tmp, [
    item({ id: 's1', url: 'https://example.com/deepseek-1', title: 'DeepSeek Ships a Faster Flash Model', source: 'search_cn_open_weight_labs', published: '2026-10-24T09:00:00Z' }),
    item({ id: 's2', url: 'https://example.com/deepseek-2', title: 'DeepSeek Releases V4.1-Flash-1017 Update', source: 'search_cn_open_weight_labs', published: '2026-10-24T08:00:00Z' }),
    item({ id: 's3', url: 'https://example.com/deepseek-3', title: 'DeepSeek Makes V4.1-Flash Official', source: 'search_cn_open_weight_labs', published: '2026-10-24T07:00:00Z' }),
    item({ id: 'p1', url: 'https://example.com/agent-eval', title: 'A practical agent evaluation harness', source: 'simon_willison', published: '2026-10-24T06:00:00Z' }),
    item({ id: 'p2', url: 'https://example.com/inference', title: 'Serving inference faster with prefix caching', source: 'openai_blog', published: '2026-10-24T05:00:00Z' }),
  ]);
  process.chdir(tmp);

  const res = await invoke({ limit: '20', label: 'brief' });
  assert.equal(res.statusCode, 200);
  const searchItems = res.body.items.filter((it) => it.source === 'search_cn_open_weight_labs');
  assert.equal(searchItems.length, 1, 'one search query contributes one card');
  assert.equal(res.body.items.length, 3);
  assert.equal(res.body.total_items, 3);
});

test('latest feed collapses items that share a pipeline story_key', async (t) => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'feed-editorial-cluster-'));
  const oldCwd = process.cwd();
  t.after(() => {
    process.chdir(oldCwd);
    fs.rmSync(tmp, { recursive: true, force: true });
  });
  writeLatest(tmp, [
    item({
      id: 'a',
      url: 'https://example.com/kimi-a',
      title: 'Kimi K3.1 Pro is the new open-weight leader',
      source: 'openai_blog',
      story_key: 'model:kimi|ver:3.1|title:kimi k3 1 pro is the new open weight leader',
      published: '2026-10-24T09:00:00Z',
    }),
    item({
      id: 'b',
      url: 'https://example.com/kimi-b',
      title: 'Moonshot releases Kimi K3.1 Pro with open weights',
      source: 'simon_willison',
      story_key: 'model:kimi|ver:3.1|title:kimi k3 1 pro is the new open weight leader',
      published: '2026-10-24T08:00:00Z',
    }),
    item({
      id: 'c',
      url: 'https://example.com/kimi-c',
      title: 'Kimi K3.1 Pro benchmark results',
      source: 'latent_space',
      story_key: 'model:kimi|ver:3.1|title:kimi k3 1 pro is the new open weight leader',
      published: '2026-10-24T07:00:00Z',
    }),
    item({
      id: 'd',
      url: 'https://example.com/other',
      title: 'A different agent memory story',
      source: 'langchain_blog',
      published: '2026-10-24T06:00:00Z',
    }),
  ]);
  process.chdir(tmp);

  const res = await invoke({ limit: '20', label: 'brief' });
  assert.equal(res.statusCode, 200);
  assert.equal(res.body.items.length, 2);
  const rep = res.body.items.find((it) => it.source === 'openai_blog');
  assert.ok(rep, 'the highest-authority first-party card is the representative');
  assert.equal(rep.also_covered.length, 2);
  assert.deepEqual(
    rep.also_covered.map((entry) => entry.source).sort(),
    ['latent_space', 'simon_willison'],
  );
});

test('editorial.json source roles are honored by the API', async (t) => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'feed-editorial-artifact-'));
  const oldCwd = process.cwd();
  t.after(() => {
    process.chdir(oldCwd);
    fs.rmSync(tmp, { recursive: true, force: true });
  });
  writeLatest(tmp, [
    item({ id: 'c1', url: 'https://example.com/custom-1', title: 'Custom feed one', source: 'custom_feed', published: '2026-10-24T09:00:00Z' }),
    item({ id: 'c2', url: 'https://example.com/custom-2', title: 'Custom feed two', source: 'custom_feed', published: '2026-10-24T08:00:00Z' }),
    item({ id: 'p1', url: 'https://example.com/practitioner', title: 'Practitioner analysis', source: 'simon_willison', published: '2026-10-24T07:00:00Z' }),
  ]);
  fs.writeFileSync(
    path.join(tmp, 'data', 'processed', 'editorial.json'),
    JSON.stringify({
      source_roles: { custom_feed: 'search' },
      caps: { search: 1 },
      role_totals: { search: 1 },
    }),
  );
  process.chdir(tmp);

  const res = await invoke({ limit: '20', label: 'brief' });
  assert.equal(res.statusCode, 200);
  assert.equal(res.body.items.filter((it) => it.source === 'custom_feed').length, 1);
  assert.equal(res.body.items.length, 2);
});
