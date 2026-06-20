// POST /api/subscribe { email, hp? } — adds an address to the Resend audience.
//
// The Resend API key is read server-side only and never reaches the browser
// (the whole reason the signup goes through our function instead of a client
// call). The provider owns the subscriber list, unsubscribe, and compliance;
// no email address is stored in this repo. Single opt-in: Resend adds the
// contact directly and its broadcasts carry the unsubscribe link + honor the
// `unsubscribed` flag. (A double opt-in confirmation step is a possible
// follow-up — it would send a confirm email before flipping the contact live.)
//
// Gating mirrors the rest of the stack: with no EMAIL_API_KEY / EMAIL_AUDIENCE_ID
// the endpoint returns 503 not_configured and the client hides the form.

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST');
    return res.status(405).json({ error: 'method_not_allowed' });
  }

  const apiKey = String(process.env.EMAIL_API_KEY || '').trim();
  const audienceId = String(process.env.EMAIL_AUDIENCE_ID || '').trim();
  if (!apiKey || !audienceId) {
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

  try {
    const r = await fetch(`https://api.resend.com/audiences/${audienceId}/contacts`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, unsubscribed: false }),
    });

    // 2xx = added; 409/422 typically means the contact already exists — treat a
    // re-subscribe as success (idempotent) rather than surfacing an error.
    if (r.ok || r.status === 409 || r.status === 422) {
      return res.status(200).json({ ok: true });
    }
    const detail = await r.text().catch(() => '');
    return res.status(502).json({ error: 'provider_error', status: r.status, detail: detail.slice(0, 200) });
  } catch (e) {
    return res.status(502).json({ error: 'provider_unreachable', detail: String(e).slice(0, 200) });
  }
}
