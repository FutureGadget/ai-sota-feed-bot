import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

// scripts/build_served_data.mjs builds data/served/*.json with the same
// functions the API handlers use, and three of those functions return a
// served/*.json file when one already exists. A leftover artifact therefore
// used to be read back and rewritten unchanged on every deploy. The build
// must compute from the source data even when stale output is present.

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const SCRIPT = path.join(ROOT, 'scripts', 'build_served_data.mjs');

function writeJson(file, payload) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, JSON.stringify(payload));
}

function isoHoursAgo(hours) {
  return new Date(Date.now() - hours * 3600 * 1000).toISOString();
}

test('a stale data/served artifact is rebuilt from source, not read back', (t) => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'served-build-'));
  t.after(() => fs.rmSync(tmp, { recursive: true, force: true }));

  const runAt = isoHoursAgo(2);
  const day = runAt.slice(0, 10);
  const fresh = {
    url: 'https://example.test/fresh-story',
    title: 'Fresh story about an agent runtime',
    source: 'hackernews_ai',
    published: runAt,
  };

  // Source data: one feed run and one admitted Brief story, both recent.
  writeJson(path.join(tmp, 'data', 'processed', 'runs', 'run.json'), {
    run_at: runAt,
    items: [{ ...fresh, global_score: 1 }],
  });
  writeJson(path.join(tmp, 'data', 'processed', 'runs_index.json'), [
    { run_at: runAt, path: 'run.json', item_count: 1 },
  ]);
  writeJson(path.join(tmp, 'data', 'processed', 'latest.json'), [{ ...fresh, global_score: 1 }]);
  writeJson(path.join(tmp, 'data', 'brief', `${day}.json`), {
    date: day,
    updated_at: runAt,
    items: {
      'story|fresh': {
        ...fresh,
        story_key: 'story|fresh',
        source_role: 'community',
        admitted_at: runAt,
        first_seen: runAt,
        utility: 1,
      },
    },
  });

  // Stale precompute from an earlier build, as a committed copy would be.
  const staleItem = { url: 'https://example.test/stale-story', title: 'Stale story', source: 'hackernews_ai' };
  writeJson(path.join(tmp, 'data', 'served', 'brief_ledger.json'), {
    version: 1,
    items: [{ ...staleItem, story_key: 'story|stale', admitted_at: '2026-01-01T00:00:00Z' }],
    files: ['2026-01-01.json'],
    updated_at: '2026-01-01T00:00:00Z',
  });
  writeJson(path.join(tmp, 'data', 'served', 'rss_items.json'), [
    { ...staleItem, published: '2026-01-01T00:00:00Z' },
  ]);
  writeJson(path.join(tmp, 'data', 'served', 'updates.json'), {
    catalog_version: 1,
    items: [{ id: 'daily:2026-01-01', section: 'daily', title: 'Stale catalog entry' }],
  });

  execFileSync(process.execPath, [SCRIPT], { cwd: tmp, stdio: 'pipe' });

  const served = (name) => JSON.parse(fs.readFileSync(path.join(tmp, 'data', 'served', name), 'utf-8'));

  const ledger = served('brief_ledger.json');
  assert.deepEqual(ledger.files, [`${day}.json`]);
  assert.deepEqual(ledger.items.map((it) => it.url), [fresh.url]);

  const rssUrls = served('rss_items.json').map((it) => it.url);
  assert.ok(rssUrls.includes(fresh.url), 'RSS pool must carry the fresh story');
  assert.ok(!rssUrls.includes(staleItem.url), 'RSS pool must not carry the stale artifact');

  const updates = served('updates.json');
  assert.ok(
    !(updates.items || []).some((it) => it.id === 'daily:2026-01-01'),
    'updates catalog must not carry the stale artifact'
  );
});

test('data/served is never tracked by git', () => {
  const ignore = fs.readFileSync(path.join(ROOT, '.gitignore'), 'utf-8');
  assert.match(ignore, /^data\/served\/$/m);
});
