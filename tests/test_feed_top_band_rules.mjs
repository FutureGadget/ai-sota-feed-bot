import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import { GET } from '../api/feed.js';

// The ledger-served Brief is ordered by admission utility. The ranker's
// top-band rules (at most three papers in the top ten, no paper or long video
// in the lead) are applied again at serving time from editorial.json.

const DAY = '2026-10-24';
const RULES = {
  enabled: true,
  top_n: 10,
  max_research: 3,
  lead_excludes_research: true,
  lead_excludes_video: true,
};

function writeJson(file, payload) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, JSON.stringify(payload));
}

function card(id, utility, overrides = {}) {
  const url = `https://example.test/${id}`;
  return {
    story_key: `story:${id}`,
    id,
    url,
    title: `Story ${id}`,
    source: `source_${id}`,
    source_role: 'practitioner',
    type: 'news',
    llm_category: 'platform',
    slot: 'practitioner_analysis',
    v2_slot: 'practitioner_analysis',
    published: `${DAY}T00:00:00Z`,
    admitted_at: `${DAY}T09:00:00Z`,
    first_seen: `${DAY}T09:00:00Z`,
    last_seen: `${DAY}T09:00:00Z`,
    utility,
    score_at_first_seen: utility,
    also_covered: [],
    ...overrides,
  };
}

const paper = (id, utility) =>
  card(id, utility, { type: 'paper', llm_category: 'research', slot: 'research_watch', v2_slot: 'research_watch' });

async function brief(t, items, rules) {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'feed-top-band-rules-'));
  const oldCwd = process.cwd();
  t.after(() => {
    process.chdir(oldCwd);
    fs.rmSync(tmp, { recursive: true, force: true });
  });
  writeJson(path.join(tmp, 'data', 'brief', `${DAY}.json`), {
    date: DAY,
    updated_at: `${DAY}T09:00:00Z`,
    items: Object.fromEntries(items.map((it) => [it.story_key, it])),
  });
  // Roomy caps so the fold does not interfere with what is under test.
  const editorial = {
    source_roles: {},
    caps: { default: 50, practitioner: 50 },
    role_totals: { practitioner: 50 },
  };
  if (rules) editorial.brief_top_band = rules;
  writeJson(path.join(tmp, 'data', 'processed', 'editorial.json'), editorial);
  writeJson(path.join(tmp, 'data', 'processed', 'runs_index.json'), []);
  process.chdir(tmp);
  const url = new URL('https://example.test/api/feed');
  url.searchParams.set('window', 'arrival');
  url.searchParams.set('from', `${DAY}T00:00:00Z`);
  url.searchParams.set('to', `${DAY}T23:59:59Z`);
  url.searchParams.set('label', 'brief');
  const res = await GET(new Request(url));
  const body = await res.json();
  assert.ok(body.ledger, 'the ledger must be the serving source');
  return body.items;
}

const isPaper = (it) => it.slot === 'research_watch';

test('at most three papers hold a top-ten seat and none is dropped', async (t) => {
  // Six papers outscore everything, as on-topic arXiv papers do.
  const items = [
    ...Array.from({ length: 6 }, (_, i) => paper(`paper${i}`, 2 - i * 0.01)),
    ...Array.from({ length: 8 }, (_, i) => card(`news${i}`, 1 - i * 0.01)),
  ];
  const out = await brief(t, items, RULES);
  assert.equal(out.length, items.length, 'no card is dropped');
  assert.equal(out.slice(0, 10).filter(isPaper).length, 3);
  assert.equal(out.filter(isPaper).length, 6, 'the demoted papers stay in the Brief');
  assert.ok(!isPaper(out[0]), 'a paper does not lead');
  assert.equal(out[0].id, 'news0', 'the best non-paper story leads');
});

test('a long video does not lead', async (t) => {
  const items = [
    card('talk', 2, { type: 'video', slot: 'video_watch', v2_slot: 'video_watch' }),
    card('news0', 1.5),
    card('news1', 1.4),
  ];
  const out = await brief(t, items, RULES);
  assert.deepEqual(out.map((it) => it.id), ['news0', 'talk', 'news1']);
});

test('a quiet day of only papers is left alone', async (t) => {
  const items = Array.from({ length: 4 }, (_, i) => paper(`paper${i}`, 2 - i * 0.1));
  const out = await brief(t, items, RULES);
  assert.deepEqual(out.map((it) => it.id), ['paper0', 'paper1', 'paper2', 'paper3']);
});

test('the lead lift keeps the front page to three cards per source', async (t) => {
  const hn = (id, utility) => card(id, utility, { source: 'hackernews_ai' });
  const items = [
    paper('paper0', 3),
    hn('hn0', 2.9),
    hn('hn1', 2.8),
    hn('hn2', 2.7),
    card('news0', 2.6),
    hn('hn3', 2.5),
    card('news1', 2.4),
  ];
  const out = await brief(t, items, RULES);
  assert.ok(!isPaper(out[0]));
  assert.ok(out.slice(0, 5).filter((it) => it.source === 'hackernews_ai').length <= 3);
  assert.equal(out.length, items.length);
});

test('without rules in editorial.json the order is the utility order', async (t) => {
  const items = [paper('paper0', 2), card('news0', 1.5), card('news1', 1.4)];
  const out = await brief(t, items, null);
  assert.deepEqual(out.map((it) => it.id), ['paper0', 'news0', 'news1']);
});
