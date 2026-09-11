import fs from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';

// Read only published indexes and their indexed records. Input bundles, drafts,
// narratives awaiting overlay, and generated page mtimes are never publications.
export const EDITORIAL_SECTIONS = {
  daily: 'Daily recap', weekly: 'Weekly recap', storylines: 'Storylines',
  playbook: 'Playbook', map: 'Agent Know-How', foundations: 'Foundations',
};
const SLUG = /^[a-z0-9][a-z0-9-]{0,120}$/;
const DAY = /^\d{4}-\d{2}-\d{2}$/;
const WEEK = /^\d{4}-W\d{2}$/;
const rows = (value) => Array.isArray(value) ? value : [];
const values = (value) => value && typeof value === 'object' && !Array.isArray(value) ? Object.values(value) : [];
const text = (value) => typeof value === 'string' ? value.replace(/\s+/g, ' ').trim() : '';
const excerpt = (value) => {
  const clean = text(value).replace(/\[([^\]]+)\]\([^)]+\)/g, '$1').replace(/[*`]/g, '');
  return clean.length <= 240 ? clean : clean.slice(0, 237).replace(/\s+\S*$/, '') + '…';
};
const instant = (value) => typeof value === 'string' && Number.isFinite(Date.parse(value)) ? value : null;
const pick = (object, keys) => Object.fromEntries(keys.filter((key) => object?.[key] !== undefined).map((key) => [key, object[key]]));

// Hash reader-facing content, never producer clocks. Same-day edits change the
// version; timestamp-only rebuilds and object-key reordering do not.
function canonical(value) {
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === 'object') return Object.fromEntries(Object.keys(value).sort()
    .filter((key) => !['generated_at', 'updated', 'last_updated', 'first_seen', 'content_sha256', 'stale'].includes(key))
    .map((key) => [key, canonical(value[key])]));
  return typeof value === 'string' ? text(value) : value;
}
export function contentVersion(value) {
  return createHash('sha256').update(JSON.stringify(canonical(value))).digest('hex').slice(0, 24);
}

export function buildEditorialCatalog(dataDir) {
  const read = (relative) => {
    try { return JSON.parse(fs.readFileSync(path.join(dataDir, relative), 'utf8')); }
    catch { return null; }
  };
  const items = new Map();
  function add(section, key, href, source, content, options = {}) {
    const title = text(source.title || source.label);
    const updated = instant(options.updated || source.updated || source.generated_at);
    if (!title || !updated || ['draft', 'withdrawn'].includes(source.status)) return;
    const id = `${section}:${key}`;
    items.set(id, {
      id, section, section_label: EDITORIAL_SECTIONS[section], href, title,
      summary: excerpt(options.summary || source.summary),
      published_at: instant(options.published) || null,
      updated_at: updated,
      date_precision: DAY.test(updated) ? 'day' : 'time',
      version: contentVersion(content),
      kind: options.kind || 'article',
      period: options.period || null,
    });
  }

  for (const section of ['daily', 'weekly', 'playbook']) {
    const field = section === 'weekly' ? 'week' : 'date';
    const pattern = section === 'weekly' ? WEEK : DAY;
    for (const entry of rows(read(`${section}/index.json`))) {
      const key = entry?.[field];
      if (typeof key !== 'string' || !pattern.test(key)) continue;
      const source = read(`${section}/${key}.json`);
      if (!source || source[field] !== key || !text(source.title)) continue;
      if (section === 'playbook' ? !rows(source.cards).length : !rows(source.categories).some((c) => rows(c.articles).length)) continue;
      const content = pick(source, ['title', 'intro', 'highlights', 'categories', 'cards']);
      const intro = Array.isArray(source.intro) ? source.intro[0] : source.intro;
      add(section, key, `/${section}/${key}`, source, content, {
        summary: rows(source.highlights)[0] || intro,
        published: source.generated_at, updated: source.updated_at || source.generated_at || entry.generated_at,
        kind: 'edition', period: section === 'weekly' ? source.end : source.date,
      });
    }
  }

  for (const entry of rows(read('storylines/index.json')?.storylines)) {
    if (!SLUG.test(entry?.slug || '')) continue;
    const source = read(`storylines/${entry.slug}.json`);
    if (!source || source.slug !== entry.slug || !rows(source.days).length) continue;
    const editorial = source.editorial || {};
    const timestamps = [source.last_updated, editorial.generated_at].filter(instant);
    timestamps.sort((a, b) => Date.parse(b) - Date.parse(a));
    add('storylines', source.slug, `/storyline/${source.slug}`, source,
      pick(source, ['label', 'days', 'editorial']), {
        published: source.first_seen, updated: timestamps[0],
        summary: editorial.stale ? entry.latest_title : editorial.whats_new || editorial.tldr || entry.latest_title,
      });
  }

  for (const [section, file, key, route] of [
    ['map', 'wiki/index.json', 'nodes', 'topic'],
    ['foundations', 'foundations/index.json', 'concepts', 'foundations'],
  ]) {
    for (const source of values(read(file)?.[key])) {
      if (!SLUG.test(source?.slug || '') || !rows(source.sections).length) continue;
      add(section, source.slug, `/${route}/${source.slug}`, source,
        pick(source, ['title', 'question', 'summary', 'sections', 'evidence', 'solutions', 'obstacles', 'related_topics', 'related_storylines', 'related_playbook_cards']),
        { published: source.created_at || source.created });
    }
  }

  // The Lab validator binds index rows to the exact published source bytes.
  // A draft, missing source, or stale index is never promoted.
  for (const entry of rows(read('playbook/lab/index.json'))) {
    if (!SLUG.test(entry?.slug || '') || !['protocol', 'published'].includes(entry.state)) continue;
    let raw;
    try { raw = fs.readFileSync(path.join(dataDir, `playbook/lab/${entry.slug}.json`)); } catch { continue; }
    if (createHash('sha256').update(raw).digest('hex') !== entry.content_sha256) continue;
    const source = read(`playbook/lab/${entry.slug}.json`);
    if (!source || source.slug !== entry.slug || source.state !== entry.state) continue;
    add('playbook', `lab:${entry.slug}`, `/playbook/lab/${entry.slug}`, source, source,
      { kind: 'lab', published: source.generated_at, updated: source.updated_at || source.generated_at, period: source.date });
  }

  return Array.from(items.values()).sort((a, b) => Date.parse(b.updated_at) - Date.parse(a.updated_at) || a.id.localeCompare(b.id));
}
