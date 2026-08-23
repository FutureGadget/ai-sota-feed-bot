import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

// Release-row gating exists twice - here in the feed shell and in
// pipeline/render_static_pages.py for the crawler seed. These pins keep the
// JS side from drifting; the Python mirror is pinned in test_seed_sanitation.py.
const source = fs.readFileSync(new URL('../web/index.html', import.meta.url), 'utf8');

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
for (const name of ['normalizeEcho', 'stripVersionTokens', 'echoesTitle', 'cleanReleaseSummary', 'isGenericReleaseNotes']) {
  vm.runInContext(extractFunction(name), context);
}

test('a bare version bump is an echo of the title', () => {
  assert.equal(context.echoesTitle('codex 0.150.0-alpha.7', 'Release 0.150.0-alpha.7'), true);
});

test('an informative release note is kept', () => {
  assert.equal(
    context.echoesTitle('codex 0.150.0-alpha.7', 'Release 0.150.0-alpha.7 fixes sandbox escaping on macOS'),
    false,
  );
});

test('a summary that reduces to version tokens counts as an echo', () => {
  assert.equal(context.echoesTitle('codex 0.150.0-alpha.7', 'v0.150.0'), true);
});

test('punctuation and casing cannot hide the echo', () => {
  assert.equal(context.echoesTitle('codex 0.150.0-alpha.7', 'Codex 0.150.0-alpha.7!'), true);
});

test('commit-log debris is cut and short remainders dropped', () => {
  assert.equal(
    context.cleanReleaseSummary('Ship sandbox escape fix for macOS Sonoma (cherry picked from commit abc123)'),
    'Ship sandbox escape fix for macOS Sonoma',
  );
  assert.equal(context.cleanReleaseSummary('Fix sandbox bug Signed-off-by: Reviewers'), '');
});

test('short non-release summaries are preserved verbatim', () => {
  assert.equal(context.cleanReleaseSummary('Yes, we\u2019re confused too.', 'news'), 'Yes, we\u2019re confused too.');
});

test('generic release-note phrases are detected', () => {
  for (const sample of ['Bug fixes', 'Reliability improvements and perf work', 'Maintenance release', 'minor fixes', 'No release notes']) {
    assert.equal(context.isGenericReleaseNotes(sample), true, sample);
  }
});

test('specific release notes are not generic', () => {
  assert.equal(context.isGenericReleaseNotes('Fixed a sandbox escape on macOS'), false);
});
