import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import { GET } from '../api/models.js';

async function invoke(query = {}) {
  const url = new URL('https://example.com/api/models');
  for (const [key, value] of Object.entries(query)) {
    url.searchParams.set(key, String(value));
  }
  const response = await GET(new Request(url));
  return { statusCode: response.status, body: await response.json() };
}

function withFixture(fixture, fn) {
  return async () => {
    const oldCwd = process.cwd();
    const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'models-api-'));
    try {
      if (fixture) {
        fs.mkdirSync(path.join(tmp, 'data', 'models'), { recursive: true });
        fs.writeFileSync(
          path.join(tmp, 'data', 'models', 'latest.json'),
          JSON.stringify(fixture)
        );
      }
      process.chdir(tmp);
      await fn();
    } finally {
      process.chdir(oldCwd);
      fs.rmSync(tmp, { recursive: true, force: true });
    }
  };
}

const realData = JSON.parse(fs.readFileSync('data/models/latest.json', 'utf8'));

test('serves the full index straight from the real data file', async () => {
  const res = await invoke();
  assert.equal(res.statusCode, 200);
  assert.deepEqual(res.body.sources, realData.sources);
  assert.equal(res.body.models.length, realData.models.length);
  assert.equal(res.body.generated_at, realData.generated_at);
});

test('serves one model by slug', async () => {
  const target = realData.models[0];
  const res = await invoke({ slug: target.slug });
  assert.equal(res.statusCode, 200);
  assert.deepEqual(res.body, target);
});

test('rejects a slug that fails the strict format regex', async () => {
  const res = await invoke({ slug: '../secret' });
  assert.equal(res.statusCode, 400);
  assert.equal(res.body.error, 'invalid_slug');
});

test('returns 404 for a well-formed but unknown slug', async () => {
  const res = await invoke({ slug: 'no-such-model-xyz' });
  assert.equal(res.statusCode, 404);
  assert.equal(res.body.error, 'model_not_found');
  assert.equal(res.body.slug, 'no-such-model-xyz');
});

test('filters by organization case-insensitively', async () => {
  const res = await invoke({ org: 'ANTHROPIC' });
  assert.equal(res.statusCode, 200);
  assert.ok(res.body.models.length > 0);
  for (const m of res.body.models) {
    assert.equal(m.organization, 'anthropic');
  }
  const expectedCount = realData.models.filter((m) => m.organization === 'anthropic').length;
  assert.equal(res.body.models.length, expectedCount);
});

test('sources block survives a filter that empties the model list', async () => {
  const res = await invoke({ org: 'no-such-organization-at-all' });
  assert.equal(res.statusCode, 200);
  assert.deepEqual(res.body.models, []);
  assert.deepEqual(res.body.sources, realData.sources);
});

test(
  'open_weights filter excludes nulls from both true and false, never treating unknown as false',
  withFixture(
    {
      generated_at: '2026-08-05T00:00:00Z',
      sources: { lmarena: { available: true } },
      models: [
        { slug: 'open-a', name: 'Open A', organization: 'acme', open_weights: true },
        { slug: 'closed-a', name: 'Closed A', organization: 'acme', open_weights: false },
        { slug: 'unknown-a', name: 'Unknown A', organization: 'acme', open_weights: null },
      ],
    },
    async () => {
      const trueRes = await invoke({ open_weights: 'true' });
      assert.equal(trueRes.statusCode, 200);
      assert.deepEqual(trueRes.body.models.map((m) => m.slug), ['open-a']);

      const falseRes = await invoke({ open_weights: 'false' });
      assert.equal(falseRes.statusCode, 200);
      assert.deepEqual(falseRes.body.models.map((m) => m.slug), ['closed-a']);

      // The null-open_weights model must appear in neither filtered result.
      for (const res of [trueRes, falseRes]) {
        assert.ok(!res.body.models.some((m) => m.slug === 'unknown-a'));
      }
    }
  )
);

test(
  'sorting by price puts null prices last regardless of asc/desc direction',
  withFixture(
    {
      generated_at: '2026-08-05T00:00:00Z',
      sources: {},
      models: [
        { slug: 'mid', name: 'Mid', organization: 'acme', price_blended_per_1m: 10 },
        { slug: 'unknown-price', name: 'Unknown Price', organization: 'acme', price_blended_per_1m: null },
        { slug: 'cheap', name: 'Cheap', organization: 'acme', price_blended_per_1m: 5 },
      ],
    },
    async () => {
      const asc = await invoke({ sort: 'price_blended_per_1m', order: 'asc' });
      assert.equal(asc.statusCode, 200);
      assert.deepEqual(asc.body.models.map((m) => m.slug), ['cheap', 'mid', 'unknown-price']);

      const desc = await invoke({ sort: 'price_blended_per_1m', order: 'desc' });
      assert.equal(desc.statusCode, 200);
      // A null price is unknown, not free - it must never be sorted to the
      // front of a descending (most-expensive-first) sort either.
      assert.deepEqual(desc.body.models.map((m) => m.slug), ['mid', 'cheap', 'unknown-price']);
    }
  )
);

