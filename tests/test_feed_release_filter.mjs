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

test('substantive releases stay in Brief and also appear in Releases', async () => {
  const oldCwd = process.cwd();
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'feed-release-tier-'));
  try {
    fs.mkdirSync(path.join(tmp, 'data', 'processed'), { recursive: true });
    fs.writeFileSync(
      path.join(tmp, 'data', 'processed', 'latest.json'),
      JSON.stringify([
        {
          id: 'analysis',
          title: 'Agent evaluation patterns',
          type: 'news',
          llm_category: 'platform',
          source: 'simon_willison',
        },
        {
          id: 'major',
          title: 'vllm v0.32.0',
          type: 'release',
          llm_category: 'release',
          release_tier: 'major',
          source: 'vllm_releases',
          summary_1line: 'Added a new endpoint for structured decisions.',
        },
        {
          id: 'minor',
          title: 'codex 0.165.0-alpha.1',
          type: 'release',
          llm_category: 'release',
          release_tier: 'minor',
          source: 'openai_codex_releases',
          summary_1line: 'Release 0.165.0-alpha.1',
        },
        {
          id: 'legacy',
          title: 'langgraph==1.2.17',
          type: 'release',
          llm_category: 'release',
          source: 'langgraph_releases',
          summary_1line: 'release(langgraph): 1.2.17',
        },
      ]),
    );
    fs.writeFileSync(path.join(tmp, 'data', 'processed', 'runs_index.json'), JSON.stringify([]));
    process.chdir(tmp);

    const brief = await (
      await GET(new Request('https://example.com/api/feed?label=brief'))
    ).json();
    const releases = await (
      await GET(new Request('https://example.com/api/feed?label=release'))
    ).json();

    assert.deepEqual(brief.items.map((item) => item.id), ['analysis', 'major']);
    assert.deepEqual(releases.items.map((item) => item.id), ['major', 'minor', 'legacy']);
    assert.equal(brief.label_counts.brief, 2);
    assert.equal(brief.label_counts.release, 3);
  } finally {
    process.chdir(oldCwd);
    fs.rmSync(tmp, { recursive: true, force: true });
  }
});
