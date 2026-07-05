import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import handler from '../api/feed.js';

function response() {
  return {
    statusCode: 200,
    body: null,
    headers: {},
    setHeader(name, value) {
      this.headers[String(name).toLowerCase()] = value;
      return this;
    },
    status(code) {
      this.statusCode = code;
      return this;
    },
    json(body) {
      this.body = body;
      return this;
    },
  };
}

async function invoke(query) {
  const res = response();
  await handler({ query }, res);
  return res;
}

function normUrl(v) {
  const s = String(v || '').trim();
  return s.endsWith('/') && s.length > 1 ? s.slice(0, -1) : s;
}

function sourceHash(it) {
  const payload = {
    also_covered: (Array.isArray(it?.also_covered) ? it.also_covered : [])
      .map((entry) => ({
        title: String(entry?.title || '').split(/\s+/).filter(Boolean).join(' '),
        url: normUrl(entry?.url),
      }))
      .filter((entry) => entry.url || entry.title),
    summary_1line: String(it?.summary_1line || '').split(/\s+/).filter(Boolean).join(' '),
    title: String(it?.title || '').split(/\s+/).filter(Boolean).join(' '),
    why_it_matters: String(it?.why_it_matters || '').split(/\s+/).filter(Boolean).join(' '),
  };
  return crypto.createHash('sha256').update(JSON.stringify(payload)).digest('hex');
}

test('rejects timezone-naive date bounds', async () => {
  const res = await invoke({ from: '2026-06-20T00:00:00' });
  assert.equal(res.statusCode, 400);
  assert.equal(res.body.error, 'timezone_required');
  assert.equal(res.body.field, 'from');
});

test('accepts timezone-aware date bounds', async () => {
  const res = await invoke({
    from: '2026-06-20T00:00:00-07:00',
    to: '2026-06-20T23:59:59.999-07:00',
    limit: '1',
  });
  assert.equal(res.statusCode, 200);
  assert.match(res.body.filters.from, /Z$/);
  assert.match(res.body.filters.to, /Z$/);
});

test('reports when the selected feed is truncated', async () => {
  const res = await invoke({ limit: '1', label: 'brief' });
  assert.equal(res.statusCode, 200);
  assert.equal(res.body.items.length, 1);
  assert.ok(res.body.total_items > res.body.items.length);
  assert.equal(res.body.has_more, true);
});

test('localized feed reports missing snapshot explicitly', async () => {
  const oldCwd = process.cwd();
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'localized-feed-missing-'));
  try {
    fs.mkdirSync(path.join(tmp, 'data', 'processed'), { recursive: true });
    // Write a dummy processed latest so the feed reads it but doesn't find ko feed
    fs.writeFileSync(
      path.join(tmp, 'data', 'processed', 'latest.json'),
      JSON.stringify([])
    );
    process.chdir(tmp);

    const res = await invoke({ locale: 'ko', localized_snapshot: 'latest', limit: '1', label: 'brief' });
    assert.equal(res.statusCode, 200);
    assert.equal(res.body.locale, 'ko');
    assert.equal(res.body.mode, 'localized_snapshot');
    assert.match(res.headers['cache-control'], /s-maxage=300/);
    assert.notEqual(res.body.status, 'current');
    assert.equal(res.body.is_current, false);
    assert.equal(res.body.is_complete, false);
    assert.ok(Array.isArray(res.body.items));
  } finally {
    process.chdir(oldCwd);
    fs.rmSync(tmp, { recursive: true, force: true });
  }
});

test('localized feed overlays translated text while preserving item identity', async () => {
  const oldCwd = process.cwd();
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'localized-feed-'));
  try {
    fs.mkdirSync(path.join(tmp, 'data', 'processed'), { recursive: true });
    fs.mkdirSync(path.join(tmp, 'data', 'i18n', 'ko', 'feed'), { recursive: true });
    const item = {
      id: 'stable-id',
      url: 'https://example.com/story/',
      title: 'English title',
      summary_1line: 'English summary',
      why_it_matters: 'English why',
      source: 'example_source',
      type: 'news',
      published: '2026-07-05T00:00:00Z',
    };
    fs.writeFileSync(
      path.join(tmp, 'data', 'processed', 'latest.json'),
      JSON.stringify([item]),
    );
    fs.writeFileSync(
      path.join(tmp, 'data', 'processed', 'runs_index.json'),
      JSON.stringify([]),
    );
    fs.writeFileSync(
      path.join(tmp, 'data', 'i18n', 'ko', 'feed', 'latest.json'),
      JSON.stringify({
        locale: 'ko',
        surface: 'feed',
        source_run_at: new Date().toISOString(),
        translated_at: new Date().toISOString(),
        expires_at: new Date(Date.now() + 3600000).toISOString(),
        is_complete: true,
        items: [{
          translation_key: 'https://example.com/story',
          id: 'stable-id',
          source_hash: sourceHash(item),
          title: '한국어 제목',
          summary_1line: '한국어 요약',
          why_it_matters: '한국어 이유',
        }],
      }),
    );
    process.chdir(tmp);
    const res = await invoke({ locale: 'ko', localized_snapshot: 'latest', label: 'brief', limit: '20' });
    assert.equal(res.statusCode, 200);
    assert.equal(res.body.status, 'current');
    assert.equal(res.body.items[0].id, 'stable-id');
    assert.equal(res.body.items[0].url, 'https://example.com/story/');
    assert.equal(res.body.items[0].title, '한국어 제목');
    assert.equal(res.body.items[0].summary_1line, '한국어 요약');
    assert.equal(res.body.items[0].why_it_matters, '한국어 이유');
  } finally {
    process.chdir(oldCwd);
    fs.rmSync(tmp, { recursive: true, force: true });
  }
});

