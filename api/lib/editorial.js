import fs from 'node:fs';
import path from 'node:path';

// Shared editorial hygiene for the served feed surfaces (JSON feed + RSS).
// The Python pipeline writes `data/processed/editorial.json`; this module is
// the JS side of the same policy so the API and the pipeline cannot disagree
// about which sources are search results or how many may reach a reader.

const DEFAULT_CAPS = {
  search: 1,
  aggregator: 2,
  community: 2,
  first_party: 4,
  practitioner: 3,
  release: 4,
  research: 4,
  default: 3,
};

const DEFAULT_ROLE_TOTALS = {
  search: 1,
  aggregator: 2,
  community: 2,
  first_party: 12,
  practitioner: 6,
  release: 6,
  research: 6,
};

const FIRST_PARTY_SOURCES = new Set([
  'openai_blog',
  'anthropic_newsroom',
  'anthropic_engineering',
  'anthropic_research',
  'google_deepmind_blog',
  'huggingface_blog',
  'nvidia_blog',
  'google_ai_blog',
  'aws_ml_blog',
  'google_cloud_blog',
  'cloudflare_blog',
  'vllm_blog',
  'databricks_blog',
  'langchain_blog',
  'github_blog_ai_ml',
  'modal_blog',
]);

const PRACTITIONER_SOURCES = new Set([
  'simon_willison',
  'latent_space',
  'infoq_ai_ml',
  'hamel_husain',
  'eugene_yan',
  'philschmid',
  'interconnects',
  'sebastian_raschka',
  'lilian_weng',
  'archer_hume',
  'kun_chen',
  'felix_rieseberg',
  'semianalysis',
]);

const ROLE_PRIORITY = {
  first_party: 0,
  practitioner: 1,
  release: 2,
  research: 2,
  aggregator: 3,
  community: 3,
  default: 3,
  search: 4,
};

function readJsonSafe(p, fallback) {
  try {
    if (!fs.existsSync(p)) return fallback;
    return JSON.parse(fs.readFileSync(p, 'utf-8'));
  } catch {
    return fallback;
  }
}

export function readEditorial() {
  const data = readJsonSafe(path.join(process.cwd(), 'data', 'processed', 'editorial.json'), null);
  return {
    source_roles: data?.source_roles && typeof data.source_roles === 'object' ? data.source_roles : {},
    source_role_prefixes:
      data?.source_role_prefixes && typeof data.source_role_prefixes === 'object'
        ? data.source_role_prefixes
        : {},
    caps: { ...DEFAULT_CAPS, ...(data?.caps && typeof data.caps === 'object' ? data.caps : {}) },
    role_totals: {
      ...DEFAULT_ROLE_TOTALS,
      ...(data?.role_totals && typeof data.role_totals === 'object' ? data.role_totals : {}),
    },
    search_quarantine:
      data?.search_quarantine && typeof data.search_quarantine === 'object'
        ? data.search_quarantine
        : {},
    first_party_quarantine:
      data?.first_party_quarantine && typeof data.first_party_quarantine === 'object'
        ? data.first_party_quarantine
        : {},
    story_clusters: data?.story_clusters || { enabled: true },
  };
}

export function sourceRole(source, editorial = null) {
  const name = String(source || '').trim();
  const explicit = editorial?.source_roles || {};
  if (explicit[name]) return String(explicit[name]);
  const prefixes = editorial?.source_role_prefixes || {};
  for (const [prefix, role] of Object.entries(prefixes)) {
    if (!prefix) continue;
    if (prefix.endsWith('_') && name.startsWith(prefix)) return String(role);
    if (prefix.startsWith('_') && name.endsWith(prefix)) return String(role);
    if (name === prefix) return String(role);
  }
  if (FIRST_PARTY_SOURCES.has(name)) return 'first_party';
  if (PRACTITIONER_SOURCES.has(name)) return 'practitioner';
  if (name.startsWith('search_')) return 'search';
  if (name === 'hackernews_ai') return 'community';
  if (name === 'infoq_ai_ml' || name === 'paperswithcode_latest') return 'aggregator';
  if (name.startsWith('arxiv_') || name.startsWith('openreview_')) return 'research';
  if (name.endsWith('_releases')) return 'release';
  return 'default';
}

export function isSearchItem(item, editorial = null) {
  return sourceRole(item?.source, editorial) === 'search';
}

function matchesAny(text, patterns) {
  for (const pattern of patterns || []) {
    try {
      if (new RegExp(pattern, 'i').test(text)) return true;
    } catch {
      // A malformed config pattern must not take the feed down.
    }
  }
  return false;
}

function nonLatinRatio(text) {
  const letters = [...String(text || '')].filter((ch) => /\p{L}/u.test(ch));
  if (!letters.length) return 0;
  const nonLatin = letters.filter((ch) => ch.codePointAt(0) > 127).length;
  return nonLatin / letters.length;
}

function normalizeTitle(value) {
  return String(value || '')
    .toLowerCase()
    .replace(/^(?:show\s+hn|hn)\s*:\s*/, '')
    .replace(/[^a-z0-9]+/g, ' ')
    .trim();
}

function coverageScore(item) {
  const value = Number(
    item?.v2_final_score ?? item?.score_at_last_seen ?? item?.score ?? item?.tier1_quick_score ?? 0
  );
  return Number.isFinite(value) ? value : 0;
}

