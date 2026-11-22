// The home page's own UI runtime, for tests that run page functions in a sandbox.
//
// The page embeds its dictionary as `window.UI` and reads every string through
// `t()`. A sandboxed function needs the same, so this lifts the real `t`,
// `tHtml`, `localHref` and `localeParam` plus the embedded `window.UI` out of
// the generated page instead of stubbing them.
import assert from 'node:assert/strict';

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

export function uiRuntime(source) {
  const data = source.match(/window\.UI = (\{[\s\S]*?\n    \});/);
  assert.ok(data, 'the page embeds window.UI');
  const functions = ['t', 'tHtml', 'localHref', 'localeParam'].map((name) => extractFunction(source, name));
  return `globalThis.window = globalThis;\nwindow.UI = ${data[1]};\n${functions.join('\n')}\n`;
}
