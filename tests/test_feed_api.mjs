import assert from 'node:assert/strict';
import crypto from 'node:crypto';
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
  const body = await res.json();
  return {
    statusCode: res.status,
    body,
    headers: Object.fromEntries(res.headers.entries()),
  };
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

// translation-budget-governor plan, Phase 5: status.json may now carry
// budget_paused fields (reason/resumes_at/mode/budget). The API must
// forward them verbatim when present, without renaming or reinterpreting
// them (except `mode`, which is exposed as `governor_mode` to avoid
// colliding with the pre-existing `mode: "localized_snapshot"` response
// field asserted above).
test('localized feed forwards budget_paused status fields verbatim', async () => {
  const oldCwd = process.cwd();
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'localized-feed-budget-paused-'));
  try {
    fs.mkdirSync(path.join(tmp, 'data', 'processed'), { recursive: true });
    fs.mkdirSync(path.join(tmp, 'data', 'i18n', 'ko', 'feed'), { recursive: true });
    fs.writeFileSync(path.join(tmp, 'data', 'processed', 'latest.json'), JSON.stringify([]));
    // Frozen snapshot is old enough to be non-current, so status falls
    // through to whatever status.json reports instead of being forced to
    // "current".
    fs.writeFileSync(
      path.join(tmp, 'data', 'i18n', 'ko', 'feed', 'latest.json'),
      JSON.stringify({
        locale: 'ko',
        surface: 'feed',
        source_run_at: new Date(Date.now() - 48 * 3600000).toISOString(),
        translated_at: new Date(Date.now() - 48 * 3600000).toISOString(),
        expires_at: new Date(Date.now() - 24 * 3600000).toISOString(),
        is_complete: true,
        items: [],
      }),
    );
    fs.writeFileSync(
      path.join(tmp, 'data', 'i18n', 'ko', 'feed', 'status.json'),
      JSON.stringify({
        locale: 'ko',
        surface: 'feed',
        status: 'budget_paused',
        reason: 'monthly_budget',
        resumes_at: '2026-08-01T00:00:00Z',
        mode: 'paused',
        budget: { chars_used: 492000, monthly_cap: 500000, month: '2026-07' },
      }),
    );
    process.chdir(tmp);
    const res = await invoke({ locale: 'ko', localized_snapshot: 'latest', limit: '1', label: 'brief' });
    assert.equal(res.statusCode, 200);
    assert.equal(res.body.status, 'budget_paused');
    assert.equal(res.body.reason, 'monthly_budget');
    assert.equal(res.body.resumes_at, '2026-08-01T00:00:00Z');
    assert.equal(res.body.governor_mode, 'paused');
    assert.deepEqual(res.body.budget, { chars_used: 492000, monthly_cap: 500000, month: '2026-07' });
    // The pre-existing response-shape field must survive untouched.
    assert.equal(res.body.mode, 'localized_snapshot');
    assert.equal(res.body.is_current, false);
  } finally {
    process.chdir(oldCwd);
    fs.rmSync(tmp, { recursive: true, force: true });
  }
});

test('localized feed omits budget-governor fields when status.json has not written them', async () => {
  const oldCwd = process.cwd();
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'localized-feed-no-governor-fields-'));
  try {
    fs.mkdirSync(path.join(tmp, 'data', 'processed'), { recursive: true });
    fs.mkdirSync(path.join(tmp, 'data', 'i18n', 'ko', 'feed'), { recursive: true });
    fs.writeFileSync(path.join(tmp, 'data', 'processed', 'latest.json'), JSON.stringify([]));
    // No latest.json / status.json at all: the pre-governor "missing" path.
    process.chdir(tmp);
    const res = await invoke({ locale: 'ko', localized_snapshot: 'latest', limit: '1', label: 'brief' });
    assert.equal(res.statusCode, 200);
    assert.equal(res.body.status, 'missing');
    assert.equal('reason' in res.body, false);
    assert.equal('resumes_at' in res.body, false);
    assert.equal('governor_mode' in res.body, false);
    assert.equal('budget' in res.body, false);
  } finally {
    process.chdir(oldCwd);
    fs.rmSync(tmp, { recursive: true, force: true });
  }
});

