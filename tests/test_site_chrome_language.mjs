import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

// web/site-chrome.js decides which language links in the site bar show. A link to
// another language shows when the browser prefers it; the link back to English
// always shows, so a reader on a /ko/ page can leave it. These tests run the real
// script against a stub page whose bar holds the given language links.

const SCRIPT = fs.readFileSync(new URL('../web/site-chrome.js', import.meta.url), 'utf8');

function runChrome({ links, languages, ui }) {
  const anchors = links.map((locale) => ({ dataset: { languageLocale: locale }, hidden: true }));
  const actions = { querySelector: () => null, querySelectorAll: () => anchors };
  const chrome = { querySelector: (selector) => (selector === '.site-actions-fallback' ? actions : null) };
  const context = vm.createContext({
    navigator: { languages, language: languages[0] },
    document: {
      documentElement: { classList: { contains: () => false, add() {} } },
      querySelector: (selector) => (selector === '.site-chrome' ? chrome : null),
    },
    ...(ui ? { UI: ui } : {}),
  });
  vm.runInContext(SCRIPT, context);
  return Object.fromEntries(anchors.map((a) => [a.dataset.languageLocale, !a.hidden]));
}

test('a Korean page shows the EN link to a reader whose browser lists only Korean', () => {
  for (const ui of [{ locale: 'ko', defaultLocale: 'en' }, undefined]) {
    assert.deepEqual(runChrome({ links: ['en'], languages: ['ko-KR', 'ko'], ui }), { en: true });
  }
});

test('an English page shows the KO link only to a reader whose browser prefers Korean', () => {
  const ui = { locale: 'en', defaultLocale: 'en' };
  assert.deepEqual(runChrome({ links: ['ko'], languages: ['en-US', 'en'], ui }), { ko: false });
  assert.deepEqual(runChrome({ links: ['ko'], languages: ['en-US', 'ko-KR'], ui }), { ko: true });
});
