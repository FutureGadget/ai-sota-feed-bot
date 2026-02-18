import { getTursoClient } from './turso.js';

const TOPIC_RULES = [
  { key: 'agent', pats: [/\bagent\b/i, /agentic/i, /claude code/i, /codex/i] },
  { key: 'eval', pats: [/\beval/i, /benchmark/i, /ablation/i] },
  { key: 'inference', pats: [/inference/i, /latency/i, /throughput/i, /serving/i] },
  { key: 'cost', pats: [/cost/i, /token/i, /pricing/i, /efficien/i] },
  { key: 'release', pats: [/release/i, /ga\b/i, /general availability/i, /changelog/i] },
  { key: 'research', pats: [/research/i, /paper/i, /arxiv/i] },
];

function clamp(v, lo, hi) {
  return Math.max(lo, Math.min(hi, v));
}

function toIsoDaysAgo(days) {
  return new Date(Date.now() - days * 24 * 60 * 60 * 1000).toISOString();
}

function itemBaseScore(it) {
  const n = Number(it?.score_at_last_seen ?? it?.v2_final_score ?? it?.score ?? 0);
  return Number.isFinite(n) ? n : 0;
}

function itemTopics(it) {
  const t = `${it?.title || ''} ${it?.summary_1line || ''} ${(it?.tags || []).join(' ')}`;
  const out = [];
  for (const r of TOPIC_RULES) {
    if (r.pats.some((p) => p.test(t))) out.push(r.key);
  }
  return out;
}

function eventTopics(row) {
  const t = `${row?.title || ''} ${row?.source || ''} ${row?.url || ''}`;
  const out = [];
  for (const r of TOPIC_RULES) {
    if (r.pats.some((p) => p.test(t))) out.push(r.key);
  }
  return out;
}

async function loadUserSourceStats(db, anonUserId, sinceIso) {
  const rs = await db.execute({
    sql: `
      SELECT
        source,
        SUM(CASE WHEN event_type='impression' THEN 1 ELSE 0 END) AS impressions,
        SUM(CASE WHEN event_type='click' THEN 1 ELSE 0 END) AS clicks
      FROM feed_events
      WHERE anon_user_id = ?
        AND ts >= ?
        AND source IS NOT NULL
      GROUP BY source
    `,
    args: [anonUserId, sinceIso],
  });
  return rs.rows || [];
}

async function loadUserGlobalStats(db, anonUserId, sinceIso) {
  const rs = await db.execute({
    sql: `
      SELECT
        SUM(CASE WHEN event_type='impression' THEN 1 ELSE 0 END) AS impressions,
        SUM(CASE WHEN event_type='click' THEN 1 ELSE 0 END) AS clicks
      FROM feed_events
      WHERE anon_user_id = ?
        AND ts >= ?
    `,
    args: [anonUserId, sinceIso],
  });
  const row = (rs.rows || [])[0] || {};
  return {
    impressions: Number(row.impressions || 0),
    clicks: Number(row.clicks || 0),
  };
}

async function loadUserEventRows(db, anonUserId, sinceIso, limit = 2000) {
  const rs = await db.execute({
    sql: `
      SELECT event_type, title, source, url
      FROM feed_events
      WHERE anon_user_id = ?
        AND ts >= ?
        AND event_type IN ('impression','click')
      ORDER BY ts DESC
      LIMIT ?
    `,
    args: [anonUserId, sinceIso, limit],
  });
  return rs.rows || [];
}

function buildSourceLiftMap(sourceRows, globalCtr, sourceMinImpressions = 20) {
  const m = new Map();
  for (const r of sourceRows) {
    const source = String(r.source || '');
    if (!source) continue;
    const imp = Number(r.impressions || 0);
    const clk = Number(r.clicks || 0);
    const ctr = clk / Math.max(imp, 1);
    const rawLift = ctr - globalCtr;
    const confidence = Math.min(1, imp / sourceMinImpressions);
    m.set(source, rawLift * confidence);
  }
  return m;
}

function buildTopicLiftMap(eventRows, globalCtr, topicMinImpressions = 20) {
  const stats = new Map();
  for (const r of eventRows) {
    const topics = eventTopics(r);
    if (!topics.length) continue;
    for (const k of topics) {
      const cur = stats.get(k) || { imp: 0, clk: 0 };
      if (r.event_type === 'impression') cur.imp += 1;
      if (r.event_type === 'click') cur.clk += 1;
      stats.set(k, cur);
    }
  }

  const out = new Map();
  for (const [k, v] of stats.entries()) {
    const ctr = v.clk / Math.max(v.imp, 1);
    const rawLift = ctr - globalCtr;
    const confidence = Math.min(1, v.imp / topicMinImpressions);
    out.set(k, rawLift * confidence);
  }
  return out;
}