test(
  'sorting by arena_elo_coding defaults to descending with nulls last',
  withFixture(
    {
      generated_at: '2026-08-05T00:00:00Z',
      sources: {},
      models: [
        { slug: 'low', name: 'Low', organization: 'acme', arena_elo_coding: 1200 },
        { slug: 'no-elo', name: 'No Elo', organization: 'acme', arena_elo_coding: null },
        { slug: 'high', name: 'High', organization: 'acme', arena_elo_coding: 1500 },
      ],
    },
    async () => {
      const res = await invoke({ sort: 'arena_elo_coding' });
      assert.equal(res.statusCode, 200);
      assert.deepEqual(res.body.models.map((m) => m.slug), ['high', 'low', 'no-elo']);
    }
  )
);

test(
  'sorting by a raw AA benchmark key puts a missing benchmark last regardless of asc/desc direction',
  withFixture(
    {
      generated_at: '2026-08-05T00:00:00Z',
      sources: {},
      models: [
        { slug: 'mid', name: 'Mid', organization: 'acme', benchmarks: { livecodebench: 0.5 } },
        { slug: 'no-benchmark', name: 'No Benchmark', organization: 'acme', benchmarks: {} },
        { slug: 'high', name: 'High', organization: 'acme', benchmarks: { livecodebench: 0.9 } },
      ],
    },
    async () => {
      const desc = await invoke({ sort: 'livecodebench' });
      assert.equal(desc.statusCode, 200);
      // Same nulls-last contract as any top-level field: a model missing the
      // benchmark is unknown, never treated as the worst (0) real score.
      assert.deepEqual(desc.body.models.map((m) => m.slug), ['high', 'mid', 'no-benchmark']);

      const asc = await invoke({ sort: 'livecodebench', order: 'asc' });
      assert.equal(asc.statusCode, 200);
      assert.deepEqual(asc.body.models.map((m) => m.slug), ['mid', 'high', 'no-benchmark']);
    }
  )
);

test(
  'a sort key that matches neither a whitelisted field nor a real benchmark in the data is ignored, not an error',
  withFixture(
    {
      generated_at: '2026-08-05T00:00:00Z',
      sources: {},
      models: [
        { slug: 'b', name: 'B', organization: 'acme', benchmarks: { livecodebench: 0.5 } },
        { slug: 'a', name: 'A', organization: 'acme', benchmarks: { livecodebench: 0.9 } },
      ],
    },
    async () => {
      const res = await invoke({ sort: 'not_a_real_benchmark_or_field' });
      assert.equal(res.statusCode, 200);
      // Unsorted: original fixture order preserved, not a 400/500.
      assert.deepEqual(res.body.models.map((m) => m.slug), ['b', 'a']);
    }
  )
);

test('limit clamps to the documented maximum and ignores invalid values', async () => {
  const clamped = await invoke({ limit: '999999' });
  assert.equal(clamped.statusCode, 200);
  // The real fixture (200 models) is smaller than MAX_LIMIT, so an absurd
  // limit degrades to "all of them" rather than erroring.
  assert.equal(clamped.body.models.length, realData.models.length);

  const small = await invoke({ limit: '3' });
  assert.equal(small.statusCode, 200);
  assert.equal(small.body.models.length, 3);

  const nonNumeric = await invoke({ limit: 'not-a-number' });
  assert.equal(nonNumeric.statusCode, 200);
  assert.equal(nonNumeric.body.models.length, realData.models.length);

  const negative = await invoke({ limit: '-5' });
  assert.equal(negative.statusCode, 200);
  assert.equal(negative.body.models.length, realData.models.length);
});

test(
  'degrades to an empty-but-valid payload when the data file is missing, never a 500',
  withFixture(null, async () => {
    const res = await invoke();
    assert.equal(res.statusCode, 200);
    assert.deepEqual(res.body, { generated_at: null, sources: {}, models: [] });
  })
);

test('resolves a model by its public url_slug', async () => {
  // /models/<url_slug> is the identifier every link on the site uses; looking
  // up only the internal normalized `slug` 404'd on it.
  const res = await invoke({ slug: 'claude-opus-5' });
  assert.equal(res.statusCode, 200);
  assert.equal(res.body.url_slug, 'claude-opus-5');
});

test('still resolves a model by its internal slug', async () => {
  const all = await invoke();
  const withSlug = all.body.models.find((m) => m.slug);
  const res = await invoke({ slug: withSlug.slug });
  assert.equal(res.statusCode, 200);
  assert.equal(res.body.slug, withSlug.slug);
});

test('url_slug lookup returns the row richest in identity fields', async () => {
  const res = await invoke({ slug: 'claude-opus-5' });
  assert.equal(res.statusCode, 200);
  // The AA-only variant rows carry no license; the merged row does.
  assert.ok(res.body.license !== null && res.body.license !== undefined);
});
