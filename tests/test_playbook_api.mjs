import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

import { GET } from '../api/playbook.js';


test('serves the deterministic source-card lookup', async () => {
  const response = await GET(new Request('https://example.com/api/playbook?sources=1'));
  const body = await response.json();
  const expected = JSON.parse(fs.readFileSync('data/playbook/source-index.json', 'utf8'));
  assert.equal(response.status, 200);
  assert.deepEqual(body, expected);
});
