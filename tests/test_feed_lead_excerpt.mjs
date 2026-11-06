// The front-page lead falls back to the first sentence of the Jev
// content_excerpt. Page excerpts can open with repeated marquee text; the
// lead must skip it instead of printing it three times (2026-11-07).
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const html = fs.readFileSync(path.join(ROOT, 'web', 'index.html'), 'utf8');

function grab(name) {
  const start = html.indexOf(`function ${name}(`);
  assert.ok(start >= 0, `missing ${name} in web/index.html`);
  let depth = 0;
  for (let k = html.indexOf('{', start); k < html.length; k++) {
    if (html[k] === '{') depth++;
    else if (html[k] === '}' && --depth === 0) return html.slice(start, k + 1);
  }
  throw new Error(`unterminated ${name}`);
}

const leadExcerpt = new Function(
  ['cleanText', 'looksLikeKeywordList', 'stripExcerptDebris', 'leadExcerpt'].map(grab).join('\n') + '\nreturn leadExcerpt;'
)();

// The Together Compiler page (Brief, 2026-11-06).
assert.equal(
  leadExcerpt({ content_excerpt: '40+ Models Chosen for Production...40+ Models Chosen for Production...40+ Models Chosen for Production... AI inference workloads are dynamic. There are thousands of regimes.' }),
  'AI inference workloads are dynamic.'
);
// Ordinary excerpts are unchanged.
assert.equal(
  leadExcerpt({ content_excerpt: 'Agents should keep working on long jobs in the background. They stay responsive.' }),
  'Agents should keep working on long jobs in the background.'
);
assert.equal(leadExcerpt({ content_excerpt: '' }), '');
// A legitimate trailing ellipsis inside the first sentence survives.
assert.equal(
  leadExcerpt({ content_excerpt: 'The model scores 12% on long tasks, and costs vary by provider. More follows.' }),
  'The model scores 12% on long tasks, and costs vary by provider.'
);

console.log('feed lead excerpt OK');
