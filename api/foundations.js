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

const FOUNDATIONS_DIR = path.join(process.cwd(), 'data', 'foundations');
const SLUG_RE = /^[a-z0-9][a-z0-9-]{0,80}$/;

// GET /api/foundations                          -> foundations index
// GET /api/foundations?slug=prompt-reliability  -> one concept page
export default function handler(req, res) {
  try {
    const index = readJsonSafe(path.join(FOUNDATIONS_DIR, 'index.json'), null);
    if (!index) return res.status(200).json({ clusters: [], concepts: {} });

    const slug = String(req.query?.slug || '').trim();
    if (slug) {
      if (!SLUG_RE.test(slug)) return res.status(400).json({ error: 'invalid_slug' });
      const concept = (index.concepts || {})[slug];
      if (!concept) return res.status(404).json({ error: 'concept_not_found', slug });
      return res.status(200).json(concept);
    }
    return res.status(200).json(index);
  } catch (e) {
    return res.status(500).json({ error: 'foundations_read_failed', detail: String(e) });
  }
}
