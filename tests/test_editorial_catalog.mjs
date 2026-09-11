import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { buildEditorialCatalog, contentVersion } from '../lib/editorial-catalog.js';
import { initializeState, itemStatus, isFresh, markItemOpened } from '../web/editorial-state.js';

const root = fs.mkdtempSync(path.join(os.tmpdir(), 'editorial-catalog-'));
const write = (file, value) => {
  fs.mkdirSync(path.dirname(path.join(root, file)), { recursive: true });
  fs.writeFileSync(path.join(root, file), JSON.stringify(value));
};
const day = '2026-09-10';
const recap = (date, title = 'Today in AI') => ({ date, title, generated_at: `${date}T10:00:00Z`, highlights: ['A useful takeaway'], categories: [{ name: 'Agents', articles: [{ title: 'Source story', url: 'https://example.com/story', summary: 'Evidence' }] }] });
function publishRecap(section, key, source) {
  const file = `${section}/index.json`;
  const existing = fs.existsSync(path.join(root, file)) ? JSON.parse(fs.readFileSync(path.join(root, file))) : [];
  const field = section === 'weekly' ? 'week' : 'date';
  write(`${section}/${key}.json`, source);
  write(file, [...existing.filter((row) => row[field] !== key), { [field]: key, generated_at: source.generated_at }]);
}
function find(id) { return buildEditorialCatalog(root).find((i) => i.id === id); }
try {
  assert.deepEqual(buildEditorialCatalog(root), []);
  publishRecap('daily', day, recap(day));
  publishRecap('weekly', '2026-W37', { ...recap(day), week: '2026-W37', end: day });
  publishRecap('playbook', day, { date: day, title: 'Agent playbook', generated_at: `${day}T10:00:00Z`, cards: [{ id: 'card-1', title: 'Test your agent', problem: 'Failures', apply: 'Evaluate', result: 'Evidence' }] });
  const thread = { slug: 'agent-evals', label: 'Agent evaluations', first_seen: '2026-09-01T01:00:00Z', last_updated: `${day}T08:00:00Z`, generated_at: `${day}T11:00:00Z`, days: [{ date: day, items: [{ sid: 'abc', title: 'An eval release' }] }], editorial: { generated_at: `${day}T09:00:00Z`, tldr: 'An evaluation thread', whats_new: 'A new eval' } };
  write('storylines/index.json', { storylines: [thread] });
  write('storylines/agent-evals.json', thread);
  const concept = { slug: 'agent-memory', title: 'Agent memory', summary: 'Keep the right context', updated: day, sections: [{ heading: 'Mechanism', html: '<p>Memory changes behavior.</p>' }] };
  write('wiki/index.json', { generated_at: `${day}T10:00:00Z`, nodes: { 'agent-memory': concept } });
  write('foundations/index.json', { concepts: { 'agent-memory': concept } });
  const lab = { id: 'lab-protocol', slug: 'protocol', state: 'protocol', title: 'Skills need receipts', summary: 'Test the claims', date: day, generated_at: `${day}T10:00:00Z` };
  write('playbook/lab/protocol.json', lab);
  write('playbook/lab/index.json', [{ ...lab, content_sha256: createHash('sha256').update(JSON.stringify(lab)).digest('hex') }]);
  const initial = buildEditorialCatalog(root);
  assert.equal(initial.length, 7, 'all six producers plus Lab are discoverable');
  assert.equal(new Set(initial.map((i) => i.id)).size, 7);
  assert.equal(find('map:agent-memory').date_precision, 'day');
  assert.equal(find('storylines:agent-evals').updated_at, thread.editorial.generated_at);
  assert.equal(find('daily:' + day).summary, 'A useful takeaway');

  // Rebuild/clock changes are not content updates, including nested clocks.
  const version = find('storylines:agent-evals').version;
  thread.generated_at = '2026-09-11T00:00:00Z';
  thread.editorial.generated_at = '2026-09-11T00:00:00Z';
  write('storylines/agent-evals.json', thread);
  assert.equal(find('storylines:agent-evals').version, version);
  assert.equal(contentVersion({ a: 1, b: 2 }), contentVersion({ b: 2, a: 1 }));
  thread.editorial.whats_new = 'A materially different conclusion';
  write('storylines/agent-evals.json', thread);
  assert.notEqual(find('storylines:agent-evals').version, version, 'narrative-only update is discovered');
  const wikiVersion = find('map:agent-memory').version;
  concept.sections[0].html = '<p>Second edit on the same calendar day.</p>';
  write('wiki/index.json', { nodes: { 'agent-memory': concept } });
  assert.notEqual(find('map:agent-memory').version, wikiVersion);

  // A later scheduled edition and a new concept require no manual registration.
  publishRecap('daily', '2026-09-11', recap('2026-09-11', 'Tomorrow in AI'));
  write('foundations/index.json', { concepts: { 'agent-memory': concept, 'agent-tools': { ...concept, slug: 'agent-tools', title: 'Agent tools' } } });
  assert.ok(find('daily:2026-09-11'));
  assert.ok(find('foundations:agent-tools'));
  assert.ok(find('daily:' + day), 'independent producers preserve existing updates');
  assert.deepEqual(buildEditorialCatalog(root), buildEditorialCatalog(root), 'retry is idempotent');

  // Failed, unindexed, and draft records never become publications.
  write('daily/2026-09-12.json', recap('2026-09-12'));
  write('playbook/lab/drafts/future.json', { ...lab, slug: 'future' });
  assert.equal(find('daily:2026-09-12'), undefined);
  write('playbook/lab/protocol.json', { ...lab, title: 'Not validated yet' });
  assert.equal(find('playbook:lab:protocol'), undefined, 'stale Lab index cannot promote altered source');
  write('daily/index.json', [{ date: '../../private' }, { date: '2026-09-12' }, { date: day }]);
  write('daily/2026-09-12.json', { date: '2026-09-12', title: 'Invalid', categories: [] });
  assert.equal(find('daily:2026-09-12'), undefined);
  fs.writeFileSync(path.join(root, 'daily/index.json'), '{broken');
  assert.ok(find('map:agent-memory'), 'one failed producer does not hide the others');

  // Migration is quiet, and opening one item never acknowledges its siblings.
  const memory = initializeState(null, initial);
  assert.ok(initial.every((i) => itemStatus(memory, i) === 'unread'));
  const daily = initial.find((i) => i.section === 'daily');
  assert.equal(markItemOpened(memory, initial, '/daily'), null, 'section visits do not mark items opened');
  assert.equal(markItemOpened(memory, initial, '/daily/1999-01-01'), null);
  markItemOpened(memory, initial, daily.href);
  assert.equal(itemStatus(memory, daily), 'seen');
  assert.equal(itemStatus(memory, initial.find((i) => i.section === 'weekly')), 'unread');
  assert.equal(itemStatus(memory, { ...daily, version: 'different' }), 'updated');
  assert.equal(itemStatus(memory, { ...daily, id: 'daily:2026-09-11' }), 'new');
  assert.equal(initializeState(memory, initial), memory);
  assert.equal(initializeState({ schema: 2, baseline: 'bad', seen: {} }, initial).schema, 2);
  assert.equal(isFresh({ ...daily, period: day }, '2026-09-11T23:00:00Z'), true);
  assert.equal(isFresh({ ...daily, period: day }, '2026-09-12T00:00:00Z'), false);
  assert.equal(isFresh({ ...daily, period: '2026-09-20' }, `${day}T12:00:00Z`), false);
  assert.equal(isFresh({ section: 'map', updated_at: '2020-01-01' }, `${day}T12:00:00Z`), true);
  console.log('editorial catalog and reader lifecycle: passed');
} finally { fs.rmSync(root, { recursive: true, force: true }); }

