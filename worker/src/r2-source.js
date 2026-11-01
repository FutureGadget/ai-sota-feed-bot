// R2-backed synchronous data source for the API layer.
//
// API handlers read data synchronously (they were written for the filesystem).
// A Worker request preloads the keys its route needs from R2 into an
// in-memory map, then the handlers read from it unchanged. Parsed values and
// raw bytes are cached per isolate with a short TTL: data only changes on
// deploy (every 2h), and the Cache API already sits in front of responses.

import { setDataSource } from '../../lib/data-source.js';

const TTL_MS = 60_000;
const store = new Map(); // key -> { value?, raw?, miss?, expires }
let bucket = null;

export function installR2Source(env) {
  bucket = env.DATA;
  setDataSource({ readJson, readRaw });
}

function readJson(rel, fallback) {
  const entry = store.get(rel);
  if (!entry || entry.miss) {
    if (!entry) console.warn(`data-source: '${rel}' read without preload`);
    return fallback;
  }
  if (entry.value !== undefined) return entry.value;
  if (entry.raw) {
    try {
      return JSON.parse(new TextDecoder().decode(entry.raw));
    } catch {
      return fallback;
    }
  }
  return fallback;
}

function readRaw(rel) {
  const entry = store.get(rel);
  if (!entry || entry.miss) {
    if (!entry) console.warn(`data-source: raw '${rel}' read without preload`);
    return null;
  }
  if (entry.raw) return entry.raw;
  if (entry.value !== undefined) {
    return new TextEncoder().encode(JSON.stringify(entry.value));
  }
  return null;
}

// Fetch keys from R2 into the isolate cache. `rawKeys` are kept as bytes (the
// playbook Lab validator hashes exact file bytes). Missing keys are cached as
// misses so handlers get the same fallback they would for an absent file.
export async function preload(keys, rawKeys = []) {
  const rawSet = new Set(rawKeys);
  const now = Date.now();
  await Promise.all(
    [...new Set(keys)].map(async (key) => {
      const cached = store.get(key);
      if (cached && cached.expires > now) return;
      let obj = null;
      try {
        obj = await bucket.get(`data/${key}`);
      } catch (e) {
        console.warn(`data-source: R2 get failed for '${key}': ${e}`);
      }
      if (!obj) {
        store.set(key, { miss: true, expires: now + TTL_MS });
        return;
      }
      const entry = { expires: now + TTL_MS };
      if (rawSet.has(key)) {
        entry.raw = new Uint8Array(await obj.arrayBuffer());
      } else {
        try {
          entry.value = await obj.json();
        } catch {
          entry.miss = true;
        }
      }
      store.set(key, entry);
    }),
  );
}

// Read one key straight through (used for two-phase preloads, e.g. the Lab
// index whose entries name the record keys to load next).
export async function loadJson(key) {
  await preload([key]);
  return readJson(key, null);
}
