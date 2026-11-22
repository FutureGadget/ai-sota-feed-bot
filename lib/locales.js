// Reader languages, from config/locales.json (shared with pipeline/locales.py).
// The first entry is the default edition; the others are localized editions.
import config from '../config/locales.json' with { type: 'json' };

const BY_CODE = new Map(config.locales.map((l) => [l.code, l]));

export const LOCALES = config.locales.map((l) => l.code);
export const DEFAULT_LOCALE = LOCALES[0];

export function getLocale(code) {
  return BY_CODE.get(code);
}

// A request's language: a supported code, else the default.
export function parseLocale(value) {
  const code = String(value || '').trim().toLowerCase();
  return BY_CODE.has(code) ? code : DEFAULT_LOCALE;
}

// True for a supported language other than the default.
export function isLocalized(value) {
  const code = String(value || '').trim().toLowerCase();
  return code !== DEFAULT_LOCALE && BY_CODE.has(code);
}

export function localePath(code, sitePath) {
  return `${BY_CODE.get(code)?.path_prefix ?? ''}${sitePath}`;
}

// The operator's off switch for every localized overlay on a live API response:
// LOCALIZED_FEED_ENABLED=0 (or false/no/off) makes each locale return plain English.
export function localizedFeedEnabled() {
  const flag = String(process.env.LOCALIZED_FEED_ENABLED || '1').trim().toLowerCase();
  return !['0', 'false', 'no', 'off'].includes(flag);
}
