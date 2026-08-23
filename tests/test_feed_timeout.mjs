import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = fs.readFileSync(new URL('../web/index.html', import.meta.url), 'utf8');

function extractFunction(name) {
  const asyncStart = source.indexOf(`async function ${name}(`);
  const start = asyncStart === -1 ? source.indexOf(`function ${name}(`) : asyncStart;
  assert.notEqual(start, -1, `missing ${name}`);
  const brace = source.indexOf(') {', start) + 2;
  let depth = 0;
  for (let i = brace; i < source.length; i += 1) {
    if (source[i] === '{') depth += 1;
    if (source[i] === '}') depth -= 1;
    if (depth === 0) return source.slice(start, i + 1);
  }
  throw new Error(`unterminated ${name}`);
}

const context = vm.createContext({
  AbortController,
  DOMException,
  Error,
  ReadableStream,
  Response,
  TextEncoder,
  clearTimeout,
  setTimeout,
});
vm.runInContext(extractFunction('fetchJsonWithTimeout'), context);

test('feed JSON timeout covers a response body that stalls after headers', async () => {
  context.fetch = async (_url, { signal }) => {
    const body = new ReadableStream({
      start(controller) {
        controller.enqueue(new TextEncoder().encode('{"items":['));
        signal.addEventListener('abort', () => {
          controller.error(new DOMException('aborted', 'AbortError'));
        }, { once: true });
      },
    });
    return new Response(body, {
      status: 200,
      headers: { 'content-type': 'application/json' },
    });
  };

  await assert.rejects(
    context.fetchJsonWithTimeout('/api/feed', {}, 20),
    /timeout_20_\/api\/feed/,
  );
});

test('feed JSON timeout returns parsed data on success', async () => {
  context.fetch = async () => new Response('{"items":[]}', {
    status: 200,
    headers: { 'content-type': 'application/json' },
  });

  const { data, response } = await context.fetchJsonWithTimeout('/api/feed', {}, 100);
  assert.equal(response.status, 200);
  assert.deepEqual(data, { items: [] });
});
