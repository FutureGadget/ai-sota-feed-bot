import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import { GET, readValidatedLabRecord } from '../api/playbook.js';


test('serves the deterministic source-card lookup', async () => {
  const response = await GET(new Request('https://example.com/api/playbook?sources=1'));
  const body = await response.json();
  const expected = JSON.parse(fs.readFileSync('data/playbook/source-index.json', 'utf8'));
  assert.equal(response.status, 200);
  assert.deepEqual(body, expected);
});

test('serves the latest validated Skill Lab record', async () => {
  const response = await GET(new Request('https://example.com/api/playbook?lab=latest'));
  const body = await response.json();
  const expected = JSON.parse(fs.readFileSync('data/playbook/lab/latest.json', 'utf8'));
  assert.equal(response.status, 200);
  assert.deepEqual(body, expected);
  assert.equal(body.state, 'protocol');
});

test('serves the bounded Skill Lab index', async () => {
  const response = await GET(new Request('https://example.com/api/playbook?lab=list'));
  const body = await response.json();
  const expected = JSON.parse(fs.readFileSync('data/playbook/lab/index.json', 'utf8'));
  assert.equal(response.status, 200);
  assert.deepEqual(body, { labs: expected });
  assert.ok(body.labs.length <= 4);
  assert.match(body.labs[0].content_sha256, /^[a-f0-9]{64}$/);
});

test('serves a Skill Lab record by validated slug', async () => {
  const response = await GET(new Request('https://example.com/api/playbook?lab=protocol'));
  const body = await response.json();
  assert.equal(response.status, 200);
  assert.equal(body.slug, 'protocol');
  assert.equal(body.id, 'lab-protocol');
});

test('rejects unsafe Skill Lab selectors without reading a path', async () => {
  const response = await GET(new Request('https://example.com/api/playbook?lab=..%2Fstate'));
  const body = await response.json();
  assert.equal(response.status, 400);
  assert.deepEqual(body, { error: 'invalid_lab', detail: 'expected latest, list, or a URL-safe slug' });
});

test('returns a bounded error for a missing Skill Lab slug', async () => {
  const response = await GET(new Request('https://example.com/api/playbook?lab=not-published'));
  const body = await response.json();
  assert.equal(response.status, 404);
  assert.deepEqual(body, { error: 'lab_not_found', slug: 'not-published' });
});

test('refuses a Skill Lab source changed after its index was built', () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'skill-lab-api-'));
  try {
    const summary = JSON.parse(fs.readFileSync('data/playbook/lab/index.json', 'utf8'))[0];
    const source = fs.readFileSync('data/playbook/lab/protocol.json');
    fs.writeFileSync(path.join(directory, 'protocol.json'), source);
    assert.equal(readValidatedLabRecord(directory, summary)?.id, 'lab-protocol');

    const changed = JSON.parse(source.toString('utf8'));
    changed.summary = 'Changed after validation.';
    fs.writeFileSync(path.join(directory, 'protocol.json'), JSON.stringify(changed));
    assert.equal(readValidatedLabRecord(directory, summary), null);
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
});
