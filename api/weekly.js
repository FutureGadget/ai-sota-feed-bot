import { readDataJson } from '../lib/data-source.js';

const WEEK_ID_RE = /^\d{4}-W\d{2}$/;

// GET /api/weekly            -> latest recap
// GET /api/weekly?week=2026-W23 -> a specific recap
// GET /api/weekly?list=1     -> index of available available recaps
export function GET(request) {
  try {
    const url = new URL(request.url);
    if (url.searchParams.get('list')) {
      const index = readDataJson('weekly/index.json', []);
      return Response.json({ weeks: Array.isArray(index) ? index : [] });
    }

    const week = String(url.searchParams.get('week') || '').trim();
    if (week) {
      if (!WEEK_ID_RE.test(week)) {
        return Response.json({ error: 'invalid_week', detail: 'expected format YYYY-Www' }, { status: 400 });
      }
      const recap = readDataJson(`weekly/${week}.json`, null);
      if (!recap) return Response.json({ error: 'week_not_found', week }, { status: 404 });
      return Response.json(recap);
    }

    const latest = readDataJson('weekly/latest.json', null);
    if (!latest) return Response.json({ error: 'no_recaps_yet' }, { status: 404 });
    return Response.json(latest);
  } catch (e) {
    return Response.json({ error: 'weekly_read_failed', detail: String(e) }, { status: 500 });
  }
}
