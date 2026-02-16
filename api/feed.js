import fs from 'node:fs';
import path from 'node:path';

function readLatest() {
  const p = path.join(process.cwd(), 'data', 'processed', 'latest.json');
  if (!fs.existsSync(p)) return [];
  return JSON.parse(fs.readFileSync(p, 'utf-8'));
}

export default function handler(req, res) {
  try {
    const items = readLatest();
    const date = new Date().toISOString().slice(0, 10);
    res.status(200).json({ date, items });
  } catch (e) {
    res.status(500).json({ error: 'feed_read_failed', detail: String(e) });
  }
}
