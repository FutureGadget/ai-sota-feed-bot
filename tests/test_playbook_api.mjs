import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

import handler from '../api/playbook.js';


function response() {
  return {
    statusCode: 200,
    body: null,
    status(code) {
      this.statusCode = code;
      return this;
    },
    json(body) {
      this.body = body;
      return this;
    },
  };
}


test('serves the deterministic source-card lookup', async () => {
  const res = response();
  await handler({ query: { sources: '1' } }, res);
  const expected = JSON.parse(fs.readFileSync('data/playbook/source-index.json', 'utf8'));
  assert.equal(res.statusCode, 200);
  assert.deepEqual(res.body, expected);
});
