// Storyline follow-by-email, served through api/subscribe.js (the project is
// at Vercel Hobby's 12-function cap, so this is a library, not a function).
//
// POST /api/subscribe { action: "follow", email, slug, hp?, reader_id? }
//   Adds `slug` to the contact's `followed_storylines` property (comma-separated
//   slugs) and puts the contact in the "Storyline followers" segment. A new
//   contact is created in that segment only — following one story does not
//   subscribe anyone to the daily/weekly digest. publish/publish_email.py
//   --kind follows emails each follower when a story they follow moves.
//
// GET|POST /api/subscribe?c=<contact id>&s=<slug | *>&t=<token>
//   Signed unfollow link carried by every follow email (and its
//   List-Unsubscribe header; POST is the RFC 8058 one-click form). `*` stops
//   every follow. The token is an HMAC keyed by EMAIL_API_KEY, so links need no
//   extra secret and die with a key rotation.
//
// The key is read server-side only. api/subscribe.js returns 503 without
// EMAIL_API_KEY, and the storyline page keeps its browser-only Follow button.

import { createHmac, timingSafeEqual } from 'node:crypto';

import { readerIdFor } from './reader-id.js';

const API = 'https://api.resend.com';
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const SLUG_RE = /^[a-z0-9][a-z0-9-]{0,99}$/;
const CONTACT_ID_RE = /^[A-Za-z0-9-]{1,64}$/;
export const FOLLOW_PROPERTY = 'followed_storylines';
export const FOLLOWERS_SEGMENT_NAME = 'Storyline followers';
// Keep the property short; oldest follows drop first.
export const MAX_FOLLOWS = 25;

export function parseFollows(value) {
  const seen = new Set();
  for (const part of String(value || '').split(',')) {
    const slug = part.trim();
    if (SLUG_RE.test(slug)) seen.add(slug);
  }
  return [...seen];
}

export function addFollow(value, slug) {
  const follows = parseFollows(value).filter((s) => s !== slug);
  follows.push(slug);
  return follows.slice(-MAX_FOLLOWS);
}

export function unfollowToken(apiKey, contactId, slug) {
  return createHmac('sha256', apiKey).update(`unfollow:${contactId}:${slug}`).digest('hex').slice(0, 32);
}

function tokenMatches(expected, given) {
  const a = Buffer.from(String(expected));
  const b = Buffer.from(String(given || ''));
  return a.length === b.length && timingSafeEqual(a, b);
}

