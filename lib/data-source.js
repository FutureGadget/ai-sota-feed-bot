// Injectable data source for the API layer.
//
// Default: read committed JSON from the repo's data/ directory (Node, Vercel,
// tests). The Cloudflare Worker installs an R2-backed synchronous source at
// startup (worker/src/r2-source.js) after preloading the keys a route needs,
// so the same handler code runs unchanged on both platforms.
//
// All paths are relative to data/ and use forward slashes
// (e.g. 'processed/latest.json').

import fs from 'node:fs';
import path from 'node:path';

let custom = null;

export function setDataSource(source) {
  custom = source || null;
}

export function hasCustomDataSource() {
  return !!custom;
}

function fsReadJson(rel, fallback) {
  try {
    const p = path.join(process.cwd(), 'data', ...String(rel).split('/'));
    if (!fs.existsSync(p)) return fallback;
    return JSON.parse(fs.readFileSync(p, 'utf-8'));
  } catch {
    return fallback;
  }
}

// Sentinel for "distinguish missing from a real value" call sites.
export const MISSING = Symbol('data-source-missing');

export function readDataJson(rel, fallback) {
  return custom ? custom.readJson(rel, fallback) : fsReadJson(rel, fallback);
}

// Raw bytes (Buffer in Node, Uint8Array in the Worker) for callers that hash
// exact file bytes; null when missing.
export function readDataRaw(rel) {
  if (custom) return custom.readRaw(rel);
  try {
    return fs.readFileSync(path.join(process.cwd(), 'data', ...String(rel).split('/')));
  } catch {
    return null;
  }
}