function publishedMs(item) {
  for (const value of [item?.published, item?.first_seen, item?.collected_at]) {
    const date = value ? new Date(value) : null;
    if (date && Number.isFinite(date.getTime())) return date.getTime();
  }
  return Number.MAX_SAFE_INTEGER;
}

function normalizedUrl(value) {
  const s = String(value || '').trim().toLowerCase().split('?')[0];
  return s.endsWith('/') && s.length > 1 ? s.slice(0, -1) : s;
}

function mergeCoverage(rep, other) {
  const selfSource = String(rep?.source || '');
  const selfUrl = normalizedUrl(rep?.url);
  const entries = Array.isArray(rep?.also_covered) ? [...rep.also_covered] : [];
  const seen = new Set(
    entries.map((entry) => `${String(entry?.source || '')}|${normalizedUrl(entry?.url)}`)
  );
  seen.add(`${selfSource}|${selfUrl}`);
  const candidates = [
    { source: other?.source, url: other?.url, title: other?.title },
    ...(Array.isArray(other?.also_covered) ? other.also_covered : []),
  ];
  for (const entry of candidates) {
    const source = String(entry?.source || '');
    const url = normalizedUrl(entry?.url);
    if (!source || source === selfSource) continue;
    const key = `${source}|${url}`;
    if (seen.has(key)) continue;
    seen.add(key);
    entries.push({ source, url: String(entry?.url || ''), title: String(entry?.title || '').slice(0, 160) });
    if (entries.length >= 4) break;
  }
  if (entries.length) rep.also_covered = entries;
}

function storyClusterKey(item) {
  if (item?.story_key) return `k:${String(item.story_key)}`;
  if (item?.story_cluster_id) return `id:${String(item.story_cluster_id)}`;
  const normalized = normalizeTitle(item?.title);
  return normalized.length >= 20 ? `t:${normalized}` : '';
}

// Collapse the same story reported by multiple outlets into one card. The
// pipeline already clusters candidates before ranking; this pass also handles
// the API's accumulated run history, where older runs may not carry a
// `story_key` yet. Exact normalized titles are the safe fallback.
export function collapseStoryClusters(items, editorial = null) {
  // Work on shallow copies. The API caches the accumulated run pool for the
  // process lifetime; mutating a pooled item's also_covered here would leak
  // into the next request (and into the Korean source-hash check).
  const list = (Array.isArray(items) ? items : []).map((item) => ({ ...item }));
  if (editorial?.story_clusters?.enabled === false) return list;

  const groups = new Map();
  for (const item of list) {
    const key = storyClusterKey(item);
    if (!key) continue;
    const group = groups.get(key) || [];
    group.push(item);
    groups.set(key, group);
  }

  const reps = new Map();
  for (const [key, group] of groups.entries()) {
    if (group.length < 2) continue;
    const rep = [...group].sort((a, b) => {
      const ar = ROLE_PRIORITY[sourceRole(a?.source, editorial)] ?? 3;
      const br = ROLE_PRIORITY[sourceRole(b?.source, editorial)] ?? 3;
      if (ar !== br) return ar - br;
      const as = coverageScore(a);
      const bs = coverageScore(b);
      if (bs !== as) return bs - as;
      return publishedMs(a) - publishedMs(b);
    })[0];
    for (const item of group) {
      if (item !== rep) mergeCoverage(rep, item);
    }
    reps.set(key, rep);
  }

  const out = [];
  for (const item of list) {
    const key = storyClusterKey(item);
    if (!key || !reps.has(key)) {
      out.push(item);
      continue;
    }
    if (reps.get(key) === item) out.push(item);
  }
  return out;
}

// Per-source and per-role caps over the accumulated pool. A search query can
// contribute one card, not one per article it happened to return today.
export function applyEditorialCaps(items, editorial = null) {
  const list = Array.isArray(items) ? items : [];
  const caps = { ...DEFAULT_CAPS, ...(editorial?.caps || {}) };
  const totals = { ...DEFAULT_ROLE_TOTALS, ...(editorial?.role_totals || {}) };
  const searchCfg = editorial?.search_quarantine || {};
  const firstPartyCfg = editorial?.first_party_quarantine || {};
  const perSource = new Map();
  const perRole = new Map();
  const out = [];

  for (const item of list) {
    const source = String(item?.source || 'unknown');
    const role = sourceRole(source, editorial);
    const titleText = String(item?.title || '').toLowerCase();
    if (role === 'search' && searchCfg.enabled !== false) {
      const maxNonLatin = Number(searchCfg.max_non_latin_ratio ?? 0.3);
      if (maxNonLatin > 0 && nonLatinRatio(titleText) > maxNonLatin) continue;
      if (
        matchesAny(titleText, searchCfg.low_quality_patterns)
        && !matchesAny(titleText, searchCfg.rescue_keywords)
      ) continue;
    }
    if (role === 'first_party' && firstPartyCfg.enabled !== false) {
      if (
        matchesAny(titleText, firstPartyCfg.low_value_patterns)
        && !matchesAny(titleText, firstPartyCfg.rescue_keywords)
      ) continue;
    }
    const sourceCap = Number(caps[role] ?? caps.default ?? 3);
    const roleCap = Number(totals[role] ?? 0);
    const sourceCount = Number(perSource.get(source) || 0);
    const roleCount = Number(perRole.get(role) || 0);
    if (sourceCap > 0 && sourceCount >= sourceCap) continue;
    if (roleCap > 0 && roleCount >= roleCap) continue;
    perSource.set(source, sourceCount + 1);
    perRole.set(role, roleCount + 1);
    out.push(item);
  }
  return out;
}
