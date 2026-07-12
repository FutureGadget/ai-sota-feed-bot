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
export function GET(request) {
  try {
    const index = readJsonSafe(path.join(FOUNDATIONS_DIR, 'index.json'), null);
    if (!index) return Response.json({ clusters: [], concepts: {} });

    const url = new URL(request.url);
    const slug = String(url.searchParams.get('slug') || '').trim();
    if (slug) {
      if (!SLUG_RE.test(slug)) return Response.json({ error: 'invalid_slug' }, { status: 400 });
      const concept = (index.concepts || {})[slug];
      if (!concept) return Response.json({ error: 'concept_not_found', slug }, { status: 404 });
      return Response.json(concept);
    }
    return Response.json(index);
  } catch (e) {
    return Response.json({ error: 'foundations_read_failed', detail: String(e) }, { status: 500 });
  }
}
