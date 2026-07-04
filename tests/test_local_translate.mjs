import assert from 'node:assert/strict';
import test from 'node:test';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const scriptPath = path.resolve(__dirname, '../web/local-translate.js');
const scriptContent = fs.readFileSync(scriptPath, 'utf8');

// Mock browser globals for IIFE evaluation
globalThis.window = {};
globalThis.document = {
  addEventListener: () => {},
  readyState: 'complete',
  head: {
    appendChild: () => {}
  },
  createElement: () => ({
    setAttribute: () => {},
    appendChild: () => {},
    addEventListener: () => {},
    style: {}
  }),
  querySelector: () => null,
  querySelectorAll: () => []
};
globalThis.Node = {
  TEXT_NODE: 3,
  ELEMENT_NODE: 1
};
Object.defineProperty(globalThis, 'navigator', {
  value: {
    languages: ['ko', 'en'],
    language: 'ko',
    userAgent: 'Mozilla/5.0'
  },
  configurable: true,
  writable: true
});

globalThis.localStorage = {
  getItem: () => null,
  setItem: () => {}
};
Object.defineProperty(globalThis, 'crypto', {
  value: {
    subtle: {
      digest: async () => new Uint8Array(32)
    }
  },
  configurable: true,
  writable: true
});


// Evaluate the script in the mocked browser context
(new Function(scriptContent))();

const { _test } = globalThis.window.llmDigestTranslate;

test('implementation stays reader-local without keyless third-party translation fallback', () => {
  assert.equal(scriptContent.includes('translate.googleapis.com'), false);
  assert.equal(scriptContent.includes('google-translate'), false);
});

test('downloadable native language packs do not start in-page translation in v1', () => {
  assert.equal(_test.isReadyInPageAvailability('available'), true);
  assert.equal(_test.isReadyInPageAvailability('readily'), true);
  assert.equal(_test.isReadyInPageAvailability('downloadable'), false);
  assert.equal(_test.isReadyInPageAvailability('after-download'), false);
  assert.equal(_test.isReadyInPageAvailability('unsupported'), false);
});

test('isUrlText helper tests', () => {
  assert.equal(_test.isUrlText('https://example.com/foo', 'https://example.com/foo'), true);
  assert.equal(_test.isUrlText('example.com/foo', 'example.com/foo'), true);
  assert.equal(_test.isUrlText('Some Human Title', 'https://example.com/foo'), false);
  assert.equal(_test.isUrlText('', ''), false);
});

test('getBrowserAssistInstruction helper tests', () => {
  const instructionKo = _test.getBrowserAssistInstruction('ko');
  assert.match(instructionKo, /번역/);

  const instructionJa = _test.getBrowserAssistInstruction('ja');
  assert.match(instructionJa, /翻訳/);

  const instructionZh = _test.getBrowserAssistInstruction('zh-CN');
  assert.match(instructionZh, /翻译/);

  const instructionEn = _test.getBrowserAssistInstruction('en');
  assert.match(instructionEn, /browser's translate/);
});

test('mobile Safari browser assist matches the real page menu flow', () => {
  navigator.userAgent = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1';
  navigator.platform = 'iPhone';
  navigator.maxTouchPoints = 5;

  assert.equal(_test.getBrowserFamily(), 'safari-mobile');
  assert.match(_test.getBrowserAssistInstruction('ko'), /페이지 메뉴/);
  assert.match(_test.getBrowserAssistInstruction('ko'), /웹 사이트 번역/);
});

test('Chrome on iOS uses Chrome mobile assist copy', () => {
  navigator.userAgent = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/138.0.0.0 Mobile/15E148 Safari/604.1';
  navigator.platform = 'iPhone';
  navigator.maxTouchPoints = 5;

  assert.equal(_test.getBrowserFamily(), 'chrome-mobile');
  assert.match(_test.getBrowserAssistInstruction('ko'), /Chrome/);
  assert.match(_test.getBrowserAssistInstruction('ko'), /더보기/);
});


test('shouldSkipElement helper tests', () => {
  const mockElement = (tagName, className, textContent, dataTrack, parent = null, skip = false, term = false) => {
    return {
      tagName: tagName.toUpperCase(),
      className,
      textContent,
      getAttribute: (attr) => {
        if (attr === 'data-track') return dataTrack;
        return null;
      },
      hasAttribute: (attr) => {
        if (attr === 'data-translate-skip') return skip;
        if (attr === 'data-translate-term') return term;
        return false;
      },
      classList: {
        contains: (cls) => {
          if (!className) return false;
          return className.split(/\s+/).includes(cls);
        }
      },
      parentElement: parent,
      closest: (selector) => {
        if (selector === 'h1, h2, h3, h4, h5, h6') {
          if (tagName.toLowerCase().match(/^h[1-6]$/)) return true;
          if (parent && parent.tagName.match(/^H[1-6]$/)) return true;
        }
        if (selector === '[data-translate-term]') {
          return term;
        }
        return null;
      }
    };
  };


  // Plain structure tags to translate
  const p = mockElement('p', '', 'Hello world');
  assert.equal(_test.shouldSkipElement(p), false);

  // Structural markup should be skipped
  const pre = mockElement('pre', '', 'code block');
  assert.equal(_test.shouldSkipElement(pre), true);

  const button = mockElement('button', 'art-toggle-btn', 'Expand');
  assert.equal(_test.shouldSkipElement(button), true);

  // Time / Date tags should be skipped
  const time = mockElement('time', '', '2026-07-04');
  assert.equal(_test.shouldSkipElement(time), true);

  // Non-human links must be skipped
  const linkUrl = mockElement('a', '', 'https://example.com', '');
  assert.equal(_test.shouldSkipElement(linkUrl), true);

  // Human title links with data-track should be translated
  const linkHuman = mockElement('a', '', 'A great article', 'daily-link');
  assert.equal(_test.shouldSkipElement(linkHuman), false);

  // Link in header should be translated
  const header = mockElement('h3', '', '');
  const linkInHeader = mockElement('a', '', 'Inside header link', '', header);
  assert.equal(_test.shouldSkipElement(linkInHeader), false);
});

test('glossary protection and restoration', () => {
  const input = 'We are deploying a new RAG system utilizing Claude 3.5 Sonnet on AWS.';
  const { text: protectedText, map } = _test.protect(input);

  // High-value technical terms should be replaced by placeholders
  assert.match(protectedText, /__ph_\d+__/);
  assert.equal(Object.keys(map).length > 0, true);


  // Simulating typical machine translation behavior where placeholder spacing may vary
  const translated1 = '우리는 AWS에서 __ph_0__ Sonnet을 활용하는 새로운 __ph_1__ 시스템을 배포하고 있습니다.';
  const restored1 = _test.restoreGlossary(translated1, map);
  assert.ok(restored1.includes('RAG'));
  assert.ok(restored1.includes('Claude 3.5'));

  // Testing spaced placeholders (e.g. "__ ph_0 __" or "__PH_0__")
  const translated2 = '우리는 AWS에서 __ ph_0 __ Sonnet을 활용하는 새로운 __PH_1__ 시스템을 배포하고 있습니다.';
  const restored2 = _test.restoreGlossary(translated2, map);
  assert.ok(restored2.includes('RAG'));
  assert.ok(restored2.includes('Claude 3.5'));
});
