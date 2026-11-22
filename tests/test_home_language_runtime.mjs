import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

import { uiRuntime } from './ui_runtime.mjs';

// The same page script runs in every language. These tests run its real
// runtime and card helpers against each generated page's own dictionary.
function readPage(path) {
  return fs.readFileSync(new URL(path, import.meta.url), 'utf8');
}

function extractFunction(source, name) {
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

function pageContext(path) {
  const source = readPage(path);
  const context = vm.createContext({});
  vm.runInContext(uiRuntime(source), context);
  for (const name of ['esc', 'languageMarks']) {
    vm.runInContext(extractFunction(source, name), context);
  }
  return context;
}

const english = pageContext('../web/index.html');
const korean = pageContext('../web/ko/index.html');

test('a card the translator skipped is tagged and marked as English on the Korean page', () => {
  const marks = korean.languageMarks({ i18n: { locale: 'ko', translated: false } });
  assert.equal(marks.attr, ' lang="en"');
  assert.match(marks.tag, /badge-lang/);
  assert.match(marks.tag, /영문/);
});

test('a translated card, or one with no language data, carries no mark', () => {
  for (const [page, item] of [
    [korean, { i18n: { locale: 'ko', translated: true } }],
    [korean, {}],
    [english, {}],
  ]) {
    const marks = page.languageMarks(item);
    assert.equal(marks.attr, '');
    assert.equal(marks.tag, '');
  }
});

test('links stay English until a Korean page exists, then follow the language', () => {
  assert.equal(korean.localHref('/'), '/ko/');
  assert.equal(korean.localHref('/daily'), '/ko/daily');
  assert.equal(korean.localHref('/models'), '/models');
  assert.equal(english.localHref('/daily'), '/daily');
});

test('text comes from the page dictionary and a missing key shows itself', () => {
  assert.equal(english.t('card.englishTag'), 'English');
  assert.equal(korean.t('card.englishTag'), '영문');
  assert.equal(korean.t('no.such.key'), 'no.such.key');
});

test('placeholders are filled, and one with no value stays visible', () => {
  assert.equal(english.t('pool.moreFrom', { range: 'Nov 22' }), 'More from Nov 22');
  assert.equal(korean.t('pool.moreFrom', { range: '11월 22일' }), '11월 22일 기사 더 보기');
  assert.equal(korean.t('pool.moreFrom', {}), '{range} 기사 더 보기');
});
