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

const WEEKLY_DIR = path.join(process.cwd(), 'data', 'weekly');
const WEEK_ID_RE = /^\d{4}-W\d{2}$/;

// GET /api/weekly            -> latest recap
// GET /api/weekly?week=2026-W23 -> a specific recap
// GET /api/weekly?list=1     -> index of available available recaps
export default function handler(request) {
  try {
    const url = new URL(request.url);
    if (url.searchParams.get('list')) {
      const index = readJsonSafe(path.join(WEEKLY_DIR, 'index.json'), []);
      return Response.json({ weeks: Array.isArray(index) ? index : [] });
    }

    const week = String(url.searchParams.get('week') || '').trim();
    if (week) {
      if (!WEEK_ID_RE.test(week)) {
        return Response.json({ error: 'invalid_week', detail: 'expected format YYYY-Www' }, { status: 400 });
      }
      const recap = readJsonSafe(path.join(WEEKLY_DIR, `${week}.json`), null);
      if (!recap) return Response.json({ error: 'week_not_found', week }, { status: 404 });
      return Response.json(recap);
    }

    const latest = readJsonSafe(path.join(WEEKLY_DIR, 'latest.json'), null);
    if (!latest) return Response.json({ error: 'no_recaps_yet' }, { status: 404 });
    return Response.json(latest);
  } catch (e) {
    return Response.json({ error: 'weekly_read_failed', detail: String(e) }, { status: 500 });
  }
}
