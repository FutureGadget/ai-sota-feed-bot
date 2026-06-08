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
export default function handler(req, res) {
  try {
    if (req.query?.list) {
      const index = readJsonSafe(path.join(DAILY_DIR, 'index.json'), []);
      return res.status(200).json({ days: Array.isArray(index) ? index : [] });
    }

    const date = String(req.query?.date || '').trim();
    if (date) {
      if (!DATE_ID_RE.test(date)) {
        return res.status(400).json({ error: 'invalid_date', detail: 'expected format YYYY-MM-DD' });
      }
      const recap = readJsonSafe(path.join(DAILY_DIR, `${date}.json`), null);
      if (!recap) return res.status(404).json({ error: 'date_not_found', date });
      return res.status(200).json(recap);
    }

    const latest = readJsonSafe(path.join(DAILY_DIR, 'latest.json'), null);
    if (!latest) return res.status(404).json({ error: 'no_recaps_yet' });
    return res.status(200).json(latest);
  } catch (e) {
    return res.status(500).json({ error: 'daily_read_failed', detail: String(e) });
  }
}