function mixWithExploration(scored, baseline, explorationRatio = 0.2, maxItems = 200) {
  const primary = [...scored].sort((a, b) => b._final_score - a._final_score);
  const exploreEvery = Math.max(2, Math.round(1 / Math.max(0.01, explorationRatio)));
  const used = new Set();
  const out = [];

  let iPrimary = 0;
  let iBase = 0;
  while (out.length < Math.min(maxItems, primary.length)) {
    const pickBase = out.length > 0 && out.length % exploreEvery === 0;
    let cand = null;

    if (pickBase) {
      while (iBase < baseline.length) {
        const b = baseline[iBase++];
        if (used.has(b._pkey)) continue;
        cand = b;
        break;
      }
    }

    if (!cand) {
      while (iPrimary < primary.length) {
        const p = primary[iPrimary++];
        if (used.has(p._pkey)) continue;
        cand = p;
        break;
      }
    }

    if (!cand) break;
    used.add(cand._pkey);
    out.push(cand);
  }

  return out;
}

export async function personalizeItems(items, opts = {}) {
  const {
    anonUserId,
    mode = process.env.PERSONALIZATION_MODE || 'shadow', // off|shadow|active
    debug = false,
    maxItems = 200,
    daysWindow = Number(process.env.PERSONALIZATION_DAYS || 14),
    wSource = Number(process.env.PERSONALIZATION_W_SOURCE || 0.10),
    wTopic = Number(process.env.PERSONALIZATION_W_TOPIC || 0.05),
    boostCap = Number(process.env.PERSONALIZATION_CAP || 0.15),
    minImpressions = Number(process.env.PERSONALIZATION_MIN_IMPRESSIONS || 30),
    minClicks = Number(process.env.PERSONALIZATION_MIN_CLICKS || 3),
    explorationRatio = Number(process.env.PERSONALIZATION_EXPLORATION || 0.2),
  } = opts;

  const baseline = items.map((it, idx) => ({ ...it, _baseline_order: idx, _pkey: `${it.url || ''}::${it.title || ''}` }));

  if (!anonUserId || mode === 'off') {
    return { items: baseline.slice(0, maxItems), diagnostics: { mode: 'off', reason: 'missing_anon_or_mode_off' } };
  }

  let db;
  try {
    db = getTursoClient();
  } catch {
    return { items: baseline.slice(0, maxItems), diagnostics: { mode, applied: false, reason: 'turso_unavailable' } };
  }
  const sinceIso = toIsoDaysAgo(daysWindow);

  let global;
  let sourceRows;
  let eventRows;
  try {
    [global, sourceRows, eventRows] = await Promise.all([
      loadUserGlobalStats(db, anonUserId, sinceIso),
      loadUserSourceStats(db, anonUserId, sinceIso),
      loadUserEventRows(db, anonUserId, sinceIso),
    ]);
  } catch {
    return { items: baseline.slice(0, maxItems), diagnostics: { mode, applied: false, reason: 'personalization_query_failed' } };
  }

  if (global.impressions < minImpressions || global.clicks < minClicks) {
    return {
      items: baseline.slice(0, maxItems),
      diagnostics: {
        mode,
        applied: false,
        reason: 'cold_start',
        impressions: global.impressions,
        clicks: global.clicks,
      },
    };
  }

  const globalCtr = global.clicks / Math.max(global.impressions, 1);
  const sourceLift = buildSourceLiftMap(sourceRows, globalCtr);
  const topicLift = buildTopicLiftMap(eventRows, globalCtr);

  const scored = baseline.map((it) => {
    const base = itemBaseScore(it);
    const sLift = Number(sourceLift.get(it.source) || 0);
    const tKeys = itemTopics(it);
    const tLiftAvg = tKeys.length ? tKeys.map((k) => Number(topicLift.get(k) || 0)).reduce((a, b) => a + b, 0) / tKeys.length : 0;

    const sourceBoost = wSource * sLift;
    const topicBoost = wTopic * tLiftAvg;
    const personalBoost = clamp(sourceBoost + topicBoost, -boostCap, boostCap);
    const finalScore = base * (1 + personalBoost);

    return {
      ...it,
      _source_boost: sourceBoost,
      _topic_boost: topicBoost,
      _personal_boost: personalBoost,
      _final_score: finalScore,
    };
  });

  const mixed = mixWithExploration(scored, baseline, explorationRatio, maxItems);
  const applied = mode === 'active';
  const out = applied ? mixed : baseline.slice(0, maxItems).map((it) => {
    const s = scored.find((x) => x._pkey === it._pkey) || it;
    return { ...it, _source_boost: s._source_boost, _topic_boost: s._topic_boost, _personal_boost: s._personal_boost, _final_score: s._final_score };
  });

  const cleaned = out.map((it) => {
    if (debug) return it;
    const { _baseline_order, _pkey, _source_boost, _topic_boost, _personal_boost, _final_score, ...rest } = it;
    return rest;
  });

  return {
    items: cleaned,
    diagnostics: {
      mode,
      applied,
      impressions: global.impressions,
      clicks: global.clicks,
      global_ctr: Number(globalCtr.toFixed(4)),
      source_rules: sourceLift.size,
      topic_rules: topicLift.size,
      window_days: daysWindow,
    },
  };
}
