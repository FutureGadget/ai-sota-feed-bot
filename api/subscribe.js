// POST /api/subscribe { email, hp? } — registers a self-serve subscriber by
// adding them to your Resend contacts.
//
// Resend's contacts are global (created at POST /contacts) — registration needs
// NO audience/segment id, only the API key. "Audiences" were renamed to
// Segments and only matter at send time (to choose broadcast recipients).
// Optionally opt the contact into a Topic (EMAIL_TOPIC_ID) so Resend's
// preference page can manage per-topic unsubscribe.
//
// The key is read server-side only (never reaches the browser). Honeypot +
// validation guard abuse. With no EMAIL_API_KEY the endpoint returns 503 and
// the client hides the form.

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

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

  const payload = { email, unsubscribed: false };
  const topicId = String(process.env.EMAIL_TOPIC_ID || '').trim();
  if (topicId) payload.topics = [{ id: topicId, status: 'opt_in' }];

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
