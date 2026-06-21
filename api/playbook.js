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
export default function handler(req, res) {
  try {
    if (req.query?.sources) {
      const sources = readJsonSafe(path.join(PLAYBOOK_DIR, 'source-index.json'), {});
      return res.status(200).json(
        sources && typeof sources === 'object' && !Array.isArray(sources) ? sources : {}
      );
    }
    if (req.query?.list) {
      const index = readJsonSafe(path.join(PLAYBOOK_DIR, 'index.json'), []);
      return res.status(200).json({ editions: Array.isArray(index) ? index : [] });
    }

    const date = String(req.query?.date || '').trim();
    if (date) {
      if (!DATE_ID_RE.test(date)) {
        return res.status(400).json({ error: 'invalid_date', detail: 'expected format YYYY-MM-DD' });
      }
      const edition = readJsonSafe(path.join(PLAYBOOK_DIR, `${date}.json`), null);
      if (!edition) return res.status(404).json({ error: 'date_not_found', date });
      return res.status(200).json(edition);
    }

    const latest = readJsonSafe(path.join(PLAYBOOK_DIR, 'latest.json'), null);
    if (!latest) return res.status(404).json({ error: 'no_editions_yet' });
    return res.status(200).json(latest);
  } catch (e) {
    return res.status(500).json({ error: 'playbook_read_failed', detail: String(e) });
  }
}
