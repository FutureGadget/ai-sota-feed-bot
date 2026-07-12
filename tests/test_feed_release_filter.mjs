import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import { GET } from '../api/feed.js';


test('legacy release markers move stored news/platform items from Brief to Releases', async () => {
  const oldCwd = process.cwd();
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'feed-release-filter-'));
  try {
    fs.mkdirSync(path.join(tmp, 'data', 'processed'), { recursive: true });
    fs.writeFileSync(
      path.join(tmp, 'data', 'processed', 'latest.json'),
      JSON.stringify([
        { id: 'analysis', title: 'Agent evaluation patterns', type: 'news', llm_category: 'platform' },
        {
          id: 'analysis-with-mention',
          title: 'Model family analysis',
          type: 'news',
          llm_category: 'platform',
          summary_1line: 'Analysis of pricing and the upcoming release schedule.',
        },
        {
          id: 'release',
          title: 'sqlite-utils 4.1',
          type: 'news',
          llm_category: 'platform',
          summary_1line: 'Release: sqlite-utils 4.1 Minor new features.',
        },
      ]),
    );
    fs.writeFileSync(path.join(tmp, 'data', 'processed', 'runs_index.json'), JSON.stringify([]));
    process.chdir(tmp);

    const briefResponse = await GET(new Request('https://example.com/api/feed?label=brief'));
    const releaseResponse = await GET(new Request('https://example.com/api/feed?label=release'));
    const brief = await briefResponse.json();
    const releases = await releaseResponse.json();

    assert.deepEqual(brief.items.map((item) => item.id), ['analysis', 'analysis-with-mention']);
    assert.deepEqual(releases.items.map((item) => item.id), ['release']);
  } finally {
    process.chdir(oldCwd);
    fs.rmSync(tmp, { recursive: true, force: true });
  }
});
