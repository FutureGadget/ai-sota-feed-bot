// Editor's Desk translations: data/i18n/<locale>/updates/titles.json, written by
// pipeline/build_localized_updates.py. /api/updates?locale=<l> returns the normal
// English catalog with each item's title and summary replaced by the stored
// text while the stored source_hash still equals the item's current English
// hash. A stale or missing entry leaves the item English. Identity fields
// (id, href, version) never change, so read state and links stay stable.
import crypto from 'node:crypto';
import { readDataJson } from './data-source.js';
import { isLocalized, localizedFeedEnabled } from './locales.js';

const cleanText = (v) => String(v || '').split(/\s+/).filter(Boolean).join(' ');

// Hash of an item's English display text, the same payload as source_hash in
// pipeline/build_localized_updates.py (tests/test_updates_hash_parity.py pins them).
export function updateHash(item) {
  const payload = { summary: cleanText(item?.summary), title: cleanText(item?.title) };
  return crypto.createHash('sha256').update(JSON.stringify(payload)).digest('hex');
}

function readEntries(locale) {
  const store = readDataJson(`i18n/${locale}/updates/titles.json`, null);
  return store && typeof store.items === 'object' && store.items ? store.items : {};
}

function overlayItem(item, entry, locale) {
  if (!entry || !entry.title || entry.source_hash !== updateHash(item)) {
    return { ...item, i18n: { locale, translated: false } };
  }
  return {
    ...item,
    title: entry.title,
    summary: item.summary ? entry.summary || item.summary : item.summary,
    i18n: { locale, translated: true },
  };
}

export function withUpdateTranslations(body, locale) {
  const code = String(locale || '').trim().toLowerCase();
  if (!isLocalized(code) || !localizedFeedEnabled() || !Array.isArray(body?.items)) return body;
  const entries = readEntries(code);
  return {
    ...body,
    items: body.items.map((item) => overlayItem(item, Object.hasOwn(entries, item?.id) ? entries[item.id] : null, code)),
  };
}