async function resend(apiKey, method, path, body) {
  const response = await fetch(`${API}${path}`, {
    method,
    headers: {
      Authorization: `Bearer ${apiKey}`,
      'Content-Type': 'application/json',
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  let json = null;
  try {
    json = await response.json();
  } catch {}
  return { ok: response.ok, status: response.status, json };
}

async function ensureProperties(apiKey) {
  const listed = await resend(apiKey, 'GET', '/contact-properties');
  if (!listed.ok) throw new Error(`contact-properties ${listed.status}`);
  const keys = new Set((listed.json?.data || []).map((p) => p?.key));
  for (const [key, fallback] of [[FOLLOW_PROPERTY, ''], ['reader_id', 'none']]) {
    if (keys.has(key)) continue;
    const payload = { key, type: 'string' };
    if (fallback) payload.fallback_value = fallback;
    const created = await resend(apiKey, 'POST', '/contact-properties', payload);
    if (!created.ok && created.status !== 409 && created.status !== 422) {
      throw new Error(`create property ${key} ${created.status}`);
    }
  }
}

export async function followersSegmentId(apiKey) {
  const configured = String(process.env.EMAIL_SEGMENT_ID_FOLLOWERS || '').trim();
  if (configured) return configured;
  const listed = await resend(apiKey, 'GET', '/segments');
  if (!listed.ok) throw new Error(`segments ${listed.status}`);
  const found = (listed.json?.data || []).find((s) => s?.name === FOLLOWERS_SEGMENT_NAME);
  if (found?.id) return found.id;
  const created = await resend(apiKey, 'POST', '/segments', { name: FOLLOWERS_SEGMENT_NAME });
  if (!created.ok || !created.json?.id) throw new Error(`create segment ${created.status}`);
  return created.json.id;
}

function propertyValue(contact, key) {
  const prop = contact?.properties?.[key];
  return prop && typeof prop === 'object' ? prop.value : prop;
}

export async function follow(body, apiKey) {
  if (String(body.hp || body.website || '').trim()) return Response.json({ ok: true });

  const email = String(body.email || '').trim().toLowerCase();
  const slug = String(body.slug || '').trim();
  if (!EMAIL_RE.test(email) || email.length > 254) {
    return Response.json({ error: 'invalid_email' }, { status: 400 });
  }
  if (!SLUG_RE.test(slug)) return Response.json({ error: 'invalid_slug' }, { status: 400 });

  try {
    await ensureProperties(apiKey);
    const segmentId = await followersSegmentId(apiKey);
    const existing = await resend(apiKey, 'GET', `/contacts/${encodeURIComponent(email)}`);
    let contactId;
    if (existing.ok && existing.json?.id) {
      contactId = existing.json.id;
      const follows = addFollow(propertyValue(existing.json, FOLLOW_PROPERTY), slug);
      const patched = await resend(apiKey, 'PATCH', `/contacts/${encodeURIComponent(contactId)}`, {
        properties: { [FOLLOW_PROPERTY]: follows.join(',') },
      });
      if (!patched.ok) throw new Error(`update contact ${patched.status}`);
    } else if (existing.status === 404) {
      const created = await resend(apiKey, 'POST', '/contacts', {
        email,
        unsubscribed: false,
        properties: { reader_id: readerIdFor(body.reader_id), [FOLLOW_PROPERTY]: slug },
        segments: [{ id: segmentId }],
      });
      if (!created.ok || !created.json?.id) throw new Error(`create contact ${created.status}`);
      contactId = created.json.id;
    } else {
      throw new Error(`get contact ${existing.status}`);
    }
    const added = await resend(
      apiKey,
      'POST',
      `/contacts/${encodeURIComponent(contactId)}/segments/${encodeURIComponent(segmentId)}`,
    );
    if (!added.ok && added.status !== 409 && added.status !== 422) {
      throw new Error(`add to segment ${added.status}`);
    }
    return Response.json({ ok: true });
  } catch (e) {
    console.error('storyline follow failed', String(e).slice(0, 300));
    return Response.json({ error: 'provider_error' }, { status: 502 });
  }
}

export function page(title, message, status = 200) {
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  return new Response(
    `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex"><title>${esc(title)} · LLM Digest</title>
<style>body{font:16px/1.5 system-ui,sans-serif;max-width:32rem;margin:4rem auto;padding:0 1rem;color:#1a1a1a}a{color:#2563eb}</style>
</head><body><h1>${esc(title)}</h1><p>${esc(message)}</p><p><a href="/storylines">Browse storylines</a> · <a href="/">Live feed</a></p></body></html>`,
    { status, headers: { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store' } },
  );
}

export async function unfollow(url, apiKey) {
  const contactId = url.searchParams.get('c') || '';
  const slug = url.searchParams.get('s') || '';
  const token = url.searchParams.get('t') || '';
  if (!CONTACT_ID_RE.test(contactId) || !(slug === '*' || SLUG_RE.test(slug))
      || !tokenMatches(unfollowToken(apiKey, contactId, slug), token)) {
    return page('Link not recognized', 'This unfollow link is invalid or has expired.', 400);
  }
  try {
    const contact = await resend(apiKey, 'GET', `/contacts/${encodeURIComponent(contactId)}`);
    if (contact.status === 404) return page('Unfollowed', 'You no longer follow any stories by email.');
    if (!contact.ok) throw new Error(`get contact ${contact.status}`);
    const follows = slug === '*'
      ? []
      : parseFollows(propertyValue(contact.json, FOLLOW_PROPERTY)).filter((s) => s !== slug);
    const patched = await resend(apiKey, 'PATCH', `/contacts/${encodeURIComponent(contactId)}`, {
      properties: { [FOLLOW_PROPERTY]: follows.join(',') },
    });
    if (!patched.ok) throw new Error(`update contact ${patched.status}`);
    if (!follows.length) {
      const segmentId = await followersSegmentId(apiKey);
      await resend(apiKey, 'DELETE', `/contacts/${encodeURIComponent(contactId)}/segments/${encodeURIComponent(segmentId)}`);
    }
    return page(
      'Unfollowed',
      slug === '*' || !follows.length
        ? 'You no longer follow any stories by email.'
        : 'You will no longer get emails about this story. Other stories you follow are unchanged.',
    );
  } catch (e) {
    console.error('storyline unfollow failed', String(e).slice(0, 300));
    return page('Something went wrong', 'We could not update your follows. Please try the link again shortly.', 502);
  }
}
