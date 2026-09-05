import fs from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';

function readJsonSafe(p, fallback) {
  try {
    if (!fs.existsSync(p)) return fallback;
    return JSON.parse(fs.readFileSync(p, 'utf-8'));
  } catch {
    return fallback;
  }
}

const PLAYBOOK_DIR = path.join(process.cwd(), 'data', 'playbook');
const SKILL_LAB_DIR = path.join(PLAYBOOK_DIR, 'lab');
const DATE_ID_RE = /^\d{4}-\d{2}-\d{2}$/;
const LAB_SLUG_RE = /^[a-z0-9][a-z0-9-]{0,79}$/;
const LAB_ID_RE = /^lab-[a-z0-9][a-z0-9-]{0,76}$/;
const LAB_SHA256_RE = /^[a-f0-9]{64}$/;
const LAB_DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
const LAB_SUMMARY_FIELDS = [
  'schema_version', 'id', 'slug', 'pilot_edition', 'pilot_size', 'state',
  'date', 'generated_at', 'featured_until', 'title', 'question', 'summary',
];

function validLabSummary(summary) {
  return summary
    && typeof summary === 'object'
    && !Array.isArray(summary)
    && summary.schema_version === 1
    && LAB_ID_RE.test(String(summary.id || ''))
    && LAB_SLUG_RE.test(String(summary.slug || ''))
    && Number.isInteger(summary.pilot_edition)
    && summary.pilot_edition >= 0
    && summary.pilot_edition <= 3
    && summary.pilot_size === 3
    && ['protocol', 'published'].includes(summary.state)
    && LAB_DATE_RE.test(String(summary.date || ''))
    && LAB_DATE_RE.test(String(summary.featured_until || ''))
    && LAB_SHA256_RE.test(String(summary.content_sha256 || ''))
    && summary.url === `/playbook/lab/${summary.slug}`;
}

export function readValidatedLabRecord(directory, summary) {
  if (!validLabSummary(summary)) return null;
  try {
    const recordPath = path.join(directory, `${summary.slug}.json`);
    const source = fs.readFileSync(recordPath);
    const digest = createHash('sha256').update(source).digest('hex');
    if (digest !== summary.content_sha256) return null;
    const record = JSON.parse(source.toString('utf-8'));
    if (!record || typeof record !== 'object' || Array.isArray(record)) return null;
    if (LAB_SUMMARY_FIELDS.some((field) => record[field] !== summary[field])) return null;
    return record;
  } catch {
    return null;
  }
}

// GET /api/playbook                 -> latest edition
// GET /api/playbook?date=2026-06-21 -> a specific edition
// GET /api/playbook?list=1          -> index of available editions
// GET /api/playbook?sources=1       -> source-sid lookup for recap overlays
// GET /api/playbook?locale=ko       -> query localized content
// GET /api/playbook?lab=latest      -> latest validated Skill Lab record
// GET /api/playbook?lab=list        -> bounded Skill Lab pilot index
// GET /api/playbook?lab=<slug>      -> one validated Skill Lab record
export function GET(request) {
  try {
    const url = new URL(request.url);
    if (url.searchParams.has('lab')) {
      const selector = String(url.searchParams.get('lab') || '').trim();
      if (selector !== 'latest' && selector !== 'list' && !LAB_SLUG_RE.test(selector)) {
        return Response.json(
          { error: 'invalid_lab', detail: 'expected latest, list, or a URL-safe slug' },
          { status: 400 }
        );
      }
      const indexPath = path.join(SKILL_LAB_DIR, 'index.json');
      const index = fs.existsSync(indexPath) ? readJsonSafe(indexPath, null) : [];
      if (!Array.isArray(index) || index.length > 4) {
        return Response.json({ error: 'lab_index_invalid' }, { status: 500 });
      }
      const validated = index.map((summary) => ({
        summary,
        record: readValidatedLabRecord(SKILL_LAB_DIR, summary),
      }));
      if (validated.some((item) => !item.record)) {
        return Response.json({ error: 'lab_index_stale' }, { status: 500 });
      }
      const labs = validated.map((item) => item.summary);
      if (selector === 'list') return Response.json({ labs });

      const selected = selector === 'latest'
        ? validated[0]
        : validated.find((item) => item.summary.slug === selector);
      if (!selected) {
        if (selector === 'latest') {
          return Response.json({ error: 'no_lab_editions_yet' }, { status: 404 });
        }
        return Response.json({ error: 'lab_not_found', slug: selector }, { status: 404 });
      }
      return Response.json(selected.record);
    }

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
