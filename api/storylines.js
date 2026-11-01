import { readDataJson } from '../lib/data-source.js';

const SLUG_RE = /^[a-z0-9][a-z0-9-]{0,80}$/;

// GET /api/storylines                      -> index of active storylines
// GET /api/storylines?slug=claude-fable    -> one storyline's day-by-day timeline
// Detail files outlive the index window (shared links keep working), so a
// slug can resolve even when it's no longer listed.
export function GET(request) {
  try {
    const url = new URL(request.url);
    const slug = String(url.searchParams.get('slug') || '').trim();
    if (slug) {
      if (!SLUG_RE.test(slug)) {
        return Response.json({ error: 'invalid_slug' }, { status: 400 });
      }
      const storyline = readDataJson(`storylines/${slug}.json`, null);
      if (!storyline) return Response.json({ error: 'storyline_not_found', slug }, { status: 404 });
      return Response.json(storyline);
    }

    const index = readDataJson('storylines/index.json', null);
    if (!index) return Response.json({ storylines: [] });
    return Response.json(index);
  } catch (e) {
    return Response.json({ error: 'storylines_read_failed', detail: String(e) }, { status: 500 });
  }
}
