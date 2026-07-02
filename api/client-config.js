export default async function handler(req, res) {
  if (req.method !== 'GET') {
    res.setHeader('Allow', 'GET');
    return res.status(405).json({ error: 'method_not_allowed' });
  }

  const defaultPostHogKey = 'phc_frYL2od402eAmmxvKFZXbb4pbLNCZpI82mPW9VVAOHu';
  const key = String(process.env.POSTHOG_PROJECT_API_KEY || defaultPostHogKey).trim();
  const host = String(process.env.POSTHOG_HOST || 'https://us.i.posthog.com').trim();
  const enabledFlag = String(process.env.POSTHOG_ENABLED || '1').trim().toLowerCase();
  const enabled = !['0', 'false', 'off'].includes(enabledFlag) && !!key;

  // Optional external email-digest signup page (e.g. an RSS-to-email form); the
  // subscribe menu shows an outbound email link only when this is configured.
  const emailSignup = String(process.env.DIGEST_EMAIL_SIGNUP_URL || '').trim();
  // In-page subscribe (POST /api/subscribe → Resend contacts). Resend contacts
  // are global, so registration needs only the API key — no audience/segment id
  // (a segment id is a send-time concern). Enabled when the key is present.
  const emailSubscribeEnabled = !!String(process.env.EMAIL_API_KEY || '').trim();

  return res.status(200).json({
    posthog: {
      enabled,
      host,
      defaults: '2026-05-30',
      project_api_key: enabled ? key : null,
    },
    digest: {
      email_signup_url: /^https:\/\//.test(emailSignup) ? emailSignup : null,
      email_subscribe_enabled: emailSubscribeEnabled,
    },
  });
}
