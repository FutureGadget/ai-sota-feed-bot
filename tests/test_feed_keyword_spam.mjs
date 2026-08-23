import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

// The keyword-spam heuristic exists twice - here in the feed shell and in
// pipeline/render_static_pages.py for the crawler seed. Both are pinned to the
// same fixture so the two implementations cannot drift apart silently.
const source = fs.readFileSync(new URL('../web/index.html', import.meta.url), 'utf8');
const samples = JSON.parse(
  fs.readFileSync(new URL('./fixtures/keyword_spam_samples.json', import.meta.url), 'utf8'),
);

function extractFunction(name) {
  const start = source.indexOf(`function ${name}(`);
  assert.notEqual(start, -1, `missing ${name}`);
  const brace = source.indexOf('{', start);
  let depth = 0;
  for (let i = brace; i < source.length; i += 1) {
    if (source[i] === '{') depth += 1;
    if (source[i] === '}') depth -= 1;
    if (depth === 0) return source.slice(start, i + 1);
  }
  throw new Error(`unterminated ${name}`);
}

const context = vm.createContext({});
vm.runInContext(extractFunction('looksLikeKeywordList'), context);

test('tag spam is detected', () => {
  for (const sample of samples.spam) {
    assert.equal(context.looksLikeKeywordList(sample), true, sample.slice(0, 60));
  }
});

test('editorial prose is kept', () => {
  for (const sample of samples.prose) {
    assert.equal(context.looksLikeKeywordList(sample), false, sample.slice(0, 60));
  }
});

test('segment count floor matches the Python side', () => {
  assert.equal(context.looksLikeKeywordList('agents, evals, memory, tools, cost'), false);
  assert.equal(context.looksLikeKeywordList('agents, evals, memory, tools, cost, rag'), true);
});

test('a clipped trailing ellipsis does not defeat detection', () => {
  assert.equal(context.looksLikeKeywordList('agents, evals, memory, tools, cost, rag…'), true);
  assert.equal(context.looksLikeKeywordList('agents, evals, memory, tools, cost, rag...'), true);
});
