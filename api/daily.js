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

const DAILY_DIR = path.join(process.cwd(), 'data', 'daily');
const DATE_ID_RE = /^\d{4}-\d{2}-\d{2}$/;

// GET /api/daily               -> latest recap
// GET /api/daily?date=2026-06-07 -> a specific recap
// GET /api/daily?list=1        -> index of available recaps
export function GET(request) {
  try {
    const url = new URL(request.url);
    if (url.searchParams.get('list')) {
      const index = readJsonSafe(path.join(DAILY_DIR, 'index.json'), []);
      return Response.json({ days: Array.isArray(index) ? index : [] });
    }

    const date = String(url.searchParams.get('date') || '').trim();
    if (date) {
      if (!DATE_ID_RE.test(date)) {
        return Response.json({ error: 'invalid_date', detail: 'expected format YYYY-MM-DD' }, { status: 400 });
      }
      const recap = readJsonSafe(path.join(DAILY_DIR, `${date}.json`), null);
      if (!recap) return Response.json({ error: 'date_not_found', date }, { status: 404 });
      return Response.json(recap);
    }

    const latest = readJsonSafe(path.join(DAILY_DIR, 'latest.json'), null);
    if (!latest) return Response.json({ error: 'no_recaps_yet' }, { status: 404 });
    return Response.json(latest);
  } catch (e) {
    return Response.json({ error: 'daily_read_failed', detail: String(e) }, { status: 500 });
  }
}
