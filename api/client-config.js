export default async function handler(req, res) {
  if (req.method !== 'GET') {
    res.setHeader('Allow', 'GET');
    return res.status(405).json({ error: 'method_not_allowed' });
  }

  const key = String(process.env.POSTHOG_PROJECT_API_KEY || '').trim();
  const host = String(process.env.POSTHOG_HOST || 'https://us.i.posthog.com').trim();
  const enabled = String(process.env.POSTHOG_ENABLED || '').trim() === '1' && !!key;

  // Public Telegram channel for the daily digest; subscribe CTAs only render
  // when this is configured (e.g. https://t.me/your_channel).
  const digestTelegram = String(process.env.DIGEST_TELEGRAM_URL || '').trim();
  // Optional external email-digest signup page (e.g. an RSS-to-email form); the
  // subscribe menu shows an outbound email link only when this is configured.
  const emailSignup = String(process.env.DIGEST_EMAIL_SIGNUP_URL || '').trim();
  // In-page subscribe (POST /api/subscribe → Resend audience). Enabled when the
  // same provider creds the send workflow uses are present on the deploy, so the
  // client renders the inline email form instead of an outbound link.
  const emailSubscribeEnabled =
    !!String(process.env.EMAIL_API_KEY || '').trim() &&
    !!String(process.env.EMAIL_AUDIENCE_ID || '').trim();

  return res.status(200).json({
    posthog: {
      enabled,
      host,
      project_api_key: enabled ? key : null,
    },
    digest: {
      telegram_url: /^https:\/\//.test(digestTelegram) ? digestTelegram : null,
      email_signup_url: /^https:\/\//.test(emailSignup) ? emailSignup : null,
      email_subscribe_enabled: emailSubscribeEnabled,
    },
  });
}
