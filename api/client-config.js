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
  // Optional email-digest signup page (e.g. a Buttondown/RSS-to-email form);
  // the subscribe menu shows an email option only when this is configured.
  const emailSignup = String(process.env.DIGEST_EMAIL_SIGNUP_URL || '').trim();

  return res.status(200).json({
    posthog: {
      enabled,
      host,
      project_api_key: enabled ? key : null,
    },
    digest: {
      telegram_url: /^https:\/\//.test(digestTelegram) ? digestTelegram : null,
      email_signup_url: /^https:\/\//.test(emailSignup) ? emailSignup : null,
    },
  });
}
