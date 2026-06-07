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
// GET /api/weekly?list=1     -> index of available recaps
export default function handler(req, res) {
  try {
    if (req.query?.list) {
      const index = readJsonSafe(path.join(WEEKLY_DIR, 'index.json'), []);
      return res.status(200).json({ weeks: Array.isArray(index) ? index : [] });
    }

    const week = String(req.query?.week || '').trim();
    if (week) {
      if (!WEEK_ID_RE.test(week)) {
        return res.status(400).json({ error: 'invalid_week', detail: 'expected format YYYY-Www' });
      }
      const recap = readJsonSafe(path.join(WEEKLY_DIR, `${week}.json`), null);
      if (!recap) return res.status(404).json({ error: 'week_not_found', week });
      return res.status(200).json(recap);
    }

    const latest = readJsonSafe(path.join(WEEKLY_DIR, 'latest.json'), null);
    if (!latest) return res.status(404).json({ error: 'no_recaps_yet' });
    return res.status(200).json(latest);
  } catch (e) {
    return res.status(500).json({ error: 'weekly_read_failed', detail: String(e) });
  }
}