// translation-budget-governor plan, Phase 5, point 2: a frozen snapshot past
// its expires_at must never be reported as current, and the cache header
// must stay bounded (short s-maxage) so an edge cache cannot extend an
// is_current:true response past the 24h window.
test('a frozen snapshot past expires_at is never served as current', async () => {
  const oldCwd = process.cwd();
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'localized-feed-expired-'));
  try {
    fs.mkdirSync(path.join(tmp, 'data', 'processed'), { recursive: true });
    fs.mkdirSync(path.join(tmp, 'data', 'i18n', 'ko', 'feed'), { recursive: true });
    fs.writeFileSync(path.join(tmp, 'data', 'processed', 'latest.json'), JSON.stringify([]));
    fs.writeFileSync(
      path.join(tmp, 'data', 'i18n', 'ko', 'feed', 'latest.json'),
      JSON.stringify({
        locale: 'ko',
        surface: 'feed',
        // is_complete: true (this WAS a good snapshot) but expires_at is
        // long past — the governor kept it frozen through a paused run.
        source_run_at: new Date(Date.now() - 72 * 3600000).toISOString(),
        translated_at: new Date(Date.now() - 72 * 3600000).toISOString(),
        expires_at: new Date(Date.now() - 48 * 3600000).toISOString(),
        is_complete: true,
        items: [],
      }),
    );
    process.chdir(tmp);
    const res = await invoke({ locale: 'ko', localized_snapshot: 'latest', limit: '1', label: 'brief' });
    assert.equal(res.statusCode, 200);
    assert.equal(res.body.is_current, false);
    assert.notEqual(res.body.status, 'current');
    // The localized cache directive must stay short-lived; a long/absent
    // s-maxage would let an edge cache keep serving a stale response past
    // expires_at for longer than the freshness contract allows.
    assert.match(res.headers['cache-control'], /s-maxage=300\b/);
  } finally {
    process.chdir(oldCwd);
    fs.rmSync(tmp, { recursive: true, force: true });
  }
});

test('a paused snapshot with frozen metadata serves dated Korean items in target order', async () => {
  const oldCwd = process.cwd();
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'localized-feed-frozen-items-'));
  try {
    fs.mkdirSync(path.join(tmp, 'data', 'processed'), { recursive: true });
    fs.mkdirSync(path.join(tmp, 'data', 'i18n', 'ko', 'feed'), { recursive: true });
    fs.writeFileSync(path.join(tmp, 'data', 'processed', 'latest.json'), JSON.stringify([]));
    fs.writeFileSync(
      path.join(tmp, 'data', 'i18n', 'ko', 'feed', 'latest.json'),
      JSON.stringify({
        locale: 'ko',
        surface: 'feed',
        source_run_at: new Date(Date.now() - 72 * 3600000).toISOString(),
        expires_at: new Date(Date.now() - 48 * 3600000).toISOString(),
        is_complete: true,
        // target_keys is the frozen ranked order; note it disagrees with the
        // items array order below, and includes one key with no source_meta
        // (must be skipped, not rendered half-empty).
        target_keys: ['https://example.com/b', 'https://example.com/a', 'https://example.com/c'],
        items: [
          { translation_key: 'https://example.com/a', id: 'ida', source_hash: 'x', title: '한국어 A', summary_1line: '요약 A',
            source_meta: { url: 'https://example.com/a', source: 'src_a', published: '2026-07-09T00:00:00Z', type: 'news' } },
          { translation_key: 'https://example.com/b', id: 'idb', source_hash: 'y', title: '한국어 B', summary_1line: '요약 B',
            source_meta: { url: 'https://example.com/b', source: 'src_b', published: '2026-07-08T00:00:00Z', type: 'news' } },
          { translation_key: 'https://example.com/c', id: 'idc', source_hash: 'z', title: '메타 없음' },
        ],
      }),
    );
    fs.writeFileSync(
      path.join(tmp, 'data', 'i18n', 'ko', 'feed', 'status.json'),
      JSON.stringify({ locale: 'ko', surface: 'feed', status: 'budget_paused', reason: 'monthly_budget',
        resumes_at: '2026-08-01T07:00:00+00:00', mode: 'paused' }),
    );
    process.chdir(tmp);
    const res = await invoke({ locale: 'ko', localized_snapshot: 'latest', limit: '20', label: 'brief' });
    assert.equal(res.statusCode, 200);
    assert.equal(res.body.is_current, false);
    assert.equal(res.body.status, 'budget_paused');
    assert.equal(res.body.frozen_snapshot, true);
    assert.equal(res.body.items.length, 2);
    assert.equal(res.body.items[0].title, '한국어 B');
    assert.equal(res.body.items[0].url, 'https://example.com/b');
    assert.equal(res.body.items[0].source, 'src_b');
    assert.equal(res.body.items[1].title, '한국어 A');
  } finally {
    process.chdir(oldCwd);
    fs.rmSync(tmp, { recursive: true, force: true });
  }
});

