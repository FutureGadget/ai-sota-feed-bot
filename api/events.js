import crypto from 'node:crypto';
import { ensureEventSchema, getTursoClient } from '../lib/turso.js';

const ALLOWED_TYPES = new Set(['impression', 'click', 'open', 'dismiss', 'save']);

function toIsoNow() {
  return new Date().toISOString();
}

function normalizeTs(v) {
  if (!v) return toIsoNow();
  const d = new Date(v);
  return Number.isNaN(d.getTime()) ? toIsoNow() : d.toISOString();
}

function asText(v, max = 500) {
  if (v === undefined || v === null) return null;
  const s = String(v).trim();
  if (!s) return null;
  return s.length > max ? s.slice(0, max) : s;
}

function asInt(v) {
  if (v === undefined || v === null || v === '') return null;
  const n = Number.parseInt(String(v), 10);
  return Number.isFinite(n) ? n : null;
}

function deriveEventId(e) {
  // Dedup impressions aggressively within the same run (or same day fallback)
  // to avoid repeated UI re-render floods.
  if (e.event_type === 'impression') {
    const scope = e.run_id || String(e.ts || '').slice(0, 10);
    const base = [
      e.anon_user_id || '',
      e.event_type || '',
      e.item_id || '',
      e.url || '',
      scope,
    ].join('::');
    return crypto.createHash('sha256').update(base).digest('hex').slice(0, 24);
  }

  // Keep click/open-like events time-sensitive so repeated explicit actions are preserved.
  const base = [
    e.anon_user_id || '',
    e.session_id || '',
    e.event_type || '',
    e.item_id || '',
    e.url || '',
    e.ts || '',
  ].join('::');
  return crypto.createHash('sha256').update(base).digest('hex').slice(0, 24);
}

function normalizeEvent(raw, req) {
  const anon_user_id = asText(raw?.anon_user_id, 120);
  const event_type = asText(raw?.event_type, 40)?.toLowerCase();
  if (!anon_user_id) return { ok: false, error: 'missing_anon_user_id' };
  if (!event_type || !ALLOWED_TYPES.has(event_type)) return { ok: false, error: 'invalid_event_type' };

  const ts = normalizeTs(raw?.ts);
  const meta = raw?.meta && typeof raw.meta === 'object' ? raw.meta : null;

  const out = {
    event_id: asText(raw?.event_id, 120),
    anon_user_id,
    session_id: asText(raw?.session_id, 120),
    event_type,
    item_id: asText(raw?.item_id, 120),
    title: asText(raw?.title, 300),
    url: asText(raw?.url, 1000),
    source: asText(raw?.source, 120),
    slot: asText(raw?.slot, 120),
    rank_position: asInt(raw?.rank_position),
    run_id: asText(raw?.run_id, 120),
    ts,
    user_agent: asText(req.headers['user-agent'], 300),
    referer: asText(req.headers.referer || req.headers.referrer, 500),
    meta_json: meta ? JSON.stringify(meta) : null,
  };

  if (!out.event_id) out.event_id = deriveEventId(out);
  return { ok: true, event: out };
}

function parseBody(req) {
  if (!req.body) return { events: [] };
  if (typeof req.body === 'string') {
    try {
      return JSON.parse(req.body);
    } catch {
      return { events: [] };
    }
  }
  return req.body;
}

export default async function handler(req, res) {
  if (req.method === 'OPTIONS') {
    res.setHeader('Allow', 'POST,OPTIONS');
    return res.status(204).end();
  }

  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST,OPTIONS');
    return res.status(405).json({ error: 'method_not_allowed' });
  }

  try {
    const body = parseBody(req) || {};
    const batch = Array.isArray(body.events) ? body.events : [body];
    if (!batch.length) return res.status(400).json({ error: 'empty_events' });

    await ensureEventSchema();
    const db = getTursoClient();

    const valid = [];
    const rejected = [];

    for (const raw of batch.slice(0, 200)) {
      const r = normalizeEvent(raw, req);
      if (r.ok) valid.push(r.event);
      else rejected.push({ error: r.error, raw });
    }

    if (!valid.length) {
      return res.status(400).json({ error: 'no_valid_events', rejected_count: rejected.length });
    }

    const statements = valid.map((e) => ({
      sql: `INSERT OR IGNORE INTO feed_events
        (event_id, anon_user_id, session_id, event_type, item_id, title, url, source, slot, rank_position, run_id, ts, user_agent, referer, meta_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      args: [
        e.event_id,
        e.anon_user_id,
        e.session_id,
        e.event_type,
        e.item_id,
        e.title,
        e.url,
        e.source,
        e.slot,
        e.rank_position,
        e.run_id,
        e.ts,
        e.user_agent,
        e.referer,
        e.meta_json,
      ],
    }));

    await db.batch(statements, 'write');

    return res.status(200).json({
      ok: true,
      accepted: valid.length,
      rejected: rejected.length,
      dedupe_mode: 'event_id_insert_or_ignore',
      server_ts: toIsoNow(),
    });
  } catch (e) {
    return res.status(500).json({ error: 'events_write_failed', detail: String(e) });
  }
}
