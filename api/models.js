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

const SLUG_RE = /^[a-z0-9][a-z0-9-]{0,80}$/;

// Hard cap on ?limit= so a runaway value can't force a huge response. There
// are ~200 models in latest.json today; 500 leaves headroom without being
// unbounded.
const MAX_LIMIT = 500;

// Fields safe to sort by: numeric benchmark/price columns plus release_date
// (an ISO YYYY-MM-DD string, which sorts correctly with plain `<`/`>`).
const SORT_KEYS = new Set([
  'arena_elo_overall',
  'arena_elo_coding',
  'arena_votes',
  'price_blended_per_1m',
  'price_input_per_1m',
  'price_output_per_1m',
  'aa_intelligence_index',
  'aa_coding_index',
  'median_output_tokens_per_second',
  'context_window_tokens',
  'parameters_total',
  'parameters_active',
  'release_date',
  // DeepSWE measured-per-task-cost fields (pipeline/collect_models.py's
  // DeepSWE ingest, 2026-08-17) - deepswe_pass_at_1 is the only metric with
  // a server-side frontier entry today (see config/models.yaml's
  // frontier_metrics), so it is also the only sortable field paired with a
  // genuine per-task cost rather than a per-token price.
  'deepswe_pass_at_1',
  'deepswe_cost_per_task_usd',
  'deepswe_median_cost_usd',
  'deepswe_ci_lo',
  'deepswe_ci_hi',
  'deepswe_n_runs',
  'deepswe_output_tokens',
]);

// Raw per-model Artificial Analysis benchmark keys (pipeline/collect_models.py's
// `benchmarks` object, config-driven via config/models.yaml's
// sources.artificial_analysis.benchmarks) are also sortable, but this
// function has no config/YAML access at request time - instead of
// hardcoding a second key list here (which would drift from the config the
// collector actually uses), a requested `sort` is checked against whichever
// keys are ACTUALLY present under some model's `benchmarks` object in the
// loaded artifact. That is still a whitelist - only a key that genuinely
// exists in the served data can be sorted on, never an arbitrary
// user-supplied path - it is just computed from the data instead of a
// static list.
function collectBenchmarkKeys(models) {
  const keys = new Set();
  for (const m of models) {
    if (m && m.benchmarks && typeof m.benchmarks === 'object') {
      for (const k of Object.keys(m.benchmarks)) keys.add(k);
    }
  }
  return keys;
}

// Comparator with nulls always sorted last, regardless of asc/desc: a null
// benchmark or price means "unknown", not "0" or "worst possible value", so
// it must never be pulled to the front of a desc sort or the Pareto-cheap
// end of an asc sort. `fromBenchmarks` reads the value from a model's
// nested `benchmarks` object instead of a top-level field - same nulls-last
// contract either way.
function compareBy(key, order, fromBenchmarks) {
  const dir = order === 'asc' ? 1 : -1;
  const read = fromBenchmarks
    ? (m) => (m && m.benchmarks ? m.benchmarks[key] : null)
    : (m) => (m ? m[key] : null);
  return (a, b) => {
    const av = read(a);
    const bv = read(b);
    const aNull = av === null || av === undefined;
    const bNull = bv === null || bv === undefined;
    if (aNull && bNull) return 0;
    if (aNull) return 1;
    if (bNull) return -1;
    if (av < bv) return -1 * dir;
    if (av > bv) return 1 * dir;
    return 0;
  };
}

// How completely a row identifies its model, used to pick which variant row
// answers a ?slug= lookup when several share one url_slug.
function identityScore(m) {
  if (!m) return -1;
  const fields = ['license', 'open_weights', 'official_url', 'release_date', 'organization'];
  return fields.reduce((n, f) => n + (m[f] !== null && m[f] !== undefined ? 1 : 0), 0);
}

// GET /api/models                              -> full index (sources + models)
// GET /api/models?slug=claude-opus-5           -> one model (public url_slug; internal slug also accepted)
// GET /api/models?org=anthropic                -> filter by organization (case-insensitive)
// GET /api/models?open_weights=true|false      -> filter by boolean (null = unknown, excluded from both)
// GET /api/models?limit=20                     -> cap result count (clamped to 1..500, invalid values ignored)
// GET /api/models?sort=arena_elo_coding&order=asc|desc -> sort (default desc); nulls always sort last
// GET /api/models?sort=livecodebench&order=asc|desc    -> sort by a raw AA benchmark key (see collectBenchmarkKeys)
export function GET(request) {
  try {
    // Resolved per-request (not a module-level constant) so tests can
    // process.chdir() into a fixture directory, matching api/feed.js.
    const modelsDir = path.join(process.cwd(), 'data', 'models');
    const index = readJsonSafe(path.join(modelsDir, 'latest.json'), null);
    const sources = (index && index.sources) || {};
    const generatedAt = (index && index.generated_at) || null;
    let models = Array.isArray(index && index.models) ? index.models : [];

    const url = new URL(request.url);

    const slug = String(url.searchParams.get('slug') || '').trim();
    if (slug) {
      if (!SLUG_RE.test(slug)) return Response.json({ error: 'invalid_slug' }, { status: 400 });
      // Match `url_slug` FIRST: that is the public identifier every link and
      // route on the site uses (/models/claude-opus-5), while `slug` is the
      // internal normalized join key ("claudeopus5high"). Looking up only the
      // internal key 404'd on the very identifier the site publishes. The
      // internal key stays accepted as a fallback so existing callers keep
      // working. url_slug is shared by a model's variants, so return the row
      // richest in identity fields rather than whichever variant sorts first.
      const byUrlSlug = models.filter((m) => m && m.url_slug === slug);
      const model = byUrlSlug.length
        ? byUrlSlug.reduce((best, m) => (identityScore(m) > identityScore(best) ? m : best))
        : models.find((m) => m && m.slug === slug);
      if (!model) return Response.json({ error: 'model_not_found', slug }, { status: 404 });
      return Response.json(model);
    }

    const org = String(url.searchParams.get('org') || '').trim();
    if (org) {
      const orgLower = org.toLowerCase();
      models = models.filter(
        (m) => m && typeof m.organization === 'string' && m.organization.toLowerCase() === orgLower
      );
    }

    const openWeightsParam = url.searchParams.get('open_weights');
    if (openWeightsParam === 'true' || openWeightsParam === 'false') {
      const want = openWeightsParam === 'true';
      // null/undefined means "unknown", not false - must not match either filter value.
      models = models.filter((m) => m && m.open_weights === want);
    }

    const sortKey = String(url.searchParams.get('sort') || '').trim();
    if (sortKey) {
      const isDirect = SORT_KEYS.has(sortKey);
      const isBenchmark = !isDirect && collectBenchmarkKeys(models).has(sortKey);
      if (isDirect || isBenchmark) {
        const order = url.searchParams.get('order') === 'asc' ? 'asc' : 'desc';
        models = [...models].sort(compareBy(sortKey, order, isBenchmark));
      }
    }

    const limitParam = url.searchParams.get('limit');
    if (limitParam !== null) {
      const n = Number(limitParam);
      if (Number.isFinite(n) && n > 0) {
        models = models.slice(0, Math.min(Math.floor(n), MAX_LIMIT));
      }
      // non-numeric, negative, zero, or NaN -> ignored, no limit applied
    }

    return Response.json({ generated_at: generatedAt, sources, models });
  } catch (e) {
    return Response.json({ error: 'models_read_failed', detail: String(e) }, { status: 500 });
  }
}