test('an incomplete-but-current snapshot with frozen metadata serves frozen cards instead of an empty list', async () => {
  const oldCwd = process.cwd();
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'localized-feed-incomplete-frozen-'));
  try {
    fs.mkdirSync(path.join(tmp, 'data', 'processed'), { recursive: true });
    fs.mkdirSync(path.join(tmp, 'data', 'i18n', 'ko', 'feed'), { recursive: true });
    const itemA = { id: 'a', url: 'https://example.com/a', title: 'A', type: 'news' };
    const itemB = { id: 'b', url: 'https://example.com/b', title: 'B (new, untranslated)', type: 'news' };
    fs.writeFileSync(path.join(tmp, 'data', 'processed', 'latest.json'), JSON.stringify([itemA, itemB]));
    fs.writeFileSync(path.join(tmp, 'data', 'processed', 'runs_index.json'), JSON.stringify([]));
    const snapshot = {
      locale: 'ko',
      surface: 'feed',
      source_run_at: new Date().toISOString(),
      expires_at: new Date(Date.now() + 3600000).toISOString(),
      is_complete: true,
      target_keys: ['https://example.com/a'],
      items: [{ translation_key: 'https://example.com/a', source_hash: sourceHash(itemA), title: '한국어 A',
        source_meta: { url: 'https://example.com/a', source: 'src_a', published: '2026-07-12T00:00:00Z', type: 'news' } }],
    };
    fs.writeFileSync(path.join(tmp, 'data', 'i18n', 'ko', 'feed', 'latest.json'), JSON.stringify(snapshot));
    process.chdir(tmp);

    // Plain incomplete (no pause): frozen cards, status stays incomplete.
    let res = await invoke({ locale: 'ko', localized_snapshot: 'latest', label: 'brief', limit: '20' });
    assert.equal(res.body.status, 'incomplete');
    assert.equal(res.body.is_current, false);
    assert.equal(res.body.frozen_snapshot, true);
    assert.equal(res.body.localized_missing_count, 1);
    assert.equal(res.body.items.length, 1);
    assert.equal(res.body.items[0].title, '한국어 A');

    // Same shape during a budget pause: the paused status wins so the shell
    // can explain WHY catch-up is not happening.
    fs.writeFileSync(
      path.join(tmp, 'data', 'i18n', 'ko', 'feed', 'status.json'),
      JSON.stringify({ locale: 'ko', surface: 'feed', status: 'budget_paused', reason: 'provider_daily_cap',
        resumes_at: new Date(Date.now() + 7200000).toISOString(), mode: 'paused' }),
    );
    res = await invoke({ locale: 'ko', localized_snapshot: 'latest', label: 'brief', limit: '20' });
    assert.equal(res.body.status, 'budget_paused');
    assert.equal(res.body.reason, 'provider_daily_cap');
    assert.equal(res.body.frozen_snapshot, true);
    assert.equal(res.body.items.length, 1);
  } finally {
    process.chdir(oldCwd);
    fs.rmSync(tmp, { recursive: true, force: true });
  }
});

test('history-path cluster decoration never leaks into localized source hashes', async () => {
  const oldCwd = process.cwd();
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'localized-feed-cluster-'));
  try {
    fs.mkdirSync(path.join(tmp, 'data', 'processed', 'runs'), { recursive: true });
    fs.mkdirSync(path.join(tmp, 'data', 'i18n', 'ko', 'feed'), { recursive: true });
    const runAt = new Date().toISOString();
    const title = 'DeepSeek slashes api pricing for its reasoning model tier today';
    const itemA = {
      id: 'a', url: 'https://news.example.com/deepseek-pricing', title,
      summary_1line: 'Pricing change coverage', source: 'google_news', type: 'news',
      published: runAt,
    };
    const itemB = {
      id: 'b', url: 'https://www.bloomberg.com/deepseek-pricing', title,
      summary_1line: 'Wire copy of the same story', source: 'bloomberg', type: 'news',
      published: runAt,
    };
    const run = { run_at: runAt, items: [itemA, itemB] };
    fs.writeFileSync(path.join(tmp, 'data', 'processed', 'runs_index.json'), JSON.stringify([
      { path: '2026/08/run.json' },
    ]));
    fs.mkdirSync(path.join(tmp, 'data', 'processed', 'runs', '2026', '08'), { recursive: true });
    fs.writeFileSync(
      path.join(tmp, 'data', 'processed', 'runs', '2026', '08', 'run.json'),
      JSON.stringify(run),
    );
    // Pin hashes to the pipeline's UNDECORATED items (no clustered also_covered),
    // mirroring what build_localized_feed.py hashed from processed/latest.json.
    fs.writeFileSync(
      path.join(tmp, 'data', 'i18n', 'ko', 'feed', 'latest.json'),
      JSON.stringify({
        locale: 'ko', surface: 'feed',
        source_run_at: runAt,
        expires_at: new Date(Date.now() + 3600000).toISOString(),
        is_complete: true,
        items: [
          { translation_key: normUrl(itemA.url), source_hash: sourceHash(itemA), title: '한국어 A' },
          { translation_key: normUrl(itemB.url), source_hash: sourceHash(itemB), title: '한국어 B' },
        ],
      }),
    );
    process.chdir(tmp);
    const en = await invoke({ limit: '20' });
    assert.equal(en.statusCode, 200);
    const decorated = en.body.items.find((it) => it.id === 'a');
    assert.ok(decorated, 'english history path returns the clustered pair');
    assert.equal(decorated.also_covered.length, 1, 'cluster decoration fires on the english path');
    assert.equal(decorated.also_covered[0].source, 'bloomberg');
    const ko = await invoke({ locale: 'ko', localized_snapshot: 'latest', label: 'brief', limit: '20' });
    assert.equal(ko.statusCode, 200);
    assert.equal(ko.body.status, 'current', 'ko hash contract unaffected by cluster decoration');
  } finally {
    process.chdir(oldCwd);
    fs.rmSync(tmp, { recursive: true, force: true });
  }
});
