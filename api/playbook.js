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

const PLAYBOOK_DIR = path.join(process.cwd(), 'data', 'playbook');
const DATE_ID_RE = /^\d{4}-\d{2}-\d{2}$/;

// GET /api/playbook                 -> latest edition
// GET /api/playbook?date=2026-06-21 -> a specific edition
// GET /api/playbook?list=1          -> index of available editions
// GET /api/playbook?sources=1       -> source-sid lookup for recap overlays
// GET /api/playbook?locale=ko       -> query localized content
export function GET(request) {
  try {
    const url = new URL(request.url);
    const locale = String(url.searchParams.get('locale') || '').trim();
    const playbookDir = locale === 'ko'
      ? path.join(process.cwd(), 'data', 'i18n', 'ko', 'playbook')
      : PLAYBOOK_DIR;

    function readJsonWithFallback(filename, fallbackVal) {
      const primaryPath = path.join(playbookDir, filename);
      if (fs.existsSync(primaryPath)) {
        return readJsonSafe(primaryPath, fallbackVal);
      }
      return readJsonSafe(path.join(PLAYBOOK_DIR, filename), fallbackVal);
    }

    if (url.searchParams.get('sources')) {
      const sources = readJsonWithFallback('source-index.json', {});
      return Response.json(
        sources && typeof sources === 'object' && !Array.isArray(sources) ? sources : {}
      );
    }
    if (url.searchParams.get('list')) {
      const index = readJsonWithFallback('index.json', []);
      return Response.json({ editions: Array.isArray(index) ? index : [] });
    }

    const date = String(url.searchParams.get('date') || '').trim();
    if (date) {
      if (!DATE_ID_RE.test(date)) {
        return Response.json({ error: 'invalid_date', detail: 'expected format YYYY-MM-DD' }, { status: 400 });
      }
      const edition = readJsonWithFallback(`${date}.json`, null);
      if (!edition) return Response.json({ error: 'date_not_found', date }, { status: 404 });
      return Response.json(edition);
    }

    const latest = readJsonWithFallback('latest.json', null);
    if (!latest) return Response.json({ error: 'no_editions_yet' }, { status: 404 });
    return Response.json(latest);
  } catch (e) {
    return Response.json({ error: 'playbook_read_failed', detail: String(e) }, { status: 500 });
  }
}