test('localized feed refuses a current snapshot that does not cover every item', async () => {
  const oldCwd = process.cwd();
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'localized-feed-incomplete-'));
  try {
    fs.mkdirSync(path.join(tmp, 'data', 'processed'), { recursive: true });
    fs.mkdirSync(path.join(tmp, 'data', 'i18n', 'ko', 'feed'), { recursive: true });
    const itemA = { id: 'a', url: 'https://example.com/a', title: 'A', type: 'news' };
    const itemB = { id: 'b', url: 'https://example.com/b', title: 'B', type: 'news' };
    fs.writeFileSync(
      path.join(tmp, 'data', 'processed', 'latest.json'),
      JSON.stringify([itemA, itemB]),
    );
    fs.writeFileSync(path.join(tmp, 'data', 'processed', 'runs_index.json'), JSON.stringify([]));
    fs.writeFileSync(
      path.join(tmp, 'data', 'i18n', 'ko', 'feed', 'latest.json'),
      JSON.stringify({
        locale: 'ko',
        surface: 'feed',
        source_run_at: new Date().toISOString(),
        expires_at: new Date(Date.now() + 3600000).toISOString(),
        is_complete: true,
        items: [{ translation_key: 'https://example.com/a', source_hash: sourceHash(itemA), title: '한국어 A' }],
      }),
    );
    process.chdir(tmp);
    const res = await invoke({ locale: 'ko', localized_snapshot: 'latest', label: 'brief', limit: '20' });
    assert.equal(res.statusCode, 200);
    assert.equal(res.body.status, 'incomplete');
    assert.equal(res.body.is_current, false);
    assert.equal(res.body.is_complete, false);
    assert.equal(res.body.localized_missing_count, 1);
    assert.deepEqual(res.body.items, []);
  } finally {
    process.chdir(oldCwd);
    fs.rmSync(tmp, { recursive: true, force: true });
  }
});

test('localized feed refuses stale translations with mismatched source hashes', async () => {
  const oldCwd = process.cwd();
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'localized-feed-stale-hash-'));
  try {
    fs.mkdirSync(path.join(tmp, 'data', 'processed'), { recursive: true });
    fs.mkdirSync(path.join(tmp, 'data', 'i18n', 'ko', 'feed'), { recursive: true });
    const item = { id: 'a', url: 'https://example.com/a', title: 'Changed English title', type: 'news' };
    fs.writeFileSync(path.join(tmp, 'data', 'processed', 'latest.json'), JSON.stringify([item]));
    fs.writeFileSync(path.join(tmp, 'data', 'processed', 'runs_index.json'), JSON.stringify([]));
    fs.writeFileSync(
      path.join(tmp, 'data', 'i18n', 'ko', 'feed', 'latest.json'),
      JSON.stringify({
        locale: 'ko',
        surface: 'feed',
        source_run_at: new Date().toISOString(),
        expires_at: new Date(Date.now() + 3600000).toISOString(),
        is_complete: true,
        items: [{ translation_key: 'https://example.com/a', source_hash: 'stale', title: '오래된 번역' }],
      }),
    );
    process.chdir(tmp);
    const res = await invoke({ locale: 'ko', localized_snapshot: 'latest', label: 'brief', limit: '20' });
    assert.equal(res.statusCode, 200);
    assert.equal(res.body.status, 'incomplete');
    assert.equal(res.body.localized_missing_count, 1);
    assert.deepEqual(res.body.items, []);
  } finally {
    process.chdir(oldCwd);
    fs.rmSync(tmp, { recursive: true, force: true });
  }
});

test('localized feed kill switch returns disabled status without items', async () => {
  const oldValue = process.env.LOCALIZED_FEED_ENABLED;
  try {
    process.env.LOCALIZED_FEED_ENABLED = '0';
    const res = await invoke({ locale: 'ko', localized_snapshot: 'latest', limit: '1', label: 'brief' });
    assert.equal(res.statusCode, 200);
    assert.equal(res.body.locale, 'ko');
    assert.equal(res.body.status, 'disabled');
    assert.equal(res.body.is_current, false);
    assert.equal(res.body.is_complete, false);
    assert.deepEqual(res.body.items, []);
  } finally {
    if (oldValue == null) delete process.env.LOCALIZED_FEED_ENABLED;
    else process.env.LOCALIZED_FEED_ENABLED = oldValue;
  }
});
