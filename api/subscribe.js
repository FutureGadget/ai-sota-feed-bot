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

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const EMAIL_LANGUAGES = new Set(['en', 'ko', 'ja', 'zh-CN']);

function normalizePreferredLanguage(value) {
  const raw = String(value || '').trim();
  const lower = raw.toLowerCase();
  if (EMAIL_LANGUAGES.has(raw)) return raw;
  if (lower === 'zh-cn') return 'zh-CN';
  if (EMAIL_LANGUAGES.has(lower)) return lower;
  return 'en';
}

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST');
    return res.status(405).json({ error: 'method_not_allowed' });
  }

  const apiKey = String(process.env.EMAIL_API_KEY || '').trim();
  if (!apiKey) {
    return res.status(503).json({ error: 'not_configured' });
  }

  let body = req.body;
  if (typeof body === 'string') {
    try { body = JSON.parse(body); } catch { body = {}; }
  }
  body = body || {};

  // Honeypot: a real user leaves this empty; bots fill every field. Report
  // success without touching the provider so the bot learns nothing.
  if (String(body.hp || body.website || '').trim()) {
    return res.status(200).json({ ok: true });
  }

  const email = String(body.email || '').trim().toLowerCase();
  if (!EMAIL_RE.test(email) || email.length > 254) {
    return res.status(400).json({ error: 'invalid_email' });
  }

  const preferredLanguage = normalizePreferredLanguage(body.language || body.preferred_language);
  const payload = {
    email,
    unsubscribed: false,
    properties: {
      preferred_language: preferredLanguage,
    },
  };
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
    const r = await fetch('https://api.resend.com/contacts', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    // 2xx = added; 409/422 typically means the contact already exists — treat a
    // re-subscribe as success (idempotent) rather than surfacing an error.
    if (r.ok || r.status === 409 || r.status === 422) {
      return res.status(200).json({ ok: true });
    }
    const detail = await r.text().catch(() => '');
    // Surface the upstream status in the Vercel function logs — the usual cause
    // is a "Sending access" API key that can't write contacts (needs Full access).
    console.error('resend create-contact failed', r.status, detail.slice(0, 300));
    return res.status(502).json({ error: 'provider_error', status: r.status, detail: detail.slice(0, 200) });
  } catch (e) {
    return res.status(502).json({ error: 'provider_unreachable', detail: String(e).slice(0, 200) });
  }
}
