import { createClient } from '@libsql/client';

let client;
let schemaReady;

export function getTursoClient() {
  if (client) return client;

  const url = process.env.TURSO_DATABASE_URL;
  const authToken = process.env.TURSO_AUTH_TOKEN;
  if (!url || !authToken) {
    throw new Error('missing_turso_env');
  }

  client = createClient({ url, authToken });
  return client;
}

export async function ensureEventSchema() {
  if (schemaReady) return schemaReady;

  const db = getTursoClient();
  schemaReady = (async () => {
    await db.batch(
      [
        `CREATE TABLE IF NOT EXISTS feed_events (
          event_id TEXT PRIMARY KEY,
          anon_user_id TEXT NOT NULL,
          session_id TEXT,
          event_type TEXT NOT NULL,
          item_id TEXT,
          title TEXT,
          url TEXT,
          source TEXT,
          slot TEXT,
          rank_position INTEGER,
          run_id TEXT,
          ts TEXT NOT NULL,
          user_agent TEXT,
          referer TEXT,
          meta_json TEXT,
          created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
        )`,
        `CREATE INDEX IF NOT EXISTS idx_feed_events_user_ts ON feed_events (anon_user_id, ts DESC)`,
        `CREATE INDEX IF NOT EXISTS idx_feed_events_item_ts ON feed_events (item_id, ts DESC)`,
        `CREATE INDEX IF NOT EXISTS idx_feed_events_type_ts ON feed_events (event_type, ts DESC)`,
      ].map((sql) => ({ sql, args: [] })),
      'write',
    );
  })();

  return schemaReady;
}
