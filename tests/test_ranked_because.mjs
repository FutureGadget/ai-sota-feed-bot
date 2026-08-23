import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

// rankedBecauseText exists twice - here in the feed shell and as _ranked_because
// in pipeline/render_static_pages.py for the crawler seed. Both are pinned to
// the same fixture so the two implementations cannot drift apart silently.
const source = fs.readFileSync(new URL('../web/index.html', import.meta.url), 'utf8');
const samples = JSON.parse(
  fs.readFileSync(new URL('./fixtures/ranked_because_samples.json', import.meta.url), 'utf8'),
);

function extractBlock(header) {
  const start = source.indexOf(header);
  assert.notEqual(start, -1, `missing ${header}`);
  const brace = source.indexOf('{', start);
  let depth = 0;
  for (let i = brace; i < source.length; i += 1) {
    if (source[i] === '{') depth += 1;
    if (source[i] === '}') depth -= 1;
    if (depth === 0) return source.slice(start, i + 1);
  }
  throw new Error(`unterminated ${header}`);
}

const context = vm.createContext({});
vm.runInContext(extractBlock('function cleanText('), context);
vm.runInContext(
  source.match(/const LEGACY_PLACEHOLDER_WHY = '[^']*';/)[0],
  context,
);
vm.runInContext(extractBlock('const SLOT_LABELS'), context);
vm.runInContext(extractBlock('function rankedBecauseText('), context);

test('ranking rationale matches the shared fixture', () => {
  for (const { item, expected } of samples) {
    assert.equal(context.rankedBecauseText(item), expected, JSON.stringify(item));
  }
});

test('missing items yield no rationale', () => {
  assert.equal(context.rankedBecauseText(null), '');
  assert.equal(context.rankedBecauseText(undefined), '');
});

test('non-finite scores and decay are skipped', () => {
  assert.equal(
    context.rankedBecauseText({ final_score: Number.NaN, time_decay_factor: Infinity }),
    '',
  );
});
