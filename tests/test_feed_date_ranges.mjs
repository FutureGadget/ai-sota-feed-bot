import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

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

const context = vm.createContext({ Date });
vm.runInContext(
  `${extractFunction('localDateBoundaryUtc')}\n${extractFunction('toDateInput')}`,
  context,
);

test('local calendar boundaries are sent as explicit UTC instants', () => {
  const start = context.localDateBoundaryUtc('2026-06-21');
  const end = context.localDateBoundaryUtc('2026-06-21', true);
  assert.match(start, /Z$/);
  assert.match(end, /Z$/);
  assert.equal(new Date(end).getTime() - new Date(start).getTime() + 1, 24 * 60 * 60 * 1000);
});

test('calendar boundaries respect the reader timezone and DST', () => {
  const fn = extractFunction('localDateBoundaryUtc');
  const script = `${fn}
    console.log(JSON.stringify({
      start: localDateBoundaryUtc('2026-03-08'),
      end: localDateBoundaryUtc('2026-03-08', true),
    }));`;
  const output = execFileSync(process.execPath, ['-e', script], {
    encoding: 'utf8',
    env: { ...process.env, TZ: 'America/Los_Angeles' },
  });
  const range = JSON.parse(output);
  assert.equal(range.start, '2026-03-08T08:00:00.000Z');
  assert.equal(range.end, '2026-03-09T06:59:59.999Z');
  assert.equal(new Date(range.end).getTime() - new Date(range.start).getTime() + 1, 23 * 60 * 60 * 1000);
});

test('Today sends exactly the current local calendar date', () => {
  const script = `
    const NativeDate = Date;
    class FixedDate extends NativeDate {
      constructor(...args) {
        super(...(args.length ? args : ['2026-06-21T03:30:00.000Z']));
      }
      static now() { return new NativeDate('2026-06-21T03:30:00.000Z').getTime(); }
    }
    globalThis.Date = FixedDate;
    ${extractFunction('localDateBoundaryUtc')}
    ${extractFunction('toDateInput')}
    ${extractFunction('buildFeedUrl')}
    const customRangeState = { from: '', to: '' };
    const presetDaysState = '1';
    const limitState = '200';
    const window = { location: { origin: 'https://example.test' } };
    function getSelectedLabels() { return ['brief']; }
    console.log(buildFeedUrl());
  `;
  const output = execFileSync(process.execPath, ['-e', script], {
    encoding: 'utf8',
    env: { ...process.env, TZ: 'America/Los_Angeles' },
  }).trim();
  const url = new URL(output, 'https://example.test');
  assert.equal(url.searchParams.get('from'), '2026-06-20T07:00:00.000Z');
  assert.equal(url.searchParams.get('to'), '2026-06-21T06:59:59.999Z');
});
