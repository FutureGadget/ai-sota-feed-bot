// POST /api/subscribe { email, hp? } — registers a self-serve subscriber by
// adding them to your Resend contacts.
//
// Resend's contacts are global (created at POST /contacts). The API key alone
// is required, but we also add the contact to EMAIL_SEGMENT_ID (the segment the
// daily/weekly broadcast sends to) via the `segments` array — otherwise the
// contact is created segment-less and the broadcast fails with 422 "...has no
// contacts". Per-digest selection rides on Resend Topics: EMAIL_TOPIC_ID_DAILY
// and EMAIL_TOPIC_ID_WEEKLY are separate topics, so a "weekly only" signup opts
// the contact OUT of the daily topic while staying in the weekly one (Resend's
// preference page then manages it). Falls back to a single legacy EMAIL_TOPIC_ID.
//
// The key is read server-side only (never reaches the browser). Honeypot +
// validation guard abuse. With no EMAIL_API_KEY the endpoint returns 503 and
// the client hides the form.

import { follow, page, unfollow } from '../lib/follow.js';
import { readerIdFor } from '../lib/reader-id.js';

export { readerIdFor };

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
function createContact(apiKey, payload) {
  return fetch('https://api.resend.com/contacts', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${apiKey}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });
}

// GET /api/subscribe?c=&s=&t= is a signed storyline unfollow link
// (lib/follow.js); plain GETs have nothing to serve.
export async function GET(request) {
  const apiKey = String(process.env.EMAIL_API_KEY || '').trim();
  if (!apiKey) return page('Unavailable', 'Story follow emails are not configured.', 503);
  return unfollow(new URL(request.url), apiKey);
}

export async function POST(request) {

  const apiKey = String(process.env.EMAIL_API_KEY || '').trim();
  const url = new URL(request.url);
  // One-click unsubscribe (RFC 8058) posts to the List-Unsubscribe URL.
  if (url.searchParams.has('t')) {
    if (!apiKey) return page('Unavailable', 'Story follow emails are not configured.', 503);
    return unfollow(url, apiKey);
  }
  if (!apiKey) {
    return Response.json({ error: 'not_configured' }, { status: 503 });
  }

  let body;
  try {
    body = await request.json();
  } catch {
    body = {};
  }
  body = body || {};
  if (body.action === 'follow') return follow(body, apiKey);

  // Honeypot: a real user leaves this empty; bots fill every field. Report
  // success without touching the provider so the bot learns nothing.
  if (String(body.hp || body.website || '').trim()) {
    return Response.json({ ok: true });
  }

  const email = String(body.email || '').trim().toLowerCase();
  if (!EMAIL_RE.test(email) || email.length > 254) {
    return Response.json({ error: 'invalid_email' }, { status: 400 });
  }

  const payload = { email, unsubscribed: false, properties: { reader_id: readerIdFor(body.reader_id) } };
  // Per-digest selection. Daily and weekly are separate Resend Topics so a reader
  // can take "weekly only — less email": opted into the weekly topic, opted OUT
  // of the daily one (Resend then suppresses the daily broadcast for them, and
  // its hosted preference page manages the choice thereafter). Default = both.
  // Falls back to the legacy single EMAIL_TOPIC_ID (both digests, one topic)
  // when the per-kind ids aren't configured.
  const dailyTopic = String(process.env.EMAIL_TOPIC_ID_DAILY || '').trim();
  const weeklyTopic = String(process.env.EMAIL_TOPIC_ID_WEEKLY || '').trim();
  const weeklyOnly = body.weekly_only === true || String(body.weekly_only || '') === 'true';
  const topics = [];
  if (dailyTopic) topics.push({ id: dailyTopic, subscription: weeklyOnly ? 'opt_out' : 'opt_in' });
  if (weeklyTopic) topics.push({ id: weeklyTopic, subscription: 'opt_in' });
  if (!topics.length) {
    const legacyTopic = String(process.env.EMAIL_TOPIC_ID || '').trim();
    if (legacyTopic) topics.push({ id: legacyTopic, subscription: 'opt_in' });
  }
  if (topics.length) payload.topics = topics;
  // Place the contact into the segment the daily/weekly broadcast targets
  // (publish_email.py sends to EMAIL_SEGMENT_ID). Without this the contact is
  // created segment-less and a broadcast to that segment fails with
  // 422 "...has no contacts". Mirror the broadcast's env resolution exactly.
  const segmentId = String(process.env.EMAIL_SEGMENT_ID || process.env.EMAIL_AUDIENCE_ID || '').trim();
  if (segmentId) payload.segments = [{ id: segmentId }];

  try {
    let r = await createContact(apiKey, payload);
    // A 422 can mean "already a contact" or a rejected custom property (e.g. the
    // `reader_id` property isn't defined yet). Retry once without properties so
    // attribution can never cost a signup; a duplicate stays a 409/422.
    if (r.status === 422) {
      const { properties, ...withoutProperties } = payload;
      r = await createContact(apiKey, withoutProperties);
    }

    // 2xx = added; 409/422 typically means the contact already exists — treat a
    // re-subscribe as success (idempotent) rather than surfacing an error.
    if (r.ok || r.status === 409 || r.status === 422) {
      return Response.json({ ok: true });
    }
    const detail = await r.text().catch(() => '');
    // Surface the upstream status in the Vercel function logs — the usual cause
    // is a "Sending access" API key that can't write contacts (needs Full access).
    console.error('resend create-contact failed', r.status, detail.slice(0, 300));
    return Response.json(
      { error: 'provider_error', status: r.status, detail: detail.slice(0, 200) },
      { status: 502 }
    );
  } catch (e) {
    return Response.json(
      { error: 'provider_unreachable', detail: String(e).slice(0, 200) },
      { status: 502 }
    );
  }
}
