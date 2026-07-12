import fs from 'node:fs';
import path from 'node:path';

function readJsonSafe(p, fallback) {
  try {
    if (!fs.existsSync(p)) return fallback;
    return JSON.parse(fs.readFileSync(p, 'utf-8'));
  } catch {
    return fallback;
  }
}

const WIKI_DIR = path.join(process.cwd(), 'data', 'wiki');
const SLUG_RE = /^[a-z0-9][a-z0-9-]{0,80}$/;

// GET /api/topics                    -> the agent-engineering wiki graph (areas + nodes)
// GET /api/topics?slug=agent-memory  -> one obstacle/solution node
// The wiki is compiled by pipeline/build_wiki.py from the markdown pages; this
// just serves the committed index.json.
export function GET(request) {
  try {
    const index = readJsonSafe(path.join(WIKI_DIR, 'index.json'), null);
    if (!index) return Response.json({ areas: [], nodes: {} });

    const url = new URL(request.url);
    const slug = String(url.searchParams.get('slug') || '').trim();
    if (slug) {
      if (!SLUG_RE.test(slug)) return Response.json({ error: 'invalid_slug' }, { status: 400 });
      const node = (index.nodes || {})[slug];
      if (!node) return Response.json({ error: 'topic_not_found', slug }, { status: 404 });
      return Response.json(node);
    }
    return Response.json(index);
  } catch (e) {
    return Response.json({ error: 'topics_read_failed', detail: String(e) }, { status: 500 });
  }
}
