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
export default function handler(req, res) {
  try {
    const index = readJsonSafe(path.join(WIKI_DIR, 'index.json'), null);
    if (!index) return res.status(200).json({ areas: [], nodes: {} });

    const slug = String(req.query?.slug || '').trim();
    if (slug) {
      if (!SLUG_RE.test(slug)) return res.status(400).json({ error: 'invalid_slug' });
      const node = (index.nodes || {})[slug];
      if (!node) return res.status(404).json({ error: 'topic_not_found', slug });
      return res.status(200).json(node);
    }
    return res.status(200).json(index);
  } catch (e) {
    return res.status(500).json({ error: 'topics_read_failed', detail: String(e) });
  }
}