// Exercise the real, committed producer outputs too. This catches an evolving
// skill/compiler schema silently dropping one of its future published records.
const actual = buildEditorialCatalog('data');
const json = (file) => JSON.parse(fs.readFileSync(file, 'utf8'));
for (const section of ['daily', 'weekly', 'playbook']) {
  const field = section === 'weekly' ? 'week' : 'date';
  for (const row of json(`data/${section}/index.json`)) {
    assert.ok(actual.some((i) => i.id === `${section}:${row[field]}`), `${section} publication ${row[field]} must remain discoverable`);
  }
}
for (const row of json('data/storylines/index.json').storylines) {
  assert.ok(actual.some((i) => i.id === `storylines:${row.slug}`));
}
for (const [section, file, key] of [['map', 'wiki', 'nodes'], ['foundations', 'foundations', 'concepts']]) {
  for (const row of Object.values(json(`data/${file}/index.json`)[key])) {
    if (['draft', 'withdrawn'].includes(row.status)) continue;
    assert.ok(actual.some((i) => i.id === `${section}:${row.slug}`));
  }
}
for (const row of json('data/playbook/lab/index.json')) {
  if (['protocol', 'published'].includes(row.state)) assert.ok(actual.some((i) => i.id === `playbook:lab:${row.slug}`));
}
for (const item of actual) {
  const target = item.kind === 'lab' ? 'web/playbook-lab.html'
    : item.section === 'playbook' ? 'web/playbook.html' : `web${item.href}.html`;
  assert.ok(fs.existsSync(target), `${item.href} must have a rendered destination`);
}
const deployment = json('vercel.json');
assert.equal(deployment.rewrites.find((r) => r.source === '/updates').destination, '/web/updates.html');
for (const pattern of ['daily/*-*-*.json', 'weekly/*-W*.json', 'storylines/*.json', 'wiki/index.json', 'foundations/index.json', 'playbook/*-*-*.json', 'playbook/lab/*.json']) {
  assert.ok(deployment.functions['api/updates.js'].includeFiles.includes(pattern), `bundle must cover ${pattern}`);
}
console.log(`committed publisher coverage and direct links: ${actual.length} items passed`);
